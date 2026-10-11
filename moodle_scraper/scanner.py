"""
downloader — 扫描模块

⚠️ 免责声明: 本工具仅供学生下载本人已注册课程的课件。
Disclaimer: For students to download their own course materials only.
"""
from __future__ import annotations

import re
import urllib.parse
from dataclasses import dataclass, replace
from email.message import Message
import mimetypes
from pathlib import PurePosixPath
from typing import Optional

from bs4 import BeautifulSoup

from .http import HttpClient, HttpResponse
from .i18n import t
from .utils import is_login_page


class ScanError(Exception):
    """扫描过程相关异常"""


COURSE_NAME_PATTERNS = [
    "h1.page-header-heading",           # Moodle 4.x
    "h1",                               # 通用 fallback
    "title",                            # 极简 fallback
]


@dataclass
class Resource:
    """一个可下载的课件资源"""
    name: str
    url: str
    filename: str = ""
    source_url: str = ""
    error: str = ""


@dataclass
class CourseInfo:
    """仪表盘上的一门课程"""
    id: str
    name: str
    url: str
    code: str = ""


class Scanner:
    """Moodle 课程页面扫描器"""

    def __init__(
        self, client: HttpClient, *,
        base_url: str = "https://moodle.must.edu.mo",
        course_names: Optional[dict[str, str]] = None,
        timeout: int = 30,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._course_names = course_names or {}
        self._timeout = timeout

    def fetch_course_name(self, course_id: str) -> str:
        """
        从课程主页抓取课程名称

        :returns: 课程名称字符串，解析失败时返回默认值
        """
        url = f"{self._base_url}/course/view.php?id={course_id}"
        try:
            resp = self._client.get(url, timeout=30)

            if is_login_page(resp.url, resp.text):
                raise ScanError(t("scanner.session_expired"))

            soup = BeautifulSoup(resp.text, "html.parser")

            # 1. Moodle 4.x 专用：h1.page-header-heading
            h1 = soup.select_one("h1.page-header-heading")
            if h1:
                return h1.get_text(strip=True)

            # 2. 通用 h1（通常第一个 h1 是课程名）
            h1s = soup.find_all("h1")
            if h1s:
                text = h1s[0].get_text(strip=True)
                if text and "course" not in text.lower():
                    return text

            # 3. 页面标题（去掉站点名后缀）
            title_tag = soup.find("title")
            if title_tag:
                title = title_tag.get_text(strip=True)
                # 去掉常见的 Moodle 后缀
                for sep in ["—", "–", "-", "|"]:
                    if sep in title:
                        title = title.split(sep)[0].strip()
                return title

        except Exception:
            pass

        return f"Course_{course_id}"

    def list_courses(self) -> list[CourseInfo]:
        """
        从仪表盘（/my/）抓取当前用户已注册的所有课程

        :returns: 课程列表，按名称排序；登录失效时返回空列表
        """
        try:
            resp = self._client.get(
                f"{self._base_url}/my/", timeout=self._timeout
            )

            if is_login_page(resp.url, resp.text):
                return []

            soup = BeautifulSoup(resp.text, "html.parser")
            by_id: dict[str, CourseInfo] = {}
            for a in soup.find_all("a", href=True):
                href = urllib.parse.urljoin(resp.url, a["href"])
                parsed = urllib.parse.urlsplit(href)
                if parsed.path != "/course/view.php":
                    continue
                raw_id = urllib.parse.parse_qs(parsed.query).get("id", [""])[0]
                if not raw_id.isdigit():
                    continue
                label = a.get_text(" ", strip=True)
                if not label:
                    continue
                # 页面常同时有短代码导航和完整课程卡片；优先保留更完整的名称。
                code_match = re.search(r"\b\d{4}-[A-Za-z0-9]+-[A-Za-z0-9]+\b", label)
                code = code_match.group(0) if code_match else ""
                name = self._course_names.get(raw_id, label)
                info = CourseInfo(id=raw_id, name=name, url=href, code=code)
                previous = by_id.get(raw_id)
                if previous is None or len(name) > len(previous.name):
                    by_id[raw_id] = info
                elif code and not previous.code:
                    previous.code = code
            courses = list(by_id.values())

            courses.sort(key=lambda c: c.name.lower())
            return courses

        except Exception:
            return []

    def discover_courses(
        self,
        start_id: int,
        end_id: int,
        *,
        max_workers: int = 24,
        on_progress: Optional[callable] = None,
    ) -> list[CourseInfo]:
        """
        尝试一段 course_id 范围，返回可访问的课程列表

        :param start_id: 起始 ID（含）
        :param end_id: 结束 ID（含）
        :param max_workers: 并行线程数（默认 24）
        :param on_progress: 进度回调 (current, total, current_course_id)
        """
        from concurrent.futures import ThreadPoolExecutor, as_completed

        total = end_id - start_id + 1
        ids = list(range(start_id, end_id + 1))
        results: list[CourseInfo] = []
        done = 0

        on_progress = on_progress or (lambda c, t, i: None)
        on_progress(0, total, start_id)

        def _check_one(cid: int) -> Optional[CourseInfo]:
            """检查单个 ID 是否可访问"""
            try:
                url = f"{self._base_url}/course/view.php?id={cid}"
                resp = self._client.get(url, timeout=5)

                # 登录页或被拒绝 → 跳过
                if is_login_page(resp.url, resp.text):
                    return None
                if "Access denied" in resp.text or "not enrolled" in resp.text.lower():
                    return None
                if "error" in resp.url.lower() and "course" in resp.url.lower():
                    return None

                # 尝试提取课程名
                soup = BeautifulSoup(resp.text, "html.parser")
                name = ""

                h1 = soup.select_one("h1.page-header-heading")
                if h1:
                    name = h1.get_text(strip=True)

                if not name:
                    h1s = soup.find_all("h1")
                    if h1s:
                        name = h1s[0].get_text(strip=True)

                if not name:
                    title_tag = soup.find("title")
                    if title_tag:
                        name = title_tag.get_text(strip=True)
                        for sep in ["—", "–", "-", "|"]:
                            if sep in name:
                                name = name.split(sep)[0].strip()

                if name and "course" not in name.lower() and "error" not in name.lower():
                    return CourseInfo(id=str(cid), name=name, url=url)

                return None
            except Exception:
                return None

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            fut_map = {pool.submit(_check_one, cid): cid for cid in ids}
            for future in as_completed(fut_map):
                cid = fut_map[future]
                done += 1
                try:
                    info = future.result()
                    if info:
                        results.append(info)
                except Exception:
                    pass
                on_progress(done, total, cid)

        results.sort(key=lambda c: c.name.lower())
        return results

    def scan_course(
        self,
        course_id: str,
        *,
        keywords: Optional[list[str]] = None,
        extensions: Optional[list[str]] = None,
    ) -> list[Resource]:
        """扫描资源页、课程中的直接文件链接及 page/folder 子页面。

        HTML 资源页必须解析成真正的文件 URL；单项失败保留为 error，
        交给下载汇总展示，不能静默漏掉或把网页当作课件。
        """
        keywords = keywords or []
        extensions = extensions or []
        course_url = f"{self._base_url}/course/view.php?id={course_id}"
        pending = [course_url]
        visited: set[str] = set()
        seen: set[str] = set()
        resources: list[Resource] = []

        while pending:
            page_url = pending.pop(0)
            if page_url in visited:
                continue
            visited.add(page_url)
            try:
                response = self._fetch(page_url)
            except Exception as exc:
                if page_url == course_url:
                    raise
                resources.append(Resource(name=page_url, url=page_url, error=str(exc)))
                continue
            soup = BeautifulSoup(response.text, "html.parser")
            content = soup.select_one("#region-main") or soup
            for tag in content.find_all(["a", "object", "embed", "iframe"]):
                href = tag.get("href") or tag.get("data") or tag.get("src") or ""
                if not href:
                    continue
                url = urllib.parse.urljoin(response.url, href)
                parsed = urllib.parse.urlsplit(url)
                if parsed.scheme not in {"http", "https"}:
                    continue
                if parsed.netloc != urllib.parse.urlsplit(self._base_url).netloc:
                    continue
                if parsed.path in {"/mod/page/view.php", "/mod/folder/view.php"}:
                    if url not in visited:
                        pending.append(url)
                    continue
                if url in seen:
                    continue
                if parsed.path == "/mod/resource/view.php":
                    name = tag.get_text(" ", strip=True) or tag.get("title", "")
                    if not name or name == "File":
                        continue
                    seen.add(url)
                    item = Resource(name=name, url=url, source_url=url)
                    try:
                        resources.append(self.resolve_resource(item))
                    except Exception as exc:
                        resources.append(replace(item, error=str(exc)))
                elif "pluginfile.php/" in parsed.path:
                    filename = urllib.parse.unquote(PurePosixPath(parsed.path).name)
                    if not self._matches(filename, keywords, extensions):
                        continue
                    seen.add(url)
                    resources.append(Resource(
                        name=PurePosixPath(filename).stem, url=url,
                        filename=filename, source_url=url,
                    ))

        # 同一文件可能同时由资源页、文件夹和正文链接指向；只下载一次。
        unique: dict[str, Resource] = {}
        for resource in resources:
            key = resource.url.split("?", 1)[0] if "pluginfile.php/" in resource.url else resource.url
            unique.setdefault(key, resource)
        return list(unique.values())

    def resolve_resource(self, resource: Resource) -> Resource:
        """解析 Moodle 的资源包装页、嵌入页或直接文件重定向。"""
        current = resource.url
        seen: set[str] = set()
        for _ in range(5):
            if current in seen:
                break
            seen.add(current)
            response = self._fetch(current)
            disposition = response.header("Content-Disposition")
            content_type = response.header("Content-Type").split(";", 1)[0].lower()
            if content_type and "html" not in content_type:
                filename = self._response_filename(response)
                return replace(resource, url=response.url, filename=filename)

            soup = BeautifulSoup(response.text, "html.parser")
            content = soup.select_one("#region-main") or soup
            candidates: list[str] = []
            for tag in content.find_all(["a", "object", "embed", "iframe"]):
                href = tag.get("href") or tag.get("data") or tag.get("src") or ""
                candidate = urllib.parse.urljoin(response.url, href)
                parsed = urllib.parse.urlsplit(candidate)
                if (
                    parsed.scheme in {"http", "https"}
                    and parsed.netloc == urllib.parse.urlsplit(self._base_url).netloc
                    and "pluginfile.php/" in parsed.path
                ):
                    candidates.append(candidate)
            if candidates:
                # 资源正文优先于页面可能附带的其它 pluginfile 链接。
                url = next((u for u in candidates if "/mod_resource/content/" in u), candidates[0])
                filename = urllib.parse.unquote(PurePosixPath(urllib.parse.urlsplit(url).path).name)
                return replace(resource, url=url, filename=filename)

            # 某些主题使用嵌套 iframe；仅沿同一 Moodle 站点的资源入口继续。
            frame = content.find(["iframe", "embed", "object"])
            if frame:
                url = urllib.parse.urljoin(response.url, frame.get("src") or frame.get("data") or "")
                parsed = urllib.parse.urlsplit(url)
                if parsed.netloc == urllib.parse.urlsplit(self._base_url).netloc and parsed.path == "/mod/resource/view.php":
                    current = url
                    continue
            if not response.text and (disposition or "pluginfile.php/" in response.url):
                return replace(resource, url=response.url, filename=self._response_filename(response))
            break
        raise ScanError(t("scanner.no_download_link"))

    @staticmethod
    def _response_filename(response: HttpResponse) -> str:
        """文件名优先采用响应头，其次最终 URL，最后按内容类型确定扩展名。"""
        message = Message()
        message["Content-Disposition"] = response.header("Content-Disposition")
        filename = message.get_filename()
        if filename:
            return PurePosixPath(filename.replace("\\", "/")).name
        filename = urllib.parse.unquote(PurePosixPath(urllib.parse.urlsplit(response.url).path).name)
        if filename and not filename.lower().endswith(".php"):
            return filename
        content_type = response.header("Content-Type").split(";", 1)[0].lower()
        return "resource" + (mimetypes.guess_extension(content_type) or ".bin")

    def _fetch(self, url: str) -> HttpResponse:
        """校验 HTTP 和登录状态后再解析页面。"""
        response = self._client.get(url, timeout=self._timeout)
        if not 200 <= response.status_code < 300:
            raise ScanError(t("scanner.http_error", status=response.status_code))
        if is_login_page(response.url, response.text):
            raise ScanError(t("scanner.session_expired"))
        return response

    @staticmethod
    def _matches(name: str, keywords: list[str], extensions: list[str]) -> bool:
        """检查文件名是否符合关键词或后缀条件"""
        name_lower = name.lower()
        if keywords:
            if any(k.lower() in name_lower for k in keywords):
                return True
        if extensions:
            if any(name_lower.endswith(e) for e in extensions):
                return True
        # 如果两者都为空，默认全部通过
        return not keywords and not extensions
