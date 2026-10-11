"""真实文件解析、无效旧文件修复和增量下载的回归检查。"""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

import pytest

from moodle_scraper.downloader import Downloader
from moodle_scraper.files import file_error
from moodle_scraper.http import FakeHttpClient, HttpResponse
from moodle_scraper.scanner import Resource, Scanner

BASE = 'https://moodle.must.edu.mo'


@pytest.mark.parametrize('old', [b'', b'<!DOCTYPE html><html>resource page</html>', b'%PDF-1.4\ncut off'])
def test_repairs_existing_invalid_pdf(tmp_path: Path, pdf_bytes: bytes, old: bytes) -> None:
    target = tmp_path / 'Lecture.pdf'
    target.write_bytes(old)
    client = FakeHttpClient()
    client.add_stream(BASE + '/lecture.pdf', [pdf_bytes])
    downloader = Downloader(client, save_dir=str(tmp_path))
    resources = [Resource('Lecture', BASE + '/lecture.pdf')]
    result = downloader.download_all(resources)
    assert (result.new_count, result.repaired, result.skipped, result.failed) == (1, 1, 0, [])
    assert target.read_bytes() == pdf_bytes
    client.request_log.clear()
    again = downloader.download_all(resources)
    assert (again.new_count, again.skipped) == (0, 1)
    assert client.request_log == []


@pytest.mark.parametrize('data', [b'', b'<!DOCTYPE html><html>Log in</html>', b'%PDF-1.4\ntruncated'])
def test_invalid_response_never_replaces_old_file(tmp_path: Path, data: bytes) -> None:
    original = b'<html>old broken download</html>'
    target = tmp_path / 'Lecture.pdf'
    target.write_bytes(original)
    client = FakeHttpClient()
    client.add_stream(BASE + '/lecture.pdf', [data])
    result = Downloader(client, save_dir=str(tmp_path)).download_all([Resource('Lecture', BASE + '/lecture.pdf')])
    assert result.new_count == 0 and result.failed == ['Lecture']
    assert result.failure_reasons['Lecture']
    assert target.read_bytes() == original
    assert not list(tmp_path.glob('*.part'))


def test_new_html_response_never_creates_pdf(tmp_path: Path) -> None:
    client = FakeHttpClient()
    client.add_stream(BASE + '/lecture.pdf', [b'<!doctype html><html>resource wrapper</html>'])
    result = Downloader(client, save_dir=str(tmp_path)).download_all([Resource('Lecture', BASE + '/lecture.pdf')])
    assert result.failed == ['Lecture']
    assert not (tmp_path / 'Lecture.pdf').exists()


def test_hash_detects_changes_that_keep_pdf_markers(tmp_path: Path, pdf_bytes: bytes) -> None:
    client = FakeHttpClient()
    client.add_stream(BASE + '/lecture.pdf', [pdf_bytes])
    downloader = Downloader(client, save_dir=str(tmp_path))
    resources = [Resource('Lecture', BASE + '/lecture.pdf')]
    downloader.download_all(resources)
    target = tmp_path / 'Lecture.pdf'
    target.write_bytes(pdf_bytes.replace(b'/Type /Page ', b'/Type /Oops '))
    assert file_error(target) is None  # 仅文件头 / EOF 检查不足以发现这类损坏。
    result = downloader.download_all(resources)
    assert result.new_count == result.repaired == 1
    assert target.read_bytes() == pdf_bytes


def test_identical_titles_do_not_overwrite_and_repeat_is_stable(tmp_path: Path, pdf_bytes: bytes) -> None:
    client = FakeHttpClient()
    resources = [Resource('Notes', BASE + f'/file{n}.pdf') for n in (1, 2)]
    for resource in resources:
        client.add_stream(resource.url, [pdf_bytes])
    downloader = Downloader(client, save_dir=str(tmp_path))
    assert downloader.download_all(resources).new_count == 2
    paths = sorted(p.name for p in tmp_path.glob('*.pdf'))
    assert len(paths) == 2 and len(set(paths)) == 2
    client.request_log.clear()
    assert downloader.download_all(list(reversed(resources))).skipped == 2
    assert sorted(p.name for p in tmp_path.glob('*.pdf')) == paths
    assert not client.request_log


def test_missing_file_redownloaded_from_existing_manifest(tmp_path: Path, pdf_bytes: bytes) -> None:
    client = FakeHttpClient()
    client.add_stream(BASE + '/lecture.pdf', [pdf_bytes])
    downloader = Downloader(client, save_dir=str(tmp_path))
    resources = [Resource('Lecture', BASE + '/lecture.pdf')]
    downloader.download_all(resources)
    (tmp_path / 'Lecture.pdf').unlink()
    result = downloader.download_all(resources)
    assert (result.new_count, result.skipped, result.repaired) == (1, 0, 0)


