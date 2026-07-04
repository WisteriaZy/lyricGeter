# TODO

## 🐛 Bug 修复

- [x] 修复 `matcher.py` 比较运算符错误（`>=` → `<=`）
- [x] 修复相似度计算自我比对 Bug（暂时禁用相似度过滤）
- [x] 调整内嵌/外部歌词优先级（外部优先）
- [x] 修复 Progress 日志被覆盖问题（`transient=False`）
- [x] **修正 SPL 格式转换逻辑**（2026-07-03）
  - [x] 时间戳格式：保持 2 位毫秒（厘秒精度）
  - [x] 逐字时间戳位置：行首/行尾用 `[]`，中间用 `<>`（SPL 延迟逐字标记）
  - [x] 网易云逐字格式：正确解析并转换为 SPL
  - [x] 行结束时间戳：显式补充下一行开始时间
- [x] **修复翻译功能**（2026-07-03）
  - [x] 实现容差匹配算法（±500ms）
  - [x] 解决网易云翻译和逐字歌词时间戳不同步问题
  - [x] 翻译行正确插入到主歌词后（无时间戳）
  - [x] 测试验证：`input/我愛你-上海蟹- - カニ研究会.mp3`
- [x] **跨源翻译合并**（2026-07-04）
  - [x] `converter.py` 新增 `extract_translation_lrc()` 和 `merge_translation()`
  - [x] `ui.py` 新增翻译来源选择子菜单和操作内循环
  - [x] 容差匹配从 ±500ms 提升到 ±2000ms，解决 YRC 与翻译 LRC 时间戳偏移
  - [x] 匹配率低于 30% 时自动回退到顺序匹配（跨平台时间戳偏移）
  - [x] 测试验证：`input/echo (feat. 初音ミク) - higma, 初音ミク.mp3`（酷狗逐字 + 网易云翻译）
  - [x] 修复 Take Me Hand 翻译不完整问题（覆盖率 54.8% → 98.4%）

## 📝 文档

- [x] 编写 README.md
- [x] 说明已知限制和使用建议
- [x] 集成 SPL 官方格式文档（`docs/SPL 格式（Salt Player Lyrics）语法标准  不要糖醋放椒盐（椒盐音乐官网）.md`）
- [x] 更新 TODO.md 和 SUMMARY.md 反映格式修正
- [ ] 添加使用截图
- [ ] 编写贡献指南
- [ ] 更新 AGENTS.md 反映项目定位变更

## ✨ 功能增强（短期）

### CLI 选项
- [ ] `--skip-existing`：跳过已有内嵌歌词的文件
- [ ] `--backup-dir <path>`：集中备份原歌词，而非 `.lrc.bak`
- [ ] `--format-filter <word|line|plain>`：仅写入指定格式的歌词
- [ ] `--batch-size <n>`：批量确认模式（每 N 个文件暂停一次）

### 错误处理
- [ ] 网络超时重试机制（指数退避）
- [ ] 失败文件单独日志（`failed.log`）
- [ ] 支持从上次中断处继续（状态文件）

### 交互体验
- [ ] 预览时显示歌曲时长和歌词行数
- [ ] 编辑模式时语法高亮（时间戳）
- [ ] 支持批量操作（"全部接受"/"全部跳过"）

## 🚀 核心功能（P0 - 本月完成）

### 平台原生 API + 逐字歌词解密
**优先级：最高**（解决相似度过滤和逐字歌词获取）

#### 第 1 周：网易云 + 酷狗

- [x] **网易云 YRC 支持**（难度 ⭐⭐）
  - [x] `decryptor/eapi.py`：EAPI 加密（AES-ECB + MD5 签名）
  - [x] `parser/yrc.py`：YRC 格式解析（纯正则，无解密）
  - [x] `parser/json_lyric.py`：新版 JSON 格式解析
  - [x] `fetcher/netease.py`：搜索 + 歌词接口
  - [x] `converter.py`：YRC/JSON → SPL 转换，支持混合格式
  - [x] 集成到 `main.py`，默认启用（`--no-netease` 禁用）
  - [x] 测试：用 `input/飞 - ANU.mp3` 验证藏语歌词+翻译

