"""测试酷狗完整歌词获取"""

import sys
import io
import json

# 强制 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from fetcher.kugou import KugouApi

api = KugouApi()

# 搜索歌曲
print("=== 搜索歌曲 ===")
song = api.search_song("我愛你-上海蟹-", "カニ研究会")
if not song:
    print("搜索失败")
    sys.exit(1)

print(f"找到歌曲: {song['title']} - {song['artist']}")
print(f"Hash: {song['hash']}")
print()

# 获取歌词
print("=== 获取歌词 ===")
lyrics = api.get_lyrics(song['hash'])
if not lyrics:
    print("获取歌词失败")
    sys.exit(1)

lyrics_data = lyrics['lyrics']
orig_lines = lyrics_data.get('orig', [])
ts_lines = lyrics_data.get('ts', [])

print(f"原文行数: {len(orig_lines)}")
print(f"翻译行数: {len(ts_lines)}")
print()

print("=== 前 10 行原文 ===")
for i, line in enumerate(orig_lines[:10]):
    text = ''.join(w.text for w in line.words)
    print(f"[{i}] 时间: {line.start}ms, 字数: {len(line.words)}, 文本: {text}")
print()

print("=== 后 10 行原文 ===")
for i, line in enumerate(orig_lines[-10:], start=len(orig_lines)-10):
    text = ''.join(w.text for w in line.words)
    print(f"[{i}] 时间: {line.start}ms, 字数: {len(line.words)}, 文本: {text}")
