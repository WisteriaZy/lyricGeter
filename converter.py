from __future__ import annotations

import re
from dataclasses import dataclass

from fetcher.base import LyricFormat, LyricResult
from parser.yrc import YrcParser
from parser.json_lyric import JsonLyricParser
from parser.netease_word import NetEaseWordLyricParser

# 匹配行首时间戳列表，如 [00:01.00][00:05.00]
_STAMP_RE = re.compile(r"\[(\d+):(\d{1,2})\.(\d{1,6})\]")
# 匹配行内中间时间戳（逐字）
_INLINE_STAMP_RE = re.compile(r"(<?)(\[)(\d+):(\d{1,2})\.(\d{1,6})(\])(>?)")


def _parse_ms(m: int, s: int, frac_str: str) -> int:
    """时间戳各部分 → 毫秒。frac_str 为小数点后字符串，不足3位后补0。"""
    frac = frac_str.ljust(3, "0")[:3]
    return m * 60_000 + s * 1_000 + int(frac)


def _ms_to_stamp(ms: int) -> str:
    """毫秒 → [mm:ss.xx] 格式。毫秒部分：最少1位、最多6位，通常保留2位（10ms精度）。"""
    m, rem = divmod(ms, 60_000)
    s, ms_part = divmod(rem, 1_000)
    # 保留2位毫秒（10ms 精度），移除尾部的 0
    cs = ms_part // 10  # 厘秒（centisecond）
    return f"[{m:02d}:{s:02d}.{cs:02d}]"


@dataclass
class _LrcLine:
    stamps: list[int]   # 行首时间戳（毫秒），可能多个（重复行）
    text: str           # 剩余文本（含逐字时间戳）


def _parse_lrc(lrc: str) -> list[_LrcLine]:
    lines: list[_LrcLine] = []
    for raw in lrc.splitlines():
        raw = raw.strip()
        stamps: list[int] = []
        pos = 0
        while pos < len(raw):
            m = _STAMP_RE.match(raw, pos)
            if not m:
                break
            stamps.append(_parse_ms(int(m.group(1)), int(m.group(2)), m.group(3)))
            pos = m.end()
        if stamps:
            lines.append(_LrcLine(stamps=stamps, text=raw[pos:]))
    return lines


def _validate_word_level(text: str) -> bool:
    """校验逐字时间戳严格递增；任何一行不符合则整体降级。"""
    for line in text.splitlines():
        stamps = [
            _parse_ms(int(m.group(3)), int(m.group(4)), m.group(5))
            for m in _INLINE_STAMP_RE.finditer(line)
        ]
        for a, b in zip(stamps, stamps[1:]):
            if b <= a:
                return False
    return True


def _merge_translation(main_lines: list[_LrcLine], trans_lrc: str) -> dict[int, str]:
    """将翻译 LRC 按时间戳映射为 {ms: 翻译文本} 字典。"""
    trans_map: dict[int, str] = {}
    for line in _parse_lrc(trans_lrc):
        for ms in line.stamps:
            if line.text.strip():
                trans_map[ms] = line.text.strip()
    return trans_map


