from __future__ import annotations

from rapidfuzz import fuzz

from fetcher.base import LyricFormat, LyricResult, LyricsFetcher
from scanner import TrackInfo

DEFAULT_THRESHOLD = 70.0


def _similarity(title: str, artist: str, query_result: str) -> float:
    """用标题+艺术家与搜索词的相似度打分。"""
    combined = f"{title} {artist}".strip()
    return fuzz.WRatio(combined.lower(), query_result.lower())


def find_best(
    track: TrackInfo,
    fetchers: list[LyricsFetcher],
    threshold: float = DEFAULT_THRESHOLD,
    force_online: bool = False,
    prefer_local: bool = False,
) -> LyricResult | None:
    """
    参考 lyricLoader.ts 的 tryOnlineByPreference 逻辑：

    - prefer_local=False（默认）：优先在线，本地仅作兜底
    - prefer_local=True：有本地歌词 + 已是 WORD 级时跳过在线
    """
    local_content, local_format = track.best_local_lyric

    # prefer_local 模式：本地已是最优格式，无需在线
    if prefer_local and local_content and local_format == LyricFormat.WORD and not force_online:
        return LyricResult(
            content=local_content,
            format=local_format,
            source_name="local",
        )

    best: LyricResult | None = None

    for fetcher in fetchers:
        result = fetcher.search(track.title, track.artist)
        if result is None:
            continue

        # 相似度过滤（暂时禁用：syncedlyrics 不返回匹配歌曲元数据，无法准确打分）
        # TODO: 实现平台原生 API 后恢复此功能
        result.score = 100.0  # 信任 syncedlyrics 内部排序
        # score = _similarity(track.title, track.artist, result.matched_title)
        # if score < threshold:
        #     continue

        # prefer_local 模式且有本地歌词时：在线结果格式必须更优才采用
        if prefer_local and local_content and local_format is not None:
            if result.format <= local_format and not force_online:
                continue

        # 取格式最优者
        if best is None or result.format < best.format:
            best = result

    if best is not None:
        return best

    # 在线无结果，回退本地
    if local_content and local_format is not None:
        return LyricResult(
            content=local_content,
            format=local_format,
            source_name="local",
        )

    return None
