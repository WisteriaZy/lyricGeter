"""QQ 音乐 API 客户端

基于 LDDC (Python) 项目的 QMApi 实现
参考: https://github.com/chenmozhijin/LDDC
"""

import json
import random
import time
from base64 import b64encode
from threading import Lock
from typing import Optional, Any

import httpx

from fetcher.base import LyricsFetcher, LyricResult, LyricFormat, SongCandidate
from decryptor.qrc import qrc_decrypt
from parser.qrc import qrc_str_parse


class QQMusicApi:
    """QQ 音乐 API 客户端（同步实现）"""

    BASE_URL = "https://u.y.qq.com/cgi-bin/musicu.fcg"

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.client = httpx.Client(
            headers={
                "cookie": "tmeLoginType=-1;",
                "content-type": "application/json",
                "accept-encoding": "gzip",
                "user-agent": "okhttp/3.14.9",
            },
            timeout=timeout,
        )
        self.comm: dict[str, Any] = {
            "ct": 11,
            "cv": "1003006",
            "v": "1003006",
            "os_ver": "15",
            "phonetype": "24122RKC7C",
            "rom": f"Redmi/miro/miro:15/AE3A.240806.005/OS2.0.10{random.choice(['5', '4', '2'])}.0.VOMCNXM:user/release-keys",
            "tmeAppID": "qqmusiclight",
            "nettype": "NETWORK_WIFI",
            "udid": "0",
        }
        self.inited = False
        self.init_lock = Lock()
        self.init()

    def init(self) -> None:
        with self.init_lock:
            if self.inited:
                return
            param = {"caller": 0, "uid": "0", "vkey": 0}
            data = self._request("GetSession", "music.getSession.session", param)
            self.comm["uid"] = data["session"]["uid"]
            self.comm["sid"] = data["session"]["sid"]
            self.comm["userip"] = data["session"]["userip"]
            self.inited = True

    def _request(self, method: str, module: str, param: dict) -> dict:
        if not self.inited and method != "GetSession":
            self.init()

        body = json.dumps(
            {
                "comm": self.comm,
                "request": {
                    "method": method,
                    "module": module,
                    "param": param,
                },
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")

        response = self.client.post(self.BASE_URL, content=body)
        response.raise_for_status()
        data = response.json()

        if data["code"] != 0 or data["request"]["code"] != 0:
            err = data["code"] if data["code"] != 0 else data["request"]["code"]
            raise RuntimeError(f"QQ 音乐 API 请求错误，错误码: {err}")

        return data["request"]["data"]

    def search_songs(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        param = {
            "query": query.strip(),
            "page_num": 1,
            "num_per_page": limit,
            "search_type": 0,
        }
        data = self._request("DoSearchForQQMusicDesktop", "music.search.SearchCgiService", param)
        songs = data.get("body", {}).get("song", {}).get("list", [])
        return songs[:limit]

    def search_song(self, title: str, artist: str = "") -> Optional[dict[str, Any]]:
        query = f"{title} {artist}".strip()
        songs = self.search_songs(query, limit=10)
        if not songs:
            return None

        # 排序：降低片段/翻唱/sped up 版本的优先级
        def score_song(song):
            name = song.get("name", "") + " " + song.get("title", "")
            score = 0
            if "片段" in name:
                score -= 500
            if "原唱" in name or "翻唱" in name:
                score -= 300
            if "sped up" in name.lower() or "slowed" in name.lower():
                score -= 200
            return score

        songs.sort(key=score_song, reverse=True)
        first = songs[0]

        singers = first.get("singer", [])
        artist_names = ", ".join(s.get("name", "") for s in singers if s.get("name"))
        return {
            "id": first.get("id", 0),
            "mid": first.get("mid", ""),
            "title": first.get("title", "") or first.get("name", ""),
            "artist": artist_names,
            "album": first.get("album", {}).get("name", ""),
            "duration": first.get("interval", 0),
        }

    def get_lyrics(self, song: dict[str, Any]) -> Optional[dict[str, str]]:
        song_id = song["id"]
        album = song.get("album", "")
        artist = song.get("artist", "")
        title = song.get("title", "")
        duration = song.get("duration", 0)

        param = {
            "albumName": b64encode(album.encode()).decode() if album else b64encode(b"").decode(),
            "crypt": 1,
            "ct": 19,
            "cv": 2111,
            "interval": duration,
            "lrc_t": 0,
            "qrc": 1,
            "qrc_t": 0,
            "roma": 1,
            "roma_t": 0,
            "singerName": b64encode(artist.encode()).decode() if artist else b64encode(b"").decode(),
            "songID": int(song_id),
            "songName": b64encode(title.encode()).decode(),
            "trans": 1,
            "trans_t": 0,
            "type": 0,
        }

        response = self._request("GetPlayLyricInfo", "music.musichallSong.PlayLyricInfo", param)

        result: dict[str, str] = {}
        for key, value in [("orig", "lyric"), ("ts", "trans"), ("roma", "roma")]:
            lrc = response.get(value, "")
            lrc_t = (response.get("qrc_t", 0) if response.get("qrc_t", 0) != 0 else response.get("lrc_t", 0)) if value == "lyric" else response.get(value + "_t", 0)

            if lrc and str(lrc_t) != "0":
                try:
                    decrypted = qrc_decrypt(lrc)
                    if decrypted:
                        result[key] = decrypted
                except Exception as e:
                    print(f"QQ 音乐解密 {key} 失败: {e}")

        return result if result else None

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


class QQMusicFetcher(LyricsFetcher):
    """QQ 音乐歌词获取器（实现 LyricsFetcher 接口）"""

    def __init__(self, timeout: int = 10):
        self.api = QQMusicApi(timeout)

    def search_songs(self, query: str, limit: int = 10) -> list[SongCandidate]:
        songs = self.api.search_songs(query, limit=limit)
        candidates: list[SongCandidate] = []
        for song in songs:
            singers = song.get("singer", [])
            artist_names = ", ".join(s.get("name", "") for s in singers if s.get("name"))
            album = song.get("album", {}) or {}
            candidates.append(SongCandidate(
                source_name="qqmusic",
                source_id=str(song.get("id", "")),
                title=song.get("title", "") or song.get("name", ""),
                artist=artist_names,
                album=album.get("name", ""),
                duration_ms=int(song.get("interval", 0) or 0) * 1000,
                payload=song,
            ))
        return candidates

    def fetch_by_song(self, song: SongCandidate) -> Optional[LyricResult]:
        song_dict = {
            "id": int(song.source_id) if song.source_id else 0,
            "mid": "",
            "title": song.title,
            "artist": song.artist,
            "album": song.album,
            "duration": song.duration_ms // 1000,
        }
        return self._fetch_lyrics(song_dict)

    def search(self, title: str, artist: str) -> Optional[LyricResult]:
        try:
            song = self.api.search_song(title, artist)
            if not song:
                return None
            return self._fetch_lyrics(song)
        except Exception as e:
            print(f"QQ 音乐获取歌词失败: {e}")
            return None

    def _fetch_lyrics(self, song: dict[str, Any]) -> Optional[LyricResult]:
        lyrics_data = self.api.get_lyrics(song)
        if not lyrics_data or "orig" not in lyrics_data:
            return None

        orig_text = lyrics_data["orig"]
        trans_text = lyrics_data.get("ts", "")
        roma_text = lyrics_data.get("roma", "")

        # 解析原文
        tags, orig_lines = qrc_str_parse(orig_text)
        if not orig_lines:
            return None

        # 判断格式：逐字 vs 行级
        has_words = any(
            len(line.words) > 1 for line in orig_lines
        ) if hasattr(orig_lines[0], "words") else False
        lyric_format = LyricFormat.WORD if has_words else LyricFormat.LINE

        # 解析翻译
        trans_lrc = None
        if trans_text:
            _, trans_lines = qrc_str_parse(trans_text)
            if trans_lines:
                trans_lrc = _lines_to_lrc(trans_lines)

        return LyricResult(
            content=orig_text,
            format=lyric_format,
            source_name="qqmusic",
            translation=trans_lrc,
            matched_title=song.get("title", ""),
            matched_artist=song.get("artist", ""),
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.api.close()


def _lines_to_lrc(lines) -> str:
    """将解析后的歌词行列表转为 LRC 文本（用于 translation 字段）"""
    from parser.qrc import LyricsLine, LyricsWord

    out = []
    for line in lines:
        if isinstance(line, LyricsLine):
            text = "".join(w.text for w in line.words)
            if text.strip():
                out.append(f"[{_ms_to_lrc_stamp(line.start)}]{text}")
    return "\n".join(out)


def _ms_to_lrc_stamp(ms: int) -> str:
    if ms is None:
        return "00:00.00"
    m, rem = divmod(ms, 60000)
    s, cs = divmod(rem, 1000)
    return f"{m:02d}:{s:02d}.{cs // 10:02d}"