def _merge_translation_to_spl(spl_content: str, trans_lrc: str) -> str:
    """将翻译歌词合并到 SPL 逐字歌词中。
    
    SPL 翻译格式：主歌词后紧跟翻译行，省略时间戳。
    
    使用容差匹配：允许 ±500ms 的时间戳误差，因为网易云翻译 LRC 和逐字歌词时间戳可能不完全同步。
    """
    # 解析翻译 LRC，构建 [(时间戳, 翻译文本)] 列表
    trans_list: list[tuple[int, str]] = []
    for line in _parse_lrc(trans_lrc):
        if line.text.strip():
            # 使用第一个时间戳
            trans_list.append((line.stamps[0], line.text.strip()))
    
    if not trans_list:
        return spl_content
    
    # 解析 SPL 主歌词，提取每行的行首时间戳
    out_lines: list[str] = []
    for spl_line in spl_content.splitlines():
        spl_line = spl_line.strip()
        if not spl_line:
            continue
        
        # 提取行首时间戳
        match = _STAMP_RE.match(spl_line)
        if match:
            line_start_ms = _parse_ms(int(match.group(1)), int(match.group(2)), match.group(3))
            out_lines.append(spl_line)
            
            # 容差匹配：找到最接近的翻译（±500ms 范围内）
            best_trans = None
            min_diff = 500  # 最大容差 500ms
            
            for trans_ms, trans_text in trans_list:
                diff = abs(trans_ms - line_start_ms)
                if diff < min_diff:
                    min_diff = diff
                    best_trans = trans_text
            
            if best_trans:
                out_lines.append(best_trans)
        else:
            out_lines.append(spl_line)
    
    return '\n'.join(out_lines)


def _yrc_to_spl(content: str) -> str:
    """将 YRC 格式转换为 SPL 逐字格式"""
    parser = YrcParser()
    yrc_lines = parser.parse(content)
    
    if not yrc_lines:
        return content  # 解析失败，原样返回
    
    out_lines: list[str] = []
    
    for i, line in enumerate(yrc_lines):
        # 行首时间戳
        line_start = _ms_to_stamp(line.start)
        
        # 构建逐字部分
        parts: list[str] = [line_start]
        
        for word in line.words:
            # 如果 word 只是纯文本（无逐字时间戳），直接拼接
            if word.text.strip():
                parts.append(word.text)
                # 在每个字后添加时间戳（SPL 逐字格式）
                if word.end > word.start:  # 有有效时间戳
                    parts.append(_ms_to_stamp(word.end))
        
        # 如果有下一行，最后加上行结束时间戳
        if i + 1 < len(yrc_lines):
            next_start = yrc_lines[i + 1].start
            # 避免重复：如果最后已经有时间戳且等于下一行开始，跳过
            if not parts[-1].startswith('['):
                parts.append(_ms_to_stamp(next_start))
        else:
            # 最后一行，用行结束时间
            parts.append(_ms_to_stamp(line.end))
        
        out_lines.append(''.join(parts))
    
    return '\n'.join(out_lines)


def _netease_word_to_spl(content: str) -> str:
    """将网易云逐字格式转换为 SPL
    
    网易云格式：[13860,2310](13860,260,0)ヤ(14120,180,0)リ
    SPL 格式：[00:13.86]ヤ<00:14.12>リ<00:14.30>タ[00:14.45]
    
    关键：行首/行尾用 []，中间时间戳用 <>（SPL 延迟逐字标记）
    """
    parser = NetEaseWordLyricParser()
    lines = parser.parse(content)
    
    if not lines:
        return content  # 解析失败，原样返回
    
    out_lines: list[str] = []
    
    for i, line in enumerate(lines):
        parts: list[str] = []
        
        # 逐字部分：行首用 []，中间用 <>
        for idx, (word_time, word_duration, word_text) in enumerate(line.words):
            if idx == 0:
                # 行首时间戳：用 []
                parts.append(_ms_to_stamp(word_time))
            else:
                # 中间时间戳：用 <>
                parts.append(f"<{_ms_to_stamp(word_time)[1:-1]}>")
            parts.append(word_text)
        
        # 行结束时间戳：用 []
        if i + 1 < len(lines):
            # 用下一行开始时间作为结束
            parts.append(_ms_to_stamp(lines[i + 1].start))
        else:
            # 最后一行，用行起始+持续时间
            parts.append(_ms_to_stamp(line.start + line.duration))
        
        out_lines.append(''.join(parts))
    
    return '\n'.join(out_lines)


