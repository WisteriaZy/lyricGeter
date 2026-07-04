"""网易云新版 JSON 歌词格式解析器

新版格式示例：
{"t":21460,"c":[{"tx":"飞"}]}
{"t":22700,"c":[{"tx":"当你想展翅翱翔之时"}]}

格式说明：
- t: 时间戳（毫秒）
- c: 内容数组，每个元素包含 tx（文本）
"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class JsonLyricLine:
    """JSON 歌词行"""
    time: int  # 毫秒
    text: str


class JsonLyricParser:
    """网易云新版 JSON 格式解析器"""
    
    def parse(self, content: str) -> list[JsonLyricLine]:
        """解析 JSON 格式歌词"""
        lines: list[JsonLyricLine] = []
        
        for raw_line in content.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            
            try:
                data = json.loads(line)
                time_ms = data.get("t", 0)
                if time_ms is None:
                    time_ms = 0
                content_arr = data.get("c", [])
                
                # 合并所有文本片段
                text_parts = [item.get("tx", "") for item in content_arr if "tx" in item]
                text = "".join(text_parts)
                
                if text:
                    lines.append(JsonLyricLine(time=time_ms, text=text))
            except json.JSONDecodeError:
                continue
        
        return lines
    
    def is_json_format(self, content: str) -> bool:
        """检测是否为 JSON 格式"""
        for line in content.splitlines()[:5]:  # 只检查前 5 行
            line = line.strip()
            if line:
                try:
                    data = json.loads(line)
                    if isinstance(data, dict) and "t" in data and "c" in data:
                        return True
                except json.JSONDecodeError:
                    pass
        return False
