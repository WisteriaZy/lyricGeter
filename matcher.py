from __future__ import annotations

from rapidfuzz import fuzz

from fetcher.base import LyricFormat, LyricResult, LyricsFetcher
from scanner import TrackInfo

DEFAULT_THRESHOLD = 70.0


def similarity_score(title: str, artist: str, query_result: str) -> float:
    """用标题+艺术家与搜索词的相似度打分。"""
    combined = f"{title} {artist}".strip()
    return fuzz.WRatio(combined.lower(), query_result.lower())


def _similarity(title: str, artist: str, query_result: str) -> float:
    """向后兼容旧的内部调用。"""
    return similarity_score(title, artist, query_result)


def find_all(
    track: TrackInfo,
    fetchers: list[LyricsFetcher],
    threshold: float = DEFAULT_THRESHOLD,
    prefer_local: bool = False,
) -> list[LyricResult]:
    """
    从所有 fetcher 获取歌词，返回通过相似度过滤的所有结果。
    
    返回列表按以下优先级排序：
    1. 格式优先级（WORD > LINE > PLAIN）
    2. 相似度评分（高 > 低）
    """
    local_content, local_format = track.best_local_lyric
    results: list[LyricResult] = []

    # prefer_local 模式：本地已是最优格式时，只添加本地结果
    if prefer_local and local_content and local_format == LyricFormat.WORD:
        return [LyricResult(
            content=local_content,
            format=local_format,
            source_name="local",
            score=100.0,
            duration_ms=track.duration_ms,
        )]

    # 从所有 fetcher 获取结果
    for fetcher in fetchers:
        result = fetcher.search(track.title, track.artist)
        if result is None:
            continue

        # 相似度过滤
        if result.matched_title or result.matched_artist:
            # 原生 API 返回了匹配歌曲信息，计算相似度
            result.score = similarity_score(
                track.title,
                track.artist,
                f"{result.matched_title} {result.matched_artist}".strip()
            )
            if result.score < threshold:
                continue
        else:
            # syncedlyrics 等第三方库，信任其内部排序
            result.score = 100.0

        # prefer_local 模式且有本地歌词时：在线结果格式必须更优才添加
        if prefer_local and local_content and local_format is not None:
            if result.format > local_format:  # 格式更差，跳过
                continue

        results.append(result)

    # 添加本地歌词作为候选（如果存在）
    if local_content and local_format is not None:
        results.append(LyricResult(
            content=local_content,
            format=local_format,
            source_name="local",
            score=100.0,
            duration_ms=track.duration_ms,
        ))

    # 排序：格式优先级 > 相似度
    results.sort(key=lambda r: (r.format.value, -r.score))
    return results


def find_best(
    track: TrackInfo,
    fetchers: list[LyricsFetcher],
    threshold: float = DEFAULT_THRESHOLD,
    force_online: bool = False,
    prefer_local: bool = False,
) -> LyricResult | None:
    """
    自动模式：返回最优结果（格式优先 > 相似度）。
    
    参考 lyricLoader.ts 的 tryOnlineByPreference 逻辑：
    - prefer_local=False（默认）：优先在线，本地仅作兜底
    - prefer_local=True：有本地歌词 + 已是 WORD 级时跳过在线
    """
    all_results = find_all(track, fetchers, threshold, prefer_local)
    return all_results[0] if all_results else None
