"""
downloader

⚠️ 免责声明 / Disclaimer:
   本工具仅供学生下载本人已注册课程的课件。
   This tool is for students to download course materials
   they are enrolled in, for offline study purposes only.
   请遵守所在机构 IT 使用政策。
   Please comply with your institution's IT Acceptable Use Policy.
"""
from __future__ import annotations

from dataclasses import replace
import os
from pathlib import Path
import re
import sys
import traceback
from typing import Literal, Optional

# Windows GBK 终端编码修复
if sys.platform == "win32" and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .auth import AuthManager
from .banner import BANNER_SHOWN_ENV
from .config import AppConfig, config as global_config
from .downloader import Downloader, DownloadResult
from .i18n import DEFAULT_LANGUAGE, resolve_language, set_language, t
from .http import HttpClient
from .scanner import CourseInfo, Scanner
from .ui import RichUI
from .utils import sanitize_filename


def _confirm(prompt: str, default: bool = True) -> bool:
    """Y/n 确认提示"""
    yn = "Y/n" if default else "y/N"
    try:
        ans = input(f"  {prompt} [{yn}] ").strip().lower()
        if not ans:
            return default
        return ans in ("y", "yes")
    except (EOFError, KeyboardInterrupt):
        return default


# ═══════════════════════════════════════════════════════════════
# 子流程
# ═══════════════════════════════════════════════════════════════

def _show_course_table(
    courses: list[CourseInfo], title: str, *, allow_all: bool = False,
) -> CourseInfo | Literal["all"] | None:
    """显示课程表格 → 让用户选课（序号或直接输入 ID）→ 返回选中课程或 None"""
    from rich.table import Table
    from moodle_scraper.ui import console
    console.print()
    table = Table(
        title=title, title_style="bold cyan",
        border_style="dim", header_style="bold blue",
    )
    table.add_column("#", style="dim", width=4)
    table.add_column(t("table.course_name"), style="white")
    table.add_column(t("table.course_code"), style="dim")
    table.add_column(t("table.course_id"), style="yellow")
    if allow_all:
        table.add_row("0", t("table.all_courses"), "—", "—")
    for i, c in enumerate(courses, 1):
        table.add_row(str(i), c.name, c.code or "—", c.id)
    console.print(table)
    console.print()
    try:
        prompt = "table.pick_all_prompt" if allow_all else "table.pick_prompt"
        choice = input(f"  {t(prompt)}").strip()
    except (EOFError, KeyboardInterrupt):
        return None
    if not choice:
        return None
    if allow_all and choice.lower() in {"0", "a", "all"}:
        return "all"
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(courses):
            return courses[idx]
    except ValueError:
        pass
    # 不是有效序号 → 检查输入是否为有效的课程 ID（至少是数字）
    if not choice.isdigit():
        console.print(f"  [red]❌ {t('table.pick_invalid')}[/]")
        return None
    return CourseInfo(id=choice, name=f"Course_{choice}", url="")


def _scanner(client: HttpClient, config: AppConfig) -> Scanner:
    """下载与批量同步共用相同的站点、课程名映射和超时。"""
    return Scanner(
        client, base_url=config.moodle_url,
        course_names=config.course_names, timeout=config.request_timeout,
    )


def _course_save_dir(course_id: str, detected_name: str) -> str:
    """保留已有课程目录；无班级代码的新目录附带 ID，防止同名课程混合。"""
    legacy = detected_name.replace(" ", "_").replace("/", "_")
    has_code = bool(re.search(r"\b\d{4}-[A-Za-z0-9]+-[A-Za-z0-9]+\b", detected_name))
    if has_code and Path(legacy).is_dir() and Path(legacy).name == legacy:
        return legacy
    name = sanitize_filename(detected_name).replace(" ", "_").strip(". ")
    if not has_code:
        name = f"{name}_{course_id}"
    return name