- [x] **酷狗 KRC 支持**（难度 ⭐⭐）✅ **已完成 2026-07-03**
  - [x] `decryptor/krc.py`：Base64 + XOR + zlib 解密
  - [x] `parser/krc.py`：解析 `<>` 标记的逐字格式 + 翻译 + 罗马音
  - [x] `fetcher/kugou.py`：两步获取（搜索候选 + 下载）+ LyricsFetcher 适配器
  - [x] `converter.py`：KRC → SPL 转换
  - [x] 集成到 `main.py`，默认启用（`--no-kugou` 禁用）
  - [x] 测试：验证 KRC 解密正确性
    - ✅ `input/飞 - ANU.mp3`：藏文歌曲，67 行逐字 + 翻译
    - ✅ `input/CHO-DARI- - 23.exe, 初音ミク.mp3`：日文歌曲，52 行逐字
  - [x] 文档：`docs/KUGOU_KRC_IMPLEMENTATION.md`

#### 第 2 周：QQ 音乐 + 相似度恢复

- [x] **QQ 音乐 QRC 支持** ✅ **已完成 2026-07-04**
  - [x] `fetcher/qqmusic.py`：搜索 + 歌词接口（基于 LDDC Python 实现）
  - [x] `parser/qrc.py`：解析 QRC 格式（XML + LRC 兼容）
  - [x] `converter.py`：QRC → SPL 转换（逐字时间戳 + 翻译）
  - [x] `decryptor/qrc.py`：3DES-ECB + zlib 解密（直接移植 LDDC Python 代码）
    - **根因修复**：`inverse_permutation` 函数的字节排列和 s0/s1 交替顺序错误
    - 改用 LDDC Python 项目的完整实现，彻底解决解密问题
  - [x] 端到端测试：Take Me Hand - DAISHI DANCE（73 行逐字 + 翻译）
  - **三大平台逐字歌词全部完成**

- [x] **恢复相似度过滤** ✅ **已完成 2026-07-03**
  - [x] 重构 `fetcher/base.py`：`LyricResult` 新增 `matched_title`, `matched_artist` 字段
  - [x] 修改网易云和酷狗 fetcher 返回匹配歌曲信息
  - [x] 修改 `matcher.py`：计算标题+艺术家相似度（`rapidfuzz.fuzz.WRatio`）
  - [x] 阈值默认 70 分（`DEFAULT_THRESHOLD`）
  - [x] 原生 API 启用过滤，syncedlyrics 等第三方库信任其内部排序
  - [x] 手动验证：相似度过滤逻辑已验证（早期根目录脚本已清理）

#### 公共任务

- [ ] **新增依赖**
  ```bash
  pip install pycryptodome  # AES/3DES 加密
  ```

- [ ] **错误处理**
  - [ ] 解密失败时回退到 syncedlyrics
  - [ ] API 限流时自动重试（指数退避）
  - [ ] 记录失败文件到 `failed.log`

- [ ] **性能优化**
  - [ ] 添加请求间隔（避免封禁）
  - [ ] 缓存搜索结果（SQLite）
  - [ ] 单首歌曲处理时间 < 3 秒

### 并行搜索优化
**优先级：中**

- [ ] 同时查询多个平台，取最优结果
- [ ] 实现格式优先级配置（用户自定义 `word > line > plain`）
- [ ] 支持平台优先级配置（如优先网易云）

### 测试覆盖
**优先级：中**（与平台实现并行）

- [ ] `pytest` 基础设施 + GitHub Actions CI
- [ ] **解密器测试**（关键！）
  - [ ] `decryptor/krc.py`：用 LDDC 已知样例验证
  - [ ] `decryptor/qrc.py`：3DES 解密边界情况
  - [ ] `decryptor/eapi.py`：EAPI 签名准确性
