"""澳科大校徽的终端字符线稿；不依赖图片、网络或额外字体。

参考 https://www.must.edu.mo/ 首页官方校徽：双环、原子轨道、书本与意誠格物。
图形刻意简化成普通字符，保证 Windows / macOS 等宽终端中的可读性。
"""
from __future__ import annotations

from rich.cells import cell_len
from rich.console import Console
from rich.text import Text

from . import __version__
from .config import AppConfig
from .i18n import t

BANNER_SHOWN_ENV = "MUST_MOODLE_BANNER_SHOWN"
BLUE = "#38a9e0"
GOLD = "#f2cf51"
WHITE = "#e6edf3"
MUTED = "#8b949e"

# 书页依照原校徽排列：左列格物，右列意誠。中文字属于徽章图形。
# 每行左右边界对称，内部按终端显示宽度居中（汉字占两格）。
_CREST: tuple[tuple[int, str, str, str], ...] = (
    (10, ".", "____________", "."),
    (6, ".-'", "", "'-."),
    (4, ".'", "澳 門 科 技 大 學", "'."),
    (2, ".'", ".----------------.", "'."),
    (1, "/", ".'       .-.        '.", "\\"),
    (0, "/", "/     .-/ | \\-.      \\", "\\"),
    (0, "|", r"|    ( /--o--\ )     |", "|"),
    (0, "|", r"|     '-\ | /-'      |", "|"),
    (0, "|", "|        '-'         |", "|"),
    (0, "|", "|   .----. .----.    |", "|"),
    (0, "|", r"|   | 格 \|/ 意 |    |", "|"),
    (0, "|", "|   | 物  |  誠 |    |", "|"),
    (0, "\\", r"\   |____/ \____|    /", "/"),
    (1, "\\", "'.    '---v---'     .'", "/"),
    (2, "'.", "'----------------'", ".'"),
    (4, "'.", "M U S T", ".'"),
    (6, "'-.", "", ".-'"),
    (10, "'", "------------", "'"),
)

_WORDMARK = (
    r" __  __  _   _  ____  _____",
    r"|  \/  || | | |/ ___||_   _|",
    r"| |\/| || | | |\___ \  | |",
    r"| |  | || |_| | ___) | | |",
    r"|_|  |_| \___/ |____/  |_|",
)


def _crest(*, ascii_only: bool = False) -> list[Text]:
    rows: list[Text] = []
    width = 34
    for i, (indent, left, center, right) in enumerate(_CREST):
        if ascii_only:
            center = center.replace("澳 門 科 技 大 學", "M A C A U   U S T")
            center = center.replace("格", "GE").replace("物", "WU")
            center = center.replace("意", "YI").replace("誠", "CH")
        room = width - 2 * indent - len(left) - len(right)
        padding = max(0, room - cell_len(center))
        row = Text(" " * indent + left + " " * (padding // 2), style=BLUE)
        row.append(center, style=GOLD if i <= 8 or i == 15 else WHITE)
        row.append(" " * (padding - padding // 2) + right, style=BLUE)
        rows.append(row)
    return rows


def print_startup_banner(console: Console, config: AppConfig) -> None:
    """真实字符输出；窄终端纵排，重定向输出也不含额外 ANSI 转义。"""
    encoding = console.encoding or "utf-8"
    try:
        "澳門科技大學意誠格物".encode(encoding)
        ascii_only = False
    except (UnicodeEncodeError, LookupError):
        ascii_only = True
    width = max(1, console.width)
    crest = _crest(ascii_only=ascii_only)
    name = t("banner.school_ascii" if ascii_only else "banner.school")
    details = [
        Text(name, style=f"bold {WHITE}"),
        Text(t("banner.school_en_1"), style=MUTED),
        Text(t("banner.school_en_2"), style=MUTED),
        Text(),
        Text(t("banner.product_ascii" if ascii_only else "banner.product"), style=f"bold {BLUE}"),
        Text(f"v{__version__}", style=MUTED),
        Text(config.moodle_url.rstrip("/"), style=MUTED),
    ]
    console.print()
    if width >= 72:
        right = [Text(), *[Text(line, style=f"bold {GOLD}") for line in _WORDMARK], Text(), *details]
        for index, left in enumerate(crest):
            row = left.copy()
            row.append(" " * (38 - row.cell_len))
            if index < len(right):
                row.append_text(right[index])
            console.print(row)
    else:
        if width >= 34:
            for line in crest:
                console.print(line)
        else:
            # 极窄窗口缩为书本与原子，避免把校徽强行折行。
            for line in ("     .-o-.", r"    ( /|\ )", "     '-o-'", " .----. .----.", r" |    \|/    |", r" |____/ \____|", "      MUST"):
                console.print(Text(line, style=GOLD), overflow="crop", no_wrap=True)
        console.print()
        for line in details:
            console.print(line)
    console.print(Text("-" * min(width, 82), style=BLUE))
    console.print()
