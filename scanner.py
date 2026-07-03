from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import mutagen
from mutagen.id3 import ID3, USLT
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis

from fetcher.base import LyricFormat

MUSIC_EXTENSIONS = {".mp3", ".flac", ".ogg", ".m4a", ".opus"}

# 逐字判断（与 fetcher/synced.py 保持一致）
_WORD_LEVEL_RE = re.compile(r"\[\d+:\d+[.:]\d+\][^\[\]]+\[\d+:\d+[.:]\d+\]")


def _detect_format(text: str) -> LyricFormat:
    for line in text.splitlines():
        if _WORD_LEVEL_RE.search(line):
            return LyricFormat.WORD
    if re.search(r"\[\d+:\d+[.:]\d+\]", text):
        return LyricFormat.LINE
    return LyricFormat.PLAIN


def _read_embedded(path: Path) -> tuple[str | None, LyricFormat | None]:
    """读取音频文件内嵌歌词，返回 (内容, 格式)。"""
    suffix = path.suffix.lower()
    try:
        if suffix == ".mp3":
            tags = ID3(path)
            frames = tags.getall("USLT")
            if frames:
                text = frames[0].text
                return text, _detect_format(text)
        elif suffix in {".flac", ".ogg", ".opus"}:
            audio = mutagen.File(path)
            if audio is None:
                return None, None
            lyrics_list = audio.get("lyrics", [])
            if lyrics_list:
                text = lyrics_list[0]
                return text, _detect_format(text)
    except Exception:
        pass
    return None, None


def _read_external(path: Path) -> str | None:
    """读取同目录下同名 .lrc / .spl 文件。"""
    for ext in (".lrc", ".spl"):
        candidate = path.with_suffix(ext)
        if candidate.exists():
            try:
                return candidate.read_text(encoding="utf-8")
            except Exception:
                pass
    return None


@dataclass
class TrackInfo:
    path: Path
    title: str
    artist: str
    embedded_lyric: str | None
    external_lyric: str | None
    embedded_format: LyricFormat | None

    @property
    def best_local_lyric(self) -> tuple[str | None, LyricFormat | None]:
        """返回质量最高的本地歌词，外部文件优先（内嵌优先级最低）。"""
        if self.external_lyric:
            return self.external_lyric, _detect_format(self.external_lyric)
        if self.embedded_lyric:
            return self.embedded_lyric, self.embedded_format
        return None, None


def scan_file(path: Path) -> TrackInfo:
    """读取单个音频文件的元数据和现有歌词。"""
    audio = mutagen.File(path, easy=True)
    title = ""
    artist = ""
    if audio is not None:
        title = (audio.get("title") or [""])[0]
        artist = (audio.get("artist") or [""])[0]

    embedded_lyric, embedded_format = _read_embedded(path)
    external_lyric = _read_external(path)

    return TrackInfo(
        path=path,
        title=title,
        artist=artist,
        embedded_lyric=embedded_lyric,
        external_lyric=external_lyric,
        embedded_format=embedded_format,
    )


def scan(target: Path) -> list[TrackInfo]:
    """扫描文件或目录，返回所有音乐文件的 TrackInfo 列表。"""
    if target.is_file():
        if target.suffix.lower() in MUSIC_EXTENSIONS:
            return [scan_file(target)]
        return []

    tracks: list[TrackInfo] = []
    for p in sorted(target.rglob("*")):
        if p.is_file() and p.suffix.lower() in MUSIC_EXTENSIONS:
            tracks.append(scan_file(p))
    return tracks