- [ ] **解析器测试**
  - [ ] `parser/yrc.py`：正则捕获准确率 > 95%
  - [ ] `parser/qrc.py`：XML 包裹情况
  - [ ] `parser/krc.py`：`<>` 标记解析
- [ ] `converter.py` 单元测试
  - [ ] YRC/QRC/KRC → SPL 转换
  - [ ] 边界情况（空行、乱序时间戳、特殊字符）
  - [ ] 翻译对齐测试
  - [ ] 逐字时间戳严格递增校验
- [ ] `matcher.py` 模拟测试
- [ ] 集成测试（端到端：扫描 → 获取 → 转换 → 写入）

## 🔬 高级功能（长期）

### TTML 支持 (AMLL 数据库)
**已完成 ✅**（2026-07-04）

通过 AMLL TTML 数据库（GitHub raw）按歌曲 ID 获取 TTML 逐字歌词。

- [x] `parser/ttml.py`：TTML XML 解析器，提取逐字时间戳 + 翻译 + 罗马音
- [x] `fetcher/amll.py`：搜索网易云/QQ音乐获取歌曲 ID，从 AMLL DB 下载 TTML
- [x] `converter.py`：TTML → SPL 转换（逐字 `[]`/`<>` + 翻译行）
- [x] 舍弃 SPL 不支持的功能（背景人声 `x-bg`、对唱 `agent`、Ruby 注音）
- [x] 保留 span 间空格（确保英文歌词可读性）
- [x] 集成到 `main.py`，默认启用（`--amll/--no-amll`）
- [x] 端到端测试：Take Me Hand - DAISHI DANCE（逐字 + 翻译）

### 智能匹配增强
**优先级：低**

- [ ] 支持从文件名提取元数据（如 `艺术家 - 标题.mp3`）
- [ ] 音频指纹匹配（AcoustID）
- [ ] 模糊搜索（处理繁简体、全半角差异）
- [ ] 专辑/发行年份辅助匹配

### 批量处理优化
**优先级：低**

- [ ] 多线程并行搜索（threadpool）
- [ ] 缓存机制（避免重复查询）
- [ ] 增量更新模式（仅处理新增文件）

### GUI 前端
**优先级：极低**（需要独立项目）

- [ ] Electron 或 Tauri 封装
- [ ] 可视化批量处理进度
- [ ] 歌词对比视图（本地 vs 在线）
- [ ] 拖拽添加文件/目录
- [ ] 内置歌词编辑器

## 📚 调研任务

### 逐字歌词解析项目
**已完成 ✅**

- [x] 调研现有的 YRC/QRC/KRC 解析库
- [x] 评估集成可行性（Python 生态）
- [x] 对比 SPL 规范和各平台格式差异
- [x] 产出技术方案文档

**成果**：找到 LDDC-Android 项目（Kotlin），已完整实现三平台解密和解析，详见 `docs/LDDC_ANALYSIS.md`

### 平台 API 逆向
- [ ] 网易云音乐 API 文档整理
- [ ] QQ 音乐 API 认证机制研究
- [ ] Musixmatch API 官方文档阅读
- [ ] 各平台限流策略调研

## 🧹 代码质量

- [ ] 类型注解覆盖率 100%（`mypy`）
- [ ] 代码格式化（`ruff format`）
- [ ] Lint 检查（`ruff check`）
- [ ] 文档字符串补全（所有公开 API）
- [ ] CI/CD 流程（GitHub Actions）

## 📦 发布

- [ ] 打包为可执行文件（PyInstaller）
- [ ] 发布到 PyPI（`pip install lyricgeter`）
- [ ] 编写安装脚本（Windows/macOS/Linux）
- [ ] 版本管理（语义化版本）

---

## 优先级说明

- **高**：影响核心功能，阻塞用户正常使用
- **中**：提升用户体验，但有替代方案
- **低**：锦上添花，长期规划
- **极低**：需要独立评估投入产出比

## 贡献

欢迎认领任务！请在 Issue 中说明你想做的部分，避免重复工作。
