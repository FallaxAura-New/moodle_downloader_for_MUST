"""Windows 菜单入口：组装现有 CLI 参数，不复制认证、下载或学习逻辑。"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
from typing import Sequence

from .banner import BANNER_SHOWN_ENV, print_startup_banner
from .config import AppConfig
from .i18n import DEFAULT_LANGUAGE, resolve_language, set_language, t
from .ui import console

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class SessionOptions:
    """只在当前菜单窗口生效；空值沿用 config.toml。"""

    browser: str = ""
    language: str = ""
    workers: int | None = None

    def arguments(self) -> list[str]:
        args: list[str] = []
        if self.browser:
            args.extend(["--browser", self.browser])
        if self.language:
            args.extend(["--lang", self.language])
        if self.workers is not None:
            args.extend(["--workers", str(self.workers)])
        return args


@dataclass
class LaunchRequest:
    arguments: list[str]
    mcp: bool = False
    banner_shown: bool = False


def _command(request: LaunchRequest) -> list[str]:
    if request.mcp:
        return [sys.executable, "-m", "moodle_scraper.mcp_server", *request.arguments]
    return [sys.executable, str(PROJECT_ROOT / "main.py"), *request.arguments]


def _run(request: LaunchRequest) -> int:
    """同一解释器、固定工作目录、参数列表调用，保留空格且不执行 shell 文本。"""
    env = None
    if request.banner_shown and not request.mcp:
        env = {**os.environ, BANNER_SHOWN_ENV: "1"}
    return subprocess.run(_command(request), cwd=PROJECT_ROOT, check=False, env=env).returncode


def _say(key: str, **values: object) -> None:
    console.print(t(key, **values), markup=False)


def _text(key: str, default: str = "") -> str:
    value = input(t(key, default=default)).strip()
    return value or default


def _path(key: str, default: str) -> str:
    value = _text(key, default)
    if len(value) >= 2 and value[0] == value[-1] == '"':
        value = value[1:-1]
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return str(path.resolve())


def _number(
    key: str, default: str = "", *, maximum: int | None = None, cancel: bool = False,
) -> int | None:
    while True:
        value = _text(key, default)
        if cancel and not value:
            return None
        if value.isascii() and value.isdecimal() and len(value) <= 10:
            number = int(value)
            if number > 0 and (maximum is None or number <= maximum):
                return number
        _say("launcher.invalid_number", maximum=maximum or 9999999999)


def _confirm(key: str) -> bool:
    while True:
        value = _text(key, "n").lower()
        if value in {"y", "yes", "是"}:
            return True
        if value in {"n", "no", "否"}:
            return False
        _say("launcher.invalid_yes_no")


def _settings(options: SessionOptions, config: AppConfig) -> None:
    _say("launcher.settings_hint")
    while True:
        browser = _text("launcher.browser_prompt", options.browser or "default").lower()
        if browser in {"default", "chrome", "edge", "firefox"}:
            options.browser = "" if browser == "default" else browser
            break
        _say("launcher.invalid_browser")
    while True:
        language = _text("launcher.language_prompt", options.language or "default").lower()
        if language == "default" or resolve_language(language):
            options.language = "" if language == "default" else resolve_language(language) or ""
            break
        _say("launcher.invalid_language")
    while True:
        workers = _text("launcher.workers_prompt", str(options.workers or "default"))
        if workers.lower() == "default":
            options.workers = None
            break
        if workers.isascii() and workers.isdecimal() and len(workers) <= 10 and int(workers) > 0:
            options.workers = int(workers)
            break
        _say("launcher.invalid_number", maximum=9999999999)
    set_language(resolve_language(options.language or config.language) or DEFAULT_LANGUAGE)
    _say("launcher.settings_saved")


def _request(choice: str, options: SessionOptions) -> LaunchRequest | None:
    args: list[str]
    if choice == "1":
        args = ["--all"]
    elif choice == "2":
        # 空位置参数清除配置中的固定 course_id，确保真正进入课程选择列表。
        args = [""]
    elif choice == "3":
        course_id = _number("launcher.course_prompt", cancel=True)
        if course_id is None:
            return None
        args = [str(course_id)]
    elif choice in {"5", "6", "7"}:
        args = ["--index", _path("launcher.root_prompt", ".")]
        if choice == "6":
            args.extend(["--obsidian", _path("launcher.vault_prompt", "vault")])
            if _confirm("launcher.copy_prompt"):
                args.append("--copy-files")
            if _confirm("launcher.overwrite_prompt"):
                args.append("--overwrite")
        elif choice == "7":
            args.extend(["--notebook", _path("launcher.notebook_prompt", "revision.ipynb")])
            days = _number("launcher.days_prompt", "7", maximum=60)
            args.extend(["--days", str(days)])
            # 留空明确表示全部课程，不受 config.toml 的固定 course_id 影响。
            args.append(_text("launcher.study_course_prompt"))
    elif choice == "8":
        request = LaunchRequest(["--root", _path("launcher.root_prompt", ".")], mcp=True)
        _say("launcher.mcp_hint")
        _say("launcher.mcp_directory", root=PROJECT_ROOT)
        console.print(subprocess.list2cmdline(_command(request)), markup=False)
        return request if _confirm("launcher.mcp_start_prompt") else None
    elif choice == "9":
        args = ["--help"]
    else:
        _say("launcher.invalid_choice")
        return None
    return LaunchRequest(args + options.arguments())


def _menu(options: SessionOptions, config: AppConfig) -> None:
    console.print()
    _say("launcher.title")
    _say(
        "launcher.current_settings",
        browser=options.browser or config.browser or t("launcher.auto"),
        language=options.language or config.language,
        workers=options.workers or config.max_workers,
    )
    for number, key in (
        ("1", "all"), ("2", "list"), ("3", "course"), ("4", "settings"),
        ("5", "index"), ("6", "obsidian"), ("7", "notebook"), ("8", "mcp"),
        ("9", "help"), ("0", "exit"),
    ):
        console.print(f"  {number}. {t('launcher.menu_' + key)}", markup=False)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    # 带参数时直接转交 CLI；MCP 的 stdout 必须只包含协议消息。
    if args:
        request = LaunchRequest(args[1:], mcp=True) if args[0] == "--mcp" else LaunchRequest(args)
        try:
            return _run(request)
        except KeyboardInterrupt:
            return 130
        except OSError as exc:
            print(t("launcher.start_failed", error=exc), file=sys.stderr)
            return 1

    config = AppConfig.load()
    options = SessionOptions()
    set_language(resolve_language(config.language) or DEFAULT_LANGUAGE)
    print_startup_banner(console, config)
    last_code = 0
    try:
        while True:
            _menu(options, config)
            choice = _text("launcher.menu_prompt")
            if choice == "0":
                return last_code
            if choice == "4":
                _settings(options, config)
                continue
            request = _request(choice, options)
            if request is None:
                continue
            request.banner_shown = True
            try:
                last_code = _run(request)
            except KeyboardInterrupt:
                last_code = 130
                _say("app.user_interrupt")
            except OSError as exc:
                last_code = 1
                _say("launcher.start_failed", error=exc)
            _say("launcher.returned", code=last_code)
    except (EOFError, KeyboardInterrupt):
        return last_code


if __name__ == "__main__":
    raise SystemExit(main())
