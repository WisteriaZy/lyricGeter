"""网易云音乐 API 客户端

支持：
- 搜索歌曲（/eapi/cloudsearch/pc）
- 获取歌词（/eapi/song/lyric/v1）含 YRC 逐字格式
"""

from __future__ import annotations

import httpx

from decryptor.eapi import encrypt_eapi_params
from fetcher.base import LyricFormat, LyricResult, LyricsFetcher, SongCandidate


class NetEaseApi(LyricsFetcher):
    """网易云音乐 API"""
    
    BASE_URL = "https://music.163.com"
    
    # 模拟客户端 User-Agent
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://music.163.com/",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    
    def search(self, title: str, artist: str) -> LyricResult | None:
        """搜索歌曲并获取歌词"""
        # 步骤 1：搜索歌曲
        song_info = self._search_song(title, artist)
        if song_info is None:
            return None
        
        # 步骤 2：获取歌词
        return self._get_lyrics(
            song_info["id"],
            song_info["title"],
            song_info["artist"]
        )
    
    def search_songs(self, query: str, limit: int = 10) -> list[SongCandidate]:
        """搜索歌曲候选，供交互式手动选择。"""
        path = "/api/cloudsearch/pc"

        params = {
            "s": query.strip(),
            "type": 1,
            "offset": 0,
            "limit": limit,
        }

        encrypted = encrypt_eapi_params(path, params)

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self.BASE_URL}/eapi/cloudsearch/pc",
                    headers=self.HEADERS,
                    content=encrypted,
                )

                if response.status_code != 200:
                    return []

                data = response.json()
                if data.get("code") != 200:
                    return []

                result = data.get("result", {})
                songs = result.get("songs", [])
                candidates: list[SongCandidate] = []
                for song in songs[:limit]:
                    artists = song.get("ar", [])
                    artist_names = ", ".join(ar.get("name", "") for ar in artists)
                    album = song.get("al", {}) or {}
                    candidates.append(SongCandidate(
                        source_name="netease",
                        source_id=str(song.get("id", "")),
                        title=song.get("name", ""),
                        artist=artist_names,
                        album=album.get("name", ""),
                        duration_ms=int(song.get("dt", 0) or 0),
                        payload=song,
                    ))
                return candidates
        except Exception:
            return []

    def fetch_by_song(self, song: SongCandidate) -> LyricResult | None:
        """按用户选中的网易云歌曲获取歌词。"""
        try:
            song_id = int(song.source_id)
        except (TypeError, ValueError):
            return None
        return self._get_lyrics(song_id, song.title, song.artist)

    def _search_song(self, title: str, artist: str) -> dict | None:
        """搜索歌曲，返回第一个结果的信息
        
        Returns:
            {"id": int, "title": str, "artist": str} 或 None
        """
        path = "/api/cloudsearch/pc"
        query = f"{title} {artist}".strip()
        
        params = {
            "s": query,
            "type": 1,      # 1=单曲
            "offset": 0,
            "limit": 10,
        }
        
        encrypted = encrypt_eapi_params(path, params)
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self.BASE_URL}/eapi/cloudsearch/pc",
                    headers=self.HEADERS,
                    content=encrypted,
                )
                
                if response.status_code != 200:
                    return None
                
                data = response.json()
                
                # 检查响应格式
                if data.get("code") != 200:
                    return None
                
                result = data.get("result", {})
                songs = result.get("songs", [])
                
                if not songs:
                    return None
                
                # 返回第一个结果的信息
                first_song = songs[0]
                artists = first_song.get("ar", [])
                artist_names = ", ".join(ar.get("name", "") for ar in artists)
                
                return {
                    "id": first_song.get("id"),
                    "title": first_song.get("name", ""),
                    "artist": artist_names,
                }
        
        except Exception as e:
            return None
    
    def _get_lyrics(self, song_id: int, matched_title: str, matched_artist: str) -> LyricResult | None:
        """获取歌词（含 YRC）
        
        Args:
            song_id: 歌曲 ID
            matched_title: 平台返回的歌曲标题
            matched_artist: 平台返回的艺术家
        """
        path = "/api/song/lyric/v1"
        
        params = {
            "id": song_id,
            "lv": -1,   # 普通歌词版本
            "tv": -1,   # 翻译版本
            "yv": -1,   # YRC 逐字版本
        }
        
        encrypted = encrypt_eapi_params(path, params)
        
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    f"{self.BASE_URL}/eapi/song/lyric/v1",
                    headers=self.HEADERS,
                    content=encrypted,
                )
                
                if response.status_code != 200:
                    return None
                
                data = response.json()
                
                if data.get("code") != 200:
                    return None
                
                # 优先 YRC（逐字），回退到 LRC（行级）
                yrc_data = data.get("yrc", {})
                lrc_data = data.get("lrc", {})
                tlyric_data = data.get("tlyric", {})  # 翻译
                
                yrc_content = yrc_data.get("lyric", "")
                lrc_content = lrc_data.get("lyric", "")
                tlyric_content = tlyric_data.get("lyric", "")
                
                # 选择最优格式（优先 YRC，回退到 LRC）
                if yrc_content:
                    content = yrc_content
                    lyric_format = LyricFormat.WORD
                elif lrc_content:
                    content = lrc_content
                    # 默认行级，converter.py 会自动检测 JSON/逐字格式
                    lyric_format = LyricFormat.LINE
                else:
                    return None
                
                # 翻译作为独立字段传递，不合并到 content
                translation = tlyric_content if tlyric_content else None
                
                return LyricResult(
                    content=content,
                    format=lyric_format,
                    source_name="netease",
                    translation=translation,
                    matched_title=matched_title,
                    matched_artist=matched_artist,
                )
        
        except Exception:
            return None
