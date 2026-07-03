# LDDC-Android 技术分析与 Python 移植方案

**项目来源**：https://github.com/chenmozhijin/LDDC（推测）  
**分析时间**：2026-07-03  
**目标**：将 Kotlin 实现的逐字歌词解析移植到 Python

---

## 项目概述

LDDC-Android 是一个已经完整实现了三大平台（网易云、QQ 音乐、酷狗）逐字歌词获取和解密的 Kotlin/Android 项目。它通过逆向平台 API 获取加密歌词，并使用自实现的解密器还原为明文。

### 核心架构

```
core/
├── api/impl/          # 平台 API 实现
│   ├── NetEaseApi.kt  # 网易云音乐
│   ├── QQMusicApi.kt  # QQ 音乐
│   └── KugouApi.kt    # 酷狗音乐
├── decryptor/         # 解密器
│   ├── EapiDecryptor.kt   # 网易云 EAPI 加密
│   ├── QrcDecryptor.kt    # QQ 音乐 QRC 解密
│   └── KrcDecryptor.kt    # 酷狗 KRC 解密
└── parser/            # 歌词解析器
    ├── YrcParser.kt   # 网易云逐字格式
    ├── QrcParser.kt   # QQ 音乐逐字格式
    ├── KrcParser.kt   # 酷狗逐字格式
    └── LrcParser.kt   # 通用 LRC 格式
```

---

## 格式详解

### 1. 网易云 YRC 格式

**原始数据结构**（JSON 字符串）：
```
[0,500]你(0,300,0)好(300,200,0)世(500,250,0)界(750,150,0)
```

**格式说明**：
- `[行开始时间ms, 行持续时间ms]` - 行级时间戳
- `文字(相对开始ms, 持续时间ms, 保留字段)` - 逐字时间戳

**Kotlin 解析代码**：
```kotlin
private val linePattern = Regex("""^\[(\d+),(\d+)\](.*)$""")
private val wordPattern = Regex("""\((\d+),(\d+),\d+\)([^\(]*)""")

// 行级解析
linePattern.matchEntire(line)?.let { match ->
    val lineStart = match.groupValues[1].toInt()
    val lineDuration = match.groupValues[2].toInt()
    val lineEnd = lineStart + lineDuration
    val lineContent = match.groupValues[3]
    
    // 逐字解析
    val words = wordPattern.findAll(lineContent).map { wordMatch ->
        val wordStart = wordMatch.groupValues[1].toInt()
        val wordDuration = wordMatch.groupValues[2].toInt()
        LyricsWord(
            start = wordStart,              // 相对行开始的偏移
            end = wordStart + wordDuration,
            text = wordMatch.groupValues[3]
        )
    }
}
```

**Python 移植重点**：
- 正则表达式可直接翻译
- 注意：`wordStart` 是**相对时间**，需加上 `lineStart` 得到绝对时间

### 2. QQ 音乐 QRC 格式

**加密流程**：
```
明文 QRC → 3DES 加密（密钥："!@#)(*$%123ZXC!@!@#)(NHL"）→ 十六进制字符串
```

**明文格式**（类似 LRC 但带逐字标记）：
```
[0,500]你好(0,300)世界(300,200)
```

**关键区别**：
- QRC 的逐字时间戳格式：`文字(开始ms, 持续ms)`
- YRC 的格式：`文字(开始ms, 持续ms, 保留字段)`
- QRC 可能被包裹在 XML：`<Lyric_1 LyricType="1" LyricContent="..."/>`

**QRC 解密器实现要点**：
```kotlin
object QrcDecryptor {
    private val QRC_KEY = "!@#)(*$%123ZXC!@!@#)(NHL".toByteArray()
    
    fun decrypt(encryptedQrc: String): String {
        // 1. 十六进制字符串 → 字节数组
        val encryptedData = hexStringToByteArray(encryptedQrc)
        
        // 2. 3DES 解密（ECB 模式）
        val key = tripledesKeySetup(QRC_KEY, DECRYPT)
        val decryptedData = bytearray()
        for (i in encryptedData.indices step 8) {
            val block = encryptedData.copyOfRange(i, min(i + 8, encryptedData.size))
            decryptedData += tripledesCrypt(block, key)
        }
        
        // 3. zlib 解压
        val inflater = Inflater()
        inflater.setInput(decryptedData)
        val result = inflater.inflate()
        
        return String(result, Charsets.UTF_8)
    }
}
```

