# lyricGeter

为本地音乐库批量获取并写入高质量同步歌词的命令行工具。

> **项目定位**：离线批量预处理工具，不是播放器插件。
> 适合在整理音乐库时一次性处理大量文件，写入前逐个确认避免错配。

## 功能特性

- **多源逐字歌词**：网易云音乐（YRC）、酷狗音乐（KRC）、QQ 音乐（QRC）、AMLL TTML 数据库，四平台互补
- **原生 API**：直接调用平台接口，支持相似度过滤和翻译/罗马音获取
- **SPL 格式**：输出符合 [Salt Player Lyrics 规范](https://moriafly.com/standards/spl.html)，支持逐字、翻译、延迟逐字
- **交互确认**：写入前彩色预览，可手动编辑、跨源合并翻译、再次搜索选歌
- **自动模式**：按权重自动选择最优结果（格式优先 > 相似度），适合批量处理
- **安全备份**：写入前自动备份原有歌词到 `.lrc.bak`
- **断点续传**：目录批处理时自动保存进度，随时退出，下次运行继续剩余文件
- **多格式音频**：MP3、FLAC、Ogg 等主流格式

## 安装

```bash
pip install -r requirements.txt
```

依赖项：`mutagen`、`syncedlyrics`、`rich`、`questionary`、`rapidfuzz`、`httpx`

## 快速开始

```bash
# 处理单个文件（交互模式）
python main.py song.mp3

# 处理整个目录
python main.py ~/Music/

# 自动模式（跳过确认，按权重选择最优结果）
python main.py ~/Music/ --auto

# 预览模式（只看不写）
python main.py song.mp3 --dry-run

# 仅使用网易云
python main.py song.mp3 --no-kugou --no-qqmusic --no-amll

# 优先使用本地已有歌词
python main.py song.mp3 --prefer-local
```

## CLI 选项

| 选项 | 默认值 | 说明 |
|-----|-------|------|
| `--auto` | 关 | 自动选择最优结果写入，跳过交互确认 |
| `--dry-run` | 关 | 仅预览匹配结果，不写入文件 |
| `--amll / --no-amll` | `--amll` | AMLL TTML 数据库（社区人工校验逐字歌词） |
| `--netease / --no-netease` | `--netease` | 网易云 API（YRC 逐字 + 翻译） |
| `--kugou / --no-kugou` | `--kugou` | 酷狗 API（KRC 逐字 + 翻译 + 罗马音） |
| `--qqmusic / --no-qqmusic` | `--qqmusic` | QQ 音乐 API（QRC 逐字 + 翻译 + 罗马音） |
| `--source` | `all` | syncedlyrics 兜底来源：`netease` / `lrclib` / `musixmatch` / `all` |
| `--threshold` | `70.0` | 相似度阈值 (0-100)，低于此分数的候选被过滤 |
| `--lang` | `zh` | 翻译语言代码，留空则不获取翻译 |
| `--prefer-local` | 关 | 优先使用本地歌词（默认优先在线） |

## 工作流程

```
扫描文件  →  搜索歌词  →  转换 SPL  →  交互确认  →  写入标签
```

1. **扫描**：读取音频元数据（标题、艺术家），检测已有内嵌/外部歌词
2. **搜索**：并行查询各平台，按格式质量排序（逐字 > 行级 > 纯文本）
3. **转换**：各平台格式统一转换为 SPL，补全时间戳、合并翻译
4. **确认**：彩色预览，可选择接受 / 合并翻译 / 再次搜索 / 编辑 / 跳过
5. **写入**：MP3 写入 `USLT` (ID3v2)，FLAC/Ogg 写入 `lyrics` (Vorbis Comment)

### 交互模式

默认逐文件交互，完整流程如下：

**第一步：选择歌词来源**

显示所有候选歌词（含格式、行数、翻译、相似度）：
```
找到 4 个候选歌词：

  1. amll - 逐字 62行 有翻译 相似度:96
  2. kugou - 逐字 39行 无翻译 相似度:96
  3. netease - 行级同步 41行 有翻译 相似度:95
  4. local - 行级同步 85行 无翻译
```

**第二步：预览并操作**

预览选中歌词（前 30 行，时间戳高亮），然后选择：

- **接受并写入**：直接写入
- **选择翻译来源合并**：从其他候选中挑翻译叠加到当前歌词（跨源翻译合并）
- **返回重新选择**：回到第一步
- **再次搜索并选择歌曲**：手动输入关键词，从搜索结果中选歌
- **手动编辑后写入**：在 `$EDITOR` 中修改
- **跳过此文件** / **退出程序**

### 自动模式 (`--auto`)

按权重直接写入，排序规则：`格式优先（逐字 > 行级 > 纯文本）→ 相似度（高 > 低）`。少于 5 行的歌词按纯音乐处理，自动清除歌词标签。

### 断点续传

处理目录时，程序在目标目录下维护 `.lyricgeter.json` 状态文件，记录已处理文件：

- 每处理完一个文件（写入 / 跳过 / 清除）立即保存进度
- 随时 Ctrl+C 退出，下次运行可从断点继续
- 再次运行检测到上次进度时：交互模式询问「继续 / 重新开始 / 取消」，自动模式直接继续
- 未找到歌词的文件下次会重试，全部处理完成后状态文件自动清除

状态文件仅目录处理时创建，单文件处理不启用。已被 `.gitignore` 忽略。

## 已支持的逐字歌词格式

| 平台 | 格式 | 翻译 | 罗马音 | 说明 |
|-----|------|:----:|:-----:|------|
| 网易云音乐 | YRC | 支持 | - | 正则解析，无需解密 |
| 酷狗音乐 | KRC | 支持 | 支持 | Base64 + XOR + zlib 解密 |
| QQ 音乐 | QRC | 支持 | 支持 | 3DES-ECB + zlib 解密 |
| AMLL TTML | TTML | 支持 | 支持 | 从 AMLL GitHub 数据库按歌曲 ID 获取 |

AMLL TTML 数据库获取流程：搜索网易云/QQ音乐拿歌曲 ID → 从 `amll-ttml-db` 仓库下载对应 TTML 文件 → 解析并转换为 SPL。舍弃 SPL 不支持的背景人声、对唱、Ruby 注音。

## 本地歌词优先级

与播放器相反，外部文件优先于内嵌：

1. 同目录同名 `.lrc` / `.spl` 文件（外部，最高优先级）
2. 音频文件内嵌歌词标签（内嵌，优先级最低）

**原因**：批处理场景中，外部文件往往是用户手动编辑或下载的精校版本，应优先保留；内嵌歌词可能是自动写入的低质量版本。


## 项目结构

```
lyricGeter/
├── main.py              # CLI 入口（click）
├── scanner.py           # 扫描音乐文件、读取内嵌/外部歌词
├── fetcher/
│   ├── base.py          # 抽象 LyricsFetcher 接口
│   ├── synced.py        # syncedlyrics 封装（兜底）
│   ├── netease.py       # 网易云原生 API（YRC）
│   ├── kugou.py         # 酷狗原生 API（KRC）
│   ├── qqmusic.py       # QQ 音乐原生 API（QRC）
│   ├── amll.py          # AMLL TTML 数据库获取器
│   └── __init__.py
├── parser/
│   ├── yrc.py           # 网易云逐字解析
│   ├── krc.py           # 酷狗逐字解析
│   ├── qrc.py           # QQ 音乐逐字解析
│   ├── ttml.py          # TTML 解析（AMLL 数据库）
│   ├── json_lyric.py    # 网易云 JSON 歌词解析
│   └── __init__.py
├── decryptor/           # 各平台加密/解密
├── matcher.py           # 格式质量评分、策略调度
├── converter.py         # 各格式 → SPL 转换
├── writer.py            # 写入音频标签
├── state.py             # 断点续传状态管理
├── ui.py                # 终端交互界面
└── example/
    └── lyricLoader.ts   # TypeScript 参考实现
```

## 已知限制

- **不支持 byId 精确匹配**：本地文件无平台 ID，仅靠标题+艺术家搜索，可能出现同名误配。建议用 `--dry-run` 预览后再写入。
- **逐字覆盖率依赖平台**：部分歌曲在各平台均无逐字版本，仅能获取行级同步歌词。
- **syncedlyrics 兜底无相似度**：Lrclib、Musixmatch 不返回匹配歌曲信息，信任其内部排序。


## 致谢

- [syncedlyrics](https://github.com/moehmeni/syncedlyrics) - 多平台歌词获取
- [mutagen](https://github.com/quodlibet/mutagen) - 音频标签操作
- [Salt Player](https://moriafly.com/) - SPL 格式规范
- [AMLL TTML Database](https://github.com/amll-dev/amll-ttml-db) - 社区维护的 TTML 歌词库
- [LDDC](https://github.com/chenmozhijin/LDDC) - 多平台搜索与解析逻辑

## 许可证

MIT
