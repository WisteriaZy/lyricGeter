from __future__ import annotations

import sys

# Windows 终端默认 GBK，强制 UTF-8 避免日文/中文字符编码错误
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from pathlib import Path

import click
import questionary
from rich.console import Console

from fetcher import SyncedLyricsFetcher, NetEaseApi
from fetcher.kugou import KugouFetcher
from fetcher.qqmusic import QQMusicFetcher
from fetcher.amll import AmllFetcher
from fetcher.base import LyricResult, LyricsFetcher, SongCandidate
from scanner import scan, TrackInfo
from matcher import find_all, similarity_score
from writer import clear_lyrics, write_spl
from ui import CLEAR_LYRICS, MIN_LYRIC_LINES, SEARCH_AGAIN, console as ui_console, summarize_result

_PROVIDER_MAP = {
    "netease": ["NetEase"],
    "lrclib": ["Lrclib"],
    "musixmatch": ["Musixmatch"],
    "all": None,  # None → 使用全部默认 provider
}
_SEARCH_NEW_QUERY = "__SEARCH_NEW_QUERY__"

err_console = Console(stderr=True, style="red", legacy_windows=False)


def _build_fetchers(use_netease: bool, use_kugou: bool, use_qqmusic: bool, use_amll: bool = True) -> list[LyricsFetcher]:
    fetchers: list[LyricsFetcher] = []
    # AMLL 优先级最高（TTML 逐字 + 翻译）
    if use_amll:
        fetchers.append(AmllFetcher())
    if use_netease:
        fetchers.append(NetEaseApi())
    if use_qqmusic:
        fetchers.append(QQMusicFetcher())
    if use_kugou:
        fetchers.append(KugouFetcher())
    return fetchers


def _song_label(song: SongCandidate) -> str:
    duration = ""
    if song.duration_ms:
        total_seconds = song.duration_ms // 1000
        duration = f" {total_seconds // 60}:{total_seconds % 60:02d}"
    album = f" / {song.album}" if song.album else ""
    return f"{song.source_name} - {song.title} - {song.artist}{album}{duration}"


def _simple_choose(prompt: str, choices: list[tuple[str, object]]) -> object:
    ui_console.print(f"\n[bold]{prompt}[/]")
    for i, (label, _) in enumerate(choices, 1):
        ui_console.print(f"  {i}. {label}")
    try:
        selected = input("\n请输入选项编号: ").strip()
        index = int(selected) - 1
        if 0 <= index < len(choices):
            return choices[index][1]
    except (EOFError, KeyboardInterrupt, ValueError):
        pass
    return None


def _choose(prompt: str, choices: list[tuple[str, object]]) -> object:
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            selection = questionary.select(
                prompt,
                choices=[questionary.Choice(label, value=value) for label, value in choices],
            ).ask()
            return selection
        except Exception as e:
            ui_console.print(f"[yellow]questionary 不可用: {e}[/]")
            ui_console.print("[dim]切换到简单文本输入模式[/]")
    return _simple_choose(prompt, choices)


def _read_manual_query(default_query: str) -> str | None:
    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            query = questionary.text("重新搜索关键词：", default=default_query).ask()
        except Exception as e:
            ui_console.print(f"[yellow]questionary 不可用: {e}[/]")
        else:
            if query is None:
                return None
            return query.strip() or default_query

    try:
        return input(f"重新搜索关键词 [{default_query}]: ").strip() or default_query
    except (EOFError, KeyboardInterrupt):
        ui_console.print("[dim]无法读取输入，取消再次搜索[/]")
        return None


def _search_song_candidates(
    query: str,
    fetchers: list[LyricsFetcher],
) -> tuple[list[SongCandidate], dict[str, LyricsFetcher]]:
    songs: list[SongCandidate] = []
    provider_by_name: dict[str, LyricsFetcher] = {}
    seen: set[tuple[str, str]] = set()

    if not fetchers:
        ui_console.print("[yellow]当前没有启用支持手动选歌的平台[/]")
        return songs, provider_by_name

    for fetcher in fetchers:
        try:
            provider_songs = fetcher.search_songs(query, limit=10)
        except Exception as e:
            ui_console.print(f"[yellow]{fetcher.__class__.__name__} 搜索失败: {e}[/]")
            continue

        for song in provider_songs:
            key = (song.source_name, song.source_id)
            if key in seen:
                continue
            seen.add(key)
            provider_by_name[song.source_name] = fetcher
            songs.append(song)

    return songs, provider_by_name


