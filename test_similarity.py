"""测试相似度过滤功能"""

import sys
import io

# 强制 UTF-8 输出（Windows 终端）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from fetcher.base import LyricResult, LyricFormat
from matcher import _similarity, DEFAULT_THRESHOLD

def test_similarity_scoring():
    """测试相似度计算"""
    print("=== 测试相似度计算 ===\n")
    
    test_cases = [
        # (标题, 艺术家, 匹配结果, 预期分数范围)
        ("我愛你-上海蟹-", "カニ研究会", "我愛你-上海蟹- カニ研究会", (95, 100)),
        ("飞", "ANU", "FLY ANU", (70, 95)),
        ("飞", "ANU", "你还要我怎样 薛之谦", (0, 50)),  # 完全不匹配
        ("Hello", "Adele", "Hello Adele", (95, 100)),
    ]
    
    for title, artist, matched, expected_range in test_cases:
        score = _similarity(title, artist, matched)
        min_score, max_score = expected_range
        
        status = "✓" if min_score <= score <= max_score else "✗"
        print(f"{status} 标题: {title}, 艺术家: {artist}")
        print(f"  匹配结果: {matched}")
        print(f"  相似度: {score:.1f} (预期: {min_score}-{max_score})")
        print()

def test_threshold_filtering():
    """测试阈值过滤"""
    print("=== 测试阈值过滤 ===\n")
    
    # 模拟 LyricResult
    results = [
        LyricResult(
            content="dummy content",
            format=LyricFormat.WORD,
            source_name="netease",
            matched_title="我愛你-上海蟹-",
            matched_artist="カニ研究会",
            score=98.5
        ),
        LyricResult(
            content="dummy content",
            format=LyricFormat.WORD,
            source_name="kugou",
            matched_title="FLY",
            matched_artist="ANU",
            score=85.0
        ),
        LyricResult(
            content="dummy content",
            format=LyricFormat.LINE,
            source_name="kugou",
            matched_title="你还要我怎样",
            matched_artist="薛之谦",
            score=45.0
        ),
    ]
    
    print(f"默认阈值: {DEFAULT_THRESHOLD}\n")
    
    for result in results:
        should_pass = result.score >= DEFAULT_THRESHOLD
        status = "通过" if should_pass else "过滤"
        
        print(f"{status} - {result.source_name}")
        print(f"  匹配: {result.matched_title} - {result.matched_artist}")
        print(f"  相似度: {result.score:.1f}")
        print()

if __name__ == "__main__":
    test_similarity_scoring()
    test_threshold_filtering()
