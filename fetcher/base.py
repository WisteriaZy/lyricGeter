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
class LyricResult:
    content: str | dict              # 主歌词（LRC/纯文本）或解析后的字典（KRC）
    format: LyricFormat
    source_name: str                 # 来源名称，如 "netease", "kugou"
    translation: str | None = None   # 翻译歌词（同格式 LRC 或纯文本）
    matched_title: str = ""          # 平台返回的歌曲标题（用于相似度评分）
    matched_artist: str = ""         # 平台返回的艺术家（用于相似度评分）
    score: float = 0.0               # rapidfuzz 相似度分 (0-100)


class LyricsFetcher(ABC):
    @abstractmethod
    def search(self, title: str, artist: str) -> LyricResult | None:
        """搜索歌词，失败返回 None。"""
