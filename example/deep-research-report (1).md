# 执行摘要

SPlayer-Next 支持从网易云音乐、QQ 音乐、酷狗音乐等平台获取歌词，涵盖 LRC、QRC、YRC、KRC、TTML 等格式。项目在 **electron/main/apis/common/lyric/** 目录下分别实现了三大平台的歌词获取模块（`netease.ts`、`qqmusic.ts`、`kugou.ts`），以及 TTML 同步歌词模块（`ttml.ts`）。这些模块调用各平台的歌词接口（如网易云的 `lyric_new`、QQ 音乐的 `lyric`、酷狗的 `lyric` 接口）来抓取原生歌词文本。主流程为：根据歌曲 ID 或元数据搜索获取平台歌曲编号，再单次请求歌词（如 `await callNetease("lyric_new", {id})`）。对于多行同步歌词（TTML），项目提供了接口对接 **AMLL 歌词数据库**，需用户配置 `lyric.amllDbServer` 模板以调用其 `ncm-lyrics`/`qq-lyrics` 服务。目前未见其他中转代理服务器。**合规风险**方面，由于使用了非公开或未授权的歌词接口（如网易云和酷狗的私有 API），以及分发版权歌词，存在潜在风险。建议优先使用官方开放的歌词 API（若有），合理缓存歌词和处理错误，并对 TTML 服务进行合规评估。

# 歌词模块与依赖

- **主要模块/函数（electron 进程）**：项目在 `electron/main/apis/common/lyric/` 下定义了各平台歌词匹配模块：
  - `netease.ts`：网易云歌词支持  
    - `getByPlatformId(id)`: 通过网易云歌 ID 调用 `callNetease("lyric_new", {id})` 获取 YRC/LRC 正文及翻译/罗马音。  
    - `getByQuery(track)`: 根据歌曲元数据搜索（`callNetease("search", {keywords})`），选择最匹配结果后调用 `getByPlatformId`。
  - `qqmusic.ts`：QQ 音乐歌词支持  
    - `getByPlatformId(id, mid?)`: 通过 QQ 数字歌曲 ID 调用 `callQQMusic("lyric", {id})` 获取 QRC/LRC 正文及翻译/罗马音。  
    - `getByQuery(track)`: 用曲目元数据搜索（`callQQMusic("search", {keywords})`），选最佳结果后再调用 `getByPlatformId`。
  - `kugou.ts`：酷狗歌词支持  
    - `fetchLyric({hash,name,durationMs})`: 调用 `callKugou("lyric", {...})` 获取 KRC/LRC 正文及翻译/罗马音。  
    - `getByPlatformId(hash)`: 直接使用酷狗歌词哈希值调用 `fetchLyric`。  
    - `getByQuery(track)`: 元数据搜索（`callKugou("search", {keywords})`），选出最佳歌曲后调用 `fetchLyric`。
  - `ttml.ts`：AMLL TTML 同步歌词支持  
    - `prefetchTTML(platform, ids) / fetchTTML(platform, ids)`: 在后台并行抓取 TTML 格式歌词，尝试使用配置的 AMLL 服务器地址 (`lyric.amllDbServer`) 逐个查询。成功返回文本后在前端可调用 Overlay 接口显示（由 `applemusic-like-lyrics` 组件渲染）。
- **第三方依赖**：  
  - `@applemusic-like-lyrics/core`：用于渲染歌词效果（Desktop/Overlay/翻译等）。  
  - *内部调用库*：项目中通过 `callNetease`、`callQQMusic`、`callKugou` 等函数访问各平台 API。代码库并未将网易云 API（如 NeteaseCloudMusicApiEnhanced）列入 `package.json` 依赖，而是在 `electron/main/apis/netease` 等模块里直接实现，或调用已集成的 SDK 函数。  
  - 无其他显式歌词服务依赖（如 Musixmatch、Genius）被使用。

| 模块 / 配置项        | 功能描述                                     | 来源路径 & 代码示例                               |
|---------------------|--------------------------------------------|----------------------------------------------|
| `netease.ts`        | 网易云歌词获取（YRC/LRC 格式）             |  |
| `qqmusic.ts`        | QQ 音乐歌词获取（QRC/LRC 格式）           |          |
| `kugou.ts`          | 酷狗歌词获取（KRC/LRC 格式）             |    |
| `ttml.ts`           | TTML 同步歌词抓取（AMLL DB，需要配置）     |   |
| **配置项**          | **用途**                                    | **配置位置**                                 |
| `lyric.enableOnlineTTMLLyric` | 是否启用在线 TTML 歌词接口             | 用户可在设置界面开启/关闭（默认关闭） |
| `lyric.amllDbServer` | AMLL 歌词数据库服务器地址模板（含 `%p` `%s`） | 示例 `https://api.amll.net/%p/%s` |
| **其他依赖**         | -                                          | -                                           |
| `@applemusic-like-lyrics/core` | 歌词渲染组件库                      | `package.json` 列出（v0.5.1）  |

# 各歌词格式来源与调用流程

项目支持多种歌词格式，其获取来源与处理流程如下：

- **YRC/LRC（网易云音乐）**：通过网易云音乐私有 API [`lyric_new`](#调用流程) 获取。调用示例：  
  ```js
  const { status, body } = await callNetease("lyric_new", { id }); // id 为网易云歌曲 ID
  ```  
  成功返回后，从 `body.yrc.lyric` 或 `body.lrc.lyric` 中选择主要歌词（优先 YRC，再 LRC）；翻译则来自 `body.ytlrc` 或 `body.tlyric`；罗马音来自 `body.yromalrc` 或 `body.romalrc`。无需额外解密，直接返回的是加密格式文本（YRC/QRC）或纯文本（LRC）。
- **QRC/LRC（QQ 音乐）**：通过 QQ 音乐公开/私有 API 获取。调用示例：  
  ```js
  const body = await callQQMusic("lyric", { id: qqMusicSongId }); // QQ 数字歌曲ID
  ```  
  返回对象 `body` 包含 `qrc`、`lrc`（歌词正文）以及可能的 `trans`（翻译）和 `roma`（罗马字）字段。代码选择 `body.qrc`（优先）或 `body.lrc` 作为主歌词，格式无需额外解密。
- **KRC/LRC（酷狗音乐）**：通过酷狗音乐 API 获取。流程为先用关键词搜索歌曲，再用歌手 ID（hash）请求歌词。调用示例：  
  ```js
  const body = await callKugou("lyric", {
    hash: songHash,
    name: songName,
    duration: Math.round(durationMs/1000)
  });
  ```  
  返回 `body.krc`（加密 KRC）和 `body.lrc`（纯文本 LRC），优先使用 KRC 内容。KRC 不需要客户端解密（由后端返回已解密文本）。翻译和罗马音字段同样包含在 `body.trans` / `body.roma`。
- **LRC（其他）**：一般为上述接口的二选一或备用格式。若主歌词格式为空，代码会尝试使用 LRC 文本。
- **TTML（同步歌词）**：从 **AMLL 歌词数据库** 获取，需项目配置远程接口地址。代码流程：根据平台（netease/qqmusic）和候选 ID 列表循环请求：  
  ```js
  // 平台参数 "netease" 或 "qqmusic"，ids 为 [mid, id] 或 [id]
  const result = await fetchTTML(platform, ids);
  ```  
  其中，`fetchTTML` 使用配置的 `lyric.amllDbServer` 模板，例如 `https://api.amll.net/%p/%s`，将 `%p` 替换为 `"ncm-lyrics"` 或 `"qq-lyrics"`，`%s` 替换为歌词 ID（或歌曲 MID）。成功时返回 TTML 格式歌词文本（否则缓存为 miss，以避免重复请求）。

各调用的**URL 示例**（实际实现由对应 `callXxx` 模块封装，以下仅示意）：  
- 网易云云音乐（未经授权，仅示意）: `POST https://music.163.com/api/song/lyric_new`，参数 `{id: /* Netease ID */}`。  
- QQ 音乐: `GET https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg` 或其他接口，参数 `{songmid: /* id */}`。  
- 酷狗音乐: 通常先调用 `http://lyrics.kugou.com/lyrics`，传 `{hash,name,duration}`。实际细节在 `callKugou` 模块中实现。  
- AMLL DB TTML: 例如 `GET https://api.amll.net/ncm-lyrics/<neteaseId>`（网易云）或 `/qq-lyrics/<qqId>`。