**Python 移植**：
```python
from Crypto.Cipher import DES3
import zlib

QRC_KEY = b"!@#)(*$%123ZXC!@!@#)(NHL"

def decrypt_qrc(encrypted_hex: str) -> str:
    # 1. 十六进制解码
    encrypted_data = bytes.fromhex(encrypted_hex)
    
    # 2. 3DES-ECB 解密
    cipher = DES3.new(QRC_KEY, DES3.MODE_ECB)
    decrypted_data = cipher.decrypt(encrypted_data)
    
    # 3. zlib 解压
    decompressed = zlib.decompress(decrypted_data)
    
    return decompressed.decode('utf-8')
```

### 3. 酷狗 KRC 格式

**加密流程**：
```
明文 → zlib 压缩 → XOR 加密（密钥："@Gaw^2tGQ61-Íni"）→ Base64 编码
```

**明文格式**：
```
[0,500]<0,300>你<300,200>好<500,250>世<750,150>界
```

**关键特征**：
- 使用 `<>` 包裹逐字时间戳
- 前 4 字节是 magic header（需跳过）
- 支持 `language` 标签（Base64 编码的 JSON，包含翻译和罗马音）

**KRC 解密器**：
```kotlin
object KrcDecryptor {
    private val KRC_KEY = byteArrayOf(
        '@'.code.toByte(), 'G'.code.toByte(), 'a'.code.toByte(), 'w'.code.toByte(),
        '^'.code.toByte(), '2'.code.toByte(), 't'.code.toByte(), 'G'.code.toByte(),
        'Q'.code.toByte(), '6'.code.toByte(), '1'.code.toByte(), '-'.code.toByte(),
        0xce.toByte(), 0xd2.toByte(), 'n'.code.toByte(), 'i'.code.toByte()
    )
    
    fun decrypt(data: ByteArray): String {
        // 1. 跳过前 4 字节
        val encryptedData = data.copyOfRange(4, data.size)
        
        // 2. XOR 解密
        val decryptedData = ByteArray(encryptedData.size)
        for (i in encryptedData.indices) {
            decryptedData[i] = (encryptedData[i].toInt() xor KRC_KEY[i % KRC_KEY.size].toInt()).toByte()
        }
        
        // 3. zlib 解压
        val inflater = Inflater()
        inflater.setInput(decryptedData)
        return String(inflater.inflate(), Charsets.UTF_8)
    }
}
```

**Python 移植**：
```python
import zlib
import base64

KRC_KEY = b'@Gaw^2tGQ61-\xce\xd2ni'

def decrypt_krc(base64_data: str) -> str:
    # 1. Base64 解码
    encrypted = base64.b64decode(base64_data)
    
    # 2. 跳过前 4 字节
    encrypted = encrypted[4:]
    
    # 3. XOR 解密
    decrypted = bytearray()
    for i, byte in enumerate(encrypted):
        decrypted.append(byte ^ KRC_KEY[i % len(KRC_KEY)])
    
    # 4. zlib 解压
    decompressed = zlib.decompress(bytes(decrypted))
    
    return decompressed.decode('utf-8')
```

---

## API 接口逆向

### 网易云音乐 API

**认证流程**：
1. 游客登录获取 `userId` 和 `cookies`
2. 使用 EAPI 加密所有请求

**关键接口**：
```
POST https://interface.music.163.com/eapi/song/lyric/v1
参数（加密前）:
{
  "id": "歌曲ID",
  "lv": -1,    # LRC 歌词
  "tv": -1,    # 翻译歌词
  "rv": -1,    # 罗马音
  "yv": -1     # YRC 逐字歌词
}
```

**EAPI 加密算法**：
```kotlin
fun encryptParams(path: String, params: Map<String, Any?>): String {
    val paramsJson = buildCompactJson(params)  // 无空格 JSON
    val signSrc = "nobody${path}use${paramsJson}md5forencrypt"
    val sign = md5(signSrc)
    
    val aesSrc = "$path-36cd479b6b5-$paramsJson-36cd479b6b5-$sign"
    val encrypted = aesEncrypt(aesSrc, "e82ckenh8dichen8")
    
    return "params=${bytesToHex(encrypted).uppercase()}"
}
```

**Python 移植**：
```python
import hashlib
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad

EAPI_KEY = b"e82ckenh8dichen8"

def encrypt_eapi_params(path: str, params: dict) -> str:
    # 1. 紧凑 JSON（无空格）
    params_json = json.dumps(params, separators=(',', ':'), ensure_ascii=False)
    
    # 2. 计算签名
    sign_src = f"nobody{path}use{params_json}md5forencrypt"
    sign = hashlib.md5(sign_src.encode()).hexdigest()
    
    # 3. 构造待加密字符串
    aes_src = f"{path}-36cd479b6b5-{params_json}-36cd479b6b5-{sign}"
    
    # 4. AES-ECB 加密
    cipher = AES.new(EAPI_KEY, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(aes_src.encode(), AES.block_size))
    
    # 5. 十六进制编码
    return f"params={encrypted.hex().upper()}"
```

