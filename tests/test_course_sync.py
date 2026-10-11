"""MUST 名称映射、选课和首次 / 后续同步的完整离线流程。"""
from __future__ import annotations

from io import StringIO
from pathlib import Path
import runpy
import sys

from rich.console import Console

import moodle_scraper.__main__ as app
import moodle_scraper.ui as ui_module
from moodle_scraper.config import AppConfig
from moodle_scraper.http import FakeHttpClient, HttpResponse
from moodle_scraper.scanner import CourseInfo, Scanner

BASE = 'https://moodle.must.edu.mo'
SCREENSHOT_COURSES = [
    ('118832', '2609-BE101EX10-C371E1', '大学微积分 I'),
    ('118856', '2609-BE104EX3-2CDA98', '计算机程序设计'),
    ('120070', '2609-BSNN101EX1-6FE48F', '无机与分析化学'),
    ('120178', '2609-CHNRW001D52-41FD4C', '中文阅读与写作'),
    ('121506', '2609-ENG003D13-CFA530', '英文 III'),
    ('121558', '2609-ENG004D13-17F09B', '英文 IV'),
    ('121706', '2609-GCLBL001D02-8BD6F5', '宪法与基本法概论'),
    ('122014', '2609-GMS001D01-11C484', '科技大师讲座'),
    ('122016', '2609-GMS001D01-D3770E', '科技大师讲座'),
    ('122408', '2609-GUL001D02-1C68BC', '大学生活'),
]


def test_screenshot_courses_show_chinese_names_and_keep_codes() -> None:
    config = AppConfig.load()
    client = FakeHttpClient()
    html = ''.join(f'<a href="/course/view.php?id={cid}">{code}</a>' for cid, code, _ in SCREENSHOT_COURSES)
    client.add_response(BASE + '/my/', HttpResponse(200, html, BASE + '/my/'))
    courses = Scanner(client, course_names=config.course_names).list_courses()
    by_id = {course.id: course for course in courses}
    assert len(courses) == 10
    for cid, code, name in SCREENSHOT_COURSES:
        assert by_id[cid].name == name and by_id[cid].code == code
    assert by_id['122014'].code != by_id['122016'].code


def test_bom_config_loads_course_names_and_other_options(tmp_path: Path) -> None:
    config = tmp_path / 'config.toml'
    config.write_text('[download]\nmax_workers = 3\n[course_names]\n"1" = "大学生活"\n', encoding='utf-8-sig')
    loaded = AppConfig.load(config)
    assert loaded.course_names == {'1': '大学生活'} and loaded.max_workers == 3


def test_unknown_course_uses_full_page_label_instead_of_first_short_link() -> None:
    client = FakeHttpClient()
    client.add_response(BASE + '/my/', HttpResponse(200,
        '<a href="/course/view.php?id=1">2609-NEW001-ABCDEF</a>'
        '<a href="/course/view.php?id=1">NEW COURSE(新课程) - 2609-NEW001-ABCDEF</a>', BASE + '/my/'))
    courses = Scanner(client).list_courses()
    assert len(courses) == 1 and '新课程' in courses[0].name
    assert courses[0].code == '2609-NEW001-ABCDEF'


def test_picker_renders_name_code_and_id_and_accepts_all(monkeypatch) -> None:
    stream = StringIO()
    monkeypatch.setattr(ui_module, 'console', Console(file=stream, width=180, force_terminal=False))
    monkeypatch.setattr('builtins.input', lambda _: '0')
    courses = [CourseInfo(cid, name, '', code) for cid, code, name in SCREENSHOT_COURSES]
    assert app._show_course_table(courses, 'Courses', allow_all=True) == 'all'
    rendered = stream.getvalue()
    assert '大学微积分 I' in rendered and '2609-BE101EX10-C371E1' in rendered and '118832' in rendered
    assert '同步全部课程' in rendered


def make_client(pdf_bytes: bytes, *, failing_course: bool = False) -> FakeHttpClient:
    client = FakeHttpClient()
    client.add_response(BASE + '/my/', HttpResponse(200,
        '<a href="/course/view.php?id=1">Course A</a>'
        '<a href="/course/view.php?id=2">Course B</a>', BASE + '/my/'))
    for cid in ('1', '2'):
        course_url = BASE + '/course/view.php?id=' + cid
        client.add_response(course_url, HttpResponse(500 if failing_course and cid == '1' else 200,
            f'<h1 class="page-header-heading">Shared Name</h1>'
            f'<a href="/mod/resource/view.php?id={cid}">Lecture</a>', course_url))
        resource_url = BASE + '/mod/resource/view.php?id=' + cid
        file_url = BASE + f'/pluginfile.php/{cid}/mod_resource/content/1/lecture.pdf'
        client.add_response(resource_url, HttpResponse(200,
            f'<div class="resourceworkaround"><a href="{file_url}">PDF</a></div>', resource_url))
        client.add_stream(file_url, [pdf_bytes])
    return client


