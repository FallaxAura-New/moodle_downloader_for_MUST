"""启动开场与真实流程的衔接；不启动浏览器或访问 Moodle。"""
from __future__ import annotations

from io import BytesIO, StringIO, TextIOWrapper
import os
import subprocess

import pytest
from rich.cells import cell_len
from rich.console import Console

import moodle_scraper.__main__ as app
import moodle_scraper.ui as ui_module
from moodle_scraper import windows_launcher as launcher
from moodle_scraper.banner import BANNER_SHOWN_ENV, print_startup_banner
from moodle_scraper.config import AppConfig
from moodle_scraper.http import FakeHttpClient, HttpResponse
from moodle_scraper.i18n import set_language


@pytest.fixture(autouse=True)
def clean_banner_state(monkeypatch):
    monkeypatch.delenv(BANNER_SHOWN_ENV, raising=False)
    set_language('zh')
    yield
    set_language('zh')


@pytest.mark.parametrize('width', [24, 34, 48, 72, 80, 120])
@pytest.mark.parametrize('language', ['zh', 'en'])
def test_banner_fits_terminal_and_redirects_without_ansi(width, language) -> None:
    output = StringIO()
    set_language(language)
    print_startup_banner(Console(file=output, width=width, color_system=None), AppConfig())
    text = output.getvalue()
    assert '澳門科技大學' in text and 'MUST' in text
    assert '\x1b' not in text
    assert all(cell_len(line) <= width for line in text.splitlines())
    assert 'moodle.must.edu.mo' in text.replace('\n', '')


def test_ascii_console_has_readable_fallback() -> None:
    raw = BytesIO()
    output = TextIOWrapper(raw, encoding='ascii')
    print_startup_banner(Console(file=output, width=80, color_system=None), AppConfig())
    output.flush()
    rendered = raw.getvalue().decode('ascii')
    assert 'MACAU UNIVERSITY' in rendered and 'MUST Moodle Downloader' in rendered
    assert '?' not in rendered


@pytest.mark.parametrize('cached', [False, True])
def test_banner_precedes_login_or_cached_course_picker(monkeypatch, cached) -> None:
    stream = StringIO()
    monkeypatch.setattr(ui_module, 'console', Console(file=stream, width=120, color_system=None))
    client = FakeHttpClient()
    client.add_response('https://moodle.must.edu.mo/my/', HttpResponse(
        200, '<a href="/course/view.php?id=118832">2609-BE101EX10-C371E1</a>',
        'https://moodle.must.edu.mo/my/',
    ))
    class Auth:
        def __init__(self, *args, **kwargs):
            assert '澳門科技大學' in stream.getvalue()
        def has_cached_cookies(self):
            return cached
        def get_authenticated_client(self, **kwargs):
            return client
    monkeypatch.setattr(app, 'AuthManager', Auth)
    prompts = []
    def answer(prompt):
        assert 'MUST Moodle' in stream.getvalue()
        prompts.append(prompt)
        return '' if cached else 'n'
    monkeypatch.setattr('builtins.input', answer)
    assert app.main_impl(AppConfig.load()) == 0
    assert len(prompts) == 1
    if cached:
        assert stream.getvalue().index('澳門科技大學') < stream.getvalue().index('大学微积分 I')
    else:
        assert '登录' in prompts[0]


def test_windows_menu_prints_once_and_child_suppression_is_scoped(monkeypatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(launcher, 'console', Console(file=stream, width=100, color_system=None))
    choices = iter(['1', '2', '0'])
    monkeypatch.setattr('builtins.input', lambda _: next(choices))
    calls = []
    def run(command, **kwargs):
        assert kwargs['env'][BANNER_SHOWN_ENV] == '1'
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)
    monkeypatch.setattr(launcher.subprocess, 'run', run)
    assert launcher.main([]) == 0
    assert stream.getvalue().count('澳門科技大學') == 1
    assert len(calls) == 2 and BANNER_SHOWN_ENV not in os.environ


def test_child_skips_banner_but_still_runs_local_operation(monkeypatch, tmp_path) -> None:
    stream = StringIO()
    monkeypatch.setattr(ui_module, 'console', Console(file=stream, width=100))
    monkeypatch.setenv(BANNER_SHOWN_ENV, '1')
    assert app.main_impl(AppConfig(), study_root=str(tmp_path)) == 0
    assert '澳門科技大學' not in stream.getvalue()
    assert str(tmp_path) in stream.getvalue().replace('\n', '').replace(' ', '')
