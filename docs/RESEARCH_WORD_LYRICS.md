# 逐字歌词格式调研报告

**调研时间**：2026-07-03  
**目标**：为 lyricGeter 项目添加 YRC/QRC/KRC 等平台专有逐字歌词格式支持

---

## 概述

目前主流音乐平台提供的逐字歌词格式各不相同，本报告汇总已知信息并提出技术方案。

## 平台格式对比

| 平台 | 格式名称 | 逐字支持 | 数据结构 | 优先级 |
|-----|---------|---------|---------|-------|
| 网易云音乐 | YRC | ✅ | JSON（推测） | 高 |
| QQ 音乐 | QRC | ✅ | 加密/压缩（推测） | 高 |
| 酷狗音乐 | KRC | ✅ | 自定义二进制 | 中 |
| 通用 | LRC | ❌ | 纯文本（行级） | 已支持 |
| Salt Player | SPL | ✅ | 增强型 LRC | 目标格式 |
| 网易云/QQ | TTML | ✅ | XML（高级格式） | 低（复杂度高） |

## 关键发现

### 1. 从 TypeScript 参考代码推断

```typescript
const PLATFORM_MAIN_FORMATS: Record<Platform, LyricFormat[]> = {
  netease: ["yrc", "lrc"],     // 网易云：YRC > LRC
  qqmusic: ["qrc", "lrc"],     // QQ 音乐：QRC > LRC
  kugou: ["krc", "lrc"],       // 酷狗：KRC > LRC
};
```

**结论**：
- YRC/QRC/KRC 是各平台的**逐字格式**，优先级高于普通 LRC
- TTML 是更高级的格式，但实现复杂度高

### 2. 格式优先级（来自 TypeScript 代码）

```
ttml > yrc/qrc/krc（逐字）> lrc（行级同步）> 纯文本
```

### 3. 当前 syncedlyrics 的支持情况

从我们的 `fetcher/synced.py` 实现来看：
- `syncedlyrics` 库的 `enhanced=True` 参数会尝试获取逐字歌词
- 但它**只返回纯文本**，不返回原始 YRC/QRC/KRC 数据结构
- 可能已内部转换为 LRC 格式（行内插入时间戳）

**推测**：
- syncedlyrics 可能已经实现了 YRC/QRC 解析，但只导出转换后的 LRC
- 我们需要直接调用平台 API 获取原始数据

---

## 各平台格式分析

### 网易云音乐 YRC

**推测数据结构**（基于常见 API 模式）：

```json
{
  "code": 200,
  "yrc": {
    "lyric": "[{\"t\":5202,\"c\":[{\"tx\":\"你好\",\"t\":0},{\"tx\":\"世界\",\"t\":300}]}]"
  }
}
```

**关键字段**：
- `t`：行开始时间（毫秒）
- `c`：字符数组
  - `tx`：文本
  - `t`：相对行开始的偏移时间（毫秒）

**API 端点**（需逆向确认）：
```
GET https://music.163.com/api/song/lyric?id={songId}
响应包含: lrc, tlyric, yrc
```

**转换难度**：⭐⭐ (中等)
- JSON 格式，易于解析
- 需要处理相对时间转绝对时间
- 网易云 API 相对开放，社区有成熟方案

### QQ 音乐 QRC

**推测数据结构**（基于社区讨论）：

QRC 可能是 **Base64 编码 + 压缩** 的二进制格式，或自定义序列化。

**已知信息**：
- QQ 音乐 API 需要 cookie 认证
- QRC 数据可能需要解密/解压缩
- 社区可能有逆向工具（需搜索 GitHub）

**API 端点**（需逆向确认）：
```
GET https://c.y.qq.com/lyric/fcgi-bin/fcg_query_lyric_new.fcg
需要: songmid, cookie
```

**转换难度**：⭐⭐⭐⭐ (高)
- 格式私有，可能加密
- 需要 cookie 认证（用户体验差）
- 社区方案可能不稳定

### 酷狗音乐 KRC

**推测数据结构**：

KRC 是酷狗专有二进制格式，可能包含：
- 压缩（zlib/gzip）
- 自定义时间戳编码
- 可能有校验和或加密

**API 端点**（需逆向确认）：
```
GET https://lyrics.kugou.com/download?...
返回加密的 KRC 文件
```

