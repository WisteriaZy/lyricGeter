"""酷狗音乐 API 客户端

API 流程：
1. 搜索歌曲获取 hash
2. 用 hash 搜索歌词候选（获取 id 和 accesskey）
3. 下载加密歌词（Base64 编码的 KRC）
4. 解密并解析

参考：LDDC-Android KugouApi.kt
"""

import hashlib
import time
from typing import Optional, Dict, Any
import httpx

from fetcher.base import LyricsFetcher, LyricResult, LyricFormat
from decryptor.krc import KrcDecryptor
from parser.krc import KrcParser


class KugouApi:
    """酷狗音乐 API 客户端"""
    
    # 常量（来自 LDDC-Android）
    SIGNATURE_KEY = "LnT6xpN3khm36zse0QzvmgTZ3waWdRSA"
    CLIENT_VER = "11070"
    
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.session = httpx.Client(timeout=timeout)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
    
    @staticmethod
    def _md5(text: str) -> str:
        """计算 MD5 哈希"""
        return hashlib.md5(text.encode()).hexdigest()
    
    def _generate_signature(self, params: Dict[str, str]) -> str:
        """生成签名
        
        规则：SIGNATURE_KEY + 参数按 key 排序拼接 + SIGNATURE_KEY
        """
        sorted_params = sorted(params.items())
        param_str = ''.join(f"{k}={v}" for k, v in sorted_params)
        sign_str = f"{self.SIGNATURE_KEY}{param_str}{self.SIGNATURE_KEY}"
        return self._md5(sign_str)
    
    def _make_request(
        self, 
        url: str, 
        params: Dict[str, str], 
        module: str
    ) -> Dict[str, Any]:
        """统一请求封装"""
        mid = self._md5(str(int(time.time() * 1000)))
        
        headers = {
            "User-Agent": f"Android14-1070-{self.CLIENT_VER}-201-0-{module}-wifi",
            "Connection": "Keep-Alive",
            "Accept-Encoding": "identity",
            "KG-Rec": "1",
            "KG-RC": "1",
            "KG-CLIENTTIMEMS": str(int(time.time() * 1000)),
            "mid": mid
        }
        
        # 根据模块添加参数
        if module == "Lyric":
            params["appid"] = "3116"
            params["clientver"] = self.CLIENT_VER
        else:
            params.update({
                "userid": "0",
                "appid": "3116",
                "token": "",
                "clienttime": str(int(time.time())),
                "iscorrection": "1",
                "uuid": "-",
                "mid": mid,
                "dfid": "-",
                "clientver": self.CLIENT_VER,
                "platform": "AndroidFilter"
            })
        
        # 生成签名
        params["signature"] = self._generate_signature(params)
        
        response = self.session.get(url, params=params, headers=headers)
        response.raise_for_status()
        return response.json()
    
    def search_song(self, title: str, artist: str = "") -> Optional[Dict[str, Any]]:
        """搜索歌曲
        
        Args:
            title: 歌曲标题
            artist: 艺术家（可选）
            
        Returns:
            包含 hash、title、artist 等信息的字典，失败返回 None
        """
        keyword = f"{artist} {title}".strip()
        
        params = {
            "keyword": keyword,
            "page": "1",
            "pagesize": "5",
            "filter": "0"
        }
        
        try:
            data = self._make_request(
                "http://mobilecdn.kugou.com/api/v3/search/song",
                params,
                "search"
            )
            
            if data.get("status") != 1:
                return None
            
            songs = data.get("data", {}).get("info", [])
            if not songs:
                return None
            
            # 返回第一个结果
            song = songs[0]
            return {
                "hash": song.get("hash", ""),
                "title": song.get("songname", ""),
                "artist": song.get("singername", ""),
                "album": song.get("album_name", ""),
                "duration": song.get("duration", 0) * 1000  # 秒转毫秒
            }
        
        except Exception as e:
            print(f"酷狗搜索失败: {e}")
            return None
    
    def get_lyrics(self, song_hash: str) -> Optional[Dict[str, Any]]:
        """获取歌词
        
        Args:
            song_hash: 歌曲 hash（从搜索结果获取）
            
        Returns:
            {
                "tags": {...},  # 元数据标签
                "lyrics": {     # 歌词数据
                    "orig": [...],  # 原文
                    "roma": [...],  # 罗马音（如有）
                    "ts": [...]     # 翻译（如有）
                }
            }
        """
        try:
            # 步骤 1: 搜索歌词候选
            search_params = {
                "clienttime": str(int(time.time())),
                "mid": self._md5(str(int(time.time() * 1000))),
                "clientver": self.CLIENT_VER,
                "dfid": "-",
                "appid": "3116",
                "keyword": "%20",
                "bitrate": "0",
                "album_id": "0",
                "hash": song_hash,
                "album_audio_id": ""
            }
            
            search_data = self._make_request(
                "https://krcs.kugou.com/search",
                search_params,
                "Lyric"
            )
            
            candidates = search_data.get("candidates", [])
            if not candidates:
                return None
            
            # 获取第一个候选
            candidate = candidates[0]
            lyric_id = candidate.get("id")
            accesskey = candidate.get("accesskey")
            
            if not lyric_id or not accesskey:
                return None
            
            # 步骤 2: 下载歌词（不需要 signature）
            download_params = {
                "id": lyric_id,
                "accesskey": accesskey,
                "fmt": "krc",
                "charset": "utf8",
                "client": "mobi",
                "ver": "1"
            }
            
            download_response = self.session.get(
                "http://lyrics.kugou.com/download",
                params=download_params,
                headers={"User-Agent": f"Android14-1070-{self.CLIENT_VER}-201-0-Lyric-wifi"}
            )
            download_response.raise_for_status()
            download_data = download_response.json()
            
            encrypted_content = download_data.get("content")
            if not encrypted_content:
                return None
            
            # 步骤 3: 解密 KRC
            decrypted = KrcDecryptor.decrypt(encrypted_content)
            if not decrypted:
                return None
            
            # 步骤 4: 解析 KRC
            parser = KrcParser()
            tags, lyrics_data = parser.parse(decrypted)
            
            return {
                "tags": tags,
                "lyrics": lyrics_data,
                "source": "kugou",
                "format": "krc"
            }
        
        except Exception as e:
            print(f"酷狗获取歌词失败: {e}")
            return None
    
    def get_lyrics_by_search(self, title: str, artist: str = "") -> Optional[Dict[str, Any]]:
        """通过搜索获取歌词（一步到位）
        
        Args:
            title: 歌曲标题
            artist: 艺术家
            
        Returns:
            歌词数据，失败返回 None
        """
        # 先搜索歌曲
        song = self.search_song(title, artist)
        if not song:
            return None
        
        # 再获取歌词
        lyrics = self.get_lyrics(song["hash"])
        if lyrics:
            lyrics["song_info"] = song
        
        return lyrics


