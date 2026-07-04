from __future__ import annotations

import re
from dataclasses import dataclass

from fetcher.base import LyricFormat, LyricResult
from parser.yrc import YrcParser
from parser.json_lyric import JsonLyricParser
from parser.netease_word import NetEaseWordLyricParser
from parser.krc import KrcParser, LyricsLine as KrcLine

# 匹配行首时间戳列表，如 [00:01.00][00:05.00]
_STAMP_RE = re.compile(r"\[(\d+):(\d{1,2})[.:](\d{1,6})\]")
# 匹配行内中间时间戳（逐字）
_INLINE_STAMP_RE = re.compile(r"(<?)(\[)(\d+):(\d{1,2})[.:](\d{1,6})(\])(>?)")


def _parse_ms(m: int, s: int, frac_str: str) -> int:
    """时间戳各部分 → 毫秒。frac_str 为小数点后字符串，不足3位后补0。"""
    frac = frac_str.ljust(3, "0")[:3]
    return m * 60_000 + s * 1_000 + int(frac)


def _ms_to_stamp(ms: int) -> str:
    """毫秒 → [mm:ss.xx] 格式。毫秒部分：最少1位、最多6位，通常保留2位（10ms精度）。"""
    if ms is None:
        ms = 0
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

    使用最近邻匹配：容差 ±2000ms，避免 YRC 与翻译 LRC 的时间戳偏移导致漏匹配。
    已匹配的翻译行会被标记，防止重复匹配。
    """
    # 解析翻译 LRC，构建 [(时间戳, 翻译文本)] 列表
    trans_list: list[tuple[int, str]] = []
    for line in _parse_lrc(trans_lrc):
        if line.text.strip():
            trans_list.append((line.stamps[0], line.text.strip()))

    if not trans_list:
        return spl_content

    used: set[int] = set()
    out_lines: list[str] = []
    for spl_line in spl_content.splitlines():
        spl_line = spl_line.strip()
        if not spl_line:
            continue

        match = _STAMP_RE.match(spl_line)
        if match:
            line_start_ms = _parse_ms(int(match.group(1)), int(match.group(2)), match.group(3))
            out_lines.append(spl_line)

            # 最近邻匹配：找最近的未使用翻译（±2000ms）
            best_idx = -1
            min_diff = 2000
            for i, (trans_ms, trans_text) in enumerate(trans_list):
                if i in used:
                    continue
                diff = abs(trans_ms - line_start_ms)
                if diff < min_diff:
                    min_diff = diff
                    best_idx = i

            if best_idx >= 0:
                used.add(best_idx)
                out_lines.append(trans_list[best_idx][1])
        else:
            out_lines.append(spl_line)

    return "\n".join(out_lines)


def extract_translation_lrc(result: LyricResult) -> str | None:
    """从任意 LyricResult 提取翻译歌词的 LRC 文本。

    - 网易云等：result.translation 直接是 LRC 文本
    - 酷狗 KRC：翻译在 content['ts'] 中，转换为 LRC 文本
    """
    # 网易云等：translation 字段直接是 LRC 文本
    if result.translation:
        return result.translation
    # 酷狗 KRC：翻译在 content['ts'] 中
    if isinstance(result.content, dict) and "ts" in result.content:
        ts_lines = result.content["ts"]
        if not ts_lines:
            return None
        lines = []
        for line in ts_lines:
            text = line.words[0].text if line.words else ""
            if text.strip():
                lines.append(f"{_ms_to_stamp(line.start)}{text}")
        return "\n".join(lines) if lines else None
    return None


def _merge_translation_sequential(spl: str, translation_lrc: str) -> str:
    """按行顺序合并翻译到 SPL（用于跨源时间戳不匹配的情况）。

    跳过翻译中的元数据行，按行号 1:1 匹配主歌词。
    """
    # 解析翻译 LRC，提取纯文本（跳过元数据）
    trans_texts: list[str] = []
    for line in _parse_lrc(translation_lrc):
        if line.text.strip():
            trans_texts.append(line.text.strip())

    if not trans_texts:
        return spl

    # 按顺序合并：第 i 个翻译对应第 i 行主歌词
    out_lines: list[str] = []
    spl_lines = [l for l in spl.splitlines() if l.strip()]
    for i, spl_line in enumerate(spl_lines):
        out_lines.append(spl_line)
        if i < len(trans_texts):
            out_lines.append(trans_texts[i])

    return "\n".join(out_lines)


def merge_translation(spl: str, translation_lrc: str) -> str:
    """将翻译 LRC 合并到 SPL 歌词中（跨源翻译合并的公开接口）。

    优先使用时间戳容差匹配（同源场景），匹配率低时回退到顺序匹配（跨源场景）。
    """
    # 先尝试时间戳容差匹配
    timestamp_result = _merge_translation_to_spl(spl, translation_lrc)

    # 统计匹配率
    result_lines = [l for l in timestamp_result.splitlines() if l.strip()]
    spl_line_count = sum(1 for l in spl.splitlines() if l.strip() and l.strip().startswith("["))
    trans_line_count = sum(1 for l in result_lines if l.strip() and not l.strip().startswith("["))

    # 匹配率低于 30% 时回退到顺序匹配
    if spl_line_count > 0 and trans_line_count < spl_line_count * 0.3:
        return _merge_translation_sequential(spl, translation_lrc)

    return timestamp_result


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


def _merge_translation_by_lrc(spl_content: str, lrc_content: str, trans_lrc: str) -> str:
    """按 LRC 行位置对齐翻译，避免 YRC intro 时间戳压缩导致的翻译错位。

    网易云 YRC 有时会将 intro 行（标题/词/曲）压在同一秒区间，
    而翻译 LRC 与普通 LRC 共享同一套时间戳。若仅按 YRC SPL
    时间戳做容差匹配，翻译会被错配给先到的 intro 行。

    此函数用 LRC 与带时间戳的 SPL 行做 1:1 位置对齐，
    再按 LRC 时间戳查 tlyric 取对应翻译文本。
    """
    lrc_lines = _parse_lrc(lrc_content)
    trans_map: dict[int, str] = {}
    for tl in _parse_lrc(trans_lrc):
        if not tl.text.strip():
            continue
        for ms in tl.stamps:
            trans_map[ms] = tl.text.strip()

    spl_lines = spl_content.splitlines()
    timed_indices = [i for i, line in enumerate(spl_lines) if _STAMP_RE.match(line)]

    if not lrc_lines or len(lrc_lines) != len(timed_indices):
        # 位置无法对齐时回退为原有容差匹配
        return _merge_translation_to_spl(spl_content, trans_lrc)

    out: list[str] = []
    for j, spl_idx in enumerate(timed_indices):
        out.append(spl_lines[spl_idx])
        lrc_ms = lrc_lines[j].stamps[0]
        if lrc_ms in trans_map:
            out.append(trans_map[lrc_ms])

    return "\n".join(out)


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


def _ttml_to_spl(lines: list) -> str:
    """将 TTML 解析结果转换为 SPL 格式

    - 逐字 span 转为 SPL 逐字格式（行首 []，中间 <>）
    - 翻译行紧跟主歌词行（无时间戳）
    - 跳过背景人声（x-bg）和 Ruby 注音
    - 行结束时间戳 = 下一行开始时间
    """
    if not lines:
        return ""

    out_lines: list[str] = []

    for i, line in enumerate(lines):
        parts: list[str] = []

        # 逐字时间戳
        if line.words and len(line.words) > 1:
            for idx, word in enumerate(line.words):
                if idx == 0:
                    parts.append(_ms_to_stamp(word.start))
                else:
                    parts.append(f"<{_ms_to_stamp(word.start)[1:-1]}>")
                parts.append(word.text)
        elif line.words:
            # 单 word（行级）
            parts.append(_ms_to_stamp(line.start))
            parts.append(line.words[0].text)
        else:
            continue

        # 行结束时间戳
        if i + 1 < len(lines):
            parts.append(_ms_to_stamp(lines[i + 1].start))
        else:
            parts.append(_ms_to_stamp(line.end))

        out_lines.append(''.join(parts))

        # 翻译行（紧跟主歌词，无时间戳）
        if line.translation:
            out_lines.append(line.translation)

    return '\n'.join(out_lines)


def _qrc_to_spl(orig_lines: list, trans_lines: list = None, roma_lines: list = None) -> str:
    """将 QRC 解析结果转换为 SPL
    
    Args:
        orig_lines: 主歌词行列表（LyricsLine 对象）
        trans_lines: 翻译行列表（可选，LyricsLine 对象）
        roma_lines: 罗马音行列表（可选，LyricsLine 对象）
    
    Returns:
        SPL 格式字符串
    """
    if not orig_lines:
        return ""
    
    out_lines: list[str] = []
    
    for i, line in enumerate(orig_lines):
        parts: list[str] = []
        
        # 如果有逐字信息（多个 word）
        if line.words and len(line.words) > 1:
            for idx, word in enumerate(line.words):
                if idx == 0:
                    parts.append(_ms_to_stamp(word.start))
                else:
                    parts.append(f"<{_ms_to_stamp(word.start)[1:-1]}>")
                parts.append(word.text)
        else:
            # 无逐字信息或单个 word，只有行级时间戳
            parts.append(_ms_to_stamp(line.start))
            if line.words:
                parts.append(line.words[0].text)
        
        # 行结束时间戳：用 []
        if i + 1 < len(orig_lines):
            parts.append(_ms_to_stamp(orig_lines[i + 1].start))
        else:
            parts.append(_ms_to_stamp(line.end))
        
        out_lines.append(''.join(parts))
        
        # 翻译行（紧跟主歌词，无时间戳）
        if trans_lines and i < len(trans_lines):
            trans = trans_lines[i]
            if trans.words:
                trans_text = trans.words[0].text
                if trans_text and trans_text.strip():
                    out_lines.append(trans_text)
    
    return '\n'.join(out_lines)


def _krc_to_spl(lyrics_data: dict, has_translation: bool = False) -> str:
    """将 KRC 格式转换为 SPL
    
    KRC 格式：[开始ms,持续ms]<偏移ms,持续ms,0>字
    SPL 格式：[00:00.00]<00:00.10>字<00:00.30>符[00:00.50]
    
    关键：
    - 行首/行尾用 []
    - 中间时间戳用 <>（延迟逐字标记）
    - 翻译紧跟主歌词，无时间戳
    """
    orig_lines: list[KrcLine] = lyrics_data.get('orig', [])
    ts_lines: list[KrcLine] = lyrics_data.get('ts', [])
    
    if not orig_lines:
        return ""
    
    out_lines: list[str] = []
    
    for i, line in enumerate(orig_lines):
        parts: list[str] = []
        
        # 逐字部分
        for idx, word in enumerate(line.words):
            if idx == 0:
                # 行首时间戳：用 []
                parts.append(_ms_to_stamp(word.start))
            else:
                # 中间时间戳：用 <>
                parts.append(f"<{_ms_to_stamp(word.start)[1:-1]}>")
            parts.append(word.text)
        
        # 行结束时间戳：用 []
        if i + 1 < len(orig_lines):
            # 用下一行开始时间作为结束
            parts.append(_ms_to_stamp(orig_lines[i + 1].start))
        else:
            # 最后一行，用行结束时间
            parts.append(_ms_to_stamp(line.end))
        
        out_lines.append(''.join(parts))
        
        # 翻译行（紧跟主歌词，无时间戳）
        if has_translation and i < len(ts_lines):
            ts_text = ts_lines[i].words[0].text if ts_lines[i].words else ""
            if ts_text.strip():
                out_lines.append(ts_text)
    
    return '\n'.join(out_lines)


def to_spl(result: LyricResult) -> str:
    """
    将 LyricResult 转换为 SPL 格式字符串。

    - 补全显式结尾时间戳（每行 end = 下一行 start）
    - 逐字模式：校验严格递增，不合格则降级为行级
    - 翻译行：同时间戳，紧跟主歌词行后（省略时间戳）
    """
    # AMLL TTML 格式
    if result.source_name == "amll":
        from parser.ttml import parse_ttml
        _, ttml_lines = parse_ttml(result.content)
        return _ttml_to_spl(ttml_lines)

    # QQ 音乐 QRC 格式
    if result.source_name == "qqmusic":
        from parser.qrc import qrc_str_parse
        _, orig_lines = qrc_str_parse(result.content)
        trans_lines = None
        if result.translation:
            _, trans_lines = qrc_str_parse(result.translation)
        return _qrc_to_spl(orig_lines, trans_lines=trans_lines)
    
    # 酷狗 KRC 格式（逐字或行级都以解析后的字典传入）
    if result.source_name == "kugou":
        if isinstance(result.content, dict) and 'orig' in result.content:
            has_translation = 'ts' in result.content and result.content['ts']
            return _krc_to_spl(result.content, has_translation)
    
    # 网易云混合格式：优先提取标准 LRC 行，过滤 JSON 元数据
    if result.source_name == "netease":
        # 检测网易云逐字格式 [ms,ms](ms,ms,0)字
        netease_word_parser = NetEaseWordLyricParser()
        if netease_word_parser.is_netease_word_format(result.content):
            spl_content = _netease_word_to_spl(result.content)
            # 如果有翻译，合并翻译行
            if result.translation:
                # 优先用 LRC 做位置对齐，避免 YRC intro 时间戳压缩导致翻译错位
                lrc_content = getattr(result, "lrc_content", None)
                if lrc_content:
                    return _merge_translation_by_lrc(spl_content, lrc_content, result.translation)
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
