"""
downloader — 国际化（中/英文案目录）

⚠️ 免责声明: 本工具仅供学生下载本人已注册课程的课件。
Disclaimer: For students to download their own course materials only.
"""
from __future__ import annotations

DEFAULT_LANGUAGE = "zh"

_ZH: dict[str, str] = {
    "banner.school_ascii": "MACAU UNIVERSITY",
    "banner.school_en_1": "Macau University of",
    "banner.school_en_2": "Science and Technology",
    "banner.product_ascii": "MUST Moodle Downloader",
    "banner.school": "澳門科技大學",
    "banner.product": "MUST Moodle 课件下载器",
    # Windows launcher
    'launcher.title': 'MUST Moodle 下载器 — Windows 功能菜单',
    'launcher.current_settings': '当前设置：浏览器 {browser} · 语言 {language} · 下载线程 {workers}',
    'launcher.auto': '自动检测',
    'launcher.menu_all': '同步全部已注册课程（补齐缺失 / 损坏课件）',
    'launcher.menu_list': '显示课程列表，选择单门课程',
    'launcher.menu_course': '输入 Moodle 课程 ID 下载',
    'launcher.menu_settings': '设置浏览器、界面语言和下载线程数',
    'launcher.menu_index': '建立 / 更新本地课件索引',
    'launcher.menu_obsidian': '导出 Obsidian 知识库',
    'launcher.menu_notebook': '生成复习 notebook',
    'launcher.menu_mcp': 'MCP 服务命令与启动',
    'launcher.menu_help': '查看现有命令行帮助',
    'launcher.menu_exit': '退出',
    'launcher.menu_prompt': '请选择 [0-9]: ',
    'launcher.invalid_choice': '请输入菜单中的编号。',
    'launcher.course_prompt': 'Moodle 课程 ID（回车返回菜单）: ',
    'launcher.invalid_number': '请输入 1 到 {maximum} 之间的整数。',
    'launcher.invalid_yes_no': '请输入 y 或 n。',
    'launcher.settings_hint': '设置仅在本窗口生效；default 沿用 config.toml，回车保留当前选项。',
    'launcher.browser_prompt': '浏览器 default / chrome / edge / firefox [{default}]: ',
    'launcher.language_prompt': '界面语言 default / zh / en [{default}]: ',
    'launcher.workers_prompt': '并行下载线程数，或 default [{default}]: ',
    'launcher.invalid_browser': '可选值：default、chrome、edge、firefox。',
    'launcher.invalid_language': '可选值：default、zh、en。',
    'launcher.settings_saved': '本窗口设置已更新；config.toml 未修改。',
    'launcher.root_prompt': '包含课程文件夹的根目录 [{default}]: ',
    'launcher.vault_prompt': 'Obsidian 输出目录 [{default}]: ',
    'launcher.copy_prompt': '同时复制原始课件？[y/N]: ',
    'launcher.overwrite_prompt': '覆盖已有的 Obsidian 笔记？[y/N]: ',
    'launcher.notebook_prompt': 'Notebook 输出文件（已有文件会覆盖）[{default}]: ',
    'launcher.days_prompt': '复习天数，1-60 [{default}]: ',
    'launcher.study_course_prompt': '仅指定课程（本地课程目录名，回车表示全部）: ',
    'launcher.mcp_hint': '以下为 MCP stdio 服务命令。手动启动后会等待客户端请求，Ctrl+C 停止；它不是下载菜单。AI 客户端可通过启动器的 --mcp 参数直接连接。',
    'launcher.mcp_directory': '命令工作目录：{root}',
    'launcher.mcp_start_prompt': '现在在此窗口启动服务？[y/N]: ',
    'launcher.start_failed': '启动失败：{error}',
    'launcher.returned': '已返回主菜单，本次任务退出码：{code}（0 表示成功，非 0 请查看上方信息）。',
    'scanner.no_download_link': '资源页面未找到真实文件链接',
    'scanner.http_error': '页面请求失败（HTTP {status}）',
    'file.empty': '文件为空或不存在',
    'file.html': '返回的是网页而非课件文件（可能是资源包装页或登录页）',
    'file.invalid_pdf': '文件不是完整的 PDF',
    'file.invalid_archive': '压缩包或 Office 文件结构损坏',
    'file.invalid_office': '文件内容与 Office 扩展名不符',
    'file.unreadable': '无法读取文件',
    'file.incomplete': '文件未完整传输',
    'flow.repaired': '已重新下载并修复 {count} 个已有文件',
    'flow.partial_failure': '有 {count} 个文件失败，请查看原因后再次同步',
    'flow.sync_start': '同步全部 {count} 门已注册课程：检查本地文件，只补下载缺失或无效文件',
    'flow.sync_course': '[{number}/{total}] {name} · ID {course_id}',
    'flow.sync_done': '已处理 {count} 门课程；下载/修复 {downloaded} 个，校验后跳过 {skipped} 个，文件失败 {failed} 个，课程扫描失败 {failed_courses} 门',
    'table.course_code': '课程代码',
    'table.all_courses': '同步全部课程（补齐缺失 / 损坏文件）',
    'table.pick_all_prompt': '输入 0 同步全部课程，或输入序号 / 课程 ID（回车退出）: ',
    'ui.scan_failed': '解析失败',
    # ── 顶层流程 ──
    "app.press_enter_exit": "按 Enter 键退出...",
    "app.user_interrupt": "用户中断",
    "app.unexpected_error": "发生未预料的错误：",
    "lang.unsupported": "不支持的语言: {lang}，已使用默认语言 (zh / en)",

    # ── 认证 ──
    "auth.cookie_expired": "Cookie 已过期，需要重新登录",
    "auth.no_credentials": "无法获取有效的登录凭据",
    "auth.cookies_cleared": "已清除本地 Cookie",
    "auth.unsupported_browser": "不支持的浏览器: {browser}，可选: {options}",
    "auth.no_browser": (
        "未检测到可用浏览器。请安装以下任一 WebDriver：\n"
        "  - Chrome:  https://chromedriver.chromium.org/\n"
        "  - Edge:    https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/\n"
        "  - Firefox: https://github.com/mozilla/geckodriver/releases"
    ),
    "auth.launching_browser": "正在唤起 {browser} 浏览器进行身份验证...",
    "auth.complete_login": "请在弹出的浏览器中完成 MUST Moodle 登录",
    "auth.auto_continue": "登录成功后无需操作，脚本将自动接管...",
    "auth.login_success": "登录成功！Cookie 已安全保存",
    "auth.login_timeout": "登录等待超时，请重新运行",
    "auth.browser_error": "浏览器调用失败: {error}",

    # ── 扫描 ──
    "scanner.session_expired": "⚠️ 登录状态已过期，请重新登录",

    # ── 下载 ──
    "downloader.queue_summary": "共 {total} 个目标，{existing} 个本地校验通过，{pending} 个待下载/修复",
    "downloader.progress": "{done}/{total} — 已成功 {ok} 个",

    # ── 主流程 ──
    "flow.confirm_login": "打开浏览器登录 MUST Moodle？",
    "flow.cancelled": "已取消",
    "flow.auth_failed_title": "认证失败",
    "flow.auth_failed_detail": "无法获取有效的登录凭据",
    "flow.detecting_course": "正在识别课程 {course_id}...",
    "flow.scanning": "正在扫描课件文件...",
    "flow.scan_failed_title": "扫描失败",
    "flow.no_resources": "未找到任何课件资源",
    "flow.confirm_download": "共 {count} 个文件，确认下载？",
    "flow.downloading": "下载中...",
    "flow.no_courses_title": "无课程",
    "flow.no_courses_detail": "未找到任何课程",
    "flow.enrolled_title": "你注册了 {count} 门课程",
    "flow.invalid_range_title": "参数无效",
    "flow.invalid_range_detail": "扫描范围无效，请使用: --discover 起始ID-结束ID",
    "flow.discover_scanning": "扫描中...",
    "flow.discover_trying": "正在试 ID {course_id}...",
    "flow.discover_none_title": "无发现",
    "flow.discover_none_detail": "范围 {start}～{end} 内未找到可访问的课程",
    "flow.discover_found_title": "发现 {count} 门可访问的课程",

    # ── 学习 / Agent 集成 ──
    "study.indexing": "正在索引本地课件 {root}...",
    "study.index_done": "已索引 {courses} 门课程、{files} 个文件",
    "study.index_saved": "索引已保存到 {path}",
    "study.no_materials": "未找到任何已下载的课件，请先下载课程",
    "study.exporting": "正在导出 Obsidian 知识库到 {vault}...",
    "study.export_done": "已写入 {notes} 篇笔记（{courses} 门课程），跳过 {skipped} 篇已存在",
    "study.export_copied": "已复制 {count} 个原文件到 _attachments/",
    "study.export_hint": "用 Obsidian 打开该文件夹即可开始复习",
    "study.notebook_building": "正在生成复习 notebook...",
    "study.notebook_done": "复习 notebook 已生成: {path}",
    "study.mcp_hint": "Agent 接入: python -m moodle_scraper.mcp_server",
    "study.failed_title": "操作失败",

    # ── 课程选择表格 ──
    "table.course_name": "课程名称",
    "table.course_id": "课程 ID",
    "table.pick_prompt": "输入序号选课，或直接输入课程 ID（回车退出）: ",
    "table.pick_invalid": "请输入数字序号或有效的课程 ID",

    # ── Rich UI ──
    "ui.welcome_sub": (
        "课程  {course}   ·   ID  {course_id}   ·   "
        "并行  {workers} 线程   ·   保存至  {save_dir}/"
    ),
    "ui.scan_title": "发现  {count}  个文件",
    "ui.col_filename": "文件名",
    "ui.col_status": "状态",
    "ui.pending": "待下载",
    "ui.more_files": "… 还有 {count} 个文件",
    "ui.card_total": "总目标",
    "ui.card_new": "下载 / 修复",
    "ui.card_skipped": "已有",
    "ui.card_failed": "失败",
    "ui.report_title": "下载报告",
    "ui.failed_list_title": "失败列表",
    "ui.up_to_date": "本次扫描的课件均已通过本地校验，无需补下载。",
    "ui.added_files": "成功下载 / 修复  {count}  个文件",
    "ui.dash_status_init": "初始化",
    "ui.dash_threads": "{count} 线程",
    "ui.dash_courses": "可访问 {count} 门课程",
    "ui.dash_save_dir": "保存至 {save_dir}/",
    "ui.dash_continue": "按 Enter 键继续",
}

