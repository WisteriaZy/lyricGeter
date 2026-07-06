from __future__ import annotations

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from fetcher.base import LyricFormat, LyricResult

from converter import to_spl, extract_translation_lrc, merge_translation
from llm_verify import llm_available, verify_translation_alignment

console = Console(legacy_windows=False)

_FORMAT_LABEL = {
    LyricFormat.WORD: "[bold green]逐字[/]",
    LyricFormat.LINE: "[bold cyan]行级同步[/]",
    LyricFormat.PLAIN: "[yellow]纯文本[/]",
}
_TIMESTAMP_LINE_RE = re.compile(r"^\s*\[\d{1,3}:\d{1,2}[.:]\d{1,6}\]")
# 匹配行内的 [] 与 <> 时间戳，高亮用
_TS_SPAN_RE = re.compile(r"(\[\d{1,3}:\d{1,2}[.:]\d{1,6}\]|<\d{1,3}:\d{1,2}[.:]\d{1,6}>)")
MIN_LYRIC_LINES = 5
CLEAR_LYRICS = "__CLEAR_LYRICS__"
SEARCH_AGAIN = "__SEARCH_AGAIN__"


def _append_line_colored(text: Text, line: str, *, default_style: str = "") -> None:
    """把一行歌词追加到 Text，高亮所有 [] 与 <> 时间戳。

    default_style 仅应用于非时间戳文本（用于 diff 视图整行变红等场景）。
    """
    pos = 0
    for m in _TS_SPAN_RE.finditer(line):
        if m.start() > pos:
            text.append(line[pos:m.start()], style=default_style)
        text.append(m.group(1), style="dim cyan" if not default_style else default_style)
        pos = m.end()
    if pos < len(line):
        text.append(line[pos:], style=default_style)


def _format_duration(duration_ms: int) -> str:
    """毫秒 → m:ss 格式，0 表示未知。"""
    if not duration_ms:
        return ""
    total_seconds = duration_ms // 1000
    return f"{total_seconds // 60}:{total_seconds % 60:02d}"


def _line_has_timestamp(line: str) -> bool:
    return bool(_TIMESTAMP_LINE_RE.match(line))


def summarize_spl(spl: str, *, translation_hint: bool = False) -> tuple[int, bool]:
    """返回总行数（含翻译行）和是否带翻译。"""
    non_empty_lines = [line.strip() for line in spl.splitlines() if line.strip()]
    timed_indices = [i for i, line in enumerate(non_empty_lines) if _line_has_timestamp(line)]

    if timed_indices:
        line_count = len(non_empty_lines)
        has_translation = translation_hint or any(
            i > 0 and _line_has_timestamp(non_empty_lines[i - 1])
            for i, line in enumerate(non_empty_lines)
            if not _line_has_timestamp(line)
        )
    else:
        line_count = len(non_empty_lines)
        has_translation = translation_hint

    return line_count, has_translation


def result_to_spl(result: LyricResult) -> str:
    spl = result.content if result.format == LyricFormat.PLAIN else to_spl(result)
    return spl if isinstance(spl, str) else str(spl)


def summarize_result(result: LyricResult) -> tuple[int, bool, str]:
    spl = result_to_spl(result)
    line_count, has_translation = summarize_spl(
        spl,
        translation_hint=bool(result.translation),
    )
    return line_count, has_translation, spl


def _visual_width(s: str) -> int:
    """估算终端显示宽度：CJK 与全角字符算 2，其余算 1。"""
    width = 0
    for ch in s:
        code = ord(ch)
        if (
            0x1100 <= code <= 0x115F        # Hangul Jamo
            or 0x2E80 <= code <= 0x303E    # CJK 形意文字、标点
            or 0x3041 <= code <= 0x33FF    # 假名/注音
            or 0x3400 <= code <= 0x4DBF    # CJK 扩展 A
            or 0x4E00 <= code <= 0x9FFF    # CJK 统一汉字
            or 0xA000 <= code <= 0xA4CF    # 彝文音节
            or 0xAC00 <= code <= 0xD7A3    # 韩文音节
            or 0xF900 <= code <= 0xFAFF    # CJK 兼容表意
            or 0xFE30 <= code <= 0xFE4F    # CJK 兼容形式
            or 0xFF00 <= code <= 0xFF60    # 全角 ASCII
            or 0xFFE0 <= code <= 0xFFE6    # 全角符号
        ):
            width += 2
        else:
            width += 1
    return width