def _choose_song_candidate(songs: list[SongCandidate]) -> int | str | None:
    choices = [(_song_label(song), i) for i, song in enumerate(songs)]
    choices.append(("换关键词再次搜索", _SEARCH_NEW_QUERY))
    choices.append(("取消再次搜索", None))
    selection = _choose("选择要读取歌词的歌曲：", choices)
    if isinstance(selection, int) or isinstance(selection, str) or selection is None:
        return selection
    return None


def _manual_search_result(
    track: TrackInfo,
    fetchers: list[LyricsFetcher],
    threshold: float,
) -> LyricResult | None:
    query_default = f"{track.title} {track.artist}".strip() or track.path.stem

    while True:
        query = _read_manual_query(query_default)
        if query is None:
            return None

        with ui_console.status("搜索歌曲候选…", spinner="dots"):
            songs, provider_by_name = _search_song_candidates(query, fetchers)

        if not songs:
            ui_console.print("[yellow]没有找到可选歌曲[/]")
            selection = _choose(
                "下一步：",
                [
                    ("换关键词再次搜索", _SEARCH_NEW_QUERY),
                    ("取消再次搜索", None),
                ],
            )
            if selection == _SEARCH_NEW_QUERY:
                query_default = query
                continue
            return None

        while True:
            selection = _choose_song_candidate(songs)
            if selection == _SEARCH_NEW_QUERY:
                query_default = query
                break
            if selection is None:
                return None

            song = songs[int(selection)]
            fetcher = provider_by_name.get(song.source_name)
            if fetcher is None:
                ui_console.print("[yellow]找不到该来源的读取器，请选择其他歌曲[/]")
                continue

            with ui_console.status(f"读取歌词：{song.title} - {song.artist}…", spinner="dots"):
                result = fetcher.fetch_by_song(song)
            if result is None:
                ui_console.print("[yellow]该歌曲没有可用歌词，请选择其他歌曲或换关键词[/]")
                continue

            matched_title = result.matched_title or song.title
            matched_artist = result.matched_artist or song.artist
            result.matched_title = matched_title
            result.matched_artist = matched_artist
            result.score = similarity_score(
                track.title,
                track.artist,
                f"{matched_title} {matched_artist}".strip(),
            )
            if result.score < threshold:
                ui_console.print(f"[yellow]注意：手动选择结果相似度较低 ({result.score:.0f})[/]")
            return result


def _fetch_results(
    track: TrackInfo,
    fetcher: SyncedLyricsFetcher,
    threshold: float,
    prefer_local: bool,
    use_netease: bool,
    use_kugou: bool,
    use_qqmusic: bool,
    use_amll: bool = True,
) -> list[LyricResult]:
    """网络搜索阶段，返回所有候选结果。"""
    if not track.title:
        return []

    fetchers = _build_fetchers(use_netease, use_kugou, use_qqmusic, use_amll)
    # syncedlyrics 作为兜底
    fetchers.append(fetcher)

    return find_all(track, fetchers, threshold=threshold, prefer_local=prefer_local)


def _apply_auto_result(track: TrackInfo, result: LyricResult, dry_run: bool) -> None:
    label = track.path.name
    line_count, has_translation, spl = summarize_result(result)
    lyric_note = "有翻译" if has_translation else "无翻译"

    if line_count < MIN_LYRIC_LINES:
        if dry_run:
            ui_console.print(f"[dim]{label}[/]  →  少于 {MIN_LYRIC_LINES} 行，dry-run 将按纯音乐处理（{result.source_name}, {line_count}行, {lyric_note}）")
            return
        try:
            clear_lyrics(track.path, existing_lyric=track.embedded_lyric)
            ui_console.print(f"[green]✓[/] {label}  →  按纯音乐处理，已清除歌词标签（{result.source_name}, {line_count}行, {lyric_note}）")
        except Exception as e:
            ui_console.print(f"[red]清除歌词失败[/] {label}: {e}")
        return

    if dry_run:
        ui_console.print(f"[dim]{label}[/]  →  预览完成（dry-run，{result.source_name}, {line_count}行, {lyric_note}）")
        return

    try:
        write_spl(track.path, spl, existing_lyric=track.embedded_lyric)
        ui_console.print(f"[green]✓[/] {label}  →  已写入 ({result.source_name}, {result.format.name}, {line_count}行, {lyric_note})")
    except Exception as e:
        ui_console.print(f"[red]写入失败[/] {label}: {e}")