**搜索接口**：
```
POST https://interface.music.163.com/eapi/cloudsearch/pc
参数:
{
  "s": "搜索关键词",
  "type": 1,      # 1=单曲
  "limit": 10,
  "offset": 0
}
```

### QQ 音乐 API

**接口地址**：
```
POST https://u.y.qq.com/cgi-bin/musicu.fcg
```

**请求格式**（多接口聚合）：
```json
{
  "comm": {
    "ct": 6,
    "cv": 0,
    "uin": "0"
  },
  "req_1": {
    "module": "music.musichallSong.PlayLyricInfo",
    "method": "GetPlayLyricInfo",
    "param": {
      "songID": 12345,
      "lrc": 1,
      "qrc": 1,      // 逐字歌词
      "trans": 1,    // 翻译
      "roma": 1      // 罗马音
    }
  }
}
```

**Python 移植**：
```python
import httpx

async def get_qq_lyrics(song_id: int) -> dict:
    url = "https://u.y.qq.com/cgi-bin/musicu.fcg"
    data = {
        "comm": {"ct": 6, "cv": 0, "uin": "0"},
        "req_1": {
            "module": "music.musichallSong.PlayLyricInfo",
            "method": "GetPlayLyricInfo",
            "param": {
                "songID": song_id,
                "lrc": 1,
                "qrc": 1,
                "trans": 1,
                "roma": 1
            }
        }
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        result = response.json()
        
        lyric_data = result["req_1"]["data"]
        
        # QRC 解密
        qrc_encrypted = lyric_data.get("qrc", "")
        if qrc_encrypted:
            qrc_plain = decrypt_qrc(qrc_encrypted)
            return {"content": qrc_plain, "format": "qrc"}
        
        # 回退到 LRC
        return {"content": lyric_data.get("lyric", ""), "format": "lrc"}
```

### 酷狗音乐 API

**两步流程**：

1. **搜索歌词 ID**：
```
GET https://krcs.kugou.com/search
参数:
- hash: 歌曲 hash
- album_id: 专辑 ID
- timelength: 歌曲时长（毫秒）
- keyword: 歌曲标题
```

2. **下载歌词**：
```
GET http://lyrics.kugou.com/download
参数:
- id: 第一步获取的歌词 ID
- accesskey: 第一步获取的访问密钥
- fmt: krc
- charset: utf8
```

**Python 移植**：
```python
async def get_kugou_lyrics(song_hash: str, duration_ms: int, title: str) -> dict:
    # 步骤 1: 搜索
    search_url = "https://krcs.kugou.com/search"
    params = {
        "hash": song_hash,
        "timelength": duration_ms,
        "keyword": title,
        "ver": 1,
        "client": "mobi",
        "man": "yes"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(search_url, params=params)
        data = response.json()
        
        if data["status"] != 200:
            return None
        
        candidates = data["candidates"]
        if not candidates:
            return None
        
        lyric_id = candidates[0]["id"]
        access_key = candidates[0]["accesskey"]
        
        # 步骤 2: 下载
        download_url = "http://lyrics.kugou.com/download"
        params = {
            "id": lyric_id,
            "accesskey": access_key,
            "fmt": "krc",
            "charset": "utf8",
            "client": "mobi"
        }
        
        response = await client.get(download_url, params=params)
        data = response.json()
        
        # Base64 解码 + KRC 解密
        krc_encrypted = data["content"]
        krc_plain = decrypt_krc(krc_encrypted)
        
        return {"content": krc_plain, "format": "krc"}
```

---

## Python 移植方案

### 项目结构

```
lyricGeter/
├── fetcher/
│   ├── base.py           # 已有
│   ├── synced.py         # 已有
│   ├── netease.py        # 新增：网易云 API
│   ├── qqmusic.py        # 新增：QQ 音乐 API
│   └── kugou.py          # 新增：酷狗 API
├── decryptor/
│   ├── __init__.py
│   ├── eapi.py           # 网易云 EAPI 加密
│   ├── qrc.py            # QQ 音乐 QRC 解密
│   └── krc.py            # 酷狗 KRC 解密
├── parser/
│   ├── __init__.py
│   ├── yrc.py            # 网易云 YRC 解析
│   ├── qrc.py            # QQ 音乐 QRC 解析
│   └── krc.py            # 酷狗 KRC 解析
└── converter.py          # 已有，需扩展支持 YRC/QRC/KRC → SPL
```

### 依赖库

```bash
pip install pycryptodome  # AES/DES3 加密
pip install httpx         # 异步 HTTP 客户端（已安装）
```