class KugouFetcher(LyricsFetcher):
    """酷狗歌词获取器（实现 LyricsFetcher 接口）"""
    
    def __init__(self, timeout: int = 10):
        self.api = KugouApi(timeout)
    
    def search(self, title: str, artist: str) -> Optional[LyricResult]:
        """搜索并获取歌词
        
        Args:
            title: 歌曲标题
            artist: 艺术家
            
        Returns:
            LyricResult 或 None
        """
        try:
            # 搜索歌曲
            song = self.api.search_song(title, artist)
            if not song:
                return None
            
            # 获取歌词
            lyrics = self.api.get_lyrics(song['hash'])
            if not lyrics:
                return None
            
            lyrics_data = lyrics['lyrics']
            
            # 检查是否有逐字时间戳
            orig_lines = lyrics_data.get('orig', [])
            has_word_timestamps = False
            if orig_lines:
                # 检查第一行是否有多个 word（逐字）
                first_line = orig_lines[0]
                has_word_timestamps = len(first_line.words) > 1
            
            lyric_format = LyricFormat.WORD if has_word_timestamps else LyricFormat.LINE
            
            # 注意：content 传递的是解析后的字典结构，不是字符串
            # converter.py 的 to_spl() 会检测到这个并调用 _krc_to_spl()
            return LyricResult(
                content=lyrics_data,  # 传递字典结构
                format=lyric_format,
                source_name="kugou",
                translation=None,  # KRC 的翻译已经在 lyrics_data['ts'] 中
                matched_title=song['title'],
                matched_artist=song['artist'],
                score=0.0  # matcher.py 会计算相似度
            )
        
        except Exception as e:
            print(f"酷狗获取歌词失败: {e}")
            return None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.api.session.close()
