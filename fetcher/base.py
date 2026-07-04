from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import IntEnum


class LyricFormat(IntEnum):
    """歌词格式质量，值越小优先级越高。"""
    WORD = 0   # 逐字（行内中间时间戳）
    LINE = 1   # 行级同步 LRC
    PLAIN = 2  # 纯文本，无时间戳


@dataclass
class SongCandidate:
    source_name: str
    source_id: str
    title: str
    artist: str
    album: str = ""
    duration_ms: int = 0
    payload: dict = field(default_factory=dict)


@dataclass
class LyricResult:
    content: str | dict              # 主歌词（LRC/纯文本）或解析后的字典（KRC）
    format: LyricFormat
    source_name: str                 # 来源名称，如 "netease", "kugou", "qqmusic"
    translation: str | list | None = None   # 翻译歌词（同格式 LRC 或纯文本，或解析后的列表）
    romanization: list | None = None        # 罗马音（QQ 音乐）
    lines: list | None = None               # 解析后的行列表（用于 QRC 等格式）
    matched_title: str = ""          # 平台返回的歌曲标题（用于相似度评分）
    matched_artist: str = ""         # 平台返回的艺术家（用于相似度评分）
    score: float = 0.0               # rapidfuzz 相似度分 (0-100)
    lrc_content: str | None = None          # 网易云 LRC 原文（用于 YRC 翻译对齐）
    duration_ms: int = 0                  # 平台匹配到的歌曲时长（毫秒），0 表示未知


class LyricsFetcher(ABC):
    @abstractmethod
    def search(self, title: str, artist: str) -> LyricResult | None:
        """搜索歌词，失败返回 None。"""

    def search_songs(self, query: str, limit: int = 10) -> list[SongCandidate]:
        """搜索平台歌曲候选，供交互式手动选择。"""
        return []

    def fetch_by_song(self, song: SongCandidate) -> LyricResult | None:
        """按用户选中的平台歌曲获取歌词。"""
        return None