### 实现优先级

#### P0（本周完成）

1. **网易云 YRC 解析器**（最简单）
   - `parser/yrc.py`：正则解析 YRC 文本
   - `converter.py`：YRC → SPL 转换

2. **酷狗 KRC 解密+解析**（中等难度）
   - `decryptor/krc.py`：XOR + zlib 解密
   - `parser/krc.py`：解析 `<>` 标记的逐字格式

3. **网易云 API 实现**
   - `decryptor/eapi.py`：EAPI 加密
   - `fetcher/netease.py`：搜索 + 歌词获取

#### P1（下周）

4. **QQ 音乐 QRC 解密+解析**（最复杂）
   - `decryptor/qrc.py`：3DES + zlib 解密
   - `parser/qrc.py`：解析 QRC 格式
   - `fetcher/qqmusic.py`：API 调用

5. **酷狗 API 实现**
   - `fetcher/kugou.py`：两步获取流程

#### P2（优化）

6. **集成测试**
   - 对比三个平台的质量
   - 添加错误处理和重试

7. **缓存机制**
   - 避免重复请求
   - SQLite 存储歌词

---

## 风险评估

### 技术风险

| 平台 | 风险等级 | 主要挑战 | 缓解方案 |
|-----|---------|---------|---------|
| 网易云 | 🟢 低 | EAPI 加密逻辑复杂 | 直接翻译 Kotlin 代码 |
| 酷狗 | 🟡 中 | 两步API + XOR密钥 | 已有完整实现参考 |
| QQ音乐 | 🔴 高 | 3DES解密 + S-Box实现 | 使用 PyCryptodome 库 |

### 法律风险

- ⚠️ **非官方 API**：所有接口均为逆向所得，可能违反平台服务条款
- ⚠️ **版权问题**：歌词受版权保护，仅供个人学习使用
- ✅ **降低风险**：
  - 添加请求间隔（避免限流）
  - 用户自行承担使用责任
  - 不提供公开服务

---

## 下一步行动

### 立即开始（今天）

1. **创建 `decryptor/` 和 `parser/` 目录**
2. **实现 `decryptor/krc.py`**（最简单，测试移植流程）
3. **实现 `parser/yrc.py`**（纯正则，无解密）
4. **测试 YRC 解析**（从 example 或手动构造样例数据）

### 本周目标

- ✅ 完成网易云 YRC 支持（解析器 + API）
- ✅ 完成酷狗 KRC 支持（解密器 + 解析器）
- ✅ 用 `input/` 目录的中文/日文歌曲测试

### 评估标准

- 解析准确率 > 95%
- SPL 时间戳严格递增
- 翻译行正确对齐
- 性能：单首歌曲 < 3 秒（包括网络请求）

---

## 关键代码对照表

| 功能 | Kotlin 代码位置 | Python 目标位置 | 难度 |
|-----|---------------|---------------|-----|
| YRC 解析 | `YrcParser.kt:10-50` | `parser/yrc.py` | ⭐ |
| KRC 解密 | `KrcDecryptor.kt:15-55` | `decryptor/krc.py` | ⭐⭐ |
| KRC 解析 | `KrcParser.kt:20-80` | `parser/krc.py` | ⭐⭐ |
| EAPI 加密 | `EapiDecryptor.kt:15-60` | `decryptor/eapi.py` | ⭐⭐⭐ |
| 网易云 API | `NetEaseApi.kt:40-150` | `fetcher/netease.py` | ⭐⭐⭐ |
| QRC 解密 | `QrcDecryptor.kt:50-250` | `decryptor/qrc.py` | ⭐⭐⭐⭐ |
| QRC 解析 | `QrcParser.kt:30-100` | `parser/qrc.py` | ⭐⭐ |
| QQ 音乐 API | `QQMusicApi.kt` | `fetcher/qqmusic.py` | ⭐⭐⭐ |
| 酷狗 API | `KugouApi.kt:60-150` | `fetcher/kugou.py` | ⭐⭐⭐ |

---

## 总结

LDDC-Android 项目为我们提供了**完整的参考实现**，大大降低了逆向成本。主要工作是：

1. **代码翻译**：Kotlin → Python（语法差异小）
2. **库替换**：Android 库 → Python 标准库/PyCryptodome
3. **测试验证**：确保解密和解析正确性

**预期收益**：
- 获得比 syncedlyrics 更高质量的逐字歌词
- 恢复相似度过滤（获取搜索结果元数据）
- 支持翻译和罗马音
- 为用户提供平台选择

**时间估算**：
- 网易云 YRC：2 天
- 酷狗 KRC：2 天
- QQ 音乐 QRC：3 天
- 总计：1 周完成核心功能
