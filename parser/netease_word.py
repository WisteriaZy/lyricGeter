"""网易云逐字歌词格式解析器

格式示例：
[13860,2310](13860,260,0)ヤ(14120,180,0)リ(14300,150,0)タ(14450,220,0)カ

格式说明：
- [起始时间ms,持续时间ms] - 行级时间戳
- (时间ms,持续ms,0)字 - 每个字的时间戳
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class NetEaseWordLyricLine:
    """网易云逐字歌词行"""
    start: int      # 行起始时间（毫秒）
    duration: int   # 行持续时间（毫秒）
    words: list[tuple[int, int, str]]  # (时间ms, 持续ms, 文字)


class NetEaseWordLyricParser:
    """网易云逐字歌词解析器"""
    
    # 匹配行首 [起始ms,持续ms]
    LINE_RE = re.compile(r'^\[(\d+),(\d+)\]')
    # 匹配逐字 (时间ms,持续ms,0)字
    WORD_RE = re.compile(r'\((\d+),(\d+),\d+\)([^\(]+?)(?=\(|$)')
    
    def is_netease_word_format(self, content: str) -> bool:
        """检测是否为网易云逐字格式"""
        for line in content.splitlines()[:5]:
            line = line.strip()
            if line.startswith('[') and ',' in line and '(' in line:
                # 检查是否匹配 [ms,ms](ms,ms,0)字 格式
                if self.LINE_RE.match(line) and self.WORD_RE.search(line):
                    return True
        return False
    
    def parse(self, content: str) -> list[NetEaseWordLyricLine]:
        """解析网易云逐字歌词"""
        lines: list[NetEaseWordLyricLine] = []
        
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line or line.startswith('{'):  # 跳过空行和 JSON 元数据
                continue
            
            # 匹配行首时间戳
            line_match = self.LINE_RE.match(line)
            if not line_match:
                continue
            
            start_ms = int(line_match.group(1))
            duration_ms = int(line_match.group(2))
            
            # 提取所有逐字时间戳
            words: list[tuple[int, int, str]] = []
            for word_match in self.WORD_RE.finditer(line):
                word_time = int(word_match.group(1))
                word_duration = int(word_match.group(2))
                word_text = word_match.group(3)
                if word_text:
                    words.append((word_time, word_duration, word_text))
            
            if words:
                lines.append(NetEaseWordLyricLine(
                    start=start_ms,
                    duration=duration_ms,
                    words=words
                ))
        
        return lines
