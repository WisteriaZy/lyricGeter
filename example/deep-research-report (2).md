# 摘要  
LDDC-Android 使用了**QQ 音乐**、**酷狗音乐**和**网易云音乐**三大平台的私有歌词接口来获取歌词内容，并对加密歌词进行了解密处理。在 `core/api/impl` 目录下的 `QQMusicApi.kt`、`KugouApi.kt` 和 `NetEaseApi.kt` 中实现了对应平台的歌词获取逻辑：分别调用 `music.musichallSong.PlayLyricInfo`（QQ 音乐）、`krcs.kugou.com/lyrics.kugou.com`（酷狗）、以及网易云的 `/eapi/song/lyric/v1` 接口。所有接口均为逆向得来的非官方公开 API，请求返回的歌词内容常以 KRC/QRC/YRC 等格式加密存储，代码通过 `KrcDecryptor`、`QrcDecryptor`、`EapiDecryptor` 等模块进行解密后解析成逐字歌词。  

## 发现清单  

| 歌词来源         | 代码位置/证据                                      | 请求示例 (URL/参数/签名)                                                                                                    | 官方接口?    | 是否逆向? | 可信度 |
|--------------|-------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|----------|-------|----|
| **QQ 音乐**（QQMusic）  | `app/src/main/java/com/example/lddc/core/api/impl/QQMusicApi.kt` 中的 `getLyrics` | POST 请求调用 `GetPlayLyricInfo`（`music.musichallSong.PlayLyricInfo`），参数包含 `songID`、base64 编码的 `songName`、`albumName`、`singerName` 及加密选项等（例：`{"songID":12345,"songName":"...","albumName":"...","singerName":"...","lrc_t":0,"qrc":1,"romalrc":1,"trans":1,...}`） | 否（私有接口） | 是      | 中   |
| **酷狗音乐**（KuGou） | `app/src/main/java/com/example/lddc/core/api/impl/KugouApi.kt` 中的 `getLyrics` | 首先 GET `https://krcs.kugou.com/search`（参数：`hash`、`album_id`、`clienttime`、`mid`等）查找歌词 `id` 和 `accesskey`，然后 GET `http://lyrics.kugou.com/download?accesskey=XXX&id=YYY&fmt=krc&charset=utf8&client=mobi&ver=1` 下载歌词 | 否（私有接口） | 是      | 中   |
| **网易云音乐**（NetEase） | `app/src/main/java/com/example/lddc/core/api/impl/NetEaseApi.kt` 中的 `getLyrics` | POST `/eapi/song/lyric/v1`（网易云私有 EAPI 接口，URL 实际为 `https://music.163.com/eapi/song/lyric/v1`），参数包含 `id`（歌曲ID）及 `lv/tv/rv/yv=-1` 等，加密后发送。返回 JSON 中包含 `lrc`、`tlyric`、`romalrc`、`yrc` 字段。 | 否（私有接口） | 是      | 中   |

**请求示例（模拟）**：以酷狗为例，发送 `GET http://lyrics.kugou.com/download?accesskey=abc123&id=100&type=1&client=mobi&fmt=krc`，服务器返回类似 `{"content":"BASE64加密后的歌词内容","status":0}`；接着解密再解析即可。QQ 音乐示例请求见上表。网易云接口要求对参数进行 EAPI 加密（见代码）后发送，返回同一首歌的不同歌词版本字段。所有请求均为逆向得来，非官方公开文档接口，解析后歌词内容可信度较高，但需注意数据可能随平台反爬策略而变化。  

## 关键代码片段与解释  
- **QQ 音乐歌词获取**：`QQMusicApi.getLyrics` 构造 JSON 参数并调用 `makeRequest("GetPlayLyricInfo", "music.musichallSong.PlayLyricInfo", param)`。返回的 `lyric`、`trans`、`roma` 字段可能为 XML 或加密字符串。若是加密（即不以 `<?xml` 开头），则用 `QrcDecryptor.decryptString` 解密；之后用 `QrcParser().parseSmart` 解析歌词行（原词、译文、罗马音分别处理）。  
- **酷狗音乐歌词获取**：`KugouApi.getLyrics` 先向 `krcs.kugou.com/search` 请求歌词搜索结果。拿到 `id` 和 `accesskey` 后，再向 `lyrics.kugou.com/download` 请求歌词数据。返回数据中的 `"content"` 是 Base64 编码后的 KRC 数据，代码首先 `Base64.decode` 再调用 `KrcDecryptor.decryptString` 解出明文歌词。最后用 `KrcParser().parseWithTags` 解析带标签的逐字歌词。  
- **网易云音乐歌词获取**：`NetEaseApi.getLyrics` 通过私有 EAPI 接口 `/eapi/song/lyric/v1` 获取歌词 JSON。JSON 可能包含原文 (`lrc`/`yrc`)、翻译 (`tlyric`)、罗马音 (`romalrc`) 等字段。代码根据是否包含 `yrc` 字段决定优先解析逐字歌词或普通歌词，对每个字段用 `YrcParser` 或 `LrcParser` 解析出 `LyricsLine` 列表。例如，当 `response["yrc"]` 非空时，`"orig"->"yrc"` 对应值传给 `YrcParser`；否则把 `"lrc"` 传给 `LrcParser`。  