def _pad_visual(s: str, target_width: int) -> str:
    """按视觉宽度右补空格到 target_width；超出则原样返回。"""
    pad = target_width - _visual_width(s)
    return s + " " * pad if pad > 0 else s


def _candidate_label(result: LyricResult, index: int | None = None) -> str:
    line_count, has_translation, _ = summarize_result(result)
    format_text = Text.from_markup(_FORMAT_LABEL[result.format]).plain
    score_text = f"相似度:{result.score:.0f}" if 0 < result.score < 100 else ""
    duration_text = f"时长 {_format_duration(result.duration_ms)}" if result.duration_ms else ""
    translation_text = "有翻译" if has_translation else "无翻译"

    # 按列对齐（视觉宽度補偿 CJK 双宽字符）
    cols = [
        _pad_visual(result.source_name, 12),  # 来源
        _pad_visual(format_text, 8),          # 格式：逐字(4) 行级同步(8) 纯文本(6)
        _pad_visual(f"{line_count}行", 6),    # 行数
        _pad_visual(translation_text, 6),      # 翻译：有/无翻译 均 6
        _pad_visual(duration_text, 10),        # 时长
        score_text,                            # 相似度（末列不补齐）
    ]
    label = " ".join(cols).rstrip()
    prefix = f"{index}. " if index is not None else ""
    return f"{prefix}{label}"


def _render_preview(spl: str, title: str, artist: str, result: LyricResult) -> None:
    """用 rich 渲染 SPL 预览面板。"""
    header = Text()
    header.append(f"{title}", style="bold white")
    if artist:
        header.append(f"  —  {artist}", style="dim")
    header.append(f"\n来源: {result.source_name}  ", style="dim")
    header.append_text(Text.from_markup(_FORMAT_LABEL[result.format]))
    line_count, has_translation = summarize_spl(spl, translation_hint=bool(result.translation))
    header.append(f"  {line_count}行  {'有翻译' if has_translation else '无翻译'}", style="dim")
    if result.duration_ms:
        header.append(f"  时长 {_format_duration(result.duration_ms)}", style="dim")
    if result.score > 0:
        header.append(f"  相似度: {result.score:.0f}", style="dim")

    # 预览前30行
    lines = spl.splitlines()
    preview_lines = lines[:30]
    if len(lines) > 30:
        preview_lines.append(f"… 共 {len(lines)} 行")

    colored = Text()
    for ln in preview_lines:
        _append_line_colored(colored, ln)
        colored.append("\n")

    console.print(Panel(colored, title=header, border_style="blue", padding=(0, 1)))


def _open_editor(spl: str) -> str:
    """在 $EDITOR 中打开临时文件供用户编辑，返回编辑后内容。"""
    editor = os.environ.get("EDITOR", "notepad" if os.name == "nt" else "nano")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".spl", delete=False, encoding="utf-8"
    ) as f:
        f.write(spl)
        tmp = f.name
    try:
        subprocess.call([editor, tmp])
        return Path(tmp).read_text(encoding="utf-8")
    finally:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _simple_select(prompt: str, choices: list[tuple[str, object]]) -> object:
    """简单的文本选择菜单，用于 questionary 不可用时的回退。"""
    console.print(f"\n[bold]{prompt}[/]")
    for i, (label, _) in enumerate(choices, 1):
        console.print(f"  {i}. {label}")

    try:
        user_input = input("\n请输入选项编号: ").strip()
        idx = int(user_input) - 1
        if 0 <= idx < len(choices):
            return choices[idx][1]
    except (ValueError, KeyboardInterrupt, EOFError):
        pass
    return None


def _strip_translation_from_spl(spl: str) -> str:
    """移除 SPL 中的翻译行（无时间戳行），仅保留带时间戳的主歌词行。"""
    return "\n".join(
        line for line in spl.splitlines()
        if line.strip() and _line_has_timestamp(line.strip())
    )


