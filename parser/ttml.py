"""TTML (Timed Text Markup Language) 解析器

解析 AMLL TTML 数据库的歌词文件，提取：
- 逐字时间戳（span begin/end）
- 翻译（ttm:role="x-translation"）
- 罗马音（ttm:role="x-roman"）

舍弃 SPL 不支持的功能：
- 背景人声（ttm:role="x-bg"）
- 对唱/演唱者信息（ttm:agent）
- Ruby 注音（tts:ruby）

参考：docs/TTML 格式介绍 AMLL Docs.md
"""

import re
from xml.etree import ElementTree as ET
from typing import List, Tuple, Optional

# TTML 命名空间
NS = {
    "tt": "http://www.w3.org/ns/ttml",
    "ttm": "http://www.w3.org/ns/ttml#metadata",
    "itunes": "http://music.apple.com/lyric-ttml-internal",
    "amll": "http://www.example.com/ns/amll",
    "tts": "http://www.w3.org/ns/ttml#styling",
}


class TtmlWord:
    """逐字歌词单元"""
    __slots__ = ("start", "end", "text")
    def __init__(self, start: int, end: int, text: str):
        self.start = start
        self.end = end
        self.text = text

    def __repr__(self):
        return f"TtmlWord(start={self.start}, end={self.end}, text='{self.text}')"


class TtmlLine:
    """逐行歌词单元"""
    __slots__ = ("start", "end", "words", "translation", "romanization", "key", "agent")
    def __init__(self, start: int, end: int, words: List[TtmlWord]):
        self.start = start
        self.end = end
        self.words = words
        self.translation: Optional[str] = None
        self.romanization: Optional[str] = None
        self.key: Optional[str] = None
        self.agent: Optional[str] = None

    def __repr__(self):
        return f"TtmlLine(start={self.start}, end={self.end}, words={len(self.words)})"


def _parse_time(time_str: str) -> int:
    """解析 TTML 时间戳为毫秒。

    支持格式：
    - 秒值："10.000" 或 "10.000s"
    - 时钟："00:10.000" 或 "00:01:10.000" 或 "1:10.000"
    """
    if time_str is None:
        return 0

    time_str = time_str.strip()

    # 秒值格式：10.000 或 10.000s
    if time_str.endswith("s") or (":" not in time_str and "." in time_str):
        seconds = float(time_str.rstrip("s"))
        return int(seconds * 1000)

    # 纯整数秒
    if ":" not in time_str:
        return int(float(time_str) * 1000)

    # 时钟格式
    parts = time_str.split(":")
    if len(parts) == 2:  # MM:SS.fff
        m, s = parts
        return int(float(m) * 60000 + float(s) * 1000)
    elif len(parts) == 3:  # HH:MM:SS.fff
        h, m, s = parts
        return int(float(h) * 3600000 + float(m) * 60000 + float(s) * 1000)

    return 0


def _get_attr(elem: ET.Element, name: str) -> Optional[str]:
    """获取属性值，处理带命名空间前缀的属性。"""
    # 先尝试无前缀
    val = elem.get(name)
    if val is not None:
        return val
    # 尝试带前缀的
    for ns_prefix, ns_uri in NS.items():
        val = elem.get(f"{{{ns_uri}}}{name}")
        if val is not None and ns_prefix in ("itunes", "ttm", "amll"):
            return val
    # 查找所有属性，匹配短名称
    for full_name, val in elem.attrib.items():
        if full_name.split("}")[-1] == name:
            return val
    return None


def _extract_text(elem: ET.Element) -> str:
    """提取元素的文本内容（包括子元素的文本）。"""
    if elem.text is not None:
        return elem.text
    # 对于有子元素的，拼接所有文本
    return "".join(child.text or "" for child in elem.iter())


def _parse_span(span: ET.Element, line_start: int) -> Optional[TtmlWord]:
    """解析单个 span 元素为 TtmlWord。"""
    # 检查是否是 ruby 容器，跳过
    ruby = _get_attr(span, "ruby")
    if ruby:
        return None

    # 获取时间戳
    begin = _get_attr(span, "begin")
    end = _get_attr(span, "end")
    dur = _get_attr(span, "dur")

    if begin is None:
        # 无 begin 属性的 span，使用行开始时间
        start_ms = line_start
    else:
        start_ms = _parse_time(begin)

    if end is not None:
        end_ms = _parse_time(end)
    elif dur is not None:
        end_ms = start_ms + _parse_time(dur)
    else:
        end_ms = start_ms

    # 提取文本
    text = _extract_text(span)
    if text is not None:
        text = text.strip()

    if not text:
        return None

    return TtmlWord(start_ms, end_ms, text)


