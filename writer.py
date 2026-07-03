from __future__ import annotations

from pathlib import Path

import mutagen
from mutagen.id3 import ID3, ID3NoHeaderError, USLT, Encoding
from mutagen.flac import FLAC
from mutagen.oggvorbis import OggVorbis


def _backup_embedded(path: Path, content: str) -> None:
    """将原有歌词备份到同目录 .lrc.bak 文件（若已存在则跳过）。"""
    bak = path.with_suffix(".lrc.bak")
    if not bak.exists():
        try:
            bak.write_text(content, encoding="utf-8")
        except Exception:
            pass


def write_spl(path: Path, spl: str, existing_lyric: str | None = None) -> None:
    """
    将 SPL 内容写入音频文件标签。

    MP3  → USLT (ID3)
    FLAC → lyrics (Vorbis Comment)
    Ogg  → lyrics (Vorbis Comment)
    """
    if existing_lyric:
        _backup_embedded(path, existing_lyric)

    suffix = path.suffix.lower()

    if suffix == ".mp3":
        tags = ID3(path)
        tags.delall("USLT")
        tags.add(USLT(encoding=Encoding.UTF8, lang="XXX", desc="", text=spl))
        tags.save()

    elif suffix == ".flac":
        audio = FLAC(path)
        audio["lyrics"] = [spl]
        audio.save()

    elif suffix in {".ogg", ".opus"}:
        audio = OggVorbis(path)
        audio["lyrics"] = [spl]
        audio.save()

    else:
        # 通用回退：尝试用 mutagen 自动检测格式
        audio = mutagen.File(path)
        if audio is None:
            raise ValueError(f"不支持的文件格式: {path.suffix}")
        audio["lyrics"] = [spl]
        audio.save()


def clear_lyrics(path: Path, existing_lyric: str | None = None) -> None:
    """清除音频文件中的歌词标签。"""
    if existing_lyric:
        _backup_embedded(path, existing_lyric)

    suffix = path.suffix.lower()

    if suffix == ".mp3":
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            return
        tags.delall("USLT")
        tags.save()
        return

    if suffix == ".flac":
        audio = FLAC(path)
        audio.pop("lyrics", None)
        audio.pop("LYRICS", None)
        audio.save()
        return

    if suffix in {".ogg", ".opus"}:
        audio = OggVorbis(path)
        audio.pop("lyrics", None)
        audio.pop("LYRICS", None)
        audio.save()
        return

    audio = mutagen.File(path)
    if audio is None:
        raise ValueError(f"不支持的文件格式: {path.suffix}")
    try:
        audio.pop("lyrics", None)
        audio.pop("LYRICS", None)
    except AttributeError:
        if "lyrics" in audio:
            del audio["lyrics"]
        if "LYRICS" in audio:
            del audio["LYRICS"]
    audio.save()