# 前导非歌词信息识别
# 这些关键词若出现在一行文本中（且回收后正文长度较短），认定其为元数据而非歌词
_METADATA_KEYWORDS = (
    "作词", "作曲", "词作者", "曲作者",
    "编曲", "编配", "混音", "混响", "制作", "制作人",
    "统筹", "企划", "出品", "发行", "出版",
    "OP", "SP", "版权", "特别鸣谢",
    "录音", "母带", "和声", "和声编写", "和声设计",
    "Executive Producer", "Producer", "Arranger",
    "Engineer", "Mixed", "Mastering", "Mastered",
    "封面", "摄影", "海报", "插画", "裝帧",
    "MV", "导演", "剪辑", "后期",
    "lyricist", "composer",
    # 英文常见写法
    "Composed", "Composed by", "Written by", "Lyrics by",
    "Vocals by", "Vocal by", "Sung by", "Performed by",
    "Guitar by", "Bass by", "Drums by", "Keyboard by",
    "Strings by", "Rap by", "Arranged by",
    "Music by", "Words by", "Text by",
)
_PURE_MUSIC_RE = re.compile(r"纯音乐.*请欣赏")
# SPL 内时间戳/延迟标记（00:01.00）用于剥离重构正文以判断是否元数据
_INLINE_TS_RE = re.compile(r"[\[<]\d+:\d{1,2}[.:]\d{1,6}[>\]]")


def _is_header_line(text: str) -> bool:
    """判断单行是否为歌词前的「非歌词」内容。

    包含：空行、注释/分隔行（//、#、--）、元数据关键词行、
    纯音乐提示、以及以冒号结尾的短身份标注行（如「演唱者：」）。
    """
    stripped = _INLINE_TS_RE.sub("", text).strip()
    if not stripped:
        return True  # 空行在头部块里允许存在
    # 注释 / 分隔行
    if stripped.startswith("//") or stripped.startswith("#"):
        return True
    if stripped in ("--", "---"):
        return True
    if _PURE_MUSIC_RE.search(stripped):
        return True
    if len(stripped) > 80:
        return False
    if any(kw in stripped for kw in _METADATA_KEYWORDS):
        return True
    # 中文以冒号结尾的短身份标注行（如「演唱者：」「Vocals：」）
    if stripped.endswith(("：", ":")) and len(stripped) < 25:
        return True
    return False


def _detect_leading_non_lyric(lines: list[str]) -> int:
    """返回从开头连续的非歌词行数，作为交互式去除的初始建议。

    会进行一次前瞻：若开头某行本身不判为非歌词，但紧随其后又有非歌词行
    （如标题行后面跟着 // 注释），把中间这个疑似标题行一并计入。
    """
    n = 0
    i = 0
    while i < len(lines):
        text = lines[i].strip()
        if _is_header_line(text):
            n += 1
            i += 1
            continue
        # 若仍在前 3 行内，且后面几行里有非歌词行，
        # 认为这个是被定位为标题的歌词行，一并去除
        if i < 3:
            ahead = [lines[j].strip() for j in range(i + 1, min(i + 4, len(lines)))]
            ahead_nonempty = [t for t in ahead if t]
            if ahead_nonempty and _is_header_line(ahead_nonempty[0]):
                n += 1
                i += 1
                continue
        break
    return n


def _render_strip_frame(lines: list[str], n: int, detected_n: int, n_total: int) -> None:
    """用 rich 渲染一帧去除预览，高亮时间戳、删除行全红。"""
    frame = Text()
    frame.append("智能去除前导非歌词信息\n", style="bold cyan")
    frame.append("↑ 减少  ↓ 增加 删除行数  |  Enter 确认写入  |  Esc 取消\n\n", style="dim")
    max_preview = 40
    for i, line in enumerate(lines):
        if i >= max_preview:
            frame.append(f"… 共 {n_total} 行，仅显示前 {max_preview} 行\n", style="dim")
            break
        if i < n:
            frame.append(f"- {i + 1:4d}| ", style="red")
            _append_line_colored(frame, line, default_style="red")
            frame.append("\n")
        else:
            frame.append(f"  {i + 1:4d}| ", style="dim")
            _append_line_colored(frame, line)
            frame.append("\n")
    frame.append("\n")
    status = f"将删除前 {n} 行，保留 {n_total - n} 行"
    if n != detected_n:
        status += f"  （自动检测 {detected_n} 行）"
    frame.append(status, style="bold yellow")
    console.print(frame)


