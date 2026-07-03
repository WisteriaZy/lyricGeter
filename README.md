# lyricGeter

为本地音乐库批量添加高质量同步歌词的 Python CLI 工具。

> **项目定位**：离线批量预处理工具，不是播放器插件。  
> 适合在整理音乐库时一次性处理大量文件，写入前逐个确认避免错配。  
> 与播放器实时加载的区别详见 [docs/PROJECT_POSITIONING.md](docs/PROJECT_POSITIONING.md)。

## 功能特性

- 🎵 **多格式支持**：MP3、FLAC、Ogg 等主流音频格式
- 🌐 **多源获取**：网易云音乐、Lrclib、Musixmatch（支持翻译）
- ⚡ **逐字优先**：自动获取 Word-level 同步歌词，优于普通 LRC
- 📝 **SPL 格式**：输出符合 [Salt Player Lyrics 规范](https://moriafly.com/standards/spl.html)
- 👀 **交互确认**：写入前彩色预览，可手动编辑或跳过
- 🔒 **安全备份**：自动备份原有歌词到 `.lrc.bak`

## 安装

```bash
pip install -r requirements.txt
```

依赖项：
- `mutagen` - 音频标签读写
- `syncedlyrics` - 多平台歌词获取
- `rich` + `questionary` - 终端 UI
- `rapidfuzz` - 相似度评分
- `httpx` - HTTP 客户端

## 快速开始

### 处理单个文件
```bash
python main.py song.mp3
```

### 处理整个目录
```bash
python main.py ~/Music/
```

### 自动模式（跳过确认）
```bash
python main.py song.mp3 --auto
```

### 预览模式（不写入）
```bash
python main.py song.mp3 --dry-run
```

## 使用示例

```bash
# 仅从网易云获取
python main.py song.mp3 --source netease

# 使用 Musixmatch 获取翻译（需要 API key）
export MUSIXMATCH_TOKEN="your_token_here"
python main.py song.mp3 --source musixmatch --lang zh

# 降低相似度阈值（匹配更宽松）
python main.py song.mp3 --threshold 50

# 优先使用本地歌词（仅当在线格式更优时才覆盖）
python main.py song.mp3 --prefer-local
```

## 工作流程

```
┌─────────────┐
│ 扫描文件    │  读取音频元数据（标题、艺术家）
└──────┬──────┘  检测已有内嵌/外部歌词
       ↓
┌─────────────┐
│ 搜索歌词    │  并行查询多个平台
└──────┬──────┘  按格式质量排序（逐字 > 行级 > 纯文本）
       ↓
┌─────────────┐
│ 转换格式    │  LRC → SPL
└──────┬──────┘  补全时间戳、校验逐字、合并翻译
       ↓
┌─────────────┐
│ 交互确认    │  彩色预览 + 4 个选项：
└──────┬──────┘  接受 / 跳过 / 编辑 / 退出
       ↓
┌─────────────┐
│ 写入标签    │  MP3 → USLT (ID3)
└─────────────┘  FLAC/Ogg → lyrics (Vorbis Comment)
```

## 本地歌词优先级（与播放器相反）

工具按以下顺序检测本地歌词：

1. **同目录同名 `.lrc` 或 `.spl` 文件**（外部，最高优先级）
2. **音频文件内嵌歌词标签**（内嵌，优先级最低）

**为何与播放器相反？**
- 播放器中：内嵌便于文件携带，优先读取
- 批处理工具中：外部文件往往是用户精心编辑/下载的版本，应优先保留；内嵌可能是自动写入的低质量版本

## SPL 格式说明

SPL（Salt Player Lyrics）是基于增强型 LRC 的格式，支持：

- **逐字同步**：行内插入中间时间戳
  ```
  [05:20.22]你好[05:23.22]椒盐音乐[05:24.22]
  ```

- **显式结尾**：每行末尾标注结束时间
  ```
  [00:01.00]文本[00:02.00]
  ```

- **翻译行**：同时间戳，紧跟主歌词后（可省略时间戳）
  ```
  [00:01.00]こんにちは
  你好
  ```

详细规范：https://moriafly.com/standards/spl.html

## 命令行选项

| 选项 | 默认值 | 说明 |
|-----|-------|------|
| `--auto` | - | 自动接受最优结果，跳过交互确认 |
| `--dry-run` | - | 仅预览，不写入文件 |
| `--source` | `all` | 歌词来源：`netease` / `lrclib` / `musixmatch` / `all` |
| `--threshold` | `70.0` | 相似度阈值 (0-100)，**当前版本暂未生效** |
| `--lang` | `zh` | 翻译语言代码（仅 Musixmatch，需 API key） |
| `--prefer-local` | - | 优先使用本地歌词（默认优先在线） |

## 已知限制

### 相似度过滤暂时禁用
`syncedlyrics` 库只返回歌词文本，不返回匹配到的歌曲标题/艺术家，导致无法准确计算相似度。当前版本信任库的内部排序，`--threshold` 参数暂不生效。

**解决方案**：实现平台原生 API（见 TODO）。

### 不支持 byId 精确匹配
本地音乐文件无平台 ID，仅支持 byQuery（搜索匹配）。可能出现同名歌曲匹配错误。

**建议**：使用 `--dry-run` 预览后再批量写入。

### Musixmatch 翻译需要 API key
```bash
# 获取 token：https://developer.musixmatch.com/
export MUSIXMATCH_TOKEN="your_token_here"
python main.py song.mp3 --source musixmatch --lang zh
```

## 项目结构

```
lyricGeter/
├── main.py            # CLI 入口
├── scanner.py         # 扫描音乐文件、读取本地歌词
├── fetcher/
│   ├── base.py        # 抽象接口
│   └── synced.py      # syncedlyrics 封装
├── matcher.py         # 格式质量评分、策略调度
├── converter.py       # LRC → SPL 转换
├── writer.py          # 写入音频标签
└── ui.py              # 终端交互界面
```

## 贡献指南

欢迎 Issue 和 PR！优先方向见 [TODO.md](TODO.md)。

## 致谢

- [syncedlyrics](https://github.com/moehmeni/syncedlyrics) - 多平台歌词获取
- [mutagen](https://github.com/quodlibet/mutagen) - 音频标签操作
- [Salt Player](https://moriafly.com/) - SPL 格式规范
- 参考实现：example/lyricLoader.ts（TypeScript）

## 许可证

MIT
