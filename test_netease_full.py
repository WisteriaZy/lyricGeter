"""测试网易云完整歌词获取"""

import sys
import io

# 强制 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from fetcher.netease import NetEaseApi

api = NetEaseApi()

# 搜索并获取歌词
result = api.search("我愛你-上海蟹-", "カニ研究会")

if not result:
    print("获取歌词失败")
    sys.exit(1)

print(f"来源: {result.source_name}")
print(f"格式: {result.format}")
print(f"匹配: {result.matched_title} - {result.matched_artist}")
print(f"相似度: {result.score}")
print()

# 解析 YRC
from parser.yrc import parse_yrc

yrc_lines = parse_yrc(result.content)
print(f"YRC 行数: {len(yrc_lines)}")
print()

print("=== 前 10 行 ===")
for i, line in enumerate(yrc_lines[:10]):
    print(f"[{i}] 时间: {line.start}ms, 字数: {len(line.words)}, 文本: {line.line_text}")
print()

print("=== 后 10 行 ===")
for i, line in enumerate(yrc_lines[-10:], start=len(yrc_lines)-10):
    print(f"[{i}] 时间: {line.start}ms, 字数: {len(line.words)}, 文本: {line.line_text}")