# 中转/代理服务器

目前**没有发现项目自建或第三方统一代理服务器**。唯一类似功能的是对 TTML 歌词的支持：用户需自行在设置中配置 `lyric.amllDbServer`，指向 AMLL 歌词库的服务地址（示例 `https://api.amll.net/%p/%s`）。项目不提供默认的 TTML 服务器，亦未使用其他域名/IP 进行歌词代理。其他歌词请求直接由客户端调用各平台 API，无额外代理。

# 逆向与模拟

源码中未体现任何签名算法或加密/解密逻辑，歌词接口均调用现成的 API 函数（`callNetease`、`callQQMusic`、`callKugou`）。这些函数内部可能封装了请求头、Cookie、GUID 等，但未在仓库代码中暴露出来。因此**未发现明确的逆向实现细节**（如自制签名算法或 UA 模拟）可供参考。所有 API 调用都是封装好的网络请求，没有额外手动算法介入。

# 第三方歌词服务

除了平台官方接口和 AMLL 数据库外，项目未整合其他第三方歌词源（如 Musixmatch、Genius、LRCLib 等）。在依赖中也未见相关库。所有歌词内容来源于上述**三大平台**和 **AMLL**。没有使用 Musixmatch/Genius 等国际服务，故无需谈及其调用限制或授权要求。