def test_must_resource_wrapper_is_resolved_then_old_html_is_repaired(tmp_path: Path, pdf_bytes: bytes) -> None:
    client = FakeHttpClient()
    course = BASE + '/course/view.php?id=118832'
    wrapper = BASE + '/mod/resource/view.php?id=123'
    file_url = BASE + '/pluginfile.php/6947946/mod_resource/content/1/2_Limits%20and%20Continuity_course_plan.pdf'
    client.add_response(course, HttpResponse(200, '<a href="/mod/resource/view.php?id=123">2_Limits and ContinuityFile</a>', course))
    # 与实际坏文件里的资源正文结构一致，只保留无个人信息的最小结构。
    client.add_response(wrapper, HttpResponse(200,
        f'<section id="region-main"><div class="resourceworkaround"><a href="{file_url}">Download</a></div></section>',
        wrapper, {'Content-Type': 'text/html'}))
    client.add_stream(file_url, [pdf_bytes])
    target = tmp_path / '2_Limits and Continuity.pdf'
    target.write_text('<!DOCTYPE html><html>resource wrapper</html>')
    resources = Scanner(client).scan_course('118832')
    assert resources[0].url == file_url and resources[0].source_url == wrapper
    result = Downloader(client, save_dir=str(tmp_path)).download_all(resources)
    assert result.new_count == result.repaired == 1
    assert target.read_bytes() == pdf_bytes
    assert ('STREAM', wrapper) not in client.request_log
    assert ('STREAM', file_url) in client.request_log


@pytest.mark.parametrize('tag', ['<object data="{url}"></object>', '<iframe src="{url}"></iframe>', '<embed src="{url}">'])
def test_embedded_pdf_links_are_resolved(tag: str) -> None:
    client = FakeHttpClient()
    wrapper = BASE + '/mod/resource/view.php?id=123'
    relative = '/pluginfile.php/1/mod_resource/content/1/slides.pdf'
    client.add_response(wrapper, HttpResponse(200, tag.format(url=relative), wrapper))
    assert Scanner(client).resolve_resource(Resource('Slides', wrapper)).url == BASE + relative


def test_resource_that_redirects_to_binary_keeps_response_filename() -> None:
    client = FakeHttpClient()
    wrapper = BASE + '/mod/resource/view.php?id=1'
    final = BASE + '/pluginfile.php/1/slides.pptx'
    client.add_response(wrapper, HttpResponse(200, '', final, {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'Content-Disposition': "attachment; filename*=UTF-8''Week%201.pptx",
    }))
    resolved = Scanner(client).resolve_resource(Resource('Slides', wrapper))
    assert resolved.url == final and resolved.filename == 'Week 1.pptx'


def test_pptx_is_not_saved_with_pdf_extension(tmp_path: Path) -> None:
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<Types/>')
        archive.writestr('ppt/presentation.xml', '<presentation/>')
    client = FakeHttpClient()
    client.add_stream(BASE + '/slides.pptx', [buffer.getvalue()])
    result = Downloader(client, save_dir=str(tmp_path)).download_all([
        Resource('Slides', BASE + '/slides.pptx', filename='Slides.pptx'),
    ])
    assert result.new_count == 1
    assert (tmp_path / 'Slides.pptx').is_file()
    assert not list(tmp_path.glob('*.pdf'))


def test_failed_resource_is_reported_without_being_written(tmp_path: Path) -> None:
    client = FakeHttpClient()
    result = Downloader(client, save_dir=str(tmp_path)).download_all([
        Resource('Missing', BASE + '/mod/resource/view.php?id=1', error='No file link'),
    ])
    assert result.failed == ['Missing'] and result.new_count == 0
    assert client.request_log == []


def test_folder_and_page_relative_links_are_followed_once() -> None:
    client = FakeHttpClient()
    course = BASE + '/course/view.php?id=1'
    folder = BASE + '/mod/folder/view.php?id=2'
    page = BASE + '/mod/page/view.php?id=3'
    client.add_response(course, HttpResponse(200, '<a href="/mod/folder/view.php?id=2">Folder</a>', course))
    client.add_response(folder, HttpResponse(200, '<a href="/mod/page/view.php?id=3">Page</a>', folder))
    client.add_response(page, HttpResponse(200,
        '<a href="/mod/folder/view.php?id=2">Back</a><a href="/pluginfile.php/9/f.pdf">File</a>', page))
    resources = Scanner(client).scan_course('1')
    assert len(resources) == 1 and resources[0].url == BASE + '/pluginfile.php/9/f.pdf'
    assert client.request_log.count(('GET', folder)) == 1


def test_failed_subpage_is_not_silently_reported_as_up_to_date() -> None:
    client = FakeHttpClient()
    course = BASE + '/course/view.php?id=1'
    client.add_response(course, HttpResponse(200, '<a href="/mod/page/view.php?id=2">Page</a>', course))
    resources = Scanner(client).scan_course('1')
    assert len(resources) == 1 and resources[0].error


def test_filename_with_hash_character_keeps_true_extension() -> None:
    resource = Resource('Slides', BASE + '/download', filename='Week#1.pptx')
    assert Downloader._filename(resource) == 'Slides.pptx'
