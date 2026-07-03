"""网易云 YRC 格式解析器

YRC 格式示例：
[0,500]你(0,300,0)好(300,200,0)世(500,250,0)界(750,150,0)

格式说明：
- [行开始ms, 行持续ms] 文本(字开始ms, 字持续ms, 保留字段)
- 字的开始时间是相对行开始时间的偏移
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class YrcWord:
    """YRC 逐字时间戳"""
    start: int  # 绝对时间（毫秒）
    end: int    # 绝对时间（毫秒）
    text: str


@dataclass
class YrcLine:
    """YRC 行级数据"""
    start: int  # 行开始时间（毫秒）
    end: int    # 行结束时间（毫秒）
    words: list[YrcWord]  # 逐字数据


class YrcParser:
    """网易云 YRC 格式解析器"""
    
    # 行级正则：[行开始ms,行持续ms]内容
    LINE_PATTERN = re.compile(r"^\[(\d+),(\d+)\](.*)$")
    
    # 逐字正则：文字(字开始ms,字持续ms,保留字段)
    WORD_PATTERN = re.compile(r"\((\d+),(\d+),\d+\)([^\(]*)")
    
    def parse(self, content: str) -> list[YrcLine]:
        """解析 YRC 文本，返回行列表"""
        lines: list[YrcLine] = []
        
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line.startswith("["):
                continue
            
            match = self.LINE_PATTERN.match(line)
            if not match:
                continue
            
            line_start = int(match.group(1))
            line_duration = int(match.group(2))
            line_end = line_start + line_duration
            line_content = match.group(3)
            
            # 解析逐字时间戳
            words: list[YrcWord] = []
            for word_match in self.WORD_PATTERN.finditer(line_content):
                word_start_offset = int(word_match.group(1))  # 相对时间
                word_duration = int(word_match.group(2))
                word_text = word_match.group(3)
                
                # 转换为绝对时间
                word_start_abs = line_start + word_start_offset
                word_end_abs = word_start_abs + word_duration
                
                words.append(YrcWord(
                    start=word_start_abs,
                    end=word_end_abs,
                    text=word_text
                ))
            
            # 如果没有逐字数据，整行作为一个 word
            if not words:
                words.append(YrcWord(
                    start=line_start,
                    end=line_end,
                    text=line_content
                ))
            
            lines.append(YrcLine(
                start=line_start,
                end=line_end,
                words=words
            ))
        
        return lines
    
    def has_word_timestamps(self, content: str) -> bool:
        """检测是否包含逐字时间戳"""
        for line in content.splitlines():
            if self.WORD_PATTERN.search(line):
                return True
        return False
