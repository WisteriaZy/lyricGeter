from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

import questionary
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from fetcher.base import LyricFormat, LyricResult

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
    展示 SPL 预览并请用户确认。

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