def _strip_leading_interactive(spl: str) -> str | None:
    """交互式去除前导非歌词信息。

    Windows 上用 msvcrt 读单个键静，上下方向键调整删除范围，Enter 确认，Esc 取消。
    不依赖 prompt_toolkit 全屏应用，避免在 questionary 会话中嵌套启动出错。

    返回值：
    - str：用户确认后的 SPL（前 N 行已删除；N 可能为 0，等于原样）
    - None：用户取消，调用方应保留原 spl 不变
    """
    lines = spl.splitlines()
    n_total = len(lines)
    if n_total == 0:
        return spl
    detected_n = _detect_leading_non_lyric(lines)
    n = detected_n

    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return _strip_leading_simple(spl)

    try:
        import msvcrt
    except ImportError:
        return _strip_leading_simple(spl)

    try:
        while True:
            console.clear()
            _render_strip_frame(lines, n, detected_n, n_total)
            try:
                ch = msvcrt.getch()
            except (OSError, KeyboardInterrupt):
                return None
            if ch in (b"\r", b"\n"):
                return "\n".join(lines[n:])
            if ch in (b"\x1b", b"\x03"):
                return None  # Esc / Ctrl-C 视为取消
            if ch in (b"\xe0", b"\x00"):
                try:
                    ch2 = msvcrt.getch()
                except (OSError, KeyboardInterrupt):
                    return None
                if ch2 == b"H" and n > 0:        # ↑
                    n -= 1
                elif ch2 == b"P" and n < n_total:  # ↓
                    n += 1
                # 其余特殊键忽略
            # 其余普通键忽略；只接受方向键 / Enter / Esc / Ctrl-C
    except Exception:
        # 任何意外都回退到简单模式，避免微交互袉住主流程
        return _strip_leading_simple(spl)