**转换难度**：⭐⭐⭐⭐ (高)
- 二进制格式，需要逆向
- 社区方案较少
- 维护成本高

### TTML 格式

TTML (Timed Text Markup Language) 是 W3C 标准，网易云和 QQ 音乐用它存储高级逐字歌词。

**示例结构**：
```xml
<tt xmlns="http://www.w3.org/ns/ttml">
  <body>
    <div>
      <p begin="00:00:05.20" end="00:00:08.50">
        <span begin="00:00:05.20">你好</span>
        <span begin="00:00:05.50">世界</span>
      </p>
    </div>
  </body>
</tt>
```

**转换难度**：⭐⭐⭐ (中高)
- XML 格式，标准库易解析
- 但嵌套结构复杂
- 需要单独的 API 端点

---

## 现有开源项目调研

### 已知可能相关的项目

由于 GitHub 搜索不可用，以下基于常见命名规则推测：

1. **syncedlyrics** (已使用)
   - 仓库：https://github.com/moehmeni/syncedlyrics
   - 功能：多平台歌词获取，支持 enhanced 模式（逐字）
   - **限制**：只返回转换后的 LRC，不暴露原始 YRC/QRC

2. **NeteaseCloudMusicApi** (Node.js)
   - 可能仓库：https://github.com/Binaryify/NeteaseCloudMusicApi
   - 功能：网易云音乐 API 封装
   - **启示**：可参考其接口定义，用 Python 复刻

3. **qqmusic-api** (可能存在)
   - 功能：QQ 音乐 API 封装
   - **状态**：未确认是否有稳定的 Python 版本

4. **python-lrc** / **pylrc**
   - 功能：LRC 格式解析库
   - **限制**：仅支持标准 LRC，不支持逐字

### 社区方案成熟度评估

| 平台 | 社区支持 | API 稳定性 | 推荐度 |
|-----|---------|-----------|-------|
| 网易云 | 🟢 高 | 🟢 稳定 | ⭐⭐⭐⭐⭐ |
| QQ 音乐 | 🟡 中 | 🔴 需认证 | ⭐⭐⭐ |
| 酷狗 | 🔴 低 | 🔴 私有 | ⭐⭐ |

---

## 技术方案建议

### 短期方案（1-2 周）

#### 优先实现：网易云 YRC

**原因**：
- 社区支持好，API 相对开放
- YRC 格式是 JSON，易于解析
- 中文歌曲主要来源

**步骤**：
1. 实现 `fetcher/netease.py`
   ```python
   class NetEaseAPI:
       def search(self, keyword: str) -> list[SearchResult]:
           """搜索歌曲，返回 songId + 元数据"""
       
       def get_lyric(self, song_id: str) -> NetEaseLyric:
           """获取 LRC + YRC + 翻译"""
   ```

2. 实现 `parser/yrc.py`
   ```python
   def parse_yrc(yrc_json: str) -> list[WordTimedLine]:
       """YRC JSON → 内部逐字结构"""
   
   def yrc_to_spl(yrc_json: str) -> str:
       """YRC → SPL 格式"""
   ```

3. 更新 `converter.py`
   - 支持从 YRC 直接转换，而非先转 LRC

**预期收益**：
- 解决相似度过滤问题（获取搜索结果元数据）
- 获得比 syncedlyrics 更高质量的逐字歌词
- 为其他平台实现提供模板

### 中期方案（1 个月）

#### 可选实现：QQ 音乐 QRC

**前提条件**：
- 找到稳定的 QRC 解析库或逆向方案
- 解决 cookie 认证问题（环境变量 or 配置文件）

**实现**：
1. `fetcher/qqmusic.py`
2. `parser/qrc.py`（可能需要调用外部库）

#### 暂缓：酷狗 KRC

- 优先级低（用户群体较小）
- 技术复杂度高
- 等待社区成熟方案

### 长期方案（3 个月+）

#### TTML 支持

- 网易云和 QQ 音乐的最高质量格式
- 需要单独 API 端点（`fetchTTMLOverlay`）
- 实现 `parser/ttml.py`（XML 解析 + SPL 转换）

**建议**：
- 先完成 YRC/QRC 基础支持
- 评估 TTML 的实际质量提升是否值得投入

---