class TtmlParser:
    """TTML 格式解析器"""

    def parse(self, xml_str: str) -> Tuple[dict, List[TtmlLine]]:
        """解析 TTML XML 字符串

        Args:
            xml_str: TTML XML 文本

        Returns:
            (tags, lines) - 元数据字典和歌词行列表
        """
        # 解析 XML
        root = ET.fromstring(xml_str)

        # 提取元数据
        tags = self._parse_metadata(root)

        # 提取歌词行
        lines = self._parse_body(root)

        return tags, lines

    def _parse_metadata(self, root: ET.Element) -> dict:
        """解析 <head><metadata> 中的元数据"""
        tags: dict[str, str] = {}

        # 查找 metadata 元素
        for meta_elem in root.iter():
            tag_name = tag_local_name(meta_elem.tag)
            if tag_name == "metadata":
                # ttm:title, ttm:agent, amll:meta 等
                for child in meta_elem:
                    child_tag = tag_local_name(child.tag)
                    if child_tag == "title":
                        tags["ti"] = _extract_text(child)
                    elif child_tag == "agent":
                        # 跳过对唱/演唱者信息
                        continue
                    elif child_tag == "meta":
                        key = _get_attr(child, "key")
                        value = _get_attr(child, "value")
                        if key and value:
                            tags[key] = value
                break

        return tags

    def _parse_body(self, root: ET.Element) -> List[TtmlLine]:
        """解析 <body><div><p> 中的歌词行"""
        lines: List[TtmlLine] = []

        for p_elem in root.iter():
            if tag_local_name(p_elem.tag) != "p":
                continue

            line = self._parse_line(p_elem)
            if line is not None:
                lines.append(line)

        return lines

    def _parse_line(self, p_elem: ET.Element) -> Optional[TtmlLine]:
        """解析单个 <p> 元素为歌词行"""
        # 行级时间戳
        begin = _get_attr(p_elem, "begin")
        end = _get_attr(p_elem, "end")
        dur = _get_attr(p_elem, "dur")

        line_start = _parse_time(begin) if begin else 0
        if end is not None:
            line_end = _parse_time(end)
        elif dur is not None:
            line_end = line_start + _parse_time(dur)
        else:
            line_end = line_start

        # itunes:key
        key = _get_attr(p_elem, "key")

        # 检查 itunes:timing 是否为 Line（逐行模式）
        timing = _get_attr(p_elem, "timing")

        words: List[TtmlWord] = []
        translation: Optional[str] = None
        romanization: Optional[str] = None

        # 遍历子元素
        for child in p_elem:
            child_tag = tag_local_name(child.tag)
            role = _get_attr(child, "role")

            if child_tag == "span":
                # 检查 role
                if role == "x-translation":
                    # 翻译行
                    trans_text = _extract_text(child)
                    if trans_text and trans_text.strip():
                        translation = trans_text.strip()
                elif role == "x-roman":
                    # 罗马音行
                    roma_text = _extract_text(child)
                    if roma_text and roma_text.strip():
                        romanization = roma_text.strip()
                elif role == "x-bg":
                    # 背景人声，跳过
                    continue
                elif _get_attr(child, "ruby"):
                    # Ruby 注音，跳过
                    continue
                else:
                    # 普通逐字 span
                    # 检查 span 内是否嵌套了 x-translation/x-roman
                    has_special_child = False
                    for sub in child:
                        sub_role = _get_attr(sub, "role")
                        if sub_role in ("x-translation", "x-roman", "x-bg"):
                            has_special_child = True
                            break

                    if not has_special_child:
                        word = _parse_span(child, line_start)
                        if word is not None:
                            # 保留 span 间的空白（单词间空格）
                            if child.tail and child.tail.strip() == "":
                                word.text += " "
                            words.append(word)

        # 如果没有逐字 span 且是 Line 模式（或纯文本），整行作为一个 word
        if not words:
            text = _extract_text(p_elem)
            if text is not None:
                text = text.strip()
            if text:
                words = [TtmlWord(line_start, line_end, text)]

        if not words and not translation:
            return None

        line = TtmlLine(line_start, line_end, words)
        line.translation = translation
        line.romanization = romanization
        line.key = key
        line.agent = _get_attr(p_elem, "agent")
        return line


def tag_local_name(tag: str) -> str:
    """提取带命名空间的标签的本地名称。"""
    if "}" in tag:
        return tag.split("}")[-1]
    return tag


def parse_ttml(xml_str: str) -> Tuple[dict, List[TtmlLine]]:
    """便捷函数：解析 TTML 歌词"""
    parser = TtmlParser()
    return parser.parse(xml_str)


def has_word_timestamps(lines: List[TtmlLine]) -> bool:
    """检查是否有逐字时间戳（至少一行有多个 word）"""
    return any(len(line.words) > 1 for line in lines)
