"""Windows 菜单到真实 CLI 的离线契约；不启动浏览器或下载课件。"""
from __future__ import annotations

from io import StringIO
import json
from pathlib import Path
import runpy
import subprocess
import sys

import pytest
from rich.console import Console

import moodle_scraper.__main__ as app
from moodle_scraper.config import AppConfig
from moodle_scraper.i18n import DEFAULT_LANGUAGE, get_language, set_language
from moodle_scraper import windows_launcher as launcher


@pytest.fixture(autouse=True)
def isolated_menu(monkeypatch):
    monkeypatch.setattr(launcher, "console", Console(file=StringIO(), width=140))
    set_language(DEFAULT_LANGUAGE)
    yield
    set_language(DEFAULT_LANGUAGE)


def answers(monkeypatch, values: list[str]) -> None:
    iterator = iter(values)
    monkeypatch.setattr("builtins.input", lambda _: next(iterator))


def parsed_request(monkeypatch, request: launcher.LaunchRequest) -> dict:
    """运行现有参数解析器，应用入口替换为记录器，避免交互登录。"""
    calls: list[dict] = []
    monkeypatch.setattr(app, "main", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(sys, "argv", ["main.py", *request.arguments])
    runpy.run_path(str(launcher.PROJECT_ROOT / "main.py"), run_name="__main__")
    assert len(calls) == 1
    return calls[0]


@pytest.mark.parametrize(
    "choice,inputs,expected",
    [
        ("1", [], {"all_courses": True}),
        ("2", [], {"course_id": "", "all_courses": False}),
        ("3", ["118832"], {"course_id": "118832"}),
        ("5", ["."], {"study_root": str(launcher.PROJECT_ROOT)}),
        ("6", [".", "My Vault", "y", "y"], {
            "study_root": str(launcher.PROJECT_ROOT),
            "export_vault_dir": str(launcher.PROJECT_ROOT / "My Vault"),
            "copy_files": True, "overwrite": True,
        }),
        ("7", [".", "My Notes.ipynb", "5", "大学微积分 I"], {
            "study_root": str(launcher.PROJECT_ROOT),
            "notebook_path": str(launcher.PROJECT_ROOT / "My Notes.ipynb"),
            "days": 5, "course_id": "大学微积分 I",
        }),
    ],
)
def test_menu_actions_reach_existing_cli_parser(monkeypatch, choice, inputs, expected) -> None:
    answers(monkeypatch, inputs)
    request = launcher._request(choice, launcher.SessionOptions(browser="edge", language="en", workers=8))
    assert request is not None and not request.mcp
    actual = parsed_request(monkeypatch, request)
    for key, value in expected.items():
        assert actual[key] == value
    assert actual["browser"] == "edge" and actual["lang"] == "en" and actual["workers"] == 8


def test_blank_notebook_course_overrides_fixed_config_course(monkeypatch) -> None:
    answers(monkeypatch, [".", "revision.ipynb", "", ""])
    request = launcher._request("7", launcher.SessionOptions())
    actual = parsed_request(monkeypatch, request)
    assert actual["course_id"] == "" and actual["days"] == 7


def test_notebook_rejects_out_of_range_days(monkeypatch) -> None:
    answers(monkeypatch, [".", "revision.ipynb", "0", "61", "abc", "14", ""])
    actual = parsed_request(monkeypatch, launcher._request("7", launcher.SessionOptions()))
    assert actual["days"] == 14


@pytest.mark.parametrize("invalid", ["0", "-1", "--all", "１２３", "118832 & echo injected", '12"34'])
def test_invalid_course_id_cannot_become_an_option_or_shell_command(monkeypatch, invalid) -> None:
    answers(monkeypatch, [invalid, "118832"])
    request = launcher._request("3", launcher.SessionOptions())
    assert request.arguments == ["118832"]


def test_blank_course_id_cancels_without_launching(monkeypatch) -> None:
    answers(monkeypatch, [""])
    assert launcher._request("3", launcher.SessionOptions()) is None


def test_defaults_do_not_overwrite_obsidian_notes_or_copy_files(monkeypatch) -> None:
    answers(monkeypatch, [".", "vault", "", ""])
    actual = parsed_request(monkeypatch, launcher._request("6", launcher.SessionOptions()))
    assert not actual["copy_files"] and not actual["overwrite"]


def test_settings_persist_across_actions_and_reset_to_config(monkeypatch) -> None:
    config = AppConfig(browser="firefox", language="zh", max_workers=3)
    monkeypatch.setattr(launcher.AppConfig, "load", lambda: config)
    calls: list[launcher.LaunchRequest] = []
    monkeypatch.setattr(launcher, "_run", lambda request: calls.append(request) or 0)
    answers(monkeypatch, [
        "4", "chrome", "en", "8", "1", "2",
        "4", "default", "default", "default", "1", "0",
    ])
    assert launcher.main([]) == 0
    assert calls[0].arguments == ["--all", "--browser", "chrome", "--lang", "en", "--workers", "8"]
    assert calls[1].arguments == ["", "--browser", "chrome", "--lang", "en", "--workers", "8"]
    assert calls[2].arguments == ["--all"]
    assert (config.browser, config.language, config.max_workers) == ("firefox", "zh", 3)
    assert get_language() == "zh"


def test_settings_reject_invalid_inputs_before_launch(monkeypatch) -> None:
    options = launcher.SessionOptions()
    answers(monkeypatch, ["bad", "edge", "unknown", "en", "0", "-1", "8"])
    launcher._settings(options, AppConfig())
    assert options == launcher.SessionOptions("edge", "en", 8)
    assert get_language() == "en"


@pytest.mark.parametrize("returncode", [0, 1, 2])
def test_menu_returns_child_exit_code(monkeypatch, returncode) -> None:
    monkeypatch.setattr(launcher, "_run", lambda request: returncode)
    answers(monkeypatch, ["1", "0"])
    assert launcher.main([]) == returncode


def test_invalid_menu_choice_does_not_launch(monkeypatch) -> None:
    def fail(request):
        pytest.fail("Invalid choice must not launch the CLI")
    monkeypatch.setattr(launcher, "_run", fail)
    answers(monkeypatch, ["bad", "0"])
    assert launcher.main([]) == 0


def test_menu_survives_launch_error(monkeypatch) -> None:
    def fail(request):
        raise OSError("test executable unavailable")
    monkeypatch.setattr(launcher, "_run", fail)
    answers(monkeypatch, ["1", "0"])
    assert launcher.main([]) == 1


def test_mcp_launch_is_explicit_and_uses_server_entry(monkeypatch, tmp_path: Path) -> None:
    answers(monkeypatch, [str(tmp_path), ""])
    assert launcher._request("8", launcher.SessionOptions()) is None
    answers(monkeypatch, [str(tmp_path), "y"])
    request = launcher._request("8", launcher.SessionOptions())
    assert request.mcp and request.arguments == ["--root", str(tmp_path)]
    assert launcher._command(request)[:3] == [sys.executable, "-m", "moodle_scraper.mcp_server"]


def test_help_uses_existing_cli_entry() -> None:
    request = launcher._request("9", launcher.SessionOptions())
    assert request.arguments == ["--help"]
    assert launcher._command(request)[1] == str(launcher.PROJECT_ROOT / "main.py")


def test_cli_passthrough_preserves_arguments_paths_and_exit_status(monkeypatch, tmp_path: Path) -> None:
    args = ["--index", 'C:\\My Courses & Notes', "--notebook", 'C:\\My Courses & Notes\\复习.ipynb', "--days", "5"]
    monkeypatch.chdir(tmp_path)
    def unexpected_input(prompt):
        pytest.fail("CLI passthrough must not open the menu")
    monkeypatch.setattr("builtins.input", unexpected_input)
    def run(command, **kwargs):
        assert command == [sys.executable, str(launcher.PROJECT_ROOT / "main.py"), *args]
        assert kwargs == {"cwd": launcher.PROJECT_ROOT, "check": False}
        return subprocess.CompletedProcess(command, 2)
    monkeypatch.setattr(launcher.subprocess, "run", run)
    assert launcher.main(args) == 2


def test_quoted_input_path_keeps_spaces_and_shell_metacharacters(monkeypatch, tmp_path: Path) -> None:
    folder = tmp_path / "课程 & My Notes"
    answers(monkeypatch, [f'"{folder}"'])
    request = launcher._request("5", launcher.SessionOptions())
    assert request.arguments == ["--index", str(folder)]


def test_mcp_passthrough_emits_only_protocol_and_never_logs_in(tmp_path: Path) -> None:
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
    ]
    result = subprocess.run(
        [sys.executable, "-m", "moodle_scraper.windows_launcher", "--mcp", "--root", str(tmp_path)],
        cwd=launcher.PROJECT_ROOT,
        input="".join(json.dumps(message) + "\n" for message in messages),
        text=True, capture_output=True, timeout=20, check=True,
    )
    responses = [json.loads(line) for line in result.stdout.splitlines()]
    assert [response["id"] for response in responses] == [1, 2]
    assert len(responses[1]["result"]["tools"]) == 5
    assert not result.stderr
