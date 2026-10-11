# Moodle Downloader for MUST

面向澳门科技大学（MUST）的 Moodle 课件下载工具：浏览器登录、中文课程名称、全部课程同步，以及缺失 / 损坏文件的增量补下载。

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

[项目仓库](https://github.com/FallaxAura-New/moodle_downloader_for_MUST) · [问题反馈](https://github.com/FallaxAura-New/moodle_downloader_for_MUST/issues) · [English quick start](#english-quick-start)

默认站点为 [MUST Moodle](https://moodle.must.edu.mo/my/)。本工具供学生下载自己已注册课程的资料，用于个人离线学习；请遵守学校的使用规定及课件版权要求。

## 目录

- [安装](#安装)
- [首次登录](#首次登录)
- [选择课程与全部同步](#选择课程与全部同步)
- [课程中文名称](#课程中文名称)
- [增量下载与文件校验](#增量下载与文件校验)
- [文件保存位置](#文件保存位置)
- [常用配置](#常用配置)
- [本地学习与 AI 接入](#本地学习与-ai-接入)
- [常见问题](#常见问题)
- [开发与测试](#开发与测试)

## 安装

需要 **Python 3.11 或更新版本**、Git，以及 Chrome、Edge、Firefox 中至少一种浏览器。浏览器登录使用 Selenium；缺少驱动时，内置的 Selenium Manager 通常会自动获取匹配驱动，首次启动需要能访问驱动下载服务，详见 [Selenium 官方说明](https://www.selenium.dev/documentation/selenium_manager/)。

### macOS / Linux

在终端中执行：

```bash
git clone https://github.com/FallaxAura-New/moodle_downloader_for_MUST.git
cd moodle_downloader_for_MUST
python3 --version
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Windows（PowerShell）

```powershell
git clone https://github.com/FallaxAura-New/moodle_downloader_for_MUST.git
cd moodle_downloader_for_MUST
py -3 --version
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

先确认版本输出为 Python 3.11+。如果 PowerShell 不允许激活虚拟环境，可以直接使用虚拟环境内的解释器：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py --all
```

运行依赖为 `requests`、`beautifulsoup4`、`selenium`、`rich`，均在 [requirements.txt](requirements.txt) 中。下载课件不需要安装 AI 客户端、Jupyter 或 PDF 文本提取库。

下文的 `python` 命令均在**仓库根目录、虚拟环境已激活**的情况下执行。以后重新打开终端时，先进入仓库并激活 `.venv`。

## 首次登录

```bash
python main.py
```

1. 首次运行会询问是否打开浏览器登录 MUST Moodle，输入 `y` 或直接按 Enter。
2. 程序打开 `https://moodle.must.edu.mo/my/`。在弹出的浏览器中，按学校登录页面的要求完成账号登录和验证。
3. 返回 Moodle 仪表盘或课程页面后，程序自动读取登录状态、关闭该浏览器窗口，并继续加载课程列表。默认等待登录的时间为 300 秒。
4. 登录会话保存在本地 `moodle_cookies.json`。后续运行会先检查缓存，失效后重新打开浏览器登录。

浏览器默认按 **Chrome → Edge → Firefox** 的顺序尝试。也可以指定：

```bash
python main.py --browser chrome
python main.py --browser edge
python main.py --browser firefox
```

`moodle_cookies.json` 包含会话凭据，已被 `.gitignore` 排除。请保留在本机，不要上传到仓库或作为问题附件分享。

## 选择课程与全部同步

### 菜单选择

运行 `python main.py` 后，课程表会同时显示**序号、课程名称、课程代码、Moodle 课程 ID**。

| 输入 | 行为 |
| --- | --- |
| `0` | 同步全部已注册课程 |
| `a` 或 `all` | 与 `0` 相同 |
| 表格中的课程序号 | 扫描所选课程，确认后下载 |
| Moodle 课程 ID，例如 `118832` | 直接扫描该课程，确认后下载 |
| 空输入（直接 Enter） | 退出选课 |

序号以本次显示的列表为准；课程 ID 与课程代码是不同字段。

### 直接同步全部课程

```bash
python main.py --all
```

程序从当前账号的 Moodle 仪表盘读取已注册课程，**逐门扫描**课程主页、Moodle 页面和文件夹中的受支持文件链接，并在每门课内并行下载。批量同步无需逐门确认；某门课或文件失败后会继续处理其余课程，并在最终报告中列出失败项。

“全部课程”取决于当前账号仪表盘实际返回的课程；“全部课件”仍受可访问链接、支持的资源类型和筛选配置限制。它不会备份整站，也不会下载测验、作业提交或外部视频平台的全部内容。

`--all` 会跳过选课和逐课确认，但首次登录仍需要在浏览器中操作，运行结束仍需按 Enter 退出。

### 下载单门课与常用参数

```bash
python main.py 118832                      # 大学微积分 I；扫描后确认下载
python main.py --all --workers 8           # 全部课程，每门课最多 8 个并行下载
python main.py --all --browser chrome      # 指定登录浏览器
python main.py --all --lang en             # 英文界面
```

本 README 的带参数用法统一使用 `python main.py ...`。

## 课程中文名称

中文名称通过 [config.toml](config.toml) 的 `[course_names]` 配置，**以 Moodle 课程 ID 为键**，不依赖列表序号，也不会把同名课程合并。

当前预置：

| Moodle 课程 ID | 中文显示名称 |
| --- | --- |
| `118832` | 大学微积分 I |
| `118856` | 计算机程序设计 |
| `120070` | 无机与分析化学 |
| `120178` | 中文阅读与写作 |
| `121506` | 英文 III |
| `121558` | 英文 IV |
| `121706` | 宪法与基本法概论 |
| `122014` | 科技大师讲座 |
| `122016` | 科技大师讲座 |
| `122408` | 大学生活 |

这些映射对应特定课程实例，并非学校所有学期的通用课程编号。使用其他账号或新学期课程时，根据实际 ID 添加或修改即可。

例如，课程地址为 `https://moodle.must.edu.mo/course/view.php?id=118832`，对应配置是：

```toml
[course_names]
"118832" = "大学微积分 I"
"120178" = "中文阅读与写作"
```

在现有 `[course_names]` 下编辑键值即可，不要重复创建同名配置节。保存后重新运行程序生效。

- 没有配置映射的课程仍显示 Moodle 返回的名称。
- 课程代码和 ID 保留在单独列中，便于区分班级。
- 两门“科技大师讲座”使用不同 ID，仍作为两门独立课程处理。
- 映射用于课程列表和批量同步提示；下载目录继续使用 Moodle 原始课程名 / 班级代码，不会随着中文显示名称自动改名。

## 增量下载与文件校验

每次运行同一个命令即可：

```bash
python main.py --all
```

| 本地状态 / 本次扫描结果 | 处理方式 |
| --- | --- |
| 首次运行，本地没有课件 | 下载扫描到的文件 |
| 新增资源或本地缺少某个文件 | 补下载对应文件 |
| 已有文件通过基础格式检查，且与已有校验记录一致 | 跳过文件下载 |
| 空文件、HTML 伪 PDF、明显不完整的 PDF 或无效的受检查 Office 文件 | 重新下载，校验通过后替换 |
| 本地文件的 SHA-256 与已有记录不一致 | 重新下载并更新记录 |
| 同一资源入口解析到的真实文件链接发生变化 | 重新下载并更新记录 |
| 解析失败、HTTP 错误、返回登录页或文件校验失败 | 记录失败原因，继续处理其他文件 |

每门课目录内的 `.moodle-downloads.json` 保存资源与文件名的对应关系、真实链接、大小及 SHA-256 校验和。请与课件一起保留；已有有效文件即使没有记录，也会先检查并建立记录。

下载先写临时 `.part` 文件，校验通过后再替换目标文件。替换失败时保留原文件。同名但来源不同的资源会使用稳定后缀区分。

需要区分以下行为：

- **重复运行仍会联网扫描课程和资源页面**，只是已通过检查的课件不会再次下载。
- **本地改过的课件也会被视为与记录不一致**，同步时可能被原版替换。请把批注版或自行修改的副本另存。
- **不自动删除本地旧文件**。远端移除的课件或本地其他资料会保留。
- **不保证发现同一 URL 下的远端内容替换**。目前未通过远端内容哈希、ETag 或 Last-Modified 判断这类更新；如果确认老师替换了文件但链接未变，可移走对应本地文件，再运行同步。
- 文件检查属于基础格式与完整性检查，不等同于使用阅读器验证每一页内容。

## 文件保存位置

从仓库根目录启动时，课件保存在该目录下的独立课程文件夹中。例如：

```text
moodle_downloader_for_MUST/
├── main.py
├── config.toml
├── moodle_cookies.json
└── UNIVERSITY_CALCULUS_I(大學微積分I)_-_2609-BE101EX10-C371E1/
    ├── .moodle-downloads.json
    ├── 2_Limits and Continuity.pdf
    ├── 3_Differentiation.pdf
    └── Applications of Derivatives.pdf
```

目录由 Moodle 原始课程名生成：有班级代码时保留班级区分，没有班级代码时附加课程 ID。兼容的已有课程目录会继续复用。

当前命令行流程会按课程生成相对当前工作目录的保存路径，**`[paths].save_dir` 不是全部课程的统一下载根目录**。为复用已有课件与登录缓存，请每次从同一个目录运行，并保留课程目录名称。

下载的课件属于本地资料，不应随代码提交。Cookie 和同步记录已由 `.gitignore` 排除，但并非所有课程目录名称都在忽略规则中；提交代码时请检查暂存文件列表。

## 常用配置

编辑仓库根目录的 [config.toml](config.toml)，保存后重新运行。以下为相关配置节示例，请修改现有配置节：

```toml
[network]
moodle_url = "https://moodle.must.edu.mo"
request_timeout = 30

[download]
max_workers = 24

[auth]
login_timeout = 300
login_check_interval = 1.0

[filters]
file_keywords = ["lecture"]
file_extensions = [".pdf", ".ppt", ".pptx"]

[ui]
language = "zh"

[browser]
browser = ""  # 空字符串表示自动检测；也可填 chrome、edge、firefox
```

`--workers`、`--browser`、`--lang` 会覆盖对应配置。浏览器配置项名称是 `[browser].browser`。

### 文件筛选

对于页面或文件夹中识别到的直接文件链接，文件名命中关键词**或**扩展名匹配即可保留；默认关键词为 `lecture`，扩展名为 `.pdf`、`.ppt`、`.pptx`。Moodle 的文件资源入口（`mod/resource`）会直接解析，不受这组筛选条件限制。

如果希望接受扫描器支持的全部文件类型，将两个列表都设为空：

```toml
[filters]
file_keywords = []
file_extensions = []
```

只清空其中一个列表时，另一个列表仍参与筛选。放宽筛选不会增加对外部平台或其他 Moodle 活动类型的支持。

## 本地学习与 AI 接入

下载之外，项目保留本地索引、Obsidian 导出、复习 notebook 和 MCP 服务。这些功能操作已下载的文件，**无需登录 Moodle**。

```bash
python main.py --index .                              # 索引当前目录
python main.py --obsidian vault                       # 导出 Obsidian 笔记
python main.py --obsidian vault --copy-files          # 同时复制课件
python main.py --notebook revision.ipynb --days 7     # 生成 7 天复习 notebook
```

`--index <目录>` 可以指定包含课程文件夹的根目录，并与导出参数组合使用。Obsidian 默认跳过已存在的笔记；需要重新生成时加 `--overwrite`。Notebook 会写入指定文件，保留自己的编辑时请使用新文件名。

索引保存为 `.moodle-index.json`。复习安排根据文件名推断的周次、材料类型和文件数量生成；笔记中的文字来自可提取的课件片段，不是自动生成的 AI 总结。

可选安装 PDF 文本提取库：

```bash
python -m pip install pypdf
```

当前正文提取支持 `.txt`、`.md`、`.csv` 和可提取文字的 PDF；扫描图片 PDF 没有 OCR，Office 文件目前主要按文件名和元数据索引。索引的文本预览默认最多 2,000 字符，检索范围是文件名、课程名及已提取片段，不是所有文件的完整正文。

### MCP 服务

从仓库根目录、已安装依赖的 Python 环境启动：

```bash
python -m moodle_scraper.mcp_server --root .
```

支持 stdio 的 MCP 客户端可将上述命令配置为服务。客户端的工作目录应设为仓库根目录；实际配置中使用虚拟环境 Python 和课件根目录的绝对路径，避免启动到其他环境。

| 工具 | 用途 |
| --- | --- |
| `list_courses` | 列出本地课程及材料数量 |
| `search_materials` | 搜索文件名、课程名和已提取文本片段 |
| `get_material_text` | 获取材料信息及可用文本片段 |
| `course_overview` | 按周次与类型查看课程材料 |
| `revision_plan` | 生成分天学习计划与间隔复习安排 |

例如，可以让 AI 客户端“根据大学微积分 I 的现有课件安排 5 天复习计划”。仓库内的 [moodle-revision Skill](skills/moodle-revision/SKILL.md) 提供复习工作流参考。

同步新增课件后，重新生成索引；正在运行的 MCP 服务需要重启以读取更新。MCP 服务本身在本机运行，连接云端 AI 客户端时，客户端读取的课件片段可能发送给相应服务商。

## 常见问题

### 下载的 PDF 打不开怎么办？

旧版本可能把 Moodle 的 HTML 资源展示页直接保存为 `.pdf`，又因“文件已经存在”而一直跳过。当前版本会先解析真实文件链接，并拒绝把 HTML 或登录页面计为下载成功。

在原课件目录所在位置重新运行 `python main.py --all`，或 `python main.py 118832` 同步对应课程，即可检查并补下载这类错误文件。若仍失败，查看报告中的 HTTP、登录或文件校验错误。

### 为什么没有中文课程名，或出现两门同名课？

确认 `[course_names]` 的键与当前课程 ID 一致，且配置文件是有效 TOML。课程实例可能随学期或班级变化；两门同名课只要 ID 不同就会分别保留，请结合代码和 ID 选择。

### 为什么某门课或文件没有下载？

先确认学校 Moodle 中当前账号能看到并打开该课程与文件，再检查筛选条件和最终失败报告。空课程、尚未发布的资料、不同类型的活动或外部平台内容，不会因为开启 `--all` 自动成为可下载文件。

### 浏览器打不开或登录超时怎么办？

先用 `--browser chrome`、`--browser edge` 或 `--browser firefox` 指定已安装的浏览器；根据终端错误检查对应 WebDriver、浏览器版本和网络。登录耗时较长时可以提高 `[auth].login_timeout`。会话过期后，重新运行会触发登录。

### 为什么下载结束后程序还在等待？

命令行入口会等待按 Enter 后退出，便于查看报告。批量同步仍使用这一交互流程。

### Windows 可以双击启动吗？

仓库保留了 `启动下载器.bat`，其中部分默认课程和范围选项沿用旧项目。MUST 用户请优先使用本文命令；若使用该菜单，选“列出我已注册的课程”，进入课程列表后输入 `0`。该脚本调用系统的 `python`，请确认它已安装项目依赖。

## 开发与测试

安装测试依赖并运行离线测试：

```bash
python -m pip install pytest
python -m pytest tests/ -q
```

测试覆盖课程映射、单课 / 全部同步、资源页解析、HTTP 异常、文件校验、重复下载与本地学习功能，使用模拟响应及临时目录，不依赖学校账号。

主要结构：

| 文件 / 目录 | 职责 |
| --- | --- |
| `main.py` | 参数解析及交互入口 |
| `moodle_scraper/auth.py` | 浏览器登录与会话缓存 |
| `moodle_scraper/scanner.py` | 课程列表、中文名称映射与真实文件链接解析 |
| `moodle_scraper/downloader.py` | 增量同步、并行下载与同步记录 |
| `moodle_scraper/files.py` | 基础文件检查与 SHA-256 校验 |
| `moodle_scraper/config.py` | TOML 配置读取 |
| `moodle_scraper/study/` | 本地索引、Obsidian 与 notebook |
| `moodle_scraper/mcp_server.py` | 本地 MCP 工具服务 |

提交 Issue 或 PR 请使用 [本仓库](https://github.com/FallaxAura-New/moodle_downloader_for_MUST)。代码约定见 [AGENTS.md](AGENTS.md)：保持类型注解，HTTP 行为通过 `HttpClient` 接口测试，新增界面文案同步维护中英文目录。

## English quick start

This fork adapts the downloader to **Macau University of Science and Technology (MUST)**. It supports browser login, Chinese course labels, all-course synchronization, and validation of existing downloads.

Install **Python 3.11+**, Git, and Chrome, Edge, or Firefox with an available WebDriver. On macOS / Linux:

```bash
git clone https://github.com/FallaxAura-New/moodle_downloader_for_MUST.git
cd moodle_downloader_for_MUST
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python main.py --all --lang en
```

For Windows, use the PowerShell installation instructions above. Complete the school's login in the browser opened at [MUST Moodle](https://moodle.must.edu.mo/my/). The session is cached in `moodle_cookies.json`; keep it private. Press Enter to exit after the final report.

- Run `python main.py`, then enter `0` to sync all enrolled courses, or select a single course by its displayed number / Moodle ID.
- Run `python main.py --all` again to scan for new resources and missing or invalid local files. Valid existing files are skipped; changed local hashes or changes to the recorded download URL for the same resource trigger a new download.
- Chinese labels are configured by Moodle course ID under `[course_names]` in `config.toml`. The existing ten mappings apply to specific course instances; update them for your own courses. Course codes and IDs remain visible, and equal display names do not merge courses.
- Keep each course's `.moodle-downloads.json` with its files. Downloads are stored in course folders under the working directory, using the original Moodle course name / class code.
- Local edits may be replaced during synchronization. Keep annotated copies separately. Remote changes at an unchanged URL are not guaranteed to be detected; move the local file aside to request a fresh download. Local files removed from Moodle are not automatically deleted.
- `--all` covers courses returned by the account's dashboard and supported file links, subject to filters and access. It is not a complete Moodle site backup.

Optional local tools remain available: `--index`, `--obsidian`, `--notebook`, and `python -m moodle_scraper.mcp_server --root .`. PDF text extraction requires an optional library such as `pypdf`; search uses extracted previews, not guaranteed full-document text.

## 致谢与许可证

基于 KunyQi 的 `moodle-downloader` 项目开发，保留原项目的下载架构及可选学习功能，并针对 MUST 登录、课程名称和课件同步进行适配。

采用 [MIT License](LICENSE)。