def _download_course(
    ui: RichUI, client: HttpClient, course_id: str, config: AppConfig, *, confirm: bool,
) -> DownloadResult | None:
    """单门课的公共执行路径；交互单选与批量同步只在确认方式上不同。"""
    course_config = replace(config, course_id=course_id)
    scanner = _scanner(client, course_config)
    ui.status("📋", t("flow.detecting_course", course_id=course_id))
    detected_name = scanner.fetch_course_name(course_id)
    course_config.course_name = detected_name
    course_config.save_dir = _course_save_dir(course_id, detected_name)

    ui.status("🔍", t("flow.scanning"))
    items = scanner.scan_course(
        course_id, keywords=config.file_keywords, extensions=config.file_extensions,
    )
    if not items:
        ui.status("❓", t("flow.no_resources"))
        return DownloadResult()

    ui.show_scan_results(items)
    if confirm and not _confirm(t("flow.confirm_download", count=len(items))):
        ui.status("⏩", t("flow.cancelled"))
        return None
    progress = ui.create_progress()
    task_id = progress.add_task(f"📥 {t('flow.downloading')}", total=len(items))
    downloader = Downloader(
        client, save_dir=course_config.save_dir,
        max_workers=config.max_workers, chunk_size=config.download_chunk_size,
        timeout=config.request_timeout,
        on_progress=lambda completed, total, message: progress.update(
            task_id, completed=completed, total=total,
            description=f"📥 {message}" if message else None,
        ),
    )
    with progress:
        return downloader.download_all(items)


def _report_download(ui: RichUI, result: DownloadResult) -> None:
    failed = [
        f"{name}: {result.failure_reasons[name]}" if result.failure_reasons.get(name) else name
        for name in result.failed
    ]
    ui.download_summary(result.new_count, result.total, failed)
    if result.repaired:
        ui.status("🔧", t("flow.repaired", count=result.repaired))
    if result.failed:
        ui.status("⚠️", t("flow.partial_failure", count=len(result.failed)))
    elif result.total:
        ui.result_banner(result.new_count)


def _download_course_by_id(ui: RichUI, client: HttpClient, course_id: str, config: AppConfig) -> int:
    try:
        result = _download_course(ui, client, course_id, config, confirm=True)
    except Exception as exc:
        ui.show_error(t("flow.scan_failed_title"), str(exc))
        return 1
    if result is None:
        return 0
    _report_download(ui, result)
    return 2 if result.failed else 0


def _sync_courses(ui: RichUI, client: HttpClient, courses: list[CourseInfo], config: AppConfig) -> int:
    """仅同步已注册课程；一门课失败不会中断剩余课程，最终如实汇总。"""
    totals = DownloadResult()
    failed_courses: list[str] = []
    ui.status("📚", t("flow.sync_start", count=len(courses)))
    for number, course in enumerate(courses, 1):
        ui.status("📚", t(
            "flow.sync_course", number=number, total=len(courses),
            name=course.name, course_id=course.id,
        ))
        try:
            result = _download_course(ui, client, course.id, config, confirm=False)
            if result is None:
                continue
            totals.total += result.total
            totals.new_count += result.new_count
            totals.skipped += result.skipped
            totals.repaired += result.repaired
            for name in result.failed:
                key = f"{course.name} ({course.id}) / {name}"
                totals.failed.append(key)
                totals.failure_reasons[key] = result.failure_reasons.get(name, "")
        except Exception as exc:
            failed_courses.append(f"{course.name} ({course.id})")
            ui.show_error(course.name, str(exc))
    # 课程扫描失败时不能展示“全部已是最新”的成功横幅。
    if failed_courses:
        ui.download_summary(totals.new_count, totals.total, totals.failed)
    else:
        _report_download(ui, totals)
    ui.status("⚠️" if failed_courses or totals.failed else "✅", t(
        "flow.sync_done", count=len(courses), failed_courses=len(failed_courses),
        downloaded=totals.new_count, skipped=totals.skipped, failed=len(totals.failed),
    ))
    return 2 if failed_courses or totals.failed else 0


def _list_courses(ui: RichUI, client: HttpClient, config: AppConfig, *, all_courses: bool = False) -> int:
    scanner = _scanner(client, config)
    courses = scanner.list_courses()
    if not courses:
        ui.show_error(t("flow.no_courses_title"), t("flow.no_courses_detail"))
        return 1
    if all_courses:
        return _sync_courses(ui, client, courses, config)
    picked = _show_course_table(
        courses, f"📚 {t('flow.enrolled_title', count=len(courses))}", allow_all=True,
    )
    if picked == "all":
        return _sync_courses(ui, client, courses, config)
    if picked is None:
        return 0
    return _download_course_by_id(ui, client, picked.id, config)


