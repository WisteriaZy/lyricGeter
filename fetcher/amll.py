"""AMLL TTML 数据库歌词获取器

从 AMLL TTML 数据库（GitHub raw）按歌曲 ID 获取 TTML 逐字歌词。

获取流程：
1. 通过网易云/QQ音乐搜索 API 获取歌曲 ID
2. 用歌曲 ID 从 AMLL 数据库下载 TTML 文件
3. 解析 TTML 并返回 LyricResult

数据源 URL：
- 网易云：ncm-lyrics/[歌曲ID].ttml
- QQ音乐：qq-lyrics/[歌曲ID].ttml

参考：https://github.com/amll-dev/amll-ttml-db
"""

from __future__ import annotations

from typing import Optional

import httpx

from fetcher.base import LyricsFetcher, LyricResult, LyricFormat, SongCandidate
from parser.ttml import TtmlParser, has_word_timestamps

AMLL_BASE_URL = "https://raw.githubusercontent.com/amll-dev/amll-ttml-db/refs/heads/main"
# 平台对应的 AMLL 文件夹
PLATFORM_DIRS = {
    "netease": "ncm-lyrics",
    "qqmusic": "qq-lyrics",
}


class AmllFetcher(LyricsFetcher):
    """AMLL TTML 数据库获取器"""

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self._netease_api = None
        self._qqmusic_api = None
        self._ttml_parser = TtmlParser()

    def _get_netease_api(self):
        if self._netease_api is None:
            from fetcher.netease import NetEaseApi
            self._netease_api = NetEaseApi()
        return self._netease_api

    def _get_qqmusic_api(self):
        if self._qqmusic_api is None:
            from fetcher.qqmusic import QQMusicApi
            self._qqmusic_api = QQMusicApi(timeout=self.timeout)
        return self._qqmusic_api

    def _fetch_ttml(self, platform: str, song_id: str) -> Optional[str]:
        """从 AMLL 数据库下载 TTML 文本"""
        dir_name = PLATFORM_DIRS.get(platform)
        if not dir_name:
            return None

        url = f"{AMLL_BASE_URL}/{dir_name}/{song_id}.ttml"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url)
                if response.status_code != 200:
                    return None
                return response.text
        except Exception:
            return None

    def _ttml_to_result(
        self,
        ttml_text: str,
        platform: str,
        matched_title: str = "",
        matched_artist: str = "",
        duration_ms: int = 0,
    ) -> Optional[LyricResult]:
        """将 TTML 文本解析为 LyricResult"""
        try:
            tags, lines = self._ttml_parser.parse(ttml_text)
        except Exception:
            return None

        if not lines:
            return None

        # 判断格式：逐字 vs 行级
        lyric_format = LyricFormat.WORD if has_word_timestamps(lines) else LyricFormat.LINE

        # 提取翻译（按行对齐的 LRC 文本）
        translation = None
        trans_lines = [l for l in lines if l.translation]
        if trans_lines:
            # 生成翻译 LRC
            from converter import _ms_to_stamp
            parts = []
            for line in lines:
                if line.translation:
                    parts.append(f"{_ms_to_stamp(line.start) if line.start is not None else ''}{line.translation}")
            translation = "\n".join(parts) if parts else None

        return LyricResult(
            content=ttml_text,
            format=lyric_format,
            source_name="amll",
            translation=translation,
            matched_title=matched_title,
            matched_artist=matched_artist,
            duration_ms=duration_ms,
        )

    def search(self, title: str, artist: str) -> Optional[LyricResult]:
        """搜索歌曲并从 AMLL 获取 TTML

        流程：先搜索网易云拿 ID，用 ID 找 AMLL；找不到再搜 QQ。
        """
        platforms_to_try = []

        # 尝试网易云
        try:
            ne_api = self._get_netease_api()
            ne_song = ne_api._search_song(title, artist)
            if ne_song:
                platforms_to_try.append(("netease", str(ne_song["id"]), ne_song["title"], ne_song["artist"], int(ne_song.get("duration_ms", 0) or 0)))
        except Exception:
            pass

        # 尝试 QQ 音乐
        try:
            qq_api = self._get_qqmusic_api()
            qq_song = qq_api.search_song(title, artist)
            if qq_song:
                platforms_to_try.append(("qqmusic", str(qq_song.get("id", "")), qq_song.get("title", ""), qq_song.get("artist", ""), int(qq_song.get("duration", 0) or 0) * 1000))
        except Exception:
            pass

        # 逐个尝试 AMLL
        for platform, song_id, matched_title, matched_artist, duration_ms in platforms_to_try:
            if not song_id:
                continue
            ttml_text = self._fetch_ttml(platform, song_id)
            if ttml_text:
                # 从 TTML 提取元数据中的匹配信息
                return self._ttml_to_result(ttml_text, platform, matched_title, matched_artist, duration_ms=duration_ms)

        return None

    def search_songs(self, query: str, limit: int = 10) -> list[SongCandidate]:
        """搜索歌曲候选（合并网易云和 QQ 音乐）"""
        candidates: list[SongCandidate] = []
        seen: set[str] = set()

        # 网易云
        try:
            ne_api = self._get_netease_api()
            ne_candidates = ne_api.search_songs(query, limit)
            for song in ne_candidates:
                if song.source_id:
                    amll_id = f"amll:netease:{song.source_id}"
                    if amll_id not in seen:
                        seen.add(amll_id)
                        candidates.append(SongCandidate(
                            source_name="amll",
                            source_id=f"netease:{song.source_id}",
                            title=song.title,
                            artist=song.artist,
                            album=song.album,
                            duration_ms=song.duration_ms,
                            payload={"platform": "netease", "song_id": song.source_id},
                        ))
        except Exception:
            pass

        # QQ 音乐
        try:
            qq_api = self._get_qqmusic_api()
            songs = qq_api.search_songs(query, limit)
            for song in songs:
                song_id = str(song.get("id", ""))
                if not song_id:
                    continue
                amll_id = f"amll:qqmusic:{song_id}"
                if amll_id not in seen:
                    seen.add(amll_id)
                    singers = song.get("singer", [])
                    artist_names = ", ".join(s.get("name", "") for s in singers if s.get("name"))
                    album = song.get("album", {}) or {}
                    candidates.append(SongCandidate(
                        source_name="amll",
                        source_id=f"qqmusic:{song_id}",
                        title=song.get("title", "") or song.get("name", ""),
                        artist=artist_names,
                        album=album.get("name", ""),
                        duration_ms=int(song.get("interval", 0) or 0) * 1000,
                        payload={"platform": "qqmusic", "song_id": song_id},
                    ))
        except Exception:
            pass

        return candidates[:limit]

    def fetch_by_song(self, song: SongCandidate) -> Optional[LyricResult]:
        """按用户选中的歌曲从 AMLL 获取 TTML"""
        # 解析 source_id 格式：netease:123456 或 qqmusic:789012
        platform_info = song.source_id.split(":", 1)
        if len(platform_info) != 2:
            return None
        platform, song_id = platform_info

        ttml_text = self._fetch_ttml(platform, song_id)
        if not ttml_text:
            return None

        return self._ttml_to_result(ttml_text, platform, song.title, song.artist, duration_ms=song.duration_ms)