def install_client(monkeypatch, client: FakeHttpClient) -> None:
    class Auth:
        def __init__(self, *args, **kwargs) -> None:
            pass
        def has_cached_cookies(self) -> bool:
            return True
        def get_authenticated_client(self, **kwargs) -> FakeHttpClient:
            return client
    monkeypatch.setattr(app, 'AuthManager', Auth)
    monkeypatch.setattr(ui_module, 'console', Console(file=StringIO(), width=120))


def test_all_courses_first_repeat_and_missing_or_broken_runs(tmp_path: Path, monkeypatch, pdf_bytes: bytes) -> None:
    monkeypatch.chdir(tmp_path)
    client = make_client(pdf_bytes)
    install_client(monkeypatch, client)
    def unexpected_prompt(*args, **kwargs):
        raise AssertionError('Batch mode should not ask once per course')
    monkeypatch.setattr(app, '_confirm', unexpected_prompt)
    config = AppConfig(max_workers=2)
    assert app.main_impl(config, all_courses=True) == 0
    files = sorted(tmp_path.glob('*/*.pdf'))
    assert len(files) == 2 and files[0].parent != files[1].parent
    assert all(p.read_bytes() == pdf_bytes for p in files)
    assert sum(method == 'STREAM' for method, _ in client.request_log) == 2
    assert config.course_id == '' and config.save_dir == 'downloads'  # 批量处理不污染共享配置。
    client.request_log.clear()
    assert app.main_impl(config, all_courses=True) == 0
    assert not any(method == 'STREAM' for method, _ in client.request_log)
    files[0].unlink()
    files[1].write_text('<html>bad saved page</html>')
    client.request_log.clear()
    assert app.main_impl(config, all_courses=True) == 0
    assert all(p.read_bytes() == pdf_bytes for p in files)
    assert sum(method == 'STREAM' for method, _ in client.request_log) == 2


def test_batch_continues_after_one_course_fails(tmp_path: Path, monkeypatch, pdf_bytes: bytes) -> None:
    monkeypatch.chdir(tmp_path)
    client = make_client(pdf_bytes, failing_course=True)
    install_client(monkeypatch, client)
    banners: list[int] = []
    monkeypatch.setattr(app.RichUI, 'result_banner', lambda self, count: banners.append(count))
    assert app.main_impl(AppConfig(), all_courses=True) == 2
    assert len(list(tmp_path.glob('*/*.pdf'))) == 1
    assert not banners  # 不能把失败批次显示为“全部已是最新”。


def test_single_course_selection_is_still_supported(tmp_path: Path, monkeypatch, pdf_bytes: bytes) -> None:
    monkeypatch.chdir(tmp_path)
    client = make_client(pdf_bytes)
    install_client(monkeypatch, client)
    monkeypatch.setattr('builtins.input', lambda _: '2')
    monkeypatch.setattr(app, '_confirm', lambda _: True)
    assert app.main_impl(AppConfig()) == 0
    assert (tmp_path / 'Shared_Name_2' / 'Lecture.pdf').is_file()
    assert not (tmp_path / 'Shared_Name_1').exists()


def test_main_py_all_flag_reaches_application(monkeypatch) -> None:
    calls: list[dict] = []
    monkeypatch.setattr(app, 'main', lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(sys, 'argv', ['main.py', '--all', '--workers', '3'])
    runpy.run_path(str(Path(__file__).resolve().parents[1] / 'main.py'), run_name='__main__')
    assert calls[0]['all_courses'] is True and calls[0]['workers'] == 3


def test_study_flow_still_bypasses_authentication(tmp_path: Path, monkeypatch) -> None:
    def unexpected_auth(*args, **kwargs):
        raise AssertionError('Local study flow must not log in')
    monkeypatch.setattr(app, 'AuthManager', unexpected_auth)
    assert app.main_impl(AppConfig(), study_root=str(tmp_path)) == 0


def test_unidentified_old_folder_does_not_merge_different_courses(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'Shared_Name').mkdir()
    assert app._course_save_dir('1', 'Shared Name') == 'Shared_Name_1'
    assert app._course_save_dir('2', 'Shared Name') == 'Shared_Name_2'