def _discover_courses(
    ui: RichUI, client, config: AppConfig,
    start_id: int, end_id: int,
) -> int:
    """扫描 ID 范围 → 列出结果 → 选一门下载"""
    if start_id <= 0 or end_id <= 0 or end_id < start_id:
        ui.show_error(t("flow.invalid_range_title"), t("flow.invalid_range_detail"))
        return 1
    total = end_id - start_id + 1
    scanner = _scanner(client, config)
    progress = ui.create_progress()
    task_id = progress.add_task(f"🔍 {t('flow.discover_scanning')}", total=total)

    def on_progress(done: int, _total: int, _cid: int):
        progress.update(
            task_id, completed=done,
            description=f"🔍 {t('flow.discover_trying', course_id=_cid)}",
        )

    with progress:
        courses = scanner.discover_courses(
            start_id, end_id,
            max_workers=config.max_workers,
            on_progress=on_progress,
        )

    if not courses:
        ui.show_error(
            t("flow.discover_none_title"),
            t("flow.discover_none_detail", start=start_id, end=end_id),
        )
        return 1
    picked = _show_course_table(courses, f"🔍 {t('flow.discover_found_title', count=len(courses))}")
    if picked is None or picked == "all":
        return 0
    return _download_course_by_id(ui, client, picked.id, config)


# ═══════════════════════════════════════════════════════════════
# 学习 / Agent 集成（操作已下载的本地文件，无需登录）
# ═══════════════════════════════════════════════════════════════

def _study_flow(
    ui: RichUI,
    *,
    root: str,
    export_vault_dir: Optional[str] = None,
    notebook_path: Optional[str] = None,
    course: Optional[str] = None,
    days: int = 7,
    overwrite: bool = False,
    copy_files: bool = False,
) -> int:
    """索引本地课件 → 可选导出 Obsidian / 生成复习 notebook"""
    from pathlib import Path

    from .study import (
        INDEX_FILENAME,
        build_index,
        build_revision_notebook,
        export_vault,
        save_index,
    )

    root_path = Path(root).resolve()

    ui.status("🔍", t("study.indexing", root=root_path))
    try:
        index = build_index(root_path)
    except Exception as e:
        ui.show_error(t("study.failed_title"), str(e))
        return 1

    materials = index.all_materials()
    if not materials:
        ui.status("❓", t("study.no_materials"))
        return 0

    ui.status("📚", t("study.index_done", courses=len(index.courses), files=len(materials)))

    index_path = root_path / INDEX_FILENAME
    try:
        save_index(index, index_path)
        ui.status("📌", t("study.index_saved", path=index_path))
    except Exception as e:
        ui.show_error(t("study.failed_title"), str(e))
        return 1

    # ── 导出 Obsidian 知识库 ──────────────────────────
    if export_vault_dir:
        ui.status("📝", t("study.exporting", vault=export_vault_dir))
        try:
            result = export_vault(
                index, export_vault_dir,
                overwrite=overwrite, copy_files=copy_files,
            )
        except Exception as e:
            ui.show_error(t("study.failed_title"), str(e))
            return 1
        ui.status("✅", t(
            "study.export_done",
            notes=result.notes_written, courses=result.courses, skipped=result.skipped,
        ))
        if result.files_copied:
            ui.status("📦", t("study.export_copied", count=result.files_copied))
        ui.status("👉", t("study.export_hint"))

    # ── 生成复习 notebook ─────────────────────────────
    if notebook_path:
        ui.status("📓", t("study.notebook_building"))
        try:
            written = build_revision_notebook(index, notebook_path, course=course, days=days)
        except Exception as e:
            ui.show_error(t("study.failed_title"), str(e))
            return 1
        ui.status("✅", t("study.notebook_done", path=written))

    ui.status("🌐", t("study.mcp_hint"))
    return 0


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

