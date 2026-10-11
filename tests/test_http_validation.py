"""用响应替身验证生产 HTTP 适配器，不访问真实 Moodle。"""
from __future__ import annotations

import pytest
import requests

from moodle_scraper.http import RequestsHttpClient


class Response:
    def __init__(self, data: bytes, *, status: int = 200, headers: dict | None = None,
                 url: str = 'https://moodle.must.edu.mo/pluginfile.php/1/file.pdf') -> None:
        self.data = data
        self.status_code = status
        self.headers = headers or {}
        self.url = url
        self.closed = False
        self.text_read = False

    def __enter__(self) -> Response:
        return self

    def __exit__(self, *args: object) -> None:
        self.closed = True

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    @property
    def text(self) -> str:
        self.text_read = True
        return self.data.decode(errors='replace')

    def iter_content(self, chunk_size: int):
        for offset in range(0, len(self.data), chunk_size):
            yield self.data[offset:offset + chunk_size]


def client_for(monkeypatch, response: Response) -> RequestsHttpClient:
    client = RequestsHttpClient()
    monkeypatch.setattr(client._session, 'get', lambda *args, **kwargs: response)
    return client


@pytest.mark.parametrize('status', [403, 404, 500])
def test_http_errors_never_yield_download_bytes(monkeypatch, status: int) -> None:
    response = Response(b'error', status=status)
    client = client_for(monkeypatch, response)
    with pytest.raises(requests.HTTPError):
        list(client.get_stream(response.url))
    assert response.closed


@pytest.mark.parametrize('headers', [{'Content-Type': 'text/html'}, {}])
def test_html_is_rejected_with_or_without_correct_mime(monkeypatch, headers: dict) -> None:
    response = Response(b'<!DOCTYPE html><html>resource wrapper</html>', headers=headers)
    client = client_for(monkeypatch, response)
    with pytest.raises(ValueError):
        list(client.get_stream(response.url))
    assert response.closed


def test_login_redirect_is_rejected(monkeypatch, pdf_bytes: bytes) -> None:
    response = Response(pdf_bytes, url='https://login.must.edu.mo/login')
    with pytest.raises(ValueError):
        list(client_for(monkeypatch, response).get_stream(response.url))


def test_short_content_length_is_rejected(monkeypatch, pdf_bytes: bytes) -> None:
    response = Response(pdf_bytes, headers={'Content-Length': str(len(pdf_bytes) + 99)})
    with pytest.raises(ValueError):
        list(client_for(monkeypatch, response).get_stream(response.url))


def test_binary_probe_does_not_read_pdf_body(monkeypatch, pdf_bytes: bytes) -> None:
    response = Response(pdf_bytes, headers={'Content-Type': 'application/pdf'})
    result = client_for(monkeypatch, response).get(response.url)
    assert result.text == '' and not response.text_read and response.closed


def test_page_probe_reads_html_and_closes_response(monkeypatch) -> None:
    response = Response(b'<html>page</html>', headers={'Content-Type': 'text/html; charset=UTF-8'})
    result = client_for(monkeypatch, response).get(response.url)
    assert result.text == '<html>page</html>' and response.closed
