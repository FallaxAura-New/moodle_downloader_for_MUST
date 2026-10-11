"""课件内容校验；下载成功与本地跳过使用同一套规则。"""
from __future__ import annotations

import hashlib
from pathlib import Path
import zipfile

from .i18n import t
from .utils import looks_like_html


def file_error(path: Path, filename: str | None = None) -> str | None:
    """返回不可用的原因；None 表示通过文件类型和完整性基础检查。"""
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return t("file.empty")
        with path.open("rb") as stream:
            head = stream.read(4096)
            stream.seek(max(0, path.stat().st_size - 4096))
            tail = stream.read()
        if looks_like_html(head):
            return t("file.html")
        suffix = Path(filename or path.name).suffix.lower()
        if suffix == ".pdf":
            if b"%PDF-" not in head[:1024] or b"%%EOF" not in tail:
                return t("file.invalid_pdf")
        elif suffix in {".pptx", ".docx", ".xlsx", ".zip"}:
            try:
                with zipfile.ZipFile(path) as archive:
                    if archive.testzip() is not None:
                        return t("file.invalid_archive")
                    if suffix != ".zip":
                        prefix = {".pptx": "ppt/", ".docx": "word/", ".xlsx": "xl/"}[suffix]
                        names = archive.namelist()
                        if "[Content_Types].xml" not in names or not any(n.startswith(prefix) for n in names):
                            return t("file.invalid_archive")
            except (OSError, zipfile.BadZipFile, RuntimeError):
                return t("file.invalid_archive")
        elif suffix in {".ppt", ".doc", ".xls"}:
            if not head.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
                return t("file.invalid_office")
        return None
    except OSError:
        return t("file.unreadable")


def file_sha256(path: Path) -> str:
    """流式计算哈希，不把整份课件读入内存。"""
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()