def _apply_final_spl(track: TrackInfo, final_spl: str | None, dry_run: bool) -> None:
    label = track.path.name
    if final_spl is None:
        ui_console.print(f"[dim]{label}[/]  →  跳过")
        return

    if final_spl == CLEAR_LYRICS:
        if dry_run:
            ui_console.print(f"[dim]{label}[/]  →  dry-run 将清除歌词标签")
            return
        try:
            clear_lyrics(track.path, existing_lyric=track.embedded_lyric)
            ui_console.print(f"[green]✓[/] {label}  →  已清除歌词标签")
        except Exception as e:
            ui_console.print(f"[red]清除歌词失败[/] {label}: {e}")
        return

    if dry_run:
        ui_console.print(f"[dim]{label}[/]  →  预览完成（dry-run）")
        return

    try:
        write_spl(track.path, final_spl, existing_lyric=track.embedded_lyric)
        ui_console.print(f"[green]✓[/] {label}  →  已写入")
    except Exception as e:
        ui_console.print(f"[red]写入失败[/] {label}: {e}")


def _choose_no_candidate_action(track: TrackInfo) -> str | None:
    ui_console.print(f"[yellow]{track.path.name}[/]  →  未找到候选歌词")
    if not sys.stdin.isatty():
        return None
    selection = _choose(
        "未找到歌词，下一步：",
        [
            ("再次搜索并选择歌曲", SEARCH_AGAIN),
            ("按纯音乐处理（清除歌词标签）", CLEAR_LYRICS),
            ("跳过此文件", None),
            ("退出程序", "quit"),
        ],
    )
    if selection == "quit":
        raise SystemExit(0)
    return selection if isinstance(selection, str) else None


def _confirm_interactive_track(
    track: TrackInfo,
    candidates: list[LyricResult],
    manual_fetchers: list[LyricsFetcher],
    threshold: float,
    dry_run: bool,
) -> None:
    from ui import confirm_with_candidates

    while True:
        if candidates:
            final_spl = confirm_with_candidates(
                candidates,
                track.title,
                track.artist,
                dry_run=dry_run,
            )
        else:
            final_spl = _choose_no_candidate_action(track)

        if final_spl == SEARCH_AGAIN:
            manual_result = _manual_search_result(track, manual_fetchers, threshold)
            if manual_result is not None:
                candidates = [manual_result] + candidates
            continue

        _apply_final_spl(track, final_spl, dry_run)
        return


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
@click.option("--qqmusic/--no-qqmusic", default=True, show_default=True, help="启用/禁用 QQ 音乐 API")
@click.option("--amll/--no-amll", default=True, show_default=True, help="启用/禁用 AMLL TTML 数据库")
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
    amll: bool,
) -> None:
    """为本地音乐文件获取并写入 SPL 歌词。\n\nPATH 可以是单个音乐文件或目录。"""
    providers = _PROVIDER_MAP.get(source.lower())
    fetcher = SyncedLyricsFetcher(providers=providers, lang=lang or None)

    tracks = scan(path)
    if not tracks:
        err_console.print(f"未找到支持的音乐文件：{path}")
        raise SystemExit(1)

    ui_console.print(f"\n[bold]共扫描到 {len(tracks)} 个文件[/]\n")
    manual_fetchers = _build_fetchers(netease, kugou, qqmusic, amll)

    for index, track in enumerate(tracks, 1):
        label = track.path.name
        display_label = f"{track.artist} - {track.title}" if track.title else label
        ui_console.print(f"\n[bold]({index}/{len(tracks)}) {display_label}[/]")

        if not track.title:
            ui_console.print(f"[dim]{label}[/]  →  跳过（无元数据标题）")
            continue

        try:
            with ui_console.status("搜索歌词…", spinner="dots"):
                candidates = _fetch_results(
                    track,
                    fetcher,
                    threshold,
                    prefer_local,
                    use_netease=netease,
                    use_kugou=kugou,
                    use_qqmusic=qqmusic,
                    use_amll=amll,
                )
        except Exception as e:
            candidates = []
            ui_console.print(f"[red]搜索出错[/] {label}: {e}")

        if auto:
            if not candidates:
                ui_console.print(f"[dim]{label}[/]  →  未找到歌词")
                continue
            _apply_auto_result(track, candidates[0], dry_run)
            continue

        try:
            _confirm_interactive_track(
                track,
                candidates,
                manual_fetchers,
                threshold,
                dry_run,
            )
        except SystemExit:
            ui_console.print("\n[yellow]已退出[/]")
            return
        except Exception as e:
            ui_console.print(f"[red]错误[/] {label}: {e}")

    ui_console.print("\n[bold green]完成[/]")


if __name__ == "__main__":
    main()

