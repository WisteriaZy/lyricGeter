from __future__ import annotations

import sys

# Windows 终端默认 GBK，强制 UTF-8 避免日文/中文字符编码错误
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from fetcher import SyncedLyricsFetcher, NetEaseApi
from fetcher.kugou import KugouFetcher
from fetcher.qqmusic import QQMusicFetcher
from fetcher.base import LyricFormat, LyricResult
from scanner import scan, TrackInfo
from matcher import find_best, find_all
from converter import to_spl
from writer import write_spl
from ui import confirm, console as ui_console

_PROVIDER_MAP = {
    "netease": ["NetEase"],
    "lrclib": ["Lrclib"],
    "musixmatch": ["Musixmatch"],
    "all": None,  # None → 使用全部默认 provider
}

err_console = Console(stderr=True, style="red", legacy_windows=False)


def _fetch_results(
    track: TrackInfo,
    fetcher: SyncedLyricsFetcher,
    threshold: float,
    prefer_local: bool,
    use_netease: bool,
    use_kugou: bool,
    use_qqmusic: bool,
) -> list[LyricResult]:
    """网络搜索阶段，返回所有候选结果。"""
    if not track.title:
        return []
    
    fetchers = []
    # 网易云 API 优先（支持逐字歌词）
    if use_netease:
        fetchers.append(NetEaseApi())
    # QQ 音乐 API（支持逐字歌词 + 翻译 + 罗马音）
    if use_qqmusic:
        fetchers.append(QQMusicFetcher())
    # 酷狗 API（支持逐字歌词 + 翻译）
    if use_kugou:
        fetchers.append(KugouFetcher())
    # syncedlyrics 作为兜底
    fetchers.append(fetcher)
    
    return find_all(track, fetchers, threshold=threshold, prefer_local=prefer_local)


@click.command()
@click.argument("path", type=click.Path(exists=True, path_type=Path))
@click.option("--auto", is_flag=True, help="跳过确认，自动写入最优结果")
@click.option("--dry-run", is_flag=True, help="只预览，不写入文件")
@click.option(
    "--source",
    type=click.Choice(["netease", "lrclib", "musixmatch", "all"], case_sensitive=False),
    default="all",
    show_default=True,
    help="指定歌词来源",
)
@click.option("--threshold", type=float, default=70.0, show_default=True, help="相似度阈值 (0-100)")
@click.option("--lang", default="zh", show_default=True, help="翻译语言代码，留空则不获取翻译")
@click.option("--prefer-local", is_flag=True, help="优先使用本地内嵌歌词（默认优先在线）")
@click.option("--netease/--no-netease", default=True, show_default=True, help="启用/禁用网易云 API")
@click.option("--kugou/--no-kugou", default=True, show_default=True, help="启用/禁用酷狗 API")
@click.option("--qqmusic/--no-qqmusic", default=False, show_default=True, help="启用/禁用 QQ 音乐 API（当前无效）")
def main(
    path: Path,
    auto: bool,
    dry_run: bool,
    source: str,
    threshold: float,
    lang: str,
    prefer_local: bool,
    netease: bool,
    kugou: bool,
    qqmusic: bool,
) -> None:
    """为本地音乐文件获取并写入 SPL 歌词。\n\nPATH 可以是单个音乐文件或目录。"""
    providers = _PROVIDER_MAP.get(source.lower())
    fetcher = SyncedLyricsFetcher(providers=providers, lang=lang or None)

    tracks = scan(path)
    if not tracks:
        err_console.print(f"未找到支持的音乐文件：{path}")
        raise SystemExit(1)

    ui_console.print(f"\n[bold]共扫描到 {len(tracks)} 个文件[/]\n")

    # 阶段一：批量搜索（带进度条）
    results: list[tuple[TrackInfo, list[LyricResult]]] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=ui_console,
        transient=False,  # 保留进度日志，避免覆盖错误信息
    ) as progress:
        task = progress.add_task("搜索歌词…", total=len(tracks))
        for track in tracks:
            label = f"{track.artist} - {track.title}" if track.title else track.path.name
            progress.update(task, description=label)
            try:
                candidates = _fetch_results(track, fetcher, threshold, prefer_local, use_netease=netease, use_kugou=kugou, use_qqmusic=qqmusic)
            except Exception as e:
                candidates = []
                ui_console.log(f"[red]搜索出错[/] {track.path.name}: {e}")
            results.append((track, candidates))
            progress.advance(task)

    ui_console.print()  # 空行分隔

    # 阶段二：逐文件交互确认
    for track, candidates in results:
        label = track.path.name
        if not track.title:
            ui_console.print(f"[dim]{label}[/]  →  跳过（无元数据标题）")
            continue
        if not candidates:
            ui_console.print(f"[dim]{label}[/]  →  未找到歌词")
            continue

        # auto 模式：自动选择最优结果
        if auto:
            result = candidates[0]
            spl = result.content if result.format == LyricFormat.PLAIN else to_spl(result)
            
            if not dry_run:
                try:
                    write_spl(track.path, spl, existing_lyric=track.embedded_lyric)
                    ui_console.print(f"[green]✓[/] {label}  →  已写入 ({result.source_name}, {result.format.name})")
                except Exception as e:
                    ui_console.print(f"[red]写入失败[/] {label}: {e}")
            else:
                ui_console.print(f"[dim]{label}[/]  →  预览完成（dry-run）")
            continue

        # 非 auto 模式：展示多个候选，由用户选择
        try:
            from ui import confirm_with_candidates
            final_spl = confirm_with_candidates(
                candidates,
                track.title,
                track.artist,
                dry_run=dry_run,
            )
        except SystemExit:
            ui_console.print("\n[yellow]已退出[/]")
            return
        except Exception as e:
            ui_console.print(f"[red]错误[/] {label}: {e}")
            continue

        if final_spl is None:
            ui_console.print(f"[dim]{label}[/]  →  跳过")
            continue

        if not dry_run:
            try:
                write_spl(track.path, final_spl, existing_lyric=track.embedded_lyric)
                ui_console.print(f"[green]✓[/] {label}  →  已写入")
            except Exception as e:
                ui_console.print(f"[red]写入失败[/] {label}: {e}")
        else:
            ui_console.print(f"[dim]{label}[/]  →  预览完成（dry-run）")

    ui_console.print("\n[bold green]完成[/]")


if __name__ == "__main__":
    main()
