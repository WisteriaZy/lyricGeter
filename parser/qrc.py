"""QQ 音乐 QRC 格式解析器

基于 LDDC (Python) 项目的 qrc.py 实现
支持 XML 包裹格式和纯 LRC 格式
"""

import re
from typing import List, Tuple, Optional


class LyricsWord:
    """逐字歌词单元"""
    def __init__(self, start: int, end: int, text: str):
        self.start = start
        self.end = end
        self.text = text

    def __repr__(self):
        return f"LyricsWord(start={self.start}, end={self.end}, text='{self.text}')"


class LyricsLine:
    """逐行歌词单元"""
    def __init__(self, start: int, end: int, words: List[LyricsWord]):
        self.start = start
        self.end = end
        self.words = words

    def __repr__(self):
        return f"LyricsLine(start={self.start}, end={self.end}, words={len(self.words)})"


QRC_MAGICHEADER = b"\x98%\xb0\xac\xe3\x02\x83h\xe8\xfcl"

_QRC_PATTERN = re.compile(r'<Lyric_1 LyricType="1" LyricContent="(?P<content>.*?)"/>', re.DOTALL)
_TAG_SPLIT_PATTERN = re.compile(r"^\[(\w+):([^\]]*)\]$")
_LINE_SPLIT_PATTERN = re.compile(r"^\[(\d+),(\d+)\](.*)$")
_WORD_SPLIT_PATTERN = re.compile(r"(?:\[\d+,\d+\])?(?P<content>(?:(?!\(\d+,\d+\)).)*)\((?P<start>\d+),(?P<duration>\d+)\)")
_WORD_TIMESTAMP_PATTERN = re.compile(r"^\(\d+,\d+\)$")


def qrc2data(s_qrc: str) -> Tuple[dict, List[LyricsLine]]:
    """将 QRC XML 格式解析为歌词行列表"""
    qrc_match = _QRC_PATTERN.search(s_qrc)
    if not qrc_match or not qrc_match.group("content"):
        return {}, []

    tags: dict[str, str] = {}
    lrc_list: list[LyricsLine] = []

    for raw_line in qrc_match.group("content").splitlines():
        line = raw_line.strip()
        if not line:
            continue

        line_match = _LINE_SPLIT_PATTERN.match(line)
        if line_match:
            line_start, line_duration, line_content = line_match.groups()
            line_start = int(line_start)
            line_end = line_start + int(line_duration)

            if line_content.startswith("(") and line_content.endswith(")") and _WORD_TIMESTAMP_PATTERN.match(line_content):
                lrc_list.append(LyricsLine(line_start, line_end, []))
                continue

            words = [
                LyricsWord(
                    int(word_match.group("start")),
                    int(word_match.group("start")) + int(word_match.group("duration")),
                    word_match.group("content"),
                )
                for word_match in _WORD_SPLIT_PATTERN.finditer(line_content)
                if word_match.group("content") != "\r"
            ]
            if not words:
                words = [LyricsWord(line_start, line_end, line_content)]

            lrc_list.append(LyricsLine(line_start, line_end, words))
        else:
            tag_split_content = re.findall(_TAG_SPLIT_PATTERN, line)
            if tag_split_content:
                tags[tag_split_content[0][0]] = tag_split_content[0][1]

    return tags, lrc_list


def parse_lrc(lrc_text: str) -> Tuple[dict, List[LyricsLine]]:
    """解析 LRC 格式歌词"""
    tags: dict[str, str] = {}
    lines: list[LyricsLine] = []
    stamp_re = re.compile(r"\[(\d+):(\d{1,2})[.:](\d{1,3})\]")

    for raw in lrc_text.splitlines():
        raw = raw.strip()
        if not raw:
            continue

        stamps: list[int] = []
        pos = 0
        while pos < len(raw):
            m = stamp_re.match(raw, pos)
            if not m:
                break
            ms = int(m.group(1)) * 60000 + int(m.group(2)) * 1000 + int(m.group(3).ljust(3, "0")[:3])
            stamps.append(ms)
            pos = m.end()

        if stamps:
            text = raw[pos:]
            for ms in stamps:
                lines.append(LyricsLine(ms, None, [LyricsWord(ms, None, text)]))
        else:
            tag_match = _TAG_SPLIT_PATTERN.match(raw)
            if tag_match:
                tags[tag_match.group(1)] = tag_match.group(2)

    return tags, lines


def qrc_str_parse(lyric: str) -> Tuple[dict, List[LyricsLine]]:
    """智能解析 QRC 歌词（自动检测 XML 或 LRC 格式）"""
    if re.search(r'<Lyric_1 LyricType="1" LyricContent="(.*?)"/>', lyric, re.DOTALL):
        return qrc2data(lyric)
    if "[" in lyric and "]" in lyric:
        try:
            return parse_lrc(lyric)
        except Exception:
            pass
    return {}, [LyricsLine(None, None, [LyricsWord(None, None, lyric)])]


def judge_lyrics_type(lyrics: List[LyricsLine]) -> str:
    """判断歌词类型：VERBATIM（逐字）或 LINEBYLINE（行级）"""
    for line in lyrics:
        if len(line.words) > 1:
            return "VERBATIM"
    return "LINEBYLINE"
