"""酷狗 KRC 格式解析器

KRC 格式说明：
- 行时间戳：[开始时间ms,持续时间ms]歌词内容
- 逐字时间戳：<相对开始ms,持续ms,保留字段>文字
- 元数据标签：[key:value]
- language 标签：Base64 编码的 JSON，包含翻译和罗马音

示例：
[0,500]<0,300,0>你<300,200,0>好
"""

import re
import json
import base64
from typing import List, Dict, Tuple, Optional


class LyricsWord:
    """逐字歌词单元"""
    def __init__(self, start: int, end: int, text: str):
        self.start = start  # 绝对时间戳（毫秒）
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


class KrcParser:
    """酷狗 KRC 解析器"""
    
    # 正则表达式
    TAG_PATTERN = re.compile(r'^\[(\w+):([^\]]*)\]$')
    LINE_PATTERN = re.compile(r'^\[(\d+),(\d+)\](.*)$')
    WORD_PATTERN = re.compile(r'<(\d+),(\d+),\d+>([^<]*)')
    
    def parse(self, content: str) -> Tuple[Dict[str, str], Dict[str, List[LyricsLine]]]:
        """解析 KRC 内容
        
        Args:
            content: 解密后的 KRC 明文
            
        Returns:
            (tags, lyrics_data)
            - tags: 元数据标签字典
            - lyrics_data: {"orig": [...], "roma": [...], "ts": [...]}
        """
        tags = {}
        orig_lines = []
        
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            
            # 解析标签
            tag_match = self.TAG_PATTERN.match(line)
            if tag_match:
                key, value = tag_match.groups()
                tags[key] = value
                continue
            
            # 解析歌词行
            line_match = self.LINE_PATTERN.match(line)
            if line_match:
                line_start = int(line_match.group(1))
                line_duration = int(line_match.group(2))
                line_end = line_start + line_duration
                line_content = line_match.group(3)
                
                # 解析逐字时间戳
                words = []
                for word_match in self.WORD_PATTERN.finditer(line_content):
                    word_offset = int(word_match.group(1))  # 相对行开始的偏移
                    word_duration = int(word_match.group(2))
                    word_text = word_match.group(3)
                    
                    word_start = line_start + word_offset  # 转换为绝对时间
                    word_end = word_start + word_duration
                    
                    words.append(LyricsWord(word_start, word_end, word_text))
                
                # 如果没有逐字时间戳，整行作为一个 word
                if not words:
                    words = [LyricsWord(line_start, line_end, line_content)]
                
                orig_lines.append(LyricsLine(line_start, line_end, words))
        
        # 解析翻译和罗马音（来自 language 标签）
        roma_lines, ts_lines = self._parse_language_tag(tags.get('language'), orig_lines)
        
        lyrics_data = {'orig': orig_lines}
        if roma_lines:
            lyrics_data['roma'] = roma_lines
        if ts_lines:
            lyrics_data['ts'] = ts_lines
        
        return tags, lyrics_data
    
    def _parse_language_tag(
        self, 
        language_b64: Optional[str], 
        orig_lines: List[LyricsLine]
    ) -> Tuple[List[LyricsLine], List[LyricsLine]]:
        """解析 language 标签（Base64 编码的 JSON）
        
        JSON 结构：
        {
            "content": [
                {"type": 0, "lyricContent": [[罗马音1, 罗马音2, ...], ...]},
                {"type": 1, "lyricContent": [[翻译1], [翻译2], ...]}
            ]
        }
        
        Returns:
            (roma_lines, ts_lines)
        """
        roma_lines = []
        ts_lines = []
        
        if not language_b64:
            return roma_lines, ts_lines
        
        try:
            # Base64 解码
            lang_json = json.loads(base64.b64decode(language_b64.strip()).decode('utf-8'))
            content_array = lang_json.get('content', [])
            
            for lang_obj in content_array:
                lang_type = lang_obj.get('type')
                lyric_content = lang_obj.get('lyricContent', [])
                
                if lang_type == 0:  # 罗马音
                    offset = 0
                    for j, orig_line in enumerate(orig_lines):
                        # 跳过空行
                        if all(w.text == '' for w in orig_line.words):
                            offset += 1
                            continue
                        
                        adjusted_index = j - offset
                        if adjusted_index >= len(lyric_content):
                            break
                        
                        roma_words_data = lyric_content[adjusted_index]
                        roma_words = []
                        
                        for k, word in enumerate(orig_line.words):
                            roma_text = roma_words_data[k] if k < len(roma_words_data) else ''
                            roma_words.append(LyricsWord(word.start, word.end, roma_text))
                        
                        roma_lines.append(LyricsLine(orig_line.start, orig_line.end, roma_words))
                
                elif lang_type == 1:  # 翻译
                    for j, orig_line in enumerate(orig_lines):
                        if j >= len(lyric_content):
                            break
                        
                        ts_text = lyric_content[j][0] if lyric_content[j] else ''
                        ts_word = LyricsWord(orig_line.start, orig_line.end, ts_text)
                        ts_lines.append(LyricsLine(orig_line.start, orig_line.end, [ts_word]))
        
        except Exception as e:
            print(f"解析 language 标签失败: {e}")
        
        return roma_lines, ts_lines
