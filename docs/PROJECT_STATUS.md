# lyricGeter 项目状态总结

**更新日期**：2026-07-03

## 当前版本功能

### ✅ 已实现的核心功能

#### 1. 多平台逐字歌词支持
- **网易云音乐（NetEase）**
  - 格式：YRC（逐字） + JSON（逐行）
  - 功能：逐字歌词 + 翻译
  - 解密：EAPI 加密（AES-ECB + MD5 签名），歌词数据无需解密
  - 状态：✅ 已完成并测试
  - 文档：`docs/NETEASE_IMPLEMENTATION.md`

- **酷狗音乐（Kugou）**
  - 格式：KRC（逐字）
  - 功能：逐字歌词 + 翻译 + 罗马音
  - 解密：Base64 + XOR + zlib
  - 状态：✅ 已完成并测试
  - 文档：`docs/KUGOU_KRC_IMPLEMENTATION.md`

#### 2. SPL 格式转换
- ✅ 完全符合 [Salt Player Lyrics 官方标准](https://moriafly.com/standards/spl.html)
- ✅ 支持逐字时间戳（行首/行尾用 `[]`，中间用 `<>`）
- ✅ 支持显式行结束时间戳
- ✅ 支持翻译行（容差匹配算法 ±500ms）
- ✅ 时间戳格式标准化（2 位毫秒，厘秒精度）

#### 3. 相似度过滤
- ✅ 网易云/酷狗原生 API：启用相似度评分（默认阈值 70）
- ✅ 使用 `rapidfuzz.fuzz.WRatio` 计算标题+艺术家相似度
- ⚠️ Lrclib/Musixmatch 第三方库：信任其内部排序

#### 4. 用户交互
- ✅ 彩色终端预览（rich）
- ✅ 四个选项：接受 / 跳过 / 编辑 / 退出
- ✅ 自动模式（`--auto`）跳过确认
- ✅ 预览模式（`--dry-run`）不写入

#### 5. 文件处理
- ✅ 支持 MP3、FLAC、Ogg 等主流格式
- ✅ 外部歌词优先于内嵌（`.lrc`/`.spl` > 内嵌标签）
- ✅ 自动备份原歌词到 `.lrc.bak`
- ✅ 批量处理整个目录

### ⚠️ 已知限制

#### 1. QQ 音乐 QRC 暂不可用
**问题描述**：
- 自定义 3DES-ECB 解密算法实现遇到技术难点
- 已完整移植 LDDC-Android 的 Kotlin 实现（S-Box、置换表、密钥调度、F函数）
- 解密后的数据无法被 zlib 解压，报错：`zlib.error: Error -3 while decompressing data: invalid code lengths set`

**可能原因**：
- 密钥调度的细微差异
- F 函数的位操作错误
- 整数符号/溢出问题
- 字节序假设错误

**当前状态**：
- 已搁置，优先级降低
- 保留代码用于后续调试：`decryptor/qrc.py`、`parser/qrc.py`、`fetcher/qqmusic.py`
- 详细分析见：`docs/QRC_DECRYPTION_STATUS.md`

**影响评估**：
- 网易云 + 酷狗已覆盖大部分逐字歌词需求
- 用户可使用 QQ 音乐客户端自带歌词下载功能，再用本工具写入

**长期解决方案**：
1. 寻找现有 Python QRC 解密库
2. 使用 jpype/pyjnius 调用 LDDC-Android 的 Kotlin 代码
3. 请求 LDDC 社区协助调试或提供 Python 移植

#### 2. 不支持 byId 精确匹配
- 本地音乐文件不携带平台 ID
- 只能用 byQuery（标题+艺术家搜索）
- 建议使用 `--dry-run` 预览后再批量写入

#### 3. 逐字歌词覆盖率依赖平台
- 部分歌曲仅提供行级同步歌词
- 即使原生平台也无逐字版本
- 两个平台（网易云 + 酷狗）互补提高覆盖率

## 项目结构

```
lyricGeter/
├── main.py                   # CLI 入口（click）
├── scanner.py                # 扫描音乐文件、读取内嵌/外部歌词
├── matcher.py                # 格式质量评分、相似度过滤、策略调度
├── converter.py              # LRC/YRC/KRC → SPL 格式转换
├── writer.py                 # 写入 SPL 到音频标签
├── ui.py                     # 终端交互界面（rich + questionary）
├── fetcher/
│   ├── base.py               # 抽象 LyricsFetcher 接口
│   ├── synced.py             # syncedlyrics 封装（Lrclib、Musixmatch）
│   ├── netease.py            # 网易云 API ✅
│   ├── kugou.py              # 酷狗 API ✅
│   └── qqmusic.py            # QQ 音乐 API ⚠️（解密未完成）
├── parser/
│   ├── json_lyric.py         # 网易云 JSON 格式解析 ✅
│   ├── netease_word.py       # 网易云逐字格式解析 ✅
│   ├── yrc.py                # YRC 旧版格式解析（网易云未使用）
│   ├── krc.py                # 酷狗 KRC 格式解析 ✅
│   └── qrc.py                # QQ 音乐 QRC 格式解析 ⚠️
├── decryptor/
│   ├── eapi.py               # 网易云 EAPI 加密 ✅
│   ├── krc.py                # 酷狗 KRC 解密 ✅
│   ├── qrc.py                # QQ 音乐 QRC 解密 ⚠️（未完成）
│   └── qrc_simple.py         # 简化版 QRC 解密（调试用）
└── docs/
    ├── NETEASE_IMPLEMENTATION.md     # 网易云实现文档
    ├── KUGOU_KRC_IMPLEMENTATION.md   # 酷狗实现文档
    ├── QRC_DECRYPTION_STATUS.md      # QRC 解密状态分析
    ├── SIMILARITY_FILTERING.md       # 相似度过滤文档
    ├── SPL_FORMAT_FIX.md             # SPL 格式修正文档
    ├── TRANSLATION_FIX.md            # 翻译功能修复文档
    └── SUMMARY.md                    # 开发总结
```

## 测试情况

### 测试文件列表
```
input/
├── 飞 - ANU.mp3                              # 藏文歌曲，网易云 YRC 测试
├── 我愛你-上海蟹- - カニ研究会.mp3            # 日文歌曲，网易云/酷狗全功能测试
├── CHO-DARI- - 23.exe, 初音ミク.mp3         # 日文歌曲，酷狗 KRC 测试
└── ... (更多测试文件)
```

### 测试覆盖
- ✅ 网易云 YRC 解析和转换
- ✅ 酷狗 KRC 解密、解析和转换
- ✅ SPL 格式正确性（时间戳、逐字、翻译）
- ✅ 相似度过滤逻辑
- ⚠️ QQ 音乐 QRC 解密失败

## 依赖项

```txt
mutagen           # 音频标签读写
syncedlyrics      # 多平台歌词获取（Lrclib、Musixmatch）
rich              # 终端彩色输出
questionary       # 交互式输入
rapidfuzz         # 字符串相似度评分
httpx             # HTTP 客户端
pycryptodome      # AES/XOR 加密解密
click             # CLI 框架
```

## 下一步计划

### 短期（本周）
1. ✅ 提交代码到 Git
2. 📝 完善用户文档
   - [ ] 添加使用截图
   - [ ] 编写常见问题解答
   - [ ] 补充使用示例
3. 🧹 清理项目
   - [ ] 删除或归档调试文件
   - [ ] 整理测试文件

### 中期（本月）
1. 🧪 补充单元测试
   - [ ] 解密器测试（KRC、EAPI）
   - [ ] 解析器测试（正则准确率 > 95%）
   - [ ] 转换器边界测试
2. 🚀 功能增强
   - [ ] 并行搜索（同时查询多平台，取最优）
   - [ ] 本地缓存（SQLite 存储搜索结果）
   - [ ] 批量确认模式（每 N 个文件暂停一次）

### 长期（未来）
1. 🔧 QRC 解密问题解决
   - 选项 A：寻找现有 Python 库
   - 选项 B：使用 jpype 调用 Kotlin 代码
   - 选项 C：社区协作调试
2. 🎨 GUI 版本（可选）
   - 使用 tkinter/PyQt 开发桌面应用
   - 拖拽文件批量处理
   - 可视化歌词预览

## 贡献指南

欢迎贡献！优先方向：
1. **单元测试**：补充核心模块的测试覆盖
2. **QRC 解密**：协助调试或提供解决方案
3. **文档改进**：英文翻译、使用示例、FAQ
4. **功能增强**：见 `TODO.md` 中的任务列表

提交前请：
- 使用 `ruff format` 格式化代码
- 更新相关文档
- 说明改动原因和测试结果

## 致谢

本项目参考和使用了以下开源项目：
- [LDDC](https://github.com/chenmozhijin/LDDC) - 歌词下载和解密算法参考
- [syncedlyrics](https://github.com/moehmeni/syncedlyrics) - 多平台歌词获取
- [mutagen](https://github.com/quodlibet/mutagen) - 音频标签读写

感谢开源社区的贡献！

---

**项目定位**：离线批量预处理工具，不是播放器插件  
**核心价值**：高质量逐字歌词 + 人工确认 + SPL 标准格式

**状态**：网易云 + 酷狗功能完整可用，适合日常使用 ✅
