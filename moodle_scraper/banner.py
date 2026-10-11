"""澳科大校徽的紧凑终端描线：双环、三个椭圆轨道及展开书页。

参考 https://www.must.edu.mo/ 首页官方校徽，以 56 x 48 点网格描线，
用 Unicode Braille 字符保存轮廓；常规终端共 12 行，不加载图片或访问网络。
旧 Windows 控制台及不支持相应编码的终端使用普通字符回退。
"""
from __future__ import annotations

from itertools import zip_longest

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

# 原子轨道取 30 / 90 / 150 度，书页保留弧形页边、双层封面和中缝。
# 书页字序遵照原校徽：左列格物，右列意誠。各段已按终端单元格对齐。
_CREST: tuple[tuple[tuple[str, str], ...], ...] = (
    (('        ⣀⡤⠴⠒⠒⠚⠒⠒⠒⠦⢤⣀        ', BLUE),),
    (('     ⢀⡴⠊⣡⠴⠚⠉⠉', BLUE), ('⣩⣍', GOLD), ('⠉⠉⠓⠦⣌⠑⢦⡀     ', BLUE),),
    (('    ⡰⠋⡴⠋  ', BLUE), ('⢠⠤⢤⣇⣸⡤⠤⡄', GOLD), ('  ⠙⢦⠙⢆    ', BLUE),),
    (('   ⡼⢁⡞    ', BLUE), ('⠈⣳⢴⡏⢽⡦⣞⠁', GOLD), ('    ⢳⡈⢧   ', BLUE),),
    (('  ⢰⠃⡞     ', BLUE), ('⠸⠥⠴⡟⢻⠦⠬⠇', GOLD), ('     ⢳⠘⡆  ', BLUE),),
    (('  ⢸ ⡇   ', BLUE), ('⣀⣀⣀⡀', WHITE), (' ', BLUE), ('⠳⠞', GOLD), (' ', BLUE), ('⢀⣀⣀⣀', WHITE), ('   ⢸ ⡇  ', BLUE),),
    (('  ⢹ ⡇  ', BLUE), ('⡤⡇', WHITE), ('  ', BLUE), ('⠉⠙⠲⡖⠊⠉', WHITE), ('  ', BLUE), ('⢸⢤', WHITE), ('  ⢸⠁⡇  ', BLUE),),
    (('  ⠸⡄⢧  ', BLUE), ('⡇⡇格', WHITE), ('   ', BLUE), ('⡇', WHITE), ('  ', BLUE), ('意⢸⢸', WHITE), ('  ⡼⢠⠇  ', BLUE),),
    (('   ⢳⡈⢧ ', BLUE), ('⡇⡇物', WHITE), ('   ', BLUE), ('⡇', WHITE), ('  ', BLUE), ('誠⢸⢸', WHITE), (' ⡼⢁⡞   ', BLUE),),
    (('    ⠱⣄⠳', BLUE), ('⣗⠓⠒⠒⠲⣄', WHITE), (' ', BLUE), ('⡇⣠⠴⠒⠒⠚⣺', WHITE), ('⠞⣠⠎    ', BLUE),),
    (('     ⠈⠳⢄⡙⠲⢤⣀', BLUE), ('⣈⣉⣉⣁', WHITE), ('⣀⡤⠖⢋⡠⠞⠁     ', BLUE),),
    (('        ⠉⠓⠲⠤⠤⠤⠥⠤⠤⠖⠚⠉        ', BLUE),),
)

_WORDMARK = (
    r" __  __  _   _  ____  _____",
    r"|  \/  || | | |/ ___||_   _|",
    r"| |\/| || | | |\___ \  | |",
    r"| |  | || |_| | ___) | | |",
    r"|_|  |_| \___/ |____/  |_|",
)

# 非 Unicode 控制台仍能看清原子和书页，不依赖特殊字形。
_ASCII_CREST = (
    r"       .-----------.",
    r"    .-'   .-.-.     '-.",
    r"  .'    .'\ | /'.     '.",
    r" /      (_-\o/-_)       \ ",
    r"|         '-'-'          |",
    r"|    .----._ _.----.     |",
    r"|    | 格  \|/ 意 |     |",
    r"|    | 物   |  誠 |     |",
    r" \   |_____/ \____|    /",
    r"  '.    '---v---'    .'",
    r"    '-.__________.-'",
)

_SMALL_CREST = (
    r"      .-(-)-.",
    r"     (\ / \ /)",
    r"     (/- o -\)",
    r"      '-(-)-'",
    r"  .----._ _.----.",
    r"  | 格  \|/ 意 |",
    r"  | 物   |  誠 |",
    r"  |_____/ \____|",
)


def _encodable(text: str, encoding: str) -> bool:
    try:
        text.encode(encoding)
        return True
    except (UnicodeEncodeError, LookupError):
        return False


def _plain_crest(lines: tuple[str, ...], *, ascii_only: bool) -> list[Text]:
    rows: list[Text] = []
    for line in lines:
        if ascii_only:
            line = line.replace("格", "GE").replace("物", "WU")
            line = line.replace("意", "YI").replace("誠", "CH")
        rows.append(Text(line, style=GOLD))
    return rows


def _crest() -> list[Text]:
    return [Text.assemble(*row) for row in _CREST]


def print_startup_banner(console: Console, config: AppConfig) -> None:
    """标准宽度开场含分隔线和空行共 14 行；48 列窗口最多 15 行。"""
    encoding = console.encoding or "utf-8"
    ascii_only = not _encodable("澳門科技大學意誠格物", encoding)
    detailed = not ascii_only and not console.legacy_windows and _encodable("⠒⢧⣉", encoding)
    width = max(1, console.width)
    name = t("banner.school_ascii" if ascii_only else "banner.school")
    product = t("banner.product_ascii" if ascii_only else "banner.product")
    site = config.moodle_url.rstrip("/")

    if width < 44:
        console.print(Text(name, style=f"bold {WHITE}"))
        for line in _plain_crest(_SMALL_CREST, ascii_only=ascii_only):
            console.print(line, overflow="crop", no_wrap=True)
        console.print(Text(product, style=f"bold {BLUE}"))
        console.print(Text(site, style=MUTED))
    else:
        crest = _crest() if detailed else _plain_crest(_ASCII_CREST, ascii_only=ascii_only)
        if width >= 68:
            right = [
                *[Text(line, style=f"bold {GOLD}") for line in _WORDMARK],
                Text(),
                Text(name, style=f"bold {WHITE}"),
                Text(t("banner.school_en_1"), style=MUTED),
                Text(t("banner.school_en_2"), style=MUTED),
                Text(product, style=f"bold {BLUE}"),
                Text(f"v{__version__}  {site}", style=MUTED),
            ]
        else:
            right = [
                Text("MUST", style=f"bold {GOLD}"),
                Text(t("banner.school_compact_ascii") if ascii_only else name, style=f"bold {WHITE}"),
                Text(),
                Text(t("banner.product_short_ascii" if ascii_only else "banner.product_short"), style=BLUE),
                Text(f"v{__version__}", style=MUTED),
            ]
        for left, description in zip_longest(crest, right, fillvalue=Text()):
            row = left.copy()
            row.append(" " * max(0, 30 - row.cell_len))
            row.append_text(description)
            console.print(row)
        if width < 68:
            console.print(Text(site, style=MUTED))
    console.print(Text("-" * min(width, 82), style=BLUE))
    console.print()
