# CLAUDE.md

Simplified Chinese only

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

**lyricGeter** 是一个 Python CLI 工具，流程如下：
1. 扫描本地音乐文件（MP3、FLAC 等），读取元数据（标题、艺术家）
2. 按优先级从多个来源获取歌词（网易云、QQ 音乐等），选出最优结果
3. 将歌词转换为 **SPL（Salt Player Lyrics）** 格式
4. 逐一写入文件，写入前展示预览并要求用户确认/编辑

## 设计原则

- **优先复用**：优先使用成熟的 Python 库（`mutagen` 读写音频标签、`syncedlyrics` 多源获取、`rapidfuzz` 相似度评分），不从零实现已有功能。
- **交互确认**：写入前展示 SPL 预览，用户可选择接受 / 跳过 / 手动编辑。
- **多源择优**：并行或按优先级查询多个平台，按格式质量（逐字 > 逐行同步 > 纯文本）和标题/艺术家相似度综合评分，取最优。

## 歌词获取逻辑（参考 `example/lyricLoader.ts`）

`lyricLoader.ts` 是已有实现，核心逻辑如下，Python 实现应对应参考：

| 概念 | 说明 |
|---|---|
| **本地优先** | 先检查音频文件内嵌歌词（embedded）和同目录外部 `.lrc`/`.spl` 文件 |
| **格式优先级** | `ttml > yrc/qrc/krc（逐字）> lrc（逐行同步）> 纯文本` |
| **平台策略** | `byId`（歌曲来自该平台，精确匹配）vs `byQuery`（跨平台，搜索后打分） |
| **智能在线升级** | 有本地歌词时，仅当在线能提供更高格式才发起请求 |
| **并行拉取** | `smartPreferOnline` 模式下并行请求所有候选平台，格式最优者覆盖 |
| **插件兜底** | 内置平台均无结果时，尝试第三方插件源 |
| **竞态保护** | 用递增 token 防止旧请求覆盖新结果 |

Python 实现映射：
- `readLocal` → `scanner.py` 读取内嵌/外部歌词
- `fetchFromPlatform` → `fetcher/<platform>.py` 各平台 API
- `tryOnlineByPreference` → `matcher.py` 策略调度
- `commit` → `writer.py` 写入标签
- `tryPluginFallback` → 暂不实现

## SPL 格式规范（来源：moriafly.com/standards/spl.html）

SPL 基于增强型 LRC，核心结构：

```
[mm:ss.xx]歌词文本
```

**时间戳规则**
- 格式：`[分:秒.毫秒]`，毫秒不足 3 位时后位补 0（`5` → 500ms）
- 分：1–3 位；秒：1–2 位（≤59）；毫秒：1–6 位

**三种行类型**
```
# 显式结尾（行末附结束时间戳）
[00:01.00]文本[00:02.00]

# 隐式结尾（结束时间 = 下一行开始时间）
[00:01.00]文本

# 重复行（多时间戳合并）
[00:01.00][00:05.00]文本
```

**逐字歌词**（行内插入中间时间戳，须严格递增）
```
[05:20.22]你好[05:23.22]椒盐音乐[05:24.22]
```

**延迟逐字**（`<>` 包裹，支持行到达但首字未开始）
```
[05:20.22]<05:21.22>你好<05:23.22>椒盐音乐[05:24.22]
```

**翻译**（同时间戳，主歌词在前，翻译紧跟其后，可省略时间戳）

将 SPL 内容写入音频标签：MP3 用 `USLT`，FLAC/Ogg 用 `LYRICS`（via `mutagen`）。

## 计划架构

```
lyricGeter/
├── main.py            # CLI 入口（click 或 argparse）
├── scanner.py         # 扫描音乐文件、读取内嵌/外部歌词（mutagen）
├── fetcher/
│   ├── base.py        # 抽象 LyricsFetcher 接口
│   ├── netease.py     # 网易云音乐
│   ├── qqmusic.py     # QQ 音乐
│   └── ...
├── matcher.py         # 格式质量 + 相似度综合评分，策略调度（参考 tryOnlineByPreference）
├── converter.py       # LRC/纯文本 → SPL 格式转换
├── writer.py          # 写入 SPL 到音频标签
└── ui.py              # 终端确认/编辑 UI（rich + questionary）
```

## 关键依赖

| 用途 | 推荐库 |
|---|---|
| 音频标签读写 | `mutagen` |
| 多源歌词获取（含网易云、QQ 音乐） | `syncedlyrics` |
| 终端 UI | `rich` + `questionary` |
| HTTP | `httpx` |
| 字符串相似度评分 | `rapidfuzz` |

```bash
pip install mutagen syncedlyrics rich questionary rapidfuzz httpx
```

## 开发命令

```bash
# 安装依赖
pip install -r requirements.txt

# 处理单个文件
python main.py song.mp3

# 处理目录
python main.py ~/Music/

# 跳过确认自动写入
python main.py song.mp3 --auto

# 预览匹配结果，不写入
python main.py song.mp3 --dry-run

# 指定来源
python main.py song.mp3 --source netease

# 运行测试
pytest

# 代码检查
ruff check .
```
