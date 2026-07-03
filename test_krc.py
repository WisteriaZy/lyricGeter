"""测试酷狗 KRC 功能

测试流程：
1. 搜索歌曲
2. 获取加密歌词
3. 解密 KRC
4. 解析为结构化数据
5. 转换为 SPL 格式
"""

import sys
import io
from fetcher.kugou import KugouApi
from converter import _krc_to_spl

# 强制 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def test_kugou_krc(title: str, artist: str = ""):
    """测试酷狗 KRC 完整流程"""
    print(f"=" * 60)
    print(f"测试歌曲: {title} - {artist}")
    print(f"=" * 60)
    
    with KugouApi() as api:
        # 步骤 1: 搜索歌曲
        print("\n[步骤 1] 搜索歌曲...")
        song = api.search_song(title, artist)
        if not song:
            print("❌ 搜索失败")
            return False
        
        print(f"✅ 找到歌曲:")
        print(f"   标题: {song['title']}")
        print(f"   艺术家: {song['artist']}")
        print(f"   专辑: {song['album']}")
        print(f"   Hash: {song['hash']}")
        
        # 步骤 2-4: 获取并解析歌词
        print("\n[步骤 2-4] 获取并解析歌词...")
        lyrics = api.get_lyrics(song['hash'])
        if not lyrics:
            print("❌ 获取歌词失败")
            return False
        
        print(f"✅ 歌词获取成功")
        print(f"   格式: {lyrics['format']}")
        print(f"   来源: {lyrics['source']}")
        
        tags = lyrics['tags']
        lyrics_data = lyrics['lyrics']
        
        print(f"\n[元数据标签]")
        for key, value in tags.items():
            if key != 'language':  # language 太长，跳过
                print(f"   {key}: {value}")
        
        print(f"\n[歌词数据]")
        print(f"   原文行数: {len(lyrics_data.get('orig', []))}")
        print(f"   翻译行数: {len(lyrics_data.get('ts', []))}")
        print(f"   罗马音行数: {len(lyrics_data.get('roma', []))}")
        
        # 显示前 3 行原文
        orig_lines = lyrics_data.get('orig', [])
        if orig_lines:
            print(f"\n[原文前 3 行]")
            for i, line in enumerate(orig_lines[:3]):
                print(f"   行 {i+1}: {line.start}ms - {line.end}ms")
                for word in line.words[:5]:  # 最多显示 5 个字
                    print(f"      {word.start}ms - {word.end}ms: '{word.text}'")
                if len(line.words) > 5:
                    print(f"      ... ({len(line.words)} 个字)")
        
        # 步骤 5: 转换为 SPL
        print(f"\n[步骤 5] 转换为 SPL 格式...")
        has_translation = 'ts' in lyrics_data and lyrics_data['ts']
        spl_content = _krc_to_spl(lyrics_data, has_translation)
        
        if not spl_content:
            print("❌ SPL 转换失败")
            return False
        
        print(f"✅ SPL 转换成功")
        print(f"\n[SPL 预览（前 10 行）]")
        print("-" * 60)
        for line in spl_content.splitlines()[:10]:
            print(line)
        print("-" * 60)
        
        print(f"\n✅ 测试完成！")
        return True


if __name__ == "__main__":
    # 测试用例
    test_cases = [
        ("我愛你", "上海蟹"),  # 日文歌
        ("23.exe", "CHO-DARI-"),  # 可能有逐字
        ("飞", "ANU"),  # input 目录中的歌
    ]
    
    if len(sys.argv) > 1:
        # 命令行参数
        title = sys.argv[1]
        artist = sys.argv[2] if len(sys.argv) > 2 else ""
        test_kugou_krc(title, artist)
    else:
        # 批量测试
        for title, artist in test_cases:
            try:
                test_kugou_krc(title, artist)
            except Exception as e:
                print(f"❌ 测试失败: {e}")
                import traceback
                traceback.print_exc()
            print("\n" * 2)