## SPL 格式映射

### YRC → SPL

**YRC 数据**：
```json
{
  "t": 5202,
  "c": [
    {"tx": "你好", "t": 0},
    {"tx": "世界", "t": 300}
  ]
}
```

**转换为 SPL**：
```spl
[00:05.20]你好[00:05.50]世界[00:08.00]
```

**关键逻辑**：
- 行开始时间：`t` (5202ms → 00:05.20)
- 字开始时间：`t + c[i].t` (5202 + 300 = 5502ms → 00:05.50)
- 行结束时间：下一行的 `t`（或文件总时长）

### SPL 延迟逐字语法

如果 YRC 提供了"行到达但首字未开始"的信息：
```spl
[00:05.20]<00:05.30>你好<00:05.50>世界[00:08.00]
```

`<00:05.30>` 表示行在 00:05.20 显示，但首字"你"在 00:05.30 才高亮。

---

## 实现优先级建议

### P0（立即开始）

- [x] 完成 Bug 修复和文档
- [ ] 调研网易云 API（搜索 + 歌词接口）
- [ ] 设计内部逐字数据结构（抽象 YRC/QRC/KRC）

### P1（本周内）

- [ ] 实现 `fetcher/netease.py`（搜索 + LRC/YRC 获取）
- [ ] 实现 `parser/yrc.py`（YRC → SPL）
- [ ] 恢复 `matcher.py` 相似度过滤
- [ ] 补充单元测试

### P2（下周）

- [ ] 评估 QQ 音乐 QRC 可行性
- [ ] 设计 cookie 认证方案（如果需要）
- [ ] 实现 `fetcher/qqmusic.py`（如果方案成熟）

### P3（长期）

- [ ] TTML 支持（评估性价比）
- [ ] 酷狗 KRC（社区方案成熟后）

---

## 风险与挑战

### 技术风险

1. **平台 API 变动**
   - 网易云/QQ 音乐可能随时调整接口
   - 缓解：使用社区成熟方案，及时更新

2. **反爬虫机制**
   - 频繁请求可能被限流/封禁
   - 缓解：添加请求间隔、缓存机制

3. **格式逆向成本**
   - QRC/KRC 格式可能需要持续逆向
   - 缓解：优先实现网易云，其他平台可选

### 法律风险

- 使用平台 API 可能违反服务条款
- **建议**：
  - 仅供个人学习使用
  - 不提供公开服务（避免侵权）
  - 用户自行承担风险

---

## 下一步行动

### 本周任务

1. **网易云 API 调研**（1 天）
   - 搜索相关 Python 封装库
   - 阅读 API 文档或逆向分析
   - 确认 YRC 格式细节

2. **设计数据结构**（0.5 天）
   ```python
   @dataclass
   class WordTiming:
       text: str
       start_ms: int
   
   @dataclass
   class WordTimedLine:
       start_ms: int
       words: list[WordTiming]
       end_ms: int | None
   ```

3. **实现网易云 fetcher**（2 天）
   - 搜索接口
   - 歌词接口（LRC + YRC + 翻译）
   - 错误处理和重试

4. **YRC 解析器**（1 天）
   - JSON → WordTimedLine
   - WordTimedLine → SPL

5. **集成测试**（1 天）
   - 用 `input/` 目录的中文歌曲测试
   - 对比 syncedlyrics 和网易云直连的质量

### 需要的资源

- [ ] 网易云音乐 API 文档或社区库推荐
- [ ] YRC 格式样例数据（用于测试）
- [ ] QQ 音乐 QRC 逆向方案（如果有）

---

## 总结

1. **优先实现网易云 YRC**：社区支持好，技术难度适中，收益最高
2. **QQ 音乐 QRC 可选**：取决于是否有成熟的解析方案
3. **酷狗 KRC 暂缓**：投入产出比低
4. **TTML 长期规划**：等基础格式稳定后评估

**预期时间线**：
- 1 周：网易云 YRC 支持完成
- 2 周：QQ 音乐 QRC 可行性评估
- 1 个月：核心功能稳定，开始优化

**关键里程碑**：
- ✅ 恢复相似度过滤
- ✅ 获得比 syncedlyrics 更高质量的逐字歌词
- ✅ 为用户提供平台选择（网易云 vs syncedlyrics）