_EN: dict[str, str] = {
    "banner.school_ascii": "MACAU UNIVERSITY",
    "banner.school_en_1": "Macau University of",
    "banner.school_en_2": "Science and Technology",
    "banner.product_ascii": "MUST Moodle Downloader",
    "banner.school": "澳門科技大學",
    "banner.product": "MUST Moodle Downloader",
    # Windows launcher
    'launcher.title': 'MUST Moodle Downloader — Windows Menu',
    'launcher.current_settings': 'Settings: browser {browser} · language {language} · download workers {workers}',
    'launcher.auto': 'auto-detect',
    'launcher.menu_all': 'Sync all enrolled courses (missing / damaged files)',
    'launcher.menu_list': 'Show courses and select one course',
    'launcher.menu_course': 'Download by Moodle course ID',
    'launcher.menu_settings': 'Set browser, language and download workers',
    'launcher.menu_index': 'Build / update the local material index',
    'launcher.menu_obsidian': 'Export an Obsidian vault',
    'launcher.menu_notebook': 'Generate a revision notebook',
    'launcher.menu_mcp': 'MCP server command and launch',
    'launcher.menu_help': 'Show existing CLI help',
    'launcher.menu_exit': 'Exit',
    'launcher.menu_prompt': 'Choose [0-9]: ',
    'launcher.invalid_choice': 'Enter a number from the menu.',
    'launcher.course_prompt': 'Moodle course ID (Enter to return): ',
    'launcher.invalid_number': 'Enter an integer between 1 and {maximum}.',
    'launcher.invalid_yes_no': 'Enter y or n.',
    'launcher.settings_hint': 'Settings apply to this window only. default uses config.toml; Enter keeps the current choice.',
    'launcher.browser_prompt': 'Browser default / chrome / edge / firefox [{default}]: ',
    'launcher.language_prompt': 'Language default / zh / en [{default}]: ',
    'launcher.workers_prompt': 'Parallel download workers, or default [{default}]: ',
    'launcher.invalid_browser': 'Choose default, chrome, edge or firefox.',
    'launcher.invalid_language': 'Choose default, zh or en.',
    'launcher.settings_saved': 'Session settings updated; config.toml was not changed.',
    'launcher.root_prompt': 'Root containing course folders [{default}]: ',
    'launcher.vault_prompt': 'Obsidian output directory [{default}]: ',
    'launcher.copy_prompt': 'Copy the original materials too? [y/N]: ',
    'launcher.overwrite_prompt': 'Overwrite existing Obsidian notes? [y/N]: ',
    'launcher.notebook_prompt': 'Notebook output file (existing file is replaced) [{default}]: ',
    'launcher.days_prompt': 'Revision days, 1-60 [{default}]: ',
    'launcher.study_course_prompt': 'Limit to a course (local folder name; Enter for all): ',
    'launcher.mcp_hint': 'This is the MCP stdio server command. It waits for client requests; Ctrl+C stops it. It is not a download menu. AI clients can connect directly using the launcher --mcp option.',
    'launcher.mcp_directory': 'Command working directory: {root}',
    'launcher.mcp_start_prompt': 'Start the server in this window now? [y/N]: ',
    'launcher.start_failed': 'Failed to start: {error}',
    'launcher.returned': 'Returned to the menu. Task exit code: {code} (0 means success; otherwise check the output above).',
    'scanner.no_download_link': 'No actual file link found on the resource page',
    'scanner.http_error': 'Page request failed (HTTP {status})',
    'file.empty': 'File is empty or missing',
    'file.html': 'Received a web page instead of a material file (resource wrapper or login page)',
    'file.invalid_pdf': 'File is not a complete PDF',
    'file.invalid_archive': 'Invalid archive or Office file structure',
    'file.invalid_office': 'File content does not match its Office extension',
    'file.unreadable': 'Could not read the file',
    'file.incomplete': 'File transfer was incomplete',
    'flow.repaired': 'Re-downloaded and repaired {count} existing files',
    'flow.partial_failure': '{count} files failed; review the reasons and sync again',
    'flow.sync_start': 'Syncing all {count} enrolled courses: validate local files and fetch missing or invalid files',
    'flow.sync_course': '[{number}/{total}] {name} · ID {course_id}',
    'flow.sync_done': 'Processed {count} courses; downloaded/repaired {downloaded}, validated/skipped {skipped}, file failures {failed}, course scan failures {failed_courses}',
    'table.course_code': 'Course Code',
    'table.all_courses': 'Sync all courses (missing / damaged files)',
    'table.pick_all_prompt': 'Enter 0 to sync all courses, a list number or course ID (Enter to quit): ',
    'ui.scan_failed': 'Resolution failed',
    # ── Top-level flow ──
    "app.press_enter_exit": "Press Enter to exit...",
    "app.user_interrupt": "Interrupted by user",
    "app.unexpected_error": "An unexpected error occurred:",
    "lang.unsupported": "Unsupported language: {lang} — falling back to default (zh / en)",

    # ── Auth ──
    "auth.cookie_expired": "Cookies expired — you need to log in again",
    "auth.no_credentials": "Could not obtain valid login credentials",
    "auth.cookies_cleared": "Local cookies cleared",
    "auth.unsupported_browser": "Unsupported browser: {browser}. Options: {options}",
    "auth.no_browser": (
        "No usable browser detected. Please install one of these WebDrivers:\n"
        "  - Chrome:  https://chromedriver.chromium.org/\n"
        "  - Edge:    https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/\n"
        "  - Firefox: https://github.com/mozilla/geckodriver/releases"
    ),
    "auth.launching_browser": "Launching {browser} for authentication...",
    "auth.complete_login": "Complete the MUST Moodle login in the browser window",
    "auth.auto_continue": "Once logged in, no further action is needed — the script takes over automatically...",
    "auth.login_success": "Login successful! Cookies saved securely",
    "auth.login_timeout": "Timed out waiting for login — please run again",
    "auth.browser_error": "Browser launch failed: {error}",

    # ── Scanner ──
    "scanner.session_expired": "⚠️ Session expired — please log in again",

    # ── Downloader ──
    "downloader.queue_summary": "{total} targets — {existing} validated, {pending} to download/repair",
    "downloader.progress": "{done}/{total} — {ok} succeeded",

    # ── Main flow ──
    "flow.confirm_login": "Open a browser to log in to MUST Moodle?",
    "flow.cancelled": "Cancelled",
    "flow.auth_failed_title": "Authentication failed",
    "flow.auth_failed_detail": "Could not obtain valid login credentials",
    "flow.detecting_course": "Identifying course {course_id}...",
    "flow.scanning": "Scanning for course files...",
    "flow.scan_failed_title": "Scan failed",
    "flow.no_resources": "No course resources found",
    "flow.confirm_download": "{count} files found. Download now?",
    "flow.downloading": "Downloading...",
    "flow.no_courses_title": "No courses",
    "flow.no_courses_detail": "No courses were found",
    "flow.enrolled_title": "You are enrolled in {count} courses",
    "flow.invalid_range_title": "Invalid arguments",
    "flow.invalid_range_detail": "Invalid scan range. Use: --discover START-END",
    "flow.discover_scanning": "Scanning...",
    "flow.discover_trying": "Trying ID {course_id}...",
    "flow.discover_none_title": "Nothing found",
    "flow.discover_none_detail": "No accessible courses found in range {start}-{end}",
    "flow.discover_found_title": "Found {count} accessible courses",

    # ── Study / agent integration ──
    "study.indexing": "Indexing local materials in {root}...",
    "study.index_done": "Indexed {courses} courses, {files} files",
    "study.index_saved": "Index saved to {path}",
    "study.no_materials": "No downloaded materials found — download a course first",
    "study.exporting": "Exporting Obsidian vault to {vault}...",
    "study.export_done": "Wrote {notes} notes across {courses} courses, skipped {skipped} existing",
    "study.export_copied": "Copied {count} source files into _attachments/",
    "study.export_hint": "Open that folder in Obsidian to start revising",
    "study.notebook_building": "Building revision notebook...",
    "study.notebook_done": "Revision notebook ready: {path}",
    "study.mcp_hint": "Agent access: python -m moodle_scraper.mcp_server",
    "study.failed_title": "Operation failed",

    # ── Course picker table ──
    "table.course_name": "Course Name",
    "table.course_id": "Course ID",
    "table.pick_prompt": "Enter a number to pick a course, or type a course ID (Enter to quit): ",
    "table.pick_invalid": "Please enter a list number or a valid course ID",

    # ── Rich UI ──
    "ui.welcome_sub": (
        "Course  {course}   ·   ID  {course_id}   ·   "
        "{workers} threads   ·   Saving to  {save_dir}/"
    ),
    "ui.scan_title": "Found  {count}  files",
    "ui.col_filename": "File Name",
    "ui.col_status": "Status",
    "ui.pending": "Pending",
    "ui.more_files": "… {count} more files",
    "ui.card_total": "Total",
    "ui.card_new": "Downloaded / repaired",
    "ui.card_skipped": "Existing",
    "ui.card_failed": "Failed",
    "ui.report_title": "Download Report",
    "ui.failed_list_title": "Failed Items",
    "ui.up_to_date": "All scanned materials passed local validation; no downloads needed.",
    "ui.added_files": "Downloaded / repaired  {count}  files",
    "ui.dash_status_init": "Initializing",
    "ui.dash_threads": "{count} threads",
    "ui.dash_courses": "{count} accessible courses",
    "ui.dash_save_dir": "Saving to {save_dir}/",
    "ui.dash_continue": "Press Enter to continue",
}