# 法律合规风险提示

- **绕过授权**：网易云、QQ 音乐、酷狗的歌词接口多数属于私有或未公开 API，使用这些接口本身可能违反服务条款。特别是网易云音乐的 `lyric_new` 接口、QQ 音乐的歌词接口、酷狗的歌词接口均非官方授权开放；项目直接调用这些接口获取歌词存在潜在风险。  
- **版权问题**：歌词文本一般属于版权作品，直接抓取并显示未经许可的歌词可能侵犯版权。特别是**高精度同步歌词（TTML）**通常质量极高，若来自 AMLL DB 并公开展示，也可能构成侵权。  
- **建议声明**：使用时应提醒用户遵守版权规定，并尽可能依赖许可渠道（如合法购买音乐并使用授权歌词）。项目在用户协议中应明确免责声明，避免自动分发版权受保护的歌词内容。

# 结论与建议

1. **稳定获取策略**：优先使用平台官方授权的歌词 API。如网易云音乐提供的 Web API（若公开）或寻求正版授权。对于不可避免的私有接口调用，可定时维护或监测接口变动。将歌词文本缓存到本地数据库，减少重复请求，提高稳定性。  
2. **TTML 同步歌词**：如需高精度同步歌词，需配置可靠的 TTML 服务地址。可以考虑自建 AMLL 数据库代理，或者仅作为可选功能提醒用户自行配置。启用时应注意网络超时和缓存策略（代码对失败请求做 72h 负缓存）。  
3. **架构改进**：当前后端（Electron 主进程）直接调用平台 API，可进一步抽象为统一的歌词服务模块，便于扩展和维护。可引入重试机制和错误日志，更细粒度处理失败情况。  
4. **缓存与容错**：已有歌词缓存实现（`lyricCache`、`lyricMatchCache`）有助于提升体验，可继续优化缓存时效和清理策略，避免缓存污染。增加网络错误处理与降级机制，例如当网络或 API 调用失败时，提示用户或自动回退到已有文本。  
5. **合规性**：建议在用户协议和界面提示中明确标注歌词可能受版权保护，避免违规转载。若有条件，探索与正版歌词服务合作或使用公开授权的歌词库，从源头保证合规。

**证据来源：**以上分析依据 SPlayer-Next 官方源码文件（Electron 主进程歌词模块）及项目文档说明。其中涉及的接口名称、字段和逻辑均来自源码实现。若仓库或 DeepWiki 中未明示的信息已如实说明为“未指定/未发现”。