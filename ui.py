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
MIN_LYRIC_LINES = 5
CLEAR_LYRICS = "__CLEAR_LYRICS__"
SEARCH_AGAIN = "__SEARCH_AGAIN__"


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
        # 时间戳高亮
        i = 0
        while i < len(ln):
            if ln[i] == "[":
                end = ln.find("]", i)
                if end != -1:
                    colored.append(ln[i : end + 1], style="dim cyan")
                    i = end + 1
                    continue
            colored.append(ln[i])
            i += 1
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
