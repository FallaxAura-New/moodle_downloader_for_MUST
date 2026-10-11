# downloader

Moodle 课件下载工具（PDF/PPT），支持并行下载与 Rich 终端 UI。

## Project

- **Stack**: Python 3.11+ · requests · BeautifulSoup 4 · Selenium (Edge) · Rich
- **Entry**: `main.py` — 快速启动；`python -m moodle_scraper` 也可
- **Config**: `config.toml` — 课程 ID、线程数、过滤规则等
- **Deps**: `pip install -r requirements.txt`

## Commands

| 用途 | 命令 |
|------|------|
| 运行 | `python main.py` |
| 安装依赖 | `pip install -r requirements.txt` |
| 语法检查 | `python -m compileall moodle_scraper/ main.py` |
| 模块验证 | `python -c "from moodle_scraper.config import AppConfig; print(AppConfig.load())"` |

## Architecture

```
moodle_scraper/
├── http.py       — HttpClient Protocol (seam) + RequestsHttpClient + FakeHttpClient
├── auth.py       — AuthManager，返回已认证的 HttpClient
├── scanner.py    — Scanner，扫描课程页面 → list[Resource] (dataclass)
├── downloader.py — Downloader，并行下载资源 → DownloadResult
├── utils.py      — sanitize_filename, is_login_page 纯函数
├── config.py     — AppConfig dataclass，从 config.toml 加载
├── i18n.py       — 中/英文案目录 + t() 翻译函数（--lang / [ui].language 切换）
├── ui.py         — RichUI，面板/进度条/表格/彩色的终端界面
└── __main__.py   — 编排：AuthManager → Scanner(client) → Downloader(client)
```

流程：`main.py` → `__main__.main_impl()` → `AuthManager.get_authenticated_client()` → `Scanner(client).scan_course()` → `Downloader(client).download_all()` → 汇总报告。

关键 seam：`HttpClient` Protocol — Scanner 和 Downloader 都依赖此 seam。生产用 `RequestsHttpClient`，测试用 `FakeHttpClient`。

## Conventions

- **类型注解**: 全部函数参数/返回值标注类型；`from __future__ import annotations` 延后求值
- **异常**: 自定义异常类（`ScanError`）；顶层 `try/except` 捕获未预期错误
- **输出**: 全部通过 `RichUI.status(emoji, msg)` 和进度回调
- **文案**: 用户可见文本一律走 `i18n.t(key)`，`_ZH` / `_EN` 目录必须同步添加（emoji 前缀留在代码里）；`main.py` 例外，保持双语静态文本
- **配置**: 不硬编码；通过 `AppConfig` dataclass 读取 `config.toml`
- **命名**: 类名 PascalCase；方法/变量 snake_case；私有方法 `_` 前缀
- **导入顺序**: stdlib → 三方库 → 本地模块，每组空行分隔
- **测试 seam**: 依赖接口（Protocol），而非具体实现。参考 `HttpClient` seam

## Notes

- 本地适配 MUST；站点从 `AppConfig.moodle_url` 读取，中文课程名来自 `[course_names]`（以课程 ID 为键），保留代码及 ID。
- `--all` 或课程菜单 `0` 只同步已注册课程，与单门课下载共用执行路径；不要复用 ID 范围探测来实现全量同步。
- `Scanner` 先解析 Moodle 资源包装页，`Resource` 还携带 `filename`、`source_url`、`error`。解析失败应显示在汇总中，不能静默忽略。
- `files.py` 负责内容校验；`Downloader` 只有校验通过后才能跳过或原子替换文件。`.moodle-downloads.json` 保存文件名 / 哈希映射，同名资源不能互相覆盖。
- 批量课程处理使用配置副本；失败时不能显示“全部已是最新”。新增检查均使用离线响应和临时目录。

- Windows 的 `启动下载器.bat` 只负责定位仓库和 Python / 依赖检查；`windows_launcher.py` 通过参数列表调用既有 `main.py`，不要复制下载逻辑。`--mcp` 转发到 `mcp_server`，标准输出不能混入菜单。