def _strip_leading_simple(spl: str) -> str | None:
    """非交互式回退：基于自动检测或文本输入。"""
    lines = spl.splitlines()
    n_total = len(lines)
    if n_total == 0:
        return spl
    detected_n = _detect_leading_non_lyric(lines)

    console.print("\n[bold cyan]智能去除前导非歌词信息[/]")
    console.print(f"[dim]自动检测到前 {detected_n} 行疑似非歌词信息[/]\n")

    frame = Text()
    for i, line in enumerate(lines[:25]):
        if i < detected_n:
            frame.append(f"~ {i + 1:3d}| ", style="red")
            _append_line_colored(frame, line, default_style="red")
            frame.append("\n")
        else:
            frame.append(f"  {i + 1:3d}| ", style="dim")
            _append_line_colored(frame, line)
            frame.append("\n")
    if n_total > 25:
        frame.append(f"… 共 {n_total} 行\n", style="dim")
    console.print(frame)

    try:
        raw = input(
            f"\n删除前几行？(0-{n_total}, 回车=接受自动检测 {detected_n}, n=取消): "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        return None

    if not raw:
        return "\n".join(lines[detected_n:])
    if raw.lower() in ("n", "q", "cancel", "no"):
        return None
    try:
        n = int(raw)
    except ValueError:
        console.print("[yellow]输入无效，已取消[/]")
        return None
    if 0 <= n <= n_total:
        return "\n".join(lines[n:])
    console.print("[yellow]行数超出范围，已取消[/]")
    return None



def _select_translation_source(
    candidates: list[LyricResult],
    exclude_index: int,
    use_questionary: bool,
) -> str | None:
    """让用户选择翻译来源，返回翻译 LRC 文本或 None。"""
    trans_choices: list[tuple[str, int]] = []
    for i, result in enumerate(candidates):
        if i == exclude_index:
            continue
        trans_lrc = extract_translation_lrc(result)
        if trans_lrc:
            line_count, _, _ = summarize_result(result)
            label = f"{result.source_name} - 有翻译 ({line_count}行)"
            trans_choices.append((label, i))

    if not trans_choices:
        console.print("[yellow]没有其他带翻译的候选歌词可合并[/]")
        return None

    trans_choices.append(("取消（不合并翻译）", -1))

    if use_questionary:
        from questionary import Choice
        choices = [Choice(label, value=idx) for label, idx in trans_choices]
        sel = questionary.select("选择翻译来源：", choices=choices).ask()
    else:
        sel = _simple_select("选择翻译来源：", trans_choices)

    if sel is None or sel == -1:
        return None

    return extract_translation_lrc(candidates[sel])


def confirm_with_candidates(
    candidates: list[LyricResult],
    title: str,
    artist: str,
    *,
    dry_run: bool = False,
    track_duration_ms: int = 0,
) -> str | None:
    """
    展示多个候选歌词，让用户选择。

    返回值：
    - str  → 用户选择的 SPL 内容（可能经过编辑）
    - CLEAR_LYRICS → 用户选择按纯音乐处理，清除歌词标签
    - SEARCH_AGAIN → 用户希望重新搜索并选择平台歌曲
    - None → 用户跳过此文件
    - 抛出 SystemExit → 用户选择退出
    """
    if not candidates:
        return None

    # 非交互式环境（如 CI、重定向输入）：直接返回最优候选
    if not sys.stdin.isatty():
        result = candidates[0]
        line_count, _, spl = summarize_result(result)
        _render_preview(spl, title, artist, result)
        if line_count < MIN_LYRIC_LINES:
            console.print("[dim]（非交互式环境，少于5行，按纯音乐处理）[/]")
            return CLEAR_LYRICS
        console.print("[dim]（非交互式环境，自动选择最优结果）[/]")
        return spl

    title_line = f"\n[bold]{title}[/]" + (f" — [dim]{artist}[/]" if artist else "")
    if track_duration_ms:
        title_line += f"  [dim]时长 {_format_duration(track_duration_ms)}[/]"
    console.print(title_line)
    console.print(f"找到 {len(candidates)} 个候选歌词：\n")

    # 尝试使用 questionary，失败则回退到简单文本输入
    use_questionary = sys.stdout.isatty()

    while True:
        # 第一步：选择候选
        if use_questionary:
            choices = [
                questionary.Choice(_candidate_label(result, i + 1), value=i)
                for i, result in enumerate(candidates)
            ]
            choices.append(questionary.Choice("再次搜索并选择歌曲", value="search_again"))
            choices.append(questionary.Choice("按纯音乐处理（清除歌词标签）", value="instrumental"))
            choices.append(questionary.Choice("跳过此文件", value="skip"))
            choices.append(questionary.Choice("退出程序", value="quit"))

            try:
                selection = questionary.select(
                    "选择歌词来源：",
                    choices=choices,
                ).ask()
            except Exception as e:
                console.print(f"[yellow]questionary 不可用: {e}[/]")
                console.print("[dim]切换到简单文本输入模式[/]")
                use_questionary = False
                continue
        else:
            choices = [
                (_candidate_label(result), i)
                for i, result in enumerate(candidates)
            ]
            choices.append(("再次搜索并选择歌曲", "search_again"))
            choices.append(("按纯音乐处理（清除歌词标签）", "instrumental"))
            choices.append(("跳过此文件", "skip"))
            choices.append(("退出程序", "quit"))

            selection = _simple_select("选择歌词来源：", choices)
            if selection is None:
                # 无法交互（如 EOFError），回退到自动模式
                result = candidates[0]
                line_count, _, spl = summarize_result(result)
                if line_count < MIN_LYRIC_LINES:
                    console.print("[dim]无法进行交互输入，少于5行，按纯音乐处理[/]")
                    return CLEAR_LYRICS
                console.print("[dim]无法进行交互输入，自动选择最优结果[/]")
                _render_preview(spl, title, artist, result)
                return spl

        if selection is None or selection == "quit":
            raise SystemExit(0)
        if selection == "skip":
            return None
        if selection == "search_again":
            return SEARCH_AGAIN
        if selection == "instrumental":
            console.print("[dim]已选择按纯音乐处理，将清除歌词标签[/]")
            return CLEAR_LYRICS

        # 第二步：生成基础 SPL，进入操作循环（允许合并翻译后继续操作）
        result = candidates[selection]
        _, _, spl = summarize_result(result)

        while True:  # 操作循环
            _render_preview(spl, title, artist, result)

            if dry_run:
                console.print("[dim]（dry-run 模式，不写入）[/]")
                return spl

            _, spl_has_translation = summarize_spl(spl, translation_hint=bool(result.translation))

            # 第三步：操作选择
            if use_questionary:
                try:
                    action_choices_q = [
                        questionary.Choice("接受并写入", value="accept"),
                        questionary.Choice("接受并写入（去除前导非歌词信息）", value="strip_leading"),
                        questionary.Choice("选择翻译来源合并", value="merge_translation"),
                    ]
                    if spl_has_translation:
                        action_choices_q.append(
                            questionary.Choice(
                                "LLM 校验翻译对齐" + ("" if llm_available() else "（未配置）"),
                                value="llm_verify",
                            )
                        )
                    action_choices_q.extend([
                        questionary.Choice("返回重新选择", value="back"),
                        questionary.Choice("手动编辑后写入", value="edit"),
                        questionary.Choice("再次搜索并选择歌曲", value="search_again"),
                        questionary.Choice("按纯音乐处理（清除歌词标签）", value="instrumental"),
                        questionary.Choice("跳过此文件", value="skip"),
                        questionary.Choice("退出程序", value="quit"),
                    ])
                    action = questionary.select(
                        "操作：",
                        choices=action_choices_q,
                    ).ask()
                except Exception:
                    use_questionary = False
                    continue
            else:
                action_choices = [
                    ("接受并写入", "accept"),
                    ("接受并写入（去除前导非歌词信息）", "strip_leading"),
                    ("选择翻译来源合并", "merge_translation"),
                ]
                if spl_has_translation:
                    action_choices.append(("LLM 校验翻译对齐", "llm_verify"))
                action_choices.extend([
                    ("返回重新选择", "back"),
                    ("手动编辑后写入", "edit"),
                    ("再次搜索并选择歌曲", "search_again"),
                    ("按纯音乐处理（清除歌词标签）", "instrumental"),
                    ("跳过此文件", "skip"),
                    ("退出程序", "quit"),
                ])
                action = _simple_select("操作：", action_choices)
                if action is None:
                    # 无法交互，默认接受
                    console.print("[dim]无法交互，自动接受[/]")
                    action = "accept"

            if action is None or action == "quit":
                raise SystemExit(0)
            if action == "skip":
                return None
            if action == "back":
                break  # 回到外层循环，重新选择候选
            if action == "search_again":
                return SEARCH_AGAIN
            if action == "instrumental":
                return CLEAR_LYRICS
            if action == "merge_translation":
                trans_lrc = _select_translation_source(
                    candidates, selection, use_questionary
                )
                if trans_lrc:
                    stripped = _strip_translation_from_spl(spl)
                    spl = merge_translation(stripped, trans_lrc)
                    if llm_available():
                        console.print("[dim]合并完成，可选「LLM 校验翻译对齐」检查结果[/]")
                continue  # 重新渲染预览
            if action == "llm_verify":
                verdict = verify_translation_alignment(spl)
                console.print(Panel(verdict, title="LLM 翻译对齐校验", border_style="magenta"))
                continue  # 校验只看不动，回到操作循环
            if action == "strip_leading":
                stripped = _strip_leading_interactive(spl)
                if stripped is None:
                    continue  # 用户取消，回到操作循环
                return stripped  # 去除后写入
            if action == "edit":
                edited = _open_editor(spl)
                return edited if edited.strip() else None
            return spl  # accept


def confirm(
    spl: str,
    title: str,
    artist: str,
    result: LyricResult,
    *,
    auto: bool = False,
    dry_run: bool = False,
) -> str | None:
    """
    展示 SPL 预览并请用户确认。（旧版单候选接口，保留向后兼容）

    返回值：
    - str  → 用户接受的 SPL 内容（可能经过编辑）
    - None → 用户跳过此文件
    - 抛出 SystemExit → 用户选择退出
    """
    _render_preview(spl, title, artist, result)

    if dry_run:
        console.print("[dim]（dry-run 模式，不写入）[/]")
        return None

    if auto:
        console.print("[green]✓ 自动接受[/]")
        return spl

    choice = questionary.select(
        "操作：",
        choices=[
            questionary.Choice("接受并写入", value="accept"),
            questionary.Choice("跳过此文件", value="skip"),
            questionary.Choice("手动编辑后写入", value="edit"),
            questionary.Choice("退出程序", value="quit"),
        ],
    ).ask()

    if choice is None or choice == "quit":
        raise SystemExit(0)
    if choice == "skip":
        return None
    if choice == "edit":
        edited = _open_editor(spl)
        return edited if edited.strip() else None
    return spl  # accept
