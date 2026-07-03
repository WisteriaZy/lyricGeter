"""QQ 音乐 QRC 格式解析器

QRC 格式类似 LRC，但带逐字时间戳
格式：[行开始ms,行持续ms]文字(字开始ms,字持续ms)文字(字开始ms,字持续ms)...
"""

import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class QrcParser:
    """QRC 格式解析器"""
    
    # 匹配行：[开始,持续]内容
    LINE_PATTERN = re.compile(r'^\[(\d+),(\d+)\](.*)$')
    
    # 匹配逐字时间戳：文字(开始,持续)
    WORD_PATTERN = re.compile(r'([^(]*)\((\d+),(\d+)\)')
    
    @classmethod
    def parse(cls, qrc_text: str) -> List[dict]:
        """解析 QRC 歌词
        
        Args:
            qrc_text: QRC 明文歌词
            
        Returns:
            解析后的行列表，每行包含：
            - start: 行开始时间（毫秒）
            - end: 行结束时间（毫秒）
            - text: 完整行文本（不含时间戳）
            - words: 逐字信息列表 [{"text": "字", "start": ms, "end": ms}, ...]
        """
        lines = []
        
        for line_text in qrc_text.split('\n'):
            line_text = line_text.strip()
            if not line_text:
                continue
            
            # 跳过元数据标签
            if line_text.startswith('[') and ':' in line_text and ']' in line_text:
                tag_end = line_text.index(']')
                tag_content = line_text[1:tag_end]
                if ':' in tag_content and not ',' in tag_content:
                    # 这是元数据标签（如 [ti:标题]），不是歌词行
                    continue
            
            # 匹配行级时间戳
            match = cls.LINE_PATTERN.match(line_text)
            if not match:
                continue
            
            line_start = int(match.group(1))
            line_duration = int(match.group(2))
            line_end = line_start + line_duration
            line_content = match.group(3)
            
            # 解析逐字时间戳
            words = []
            full_text = ""
            
            # 查找所有 文字(时间,持续) 模式
            for word_match in cls.WORD_PATTERN.finditer(line_content):
                text = word_match.group(1)
                word_start = int(word_match.group(2))
                word_duration = int(word_match.group(3))
                word_end = word_start + word_duration
                
                if text:  # 只添加非空文本
                    words.append({
                        "text": text,
                        "start": line_start + word_start,  # 转换为绝对时间
                        "end": line_start + word_end
                    })
                    full_text += text
            
            # 如果没有逐字信息，提取纯文本
            if not words:
                # 移除所有时间戳标记，获取纯文本
                full_text = cls.WORD_PATTERN.sub(r'\1', line_content)
            
            if full_text or words:  # 只添加有内容的行
                lines.append({
                    "start": line_start,
                    "end": line_end,
                    "text": full_text,
                    "words": words
                })
        
        logger.debug(f"QRC 解析完成：{len(lines)} 行")
        return lines
    
    @classmethod
    def parse_smart(cls, qrc_text: str) -> Tuple[str, List[dict]]:
        """智能解析 QRC（兼容 XML 包裹格式）
        
        Args:
            qrc_text: QRC 文本（可能被 XML 包裹）
            
        Returns:
            (lyric_type, lines) - 歌词类型和解析后的行
        """
        # 处理 XML 包裹的情况
        if qrc_text.strip().startswith('<?xml') or '<Lyric_1' in qrc_text:
            # 提取 LyricContent 属性
            import xml.etree.ElementTree as ET
            try:
                root = ET.fromstring(qrc_text)
                lyric_content = root.get('LyricContent', '')
                if lyric_content:
                    qrc_text = lyric_content
                    logger.debug("从 XML 中提取 LyricContent")
            except ET.ParseError:
                # 如果 XML 解析失败，尝试正则提取
                match = re.search(r'LyricContent="([^"]*)"', qrc_text)
                if match:
                    qrc_text = match.group(1)
                    logger.debug("通过正则从 XML 中提取 LyricContent")
        
        lines = cls.parse(qrc_text)
        
        # 判断歌词类型
        lyric_type = "VERBATIM" if any(line["words"] for line in lines) else "LINEBYLINE"
        
        return lyric_type, lines


def parse_qrc(qrc_text: str) -> List[dict]:
    """便捷函数：解析 QRC 歌词"""
    return QrcParser.parse(qrc_text)
