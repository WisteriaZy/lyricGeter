from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from fetcher.base import LyricFormat, LyricResult

from converter import to_spl

console = Console(legacy_windows=False)

_FORMAT_LABEL = {
    LyricFormat.WORD: "[bold green]逐字[/]",
    LyricFormat.LINE: "[bold cyan]行级同步[/]",
    LyricFormat.PLAIN: "[yellow]纯文本[/]",
}


def _render_preview(spl: str, title: str, artist: str, result: LyricResult) -> None:
    """用 rich 渲染 SPL 预览面板。"""
    header = Text()
    header.append(f"{title}", style="bold white")
    if artist:
        header.append(f"  —  {artist}", style="dim")
    header.append(f"\n来源: {result.source_name}  ", style="dim")
    header.append_text(Text.from_markup(_FORMAT_LABEL[result.format]))
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


def confirm_with_candidates(
    candidates: list[LyricResult],
    title: str,
    artist: str,
    *,
    dry_run: bool = False,
) -> str | None:
    """
    展示多个候选歌词，让用户选择。
    
    返回值：
    - str  → 用户选择的 SPL 内容（可能经过编辑）
    - None → 用户跳过此文件
    - 抛出 SystemExit → 用户选择退出
    """
    if not candidates:
        return None
    
    # 非交互式环境（如 CI、重定向输入）：直接返回最优候选
    if not sys.stdin.isatty():
        result = candidates[0]
        spl = result.content if result.format == LyricFormat.PLAIN else to_spl(result)
        _render_preview(spl, title, artist, result)
        console.print("[dim]（非交互式环境，自动选择最优结果）[/]")
        return spl if not dry_run else None
    
    # 第一步：选择候选
    choices = []
    for i, result in enumerate(candidates):
        format_label = _FORMAT_LABEL[result.format]
        score_text = f" (相似度: {result.score:.0f})" if result.score > 0 and result.score < 100 else ""
        label = f"{i+1}. {result.source_name} - {Text.from_markup(format_label).plain}{score_text}"
        choices.append(questionary.Choice(label, value=i))
    
    choices.append(questionary.Choice("跳过此文件", value="skip"))
    choices.append(questionary.Choice("退出程序", value="quit"))
    
    console.print(f"\n[bold]{title}[/]" + (f" — [dim]{artist}[/]" if artist else ""))
    console.print(f"找到 {len(candidates)} 个候选歌词：\n")
    
    try:
        selection = questionary.select(
            "选择歌词来源：",
            choices=choices,
        ).ask()
    except Exception as e:
        # questionary 在某些环境下可能失败，回退到简单输入
        console.print(f"[yellow]交互菜单不可用: {e}[/]")
        console.print("[dim]自动选择最优结果[/]")
        selection = 0
    
    if selection is None or selection == "quit":
        raise SystemExit(0)
    if selection == "skip":
        return None
    
    # 第二步：预览并确认
    result = candidates[selection]
    spl = result.content if result.format == LyricFormat.PLAIN else to_spl(result)
    
    _render_preview(spl, title, artist, result)
    
    if dry_run:
        console.print("[dim]（dry-run 模式，不写入）[/]")
        return None
    
    # 第三步：操作选择
    try:
        action = questionary.select(
            "操作：",
            choices=[
                questionary.Choice("接受并写入", value="accept"),
                questionary.Choice("返回重新选择", value="back"),
                questionary.Choice("手动编辑后写入", value="edit"),
                questionary.Choice("跳过此文件", value="skip"),
                questionary.Choice("退出程序", value="quit"),
            ],
        ).ask()
    except Exception:
        # 非交互式环境，自动接受
        console.print("[dim]（非交互式环境，自动接受）[/]")
        action = "accept"
    
    if action is None or action == "quit":
        raise SystemExit(0)
    if action == "skip":
        return None
    if action == "back":
        # 递归调用，让用户重新选择
        return confirm_with_candidates(candidates, title, artist, dry_run=dry_run)
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
