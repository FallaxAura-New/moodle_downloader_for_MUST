"""课件同步：校验已有文件，补下缺失或损坏文件，原子替换并记录校验和。"""
from __future__ import annotations

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Callable, Optional

from .files import file_error, file_sha256
from .http import HttpClient
from .i18n import t
from .scanner import Resource
from .utils import extract_extension, sanitize_filename

MANIFEST_FILENAME = ".moodle-downloads.json"


@dataclass
class DownloadResult:
    """new_count 包括成功修复的文件；每个资源恰好属于成功、跳过或失败。"""
    new_count: int = 0
    total: int = 0
    skipped: int = 0
    failed: list[str] = field(default_factory=list)
    repaired: int = 0
    failure_reasons: dict[str, str] = field(default_factory=dict)


class Downloader:
    """使用 HttpClient 接口同步文件，不依赖 requests 或终端界面。"""

    def __init__(
        self,
        client: HttpClient,
        *,
        save_dir: str = "downloads",
        max_workers: int = 4,
        chunk_size: int = 8192,
        timeout: int = 30,
        on_progress: Optional[Callable[[int, int, str], None]] = None,
    ) -> None:
        self._client = client
        self._save_dir = Path(save_dir)
        self._max_workers = max_workers
        self._chunk_size = chunk_size
        self._timeout = timeout
        self._on_progress = on_progress or (lambda c, total, m: None)

    def download_all(self, resources: list[Resource]) -> DownloadResult:
        """以本次远端扫描结果为准；存在但无效的本地文件也进入下载队列。"""
        self._save_dir.mkdir(parents=True, exist_ok=True)
        manifest = self._load_manifest()
        paths = self._target_paths(resources, manifest)
        result = DownloadResult(total=len(resources))
        pending: list[tuple[Resource, Path, bool]] = []

        for resource, path in zip(resources, paths):
            if resource.error:
                result.failed.append(resource.name)
                result.failure_reasons[resource.name] = resource.error
                continue
            key = self._key(resource)
            previous = manifest.get(key, {})
            if file_error(path) is None:
                digest = file_sha256(path)
                if (
                    (not previous.get("sha256") or previous["sha256"] == digest)
                    and (not previous.get("url") or previous["url"] == resource.url)
                ):
                    result.skipped += 1
                    manifest[key] = self._record(resource, path, digest)
                    continue
            pending.append((resource, path, path.exists()))

        completed = result.skipped + len(result.failed)
        self._on_progress(completed, result.total, t(
            "downloader.queue_summary", total=result.total,
            existing=result.skipped, pending=len(pending),
        ))
        if pending:
            with ThreadPoolExecutor(max_workers=self._max_workers) as executor:
                futures = {
                    executor.submit(self._download_one, resource, path): (resource, path, existed)
                    for resource, path, existed in pending
                }
                for future in as_completed(futures):
                    resource, path, existed = futures[future]
                    try:
                        digest = future.result()
                        result.new_count += 1
                        result.repaired += int(existed)
                        manifest[self._key(resource)] = self._record(resource, path, digest)
                    except Exception as exc:
                        result.failed.append(resource.name)
                        result.failure_reasons[resource.name] = str(exc)
                    completed += 1
                    self._on_progress(completed, result.total, t(
                        "downloader.progress", done=completed, total=result.total,
                        ok=result.new_count,
                    ))
        self._save_manifest(manifest)
        return result

    def _download_one(self, resource: Resource, path: Path) -> str:
        """验证临时文件后才替换；失败时保留原文件，清理本次临时文件。"""
        fd, temporary = tempfile.mkstemp(prefix=f".{path.stem[:60]}-", suffix=".part", dir=path.parent)
        part_path = Path(temporary)
        try:
            with os.fdopen(fd, "wb") as stream:
                for chunk in self._client.get_stream(
                    resource.url, timeout=self._timeout, chunk_size=self._chunk_size,
                ):
                    stream.write(chunk)
            error = file_error(part_path, path.name)
            if error:
                raise ValueError(error)
            digest = file_sha256(part_path)
            os.replace(part_path, path)
            return digest
        finally:
            part_path.unlink(missing_ok=True)

    @staticmethod
    def _key(resource: Resource) -> str:
        """Moodle 资源入口比标题稳定，不把同名资源误认为同一个文件。"""
        return resource.source_url or resource.url

    @staticmethod
    def _filename(resource: Resource) -> str:
        suffix = Path(resource.filename).suffix.lower() if resource.filename else ""
        suffix = suffix or extract_extension(resource.url)
        name = sanitize_filename(resource.name).strip().rstrip(". ") or "Unnamed_Resource"
        if not name.lower().endswith(suffix.lower()):
            name += suffix
        return name

    def _target_paths(self, resources: list[Resource], manifest: dict) -> list[Path]:
        """稳定复用文件名；同名资源按资源地址加短后缀，避免并行覆盖。"""
        names = [self._filename(resource) for resource in resources]
        counts = Counter(name.casefold() for name in names)
        used = {entry["filename"].casefold(): key for key, entry in manifest.items()}
        paths: list[Path] = []
        for resource, name in zip(resources, names):
            key = self._key(resource)
            saved = manifest.get(key, {}).get("filename")
            if saved and Path(saved).suffix.lower() == Path(name).suffix.lower():
                name = saved
            elif counts[name.casefold()] > 1 or used.get(name.casefold(), key) != key:
                suffix = Path(name).suffix
                digest = hashlib.sha256(key.encode()).hexdigest()[:10]
                name = f"{Path(name).stem}_{digest}{suffix}"
            used[name.casefold()] = key
            paths.append(self._save_dir / name)
        return paths

    @staticmethod
    def _record(resource: Resource, path: Path, digest: str) -> dict:
        return {"filename": path.name, "url": resource.url, "size": path.stat().st_size, "sha256": digest}

    def _load_manifest(self) -> dict:
        try:
            payload = json.loads((self._save_dir / MANIFEST_FILENAME).read_text(encoding="utf-8"))
            entries = payload.get("files", {})
            if not isinstance(entries, dict):
                return {}
            # 不信任记录中的路径，记录只能引用当前课程目录里的单个文件。
            return {
                key: value for key, value in entries.items()
                if isinstance(value, dict) and isinstance(value.get("filename"), str)
                and value["filename"] not in {"", ".", ".."}
                and Path(value["filename"]).name == value["filename"]
                and "/" not in value["filename"] and "\\" not in value["filename"]
            }
        except (OSError, ValueError, AttributeError):
            return {}

    def _save_manifest(self, files: dict) -> None:
        target = self._save_dir / MANIFEST_FILENAME
        fd, temporary = tempfile.mkstemp(prefix=".moodle-downloads-", suffix=".part", dir=self._save_dir)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump({"version": 1, "files": files}, stream, ensure_ascii=False, indent=2)
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