CATALOGS: dict[str, dict[str, str]] = {"zh": _ZH, "en": _EN}

# 语言别名 → 规范代码
_ALIASES: dict[str, str] = {
    "zh": "zh", "cn": "zh", "zh-cn": "zh", "zh_cn": "zh",
    "zh-hans": "zh", "chinese": "zh", "中文": "zh",
    "en": "en", "en-us": "en", "en_us": "en", "en-gb": "en",
    "en-au": "en", "english": "en",
}

_current = DEFAULT_LANGUAGE


def resolve_language(lang: str) -> str | None:
    """解析语言别名 → 规范代码；无法识别时返回 None"""
    return _ALIASES.get((lang or "").strip().lower())


def set_language(lang: str) -> str:
    """切换当前语言（接受别名）；无法识别时抛 ValueError"""
    global _current
    resolved = resolve_language(lang)
    if resolved is None:
        raise ValueError(f"Unsupported language: {lang!r} (supported: {', '.join(CATALOGS)})")
    _current = resolved
    return resolved


def get_language() -> str:
    """当前语言代码"""
    return _current


def t(key: str, **kwargs) -> str:
    """
    取当前语言的文案并格式化

    未知 key 原样返回（便于发现漏翻译）；缺少格式参数时返回未格式化模板。
    """
    catalog = CATALOGS.get(_current, _ZH)
    template = catalog.get(key)
    if template is None:
        template = _ZH.get(key, key)
    if kwargs:
        try:
            return template.format(**kwargs)
        except (KeyError, IndexError):
            return template
    return template
