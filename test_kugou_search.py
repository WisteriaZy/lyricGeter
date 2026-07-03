"""测试酷狗搜索结果"""

import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from fetcher.kugou import KugouApi

api = KugouApi()

# 搜索参数
keyword = "カニ研究会 我愛你-上海蟹-"

params = {
    "keyword": keyword,
    "page": "1",
    "pagesize": "10",  # 增加返回数量
    "filter": "0"
}

import hashlib
import time

def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()

def _generate_signature(params):
    SIGNATURE_KEY = "LnT6xpN3khm36zse0QzvmgTZ3waWdRSA"
    sorted_params = sorted(params.items())
    param_str = ''.join(f"{k}={v}" for k, v in sorted_params)
    sign_str = f"{SIGNATURE_KEY}{param_str}{SIGNATURE_KEY}"
    return _md5(sign_str)

mid = _md5(str(int(time.time() * 1000)))

params.update({
    "userid": "0",
    "appid": "3116",
    "token": "",
    "clienttime": str(int(time.time())),
    "iscorrection": "1",
    "uuid": "-",
    "mid": mid,
    "dfid": "-",
    "clientver": "11070",
    "platform": "AndroidFilter"
})

params["signature"] = _generate_signature(params)

headers = {
    "User-Agent": f"Android14-1070-11070-201-0-search-wifi",
    "Connection": "Keep-Alive",
    "Accept-Encoding": "identity",
    "KG-Rec": "1",
    "KG-RC": "1",
    "KG-CLIENTTIMEMS": str(int(time.time() * 1000)),
    "mid": mid
}

import httpx

response = httpx.get(
    "http://mobilecdn.kugou.com/api/v3/search/song",
    params=params,
    headers=headers,
    timeout=10
)

data = response.json()

if data.get("status") == 1:
    songs = data.get("data", {}).get("info", [])
    print(f"找到 {len(songs)} 首歌曲:\n")
    
    for i, song in enumerate(songs):
        title = song.get("songname", "")
        artist = song.get("singername", "")
        duration = song.get("duration", 0)
        has_fragment = '片段' in title
        
        print(f"[{i}] {title} - {artist}")
        print(f"    时长: {duration}秒")
        print(f"    片段: {'是' if has_fragment else '否'}")
        print()
    
    # 测试过滤逻辑
    full_version_songs = [s for s in songs if '片段' not in s.get("songname", "")]
    print(f"过滤后剩余 {len(full_version_songs)} 首完整版")
    
    if full_version_songs:
        selected = full_version_songs[0]
        print(f"\n选中: {selected.get('songname')} - {selected.get('singername')}")
    else:
        print("\n⚠️  没有找到完整版，会使用第一个结果（片段版）")
else:
    print(f"搜索失败: {data}")
