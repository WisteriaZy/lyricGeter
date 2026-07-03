# lyricGeter 项目定位说明

**最后更新**：2026-07-03  
**状态**：已完成定位调整和技术方案确认

---

## 核心定位

lyricGeter 是一个 **离线批量歌词嵌入工具**，不是播放器插件。

### 与播放器歌词加载的本质区别

| 维度 | 播放器（如 Salt Player） | lyricGeter（本项目） |
|-----|------------------------|---------------------|
| **使用场景** | 播放时实时加载 | 批量预处理 |
| **用户控制** | 自动后台获取 | 逐文件人工确认 |
| **本地优先级** | 内嵌 > 外部 | **外部 > 内嵌** |
| **平台匹配** | byId + byQuery | 仅 byQuery |
| **智能升级** | 有本地时按需请求 | 总是请求，用户决定 |

### 关键设计决策：文件内嵌优先级最低

**为何与播放器相反？**

- **播放器场景**：内嵌歌词便于文件携带（移动时歌词跟随），优先读取
- **批处理场景**：外部 `.lrc`/`.spl` 往往是用户精心编辑/下载的版本，应优先保留；内嵌可能是自动写入的低质量版本

**实现逻辑**（已完成）：
```python
# scanner.py - TrackInfo.best_local_lyric
if self.external_lyric:  # 优先外部
    return self.external_lyric, _detect_format(...)
if self.embedded_lyric:  # 兜底内嵌
    return self.embedded_lyric, self.embedded_format
```

---

## 技术路线

### 当前状态（v0.1）

- ✅ 基于 `syncedlyrics` 获取多平台歌词
- ✅ 支持 LRC → SPL 转换
- ✅ 交互式预览和确认
- ⚠️ 相似度过滤暂时禁用（syncedlyrics 不返回搜索结果元数据）
- ⚠️ 不支持平台专有逐字格式（YRC/QRC/KRC）

### 下一阶段（v0.2 - 本月）

参考 LDDC-Android 项目（Kotlin），移植三大平台逐字歌词支持：

#### 第 1 周：网易云 + 酷狗

1. **网易云 YRC**（难度 ⭐⭐）
   - EAPI 加密（AES-ECB + MD5）
   - YRC 正则解析（纯文本 JSON）
   - 转换为 SPL 逐字格式

2. **酷狗 KRC**（难度 ⭐⭐）
   - Base64 + XOR + zlib 解密
   - `<mm:ss.xx>文字` 格式解析
   - 两步获取流程（搜索候选 + 下载）

#### 第 2 周：QQ 音乐 + 相似度恢复

3. **QQ 音乐 QRC**（难度 ⭐⭐⭐⭐）
   - 3DES-ECB + zlib 解密
   - XML 包裹处理
   - Cookie 认证

4. **恢复相似度过滤**
   - 平台原生 API 返回完整搜索结果
   - 计算标题+艺术家相似度（rapidfuzz）
   - 阈值默认 70 分，可配置

---

## 文件结构调整

```
lyricGeter/
├── decryptor/          # 新增：解密器
│   ├── eapi.py         # 网易云 EAPI 加密
│   ├── krc.py          # 酷狗 KRC 解密
│   └── qrc.py          # QQ 音乐 QRC 解密
├── parser/             # 新增：格式解析器
│   ├── yrc.py          # 网易云 YRC 解析
│   ├── qrc.py          # QQ 音乐 QRC 解析
│   └── krc.py          # 酷狗 KRC 解析
├── fetcher/
│   ├── synced.py       # 现有：syncedlyrics 封装
│   ├── netease.py      # 新增：网易云原生 API
│   ├── qqmusic.py      # 新增：QQ 音乐原生 API
│   └── kugou.py        # 新增：酷狗原生 API
└── converter.py        # 扩展：支持 YRC/QRC/KRC → SPL
```

---

## 已知风险与缓解

| 风险 | 等级 | 缓解措施 |
|-----|------|---------|
| 平台 API 逆向接口非官方 | 🔴 高 | 添加请求间隔、用户自担风险声明 |
| 3DES 解密复杂度高 | 🟡 中 | 使用 pycryptodome 库，参考 LDDC 实现 |
| 格式解析准确率 | 🟡 中 | 单元测试覆盖，目标 > 95% |
| API 限流/封禁 | 🟡 中 | 指数退避重试、缓存搜索结果 |

---

## 参考资料

- **SPL 规范**：https://moriafly.com/standards/spl.html
- **LDDC-Android**：`example/LDDC-Android-main/`（Kotlin 参考实现）
- **技术分析**：`docs/LDDC_ANALYSIS.md`
- **格式调研**：`docs/RESEARCH_WORD_LYRICS.md`
- **播放器参考**：`example/lyricLoader.ts`（仅供对比，逻辑不同）

---

## 评估标准

### 成功指标（v0.2）

- ✅ 网易云/酷狗/QQ 音乐三平台逐字歌词成功率 > 80%
- ✅ YRC/QRC/KRC 解析准确率 > 95%
- ✅ 相似度过滤错配率 < 5%
- ✅ 单首歌曲处理时间 < 3 秒（含网络请求）
- ✅ SPL 时间戳严格递增校验通过率 100%

### 用户体验目标

- 批量处理 100 首歌曲 < 5 分钟
- 预览界面清晰展示格式质量（WORD/LINE/PLAIN）
- 错误提示友好，提供重试选项
- 生成日志便于排查失败原因

---

## 长期规划

### 不做的事

- ❌ 实时播放器插件
- ❌ GUI 图形界面（优先级极低）
- ❌ 音频指纹识别（成本高，收益低）
- ❌ TTML 格式（YRC/QRC 已够用）

### 可能做的事

- ✅ 多线程并行搜索（提速）
- ✅ SQLite 缓存（避免重复请求）
- ✅ 从文件名提取元数据（`艺术家 - 标题.mp3`）
- ✅ 支持 byId 精确匹配（如果元数据含平台 ID）

---

## 贡献者指南

1. **优先级排序**：P0（核心功能）> P1（用户体验）> P2（优化）> P3（锦上添花）
2. **代码规范**：完整类型注解 + ruff 格式化
3. **测试要求**：解密器/解析器必须有单元测试
4. **文档更新**：修改核心逻辑时同步更新 AGENTS.md

---

**问题反馈**：提交 Issue 时请附上歌曲元数据、错误日志、`--dry-run` 输出
