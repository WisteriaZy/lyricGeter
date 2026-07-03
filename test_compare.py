"""对比网易云和酷狗的歌词完整度"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from converter import to_spl
from fetcher.netease import NetEaseApi
from fetcher.kugou import KugouFetcher

print("=== 网易云 ===")
netease = NetEaseApi()
netease_result = netease.search('我愛你-上海蟹-', 'カニ研究会')
if netease_result:
    netease_spl = to_spl(netease_result)
    netease_lines = [l for l in netease_spl.split('\n') if l.strip() and l.startswith('[')]
    print(f"匹配: {netease_result.matched_title}")
    print(f"SPL 行数: {len(netease_lines)}")
    print(f"相似度: {netease_result.score}")
    print("\n最后 5 行:")
    for line in netease_lines[-5:]:
        print(line[:80])
else:
    print("获取失败")

print("\n=== 酷狗 ===")
kugou = KugouFetcher()
kugou_result = kugou.search('我愛你-上海蟹-', 'カニ研究会')
if kugou_result:
    kugou_spl = to_spl(kugou_result)
    kugou_lines = [l for l in kugou_spl.split('\n') if l.strip() and l.startswith('[')]
    print(f"匹配: {kugou_result.matched_title}")
    print(f"SPL 行数: {len(kugou_lines)}")
    print(f"相似度: {kugou_result.score}")
    print("\n最后 5 行:")
    for line in kugou_lines[-5:]:
        print(line[:80])
else:
    print("获取失败")

print("\n=== 结论 ===")
if netease_result and kugou_result:
    diff = len(netease_lines) - len(kugou_lines)
    print(f"网易云比酷狗多 {diff} 行")
    print(f"酷狗搜到的是: {kugou_result.matched_title}")
    if '片段' in kugou_result.matched_title:
        print("⚠️  酷狗返回的是片段版本，不是完整版")
