"""QQ 音乐 API 获取器

基于 LDDC-Android QQMusicApi.kt 实现
"""

import httpx
import logging
from typing import Optional, Dict, Any
from fetcher.base import LyricsFetcher, LyricResult
from decryptor.qrc import decrypt_qrc
from parser.qrc import QrcParser

logger = logging.getLogger(__name__)


class QQMusicApi:
    """QQ 音乐 API 客户端"""
    
    BASE_URL = "https://u.y.qq.com/cgi-bin/musicu.fcg"
    
    def __init__(self):
        self.session: Optional[Dict[str, str]] = None
        self.comm = {
            "ct": "11",
            "cv": "1003006",
            "v": "1003006",
            "os_ver": "15",
            "phonetype": "24122RKC7C",
            "rom": "Redmi/miro/miro:15/AE3A.240806.005/OS2.0.105.0.VOMCNXM:user/release-keys",
            "tmeAppID": "qqmusiclight",
            "nettype": "NETWORK_WIFI",
            "udid": "0"
        }
    
    async def _ensure_initialized(self):
        """确保 Session 已初始化"""
        if self.session is not None:
            return
        
        logger.debug("初始化 QQ 音乐 Session...")
        
        request_body = {
            "comm": self.comm,
            "request": {
                "method": "GetSession",
                "module": "music.getSession.session",
                "param": {
                    "caller": 0,
                    "uid": "0",
                    "vkey": 0
                }
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.BASE_URL,
                    json=request_body,
                    headers={
                        "Cookie": "tmeLoginType=-1;",
                        "User-Agent": "okhttp/3.14.9"
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            code = data.get("code", -1)
            request_code = data.get("request", {}).get("code", -1)
            
            if code != 0 or request_code != 0:
                raise Exception(f"Session 初始化失败: code={code}, requestCode={request_code}")
            
            session_data = data["request"]["data"]["session"]
            self.session = {
                "uid": session_data.get("uid", "0"),
                "sid": session_data.get("sid", ""),
                "userip": session_data.get("userip", "")
            }
            
            # 更新 comm
            self.comm["uid"] = self.session["uid"]
            self.comm["sid"] = self.session["sid"]
            self.comm["userip"] = self.session["userip"]
            
            logger.info(f"Session 初始化成功: uid={self.session['uid']}")
        
        except Exception as e:
            logger.error(f"Session 初始化失败: {e}")
            raise
    
    async def _make_request(self, method: str, module: str, param: dict) -> dict:
        """发起 API 请求"""
        await self._ensure_initialized()
        
        request_body = {
            "comm": self.comm,
            "request": {
                "method": method,
                "module": module,
                "param": param
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.BASE_URL,
                    json=request_body,
                    headers={
                        "Cookie": "tmeLoginType=-1;",
                        "User-Agent": "okhttp/3.14.9"
                    }
                )
                response.raise_for_status()
                data = response.json()
            
            code = data.get("code", -1)
            request_code = data.get("request", {}).get("code", -1)
            
            if code != 0 or request_code != 0:
                raise Exception(f"API 请求失败: code={code}, requestCode={request_code}")
            
            return data["request"]["data"]
        
        except Exception as e:
            logger.error(f"API 请求失败 ({method}): {e}")
            raise
    
    @staticmethod
    def _generate_search_id() -> str:
        """生成搜索 ID（模仿 LDDC 实现）"""
        import random
        import time
        
        random_gen = random.Random()
        part1 = random_gen.randint(0, 19) * 18014398509481984
        part2 = random_gen.randint(0, 4194303) * 4294967296
        part3 = int((time.time() * 1000) % 86400000)
        return str(part1 + part2 + part3)
    
    async def search_song(self, title: str, artist: str = "") -> Optional[Dict[str, Any]]:
        """搜索歌曲
        
        Args:
            title: 歌曲标题
            artist: 艺术家名称（可选）
            
        Returns:
            歌曲信息字典，包含 id, mid, title, artist, duration 等
        """
        keyword = f"{title} {artist}".strip()
        logger.debug(f"QQ 音乐搜索: {keyword}")
        
        try:
            param = {
                "search_id": self._generate_search_id(),
                "remoteplace": "search.android.keyboard",
                "query": keyword,
                "search_type": 0,
                "num_per_page": 20,
                "page_num": 1
            }
            
            data = await self._make_request("DoSearchForQQMusicDesktop", "music.search.SearchCgiService", param)
            
            songs = data.get("body", {}).get("song", {}).get("list", [])
            
            if not songs:
                logger.debug("未找到搜索结果")
                return None
            
            # 取第一个结果
            song = songs[0]
            
            # 提取艺术家名称
            singers = song.get("singer", [])
            artist_name = "/".join(s.get("name", "") for s in singers)
            
            # 提取专辑信息
            album = song.get("album", {})
            album_mid = album.get("mid", "")
            
            result = {
                "id": str(song.get("id", "")),
                "mid": song.get("mid", ""),
                "title": song.get("title", ""),
                "artist": artist_name,
                "album": album.get("name", ""),
                "duration": song.get("interval", 0),  # 单位：秒
                "album_mid": album_mid
            }
            
            logger.debug(f"找到歌曲: {result['title']} - {result['artist']}")
            return result
        
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return None
    
    async def get_lyrics(self, song_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """获取歌词
        
        Args:
            song_info: 歌曲信息字典，需包含 id, mid, title, artist, album, duration
            
        Returns:
            包含 orig（原文）、trans（翻译）、roma（罗马音）的字典
        """
        logger.debug(f"获取歌词: mid={song_info.get('mid')}")
        
        try:
            import base64
            
            # Base64 编码歌曲信息（LDDC 要求）
            title_b64 = base64.b64encode(song_info["title"].encode("utf-8")).decode("ascii")
            artist_b64 = base64.b64encode(song_info["artist"].encode("utf-8")).decode("ascii")
            album_b64 = base64.b64encode(song_info.get("album", "").encode("utf-8")).decode("ascii") if song_info.get("album") else None
            
            param = {
                "songName": title_b64,
                "singerName": artist_b64,
                "albumName": album_b64,
                "songID": int(song_info.get("id", 0)),
                "interval": song_info.get("duration", 0),
                "crypt": 1,
                "ct": 19,
                "cv": 2111,
                "lrc_t": 0,
                "qrc": 1,
                "qrc_t": 0,
                "roma": 1,
                "roma_t": 0,
                "trans": 1,
                "trans_t": 0,
                "type": 0
            }
            
            data = await self._make_request("GetPlayLyricInfo", "music.musichallSong.PlayLyricInfo", param)
            
            lyric_data = data.get("lyric", "")
            trans_data = data.get("trans", "")
            roma_data = data.get("roma", "")
            
            # 检查状态字段（注意是 lrc_t/qrc_t 而不是 lyric_t）
            lrc_t = data.get("lrc_t", "0")
            qrc_t = data.get("qrc_t", "0")
            trans_t = data.get("trans_t", "0")
            roma_t = data.get("roma_t", "0")
            
            has_lyric = qrc_t != "0" or lrc_t != "0"
            
            result = {
                "orig": lyric_data if has_lyric else "",
                "trans": trans_data if trans_t != "0" else "",
                "roma": roma_data if roma_t != "0" else ""
            }
            
            logger.debug(f"获取歌词成功: orig={len(result['orig'])}, trans={len(result['trans'])}, roma={len(result['roma'])}")
            logger.debug(f"状态标志: lrc_t={lrc_t}, qrc_t={qrc_t}, trans_t={trans_t}, roma_t={roma_t}")
            return result
        
        except Exception as e:
            logger.error(f"获取歌词失败: {e}")
            return None


class QQMusicFetcher(LyricsFetcher):
    """QQ 音乐歌词获取器（LyricsFetcher 适配器）"""
    
    def __init__(self):
        self.api = QQMusicApi()
    
    def search(self, title: str, artist: str) -> Optional[LyricResult]:
        """搜索并获取歌词（同步接口）
        
        Args:
            title: 歌曲标题
            artist: 艺术家名称
            
        Returns:
            LyricResult 对象
        """
        import asyncio
        
        # 在同步上下文中运行异步代码
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已在运行，创建新循环
                import nest_asyncio
                nest_asyncio.apply()
                return loop.run_until_complete(self._fetch_async(title, artist))
            else:
                return loop.run_until_complete(self._fetch_async(title, artist))
        except RuntimeError:
            # 没有事件循环，创建新的
            return asyncio.run(self._fetch_async(title, artist))
    
    async def _fetch_async(self, title: str, artist: str) -> Optional[LyricResult]:
        """获取歌词（异步实现）
        
        Args:
            title: 歌曲标题
            artist: 艺术家名称
            
        Returns:
            LyricResult 对象
        """
        try:
            # 1. 搜索歌曲
            song = await self.api.search_song(title, artist)
            if not song:
                return None
            
            # 2. 获取歌词
            lyrics = await self.api.get_lyrics(song)
            if not lyrics or not lyrics["orig"]:
                return None
            
            # 3. 解密原文
            orig_encrypted = lyrics["orig"]
            try:
                # 检查是否需要解密
                if orig_encrypted.strip().startswith('<?xml') or '<Lyric_1' in orig_encrypted:
                    orig_text = orig_encrypted
                else:
                    orig_text = decrypt_qrc(orig_encrypted)
                
                lyric_type, lines = QrcParser.parse_smart(orig_text)
            except Exception as e:
                logger.error(f"解析原文失败: {e}")
                return None
            
            # 4. 解密翻译（如果有）
            trans_lines = []
            if lyrics["trans"]:
                try:
                    trans_encrypted = lyrics["trans"]
                    if trans_encrypted.strip().startswith('<?xml') or '<Lyric_1' in trans_encrypted:
                        trans_text = trans_encrypted
                    else:
                        trans_text = decrypt_qrc(trans_encrypted)
                    
                    _, trans_lines = QrcParser.parse_smart(trans_text)
                except Exception as e:
                    logger.warning(f"解析翻译失败: {e}")
            
            # 5. 解密罗马音（如果有）
            roma_lines = []
            if lyrics["roma"]:
                try:
                    roma_encrypted = lyrics["roma"]
                    if roma_encrypted.strip().startswith('<?xml') or '<Lyric_1' in roma_encrypted:
                        roma_text = roma_encrypted
                    else:
                        roma_text = decrypt_qrc(roma_encrypted)
                    
                    _, roma_lines = QrcParser.parse_smart(roma_text)
                except Exception as e:
                    logger.warning(f"解析罗马音失败: {e}")
            
            return LyricResult(
                source="qqmusic",
                format=lyric_type.lower(),
                lines=lines,
                translation=trans_lines if trans_lines else None,
                romanization=roma_lines if roma_lines else None,
                matched_title=song["title"],
                matched_artist=song["artist"]
            )
        
        except Exception as e:
            logger.error(f"QQ 音乐获取歌词失败: {e}")
            return None


async def fetch_qqmusic_lyrics(title: str, artist: str = "", album: str = "") -> Optional[LyricResult]:
    """便捷函数：从 QQ 音乐获取歌词"""
    fetcher = QQMusicFetcher()
    return await fetcher.fetch(title, artist, album)
