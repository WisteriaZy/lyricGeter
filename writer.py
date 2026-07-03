from __future__ import annotations

from pathlib import Path

import mutagen
from mutagen.id3 import ID3, USLT, Encoding
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