```kotlin
// QQ音乐示例：调用PlayLyricInfo接口获取歌词数据
val response = makeRequest(
    "GetPlayLyricInfo",
    "music.musichallSong.PlayLyricInfo",
    jsonObjectOf(
        "songID" to songInfo.id,
        "songName" to songNameBase64,
        "albumName" to albumNameBase64,
        "singerName" to singerNameBase64,
        // ...其他参数...
        "lrc_t" to 0, "qrc" to 1, "trans" to 1, "roma" to 1
    )
)
// 从返回值提取歌词
val lyric = response["lyric"]?.jsonPrimitive?.content ?: ""
if (!lyric.startsWith("<?xml")) {
    // 非XML歌词需解密QRC
    val decrypted = QrcDecryptor.decryptString(lyric.toByteArray())
    val (tags, lines) = QrcParser().parseSmart(decrypted)
    // lines即逐字歌词行
}
```

```kotlin
// 酷狗示例：下载并解密KRC歌词
val searchRes = makeRequest("https://krcs.kugou.com/search", params, "Lyric")
// ...取出id和accesskey...
val downloadRes = client.get("http://lyrics.kugou.com/download") {
    parameter("id", id); parameter("accesskey", accesskey); parameter("fmt", "krc")
    header("User-Agent", "Android14-...")
}
val contentBase64 = Json.parseToJsonElement(downloadRes.bodyAsText())
    .jsonObject["content"]!!.jsonPrimitive.content
val encryptedBytes = Base64.decode(contentBase64, Base64.DEFAULT)
val plainText = KrcDecryptor.decryptString(encryptedBytes)  // 解密KRC
val (tags, lines, types) = KrcParser().parseWithTags(plainText)  // 解析歌词
```

## 加密/解密流程图  
```mermaid
graph LR
  A[酷狗歌词搜索 API (krcs.kugou.com/search)] --> B[取出歌词 ID & AccessKey]
  B --> C[请求下载歌词 (lyrics.kugou.com/download)]
  C --> D[获取 Base64 加密内容]
  D --> E[KRC 解密 (KrcDecryptor)]
  E --> F[KRC 解析 (KrcParser)] --> G[得到逐字歌词]
```
```mermaid
graph TD
  H[QQ音乐 PlayLyricInfo 接口] --> I[返回 lyric/trans/roma (可能为 XML 或加密文本)]
  I --> J{是否 XML 格式?}
  J -->|是| K[直接 QrcParser 解析]
  J -->|否| L[QRC 解密 (QrcDecryptor)] --> K
  K --> M[得到逐字歌词]
```

## 结论与建议  
LDDC-Android 的歌词获取模块自行实现了多平台歌词接口的调用和解密逻辑，可直接在本地播放器项目中复用。建议按需引入相应代码（如 `QQMusicApi`、`KugouApi`、`NetEaseApi` 及解密器），并注意处理网络异步调用和错误情况。在复用时，可考虑：  
- 如果需要合法渠道，可使用网易云开放平台的官方 API 获取歌词（但该官方接口通常只返回 LRC 文本，且需要开发者申请 Key）。  
- 对于版权内容（特别是歌词文本），应遵守相关法规与平台服务条款，不建议大规模缓存/分享歌词文本。  
- 可使用本地**歌词缓存机制**（项目中有 `LyricsCacheDao`）避免重复网络请求，提高性能和抗封禁能力。  
- 对于无法稳定获取或加密过于复杂的平台，考虑使用替代方案，如 Musixmatch 等第三方歌词服务（需评估额外依赖）或用户提供歌词文件。  

## 风险与合规性评估  
- **服务条款风险**：上述歌词接口均非公开授权接口，调用可能违反 QQ、酷狗、网易云等平台的服务协议，存在被封禁 IP 或账号的风险。  
- **版权风险**：歌词通常受版权保护，未经授权的获取、存储和分发可能侵犯版权。在应用中使用歌词时应审慎，避免公开转载或商业用途。  
- **反爬虫策略**：频繁调用私有接口或使用固定签名方式可能触发平台反爬虫策略。应限制请求频率，使用随机 UA 或缓存机制降低被封概率。  
- **隐私合规**：代码示例中无涉及用户敏感数据，但注意网络请求中不要泄露用户隐私信息。  

**参考资料**：上述分析主要基于项目源码及开放平台文档。各代码链接已给出，可点击查看详细实现。