def _json_lyric_to_spl(content: str) -> str:
    """将网易云新版 JSON 格式转换为 SPL"""
    parser = JsonLyricParser()
    json_lines = parser.parse(content)
    
    if not json_lines:
        return content  # 解析失败，原样返回
    
    out_lines: list[str] = []
    
    for i, line in enumerate(json_lines):
        # 行首时间戳
        line_start = _ms_to_stamp(line.time)
        
        # 行尾时间戳（下一行开始时间）
        if i + 1 < len(json_lines):
            line_end = _ms_to_stamp(json_lines[i + 1].time)
            out_lines.append(f"{line_start}{line.text}{line_end}")
        else:
            # 最后一行，暂不添加结束时间戳
            out_lines.append(f"{line_start}{line.text}")
    
    return '\n'.join(out_lines)


def to_spl(result: LyricResult) -> str:
    """
    将 LyricResult 转换为 SPL 格式字符串。

    - 补全显式结尾时间戳（每行 end = 下一行 start）
    - 逐字模式：校验严格递增，不合格则降级为行级
    - 翻译行：同时间戳，紧跟主歌词行后（省略时间戳）
    """
    # 网易云混合格式：优先提取标准 LRC 行，过滤 JSON 元数据
    if result.source_name == "netease":
        # 检测网易云逐字格式 [ms,ms](ms,ms,0)字
        netease_word_parser = NetEaseWordLyricParser()
        if netease_word_parser.is_netease_word_format(result.content):
            spl_content = _netease_word_to_spl(result.content)
            # 如果有翻译，合并翻译行
            if result.translation:
                return _merge_translation_to_spl(spl_content, result.translation)
            return spl_content
        
        json_parser = JsonLyricParser()
        # 检测是否包含 JSON 格式行
        if json_parser.is_json_format(result.content):
            # 分离 LRC 行和 JSON 行
            lrc_lines_text = []
            for line in result.content.splitlines():
                line = line.strip()
                if line.startswith('['):
                    # 标准 LRC 行
                    lrc_lines_text.append(line)
            
            # 如果有 LRC 行，优先使用
            if lrc_lines_text:
                content_to_parse = '\n'.join(lrc_lines_text)
            else:
                # 纯 JSON 格式，转换为 SPL
                return _json_lyric_to_spl(result.content)
        else:
            content_to_parse = result.content
        
        # YRC 格式（旧版）
        if result.format == LyricFormat.WORD:
            yrc_parser = YrcParser()
            if yrc_parser.has_word_timestamps(content_to_parse):
                return _yrc_to_spl(content_to_parse)
    else:
        content_to_parse = result.content
    
    fmt = result.format
    lrc_lines = _parse_lrc(content_to_parse)
    if not lrc_lines:
        return content_to_parse  # 无法解析，原样返回

    # 逐字模式校验
    if fmt == LyricFormat.WORD and not _validate_word_level(content_to_parse):
        fmt = LyricFormat.LINE

    trans_map: dict[int, str] = {}
    if result.translation:
        trans_map = _merge_translation(lrc_lines, result.translation)

    out_lines: list[str] = []

    for i, line in enumerate(lrc_lines):
        next_start = lrc_lines[i + 1].stamps[0] if i + 1 < len(lrc_lines) else None

        # 构建行首时间戳部分（重复行合并）
        stamp_prefix = "".join(_ms_to_stamp(ms) for ms in sorted(set(line.stamps)))

        if fmt == LyricFormat.WORD:
            # 逐字：保留行内时间戳，行尾附结束时间戳
            body = line.text
            if next_start is not None:
                body = body.rstrip() + _ms_to_stamp(next_start)
            out_lines.append(stamp_prefix + body)
        else:
            # 行级：文本 + 显式结尾时间戳
            body = line.text.strip()
            if next_start is not None:
                out_lines.append(f"{stamp_prefix}{body}{_ms_to_stamp(next_start)}")
            else:
                out_lines.append(f"{stamp_prefix}{body}")

        # 翻译行（取第一个时间戳对应的翻译）
        main_ms = line.stamps[0]
        if main_ms in trans_map:
            out_lines.append(trans_map[main_ms])

    return "\n".join(out_lines)