def main_impl(
    config: AppConfig,
    *,
    course_id: Optional[str] = None,
    all_courses: bool = False,
    workers: Optional[int] = None,
    discover_range: Optional[str] = None,
    browser: str = "",
    lang: str = "",
    study_root: Optional[str] = None,
    export_vault_dir: Optional[str] = None,
    notebook_path: Optional[str] = None,
    days: int = 7,
    overwrite: bool = False,
    copy_files: bool = False,
) -> int:
    """主流程 — 返回退出码 (0=成功)"""
    if course_id is not None:
        config.course_id = course_id
    if workers is not None:
        config.max_workers = workers
    if browser:
        config.browser = browser
    if lang:
        config.language = lang

    # 解析界面语言（--lang 优先于 config.toml；无法识别时回退默认并提示）
    requested_lang = (config.language or "").strip()
    resolved_lang = resolve_language(requested_lang) if requested_lang else DEFAULT_LANGUAGE
    unsupported_lang = requested_lang if resolved_lang is None else ""
    set_language(resolved_lang or DEFAULT_LANGUAGE)

    # 解析 discover 范围（必须由 --discover start-end 指定）
    discover_start, discover_end = 0, 0
    if discover_range:
        try:
            parts = discover_range.split("-")
            discover_start = int(parts[0])
            discover_end = int(parts[1]) if len(parts) > 1 else 0
        except (ValueError, IndexError):
            discover_start, discover_end = 0, 0

    ui = RichUI(config)
    if os.environ.get(BANNER_SHOWN_ENV) != "1":
        ui.welcome()
    if unsupported_lang:
        ui.status("⚠️", t("lang.unsupported", lang=unsupported_lang))

    # ── 学习 / Agent 集成：只读本地文件，在认证之前短路返回 ──
    if study_root is not None or export_vault_dir or notebook_path:
        return _study_flow(
            ui,
            root=study_root or ".",
            export_vault_dir=export_vault_dir,
            notebook_path=notebook_path,
            course=config.course_id or None,
            days=days,
            overwrite=overwrite,
            copy_files=copy_files,
        )

    auth = AuthManager(config, on_status=ui.status)

    # ── 认证 ──────────────────────────────────────────
    cookies_exist = auth.has_cached_cookies()
    if not cookies_exist:
        if not _confirm(t("flow.confirm_login")):
            ui.status("👋", t("flow.cancelled"))
            return 0

    client = auth.get_authenticated_client(use_cached_first=cookies_exist)
    if not client:
        ui.show_error(t("flow.auth_failed_title"), t("flow.auth_failed_detail"))
        return 1

    # ── 分发 ──────────────────────────────────────────
    if discover_range is not None:
        return _discover_courses(ui, client, config, discover_start, discover_end)

    if all_courses:
        return _list_courses(ui, client, config, all_courses=True)

    # 命令行传了 course_id → 直接下载
    if config.course_id:
        return _download_course_by_id(ui, client, config.course_id, config)

    # 默认流程：列出已注册课程 → 用户选择 → 下载
    return _list_courses(ui, client, config)


def main(
    course_id: Optional[str] = None,
    all_courses: bool = False,
    workers: Optional[int] = None,
    discover_range: Optional[str] = None,
    browser: str = "",
    lang: str = "",
    study_root: Optional[str] = None,
    export_vault_dir: Optional[str] = None,
    notebook_path: Optional[str] = None,
    days: int = 7,
    overwrite: bool = False,
    copy_files: bool = False,
) -> None:
    """CLI 入口"""
    exit_code = 1
    try:
        exit_code = main_impl(
            global_config,
            course_id=course_id,
            all_courses=all_courses,
            workers=workers,
            discover_range=discover_range,
            browser=browser,
            lang=lang,
            study_root=study_root,
            export_vault_dir=export_vault_dir,
            notebook_path=notebook_path,
            days=days,
            overwrite=overwrite,
            copy_files=copy_files,
        )
    except KeyboardInterrupt:
        print(f"\n  ⛔ {t('app.user_interrupt')}")
    except Exception:
        print(f"\n  💥 {t('app.unexpected_error')}")
        traceback.print_exc()
    finally:
        input(f"\n  {t('app.press_enter_exit')}")
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
