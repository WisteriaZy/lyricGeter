# AGENTS.md

**仅使用简体中文回复**

本文件为 Codex（Codex.ai/code）提供项目上下文和开发指南。

注意终端环境为PowerShell,此外注意中文编码问题

## 项目定位

**lyricGeter** 是一个 **离线批量歌词嵌入工具**，面向本地播放器用户（Salt Player、foobar2000），为音乐库批量添加高质量同步歌词。

**当前状态（2026-07-04）**：
- ✅ 网易云 API 完整实现，支持逐字歌词（YRC）+ 翻译
- ✅ 酷狗 API 完整实现，支持逐字歌词（KRC）+ 翻译 + 罗马音
- ✅ QQ 音乐 QRC 完整实现，支持逐字歌词（QRC）+ 翻译 + 罗马音
- ✅ AMLL TTML 数据库支持，通过歌曲 ID 获取 TTML 逐字歌词 + 翻译
- ✅ 相似度过滤恢复正常（网易云、酷狗、QQ 音乐启用，阈值 70）
- ✅ SPL 格式转换完全符合官方标准

### 核心价值

- **批量处理**：整个目录一次处理完，而非播放时实时获取
- **逐字优先**：主动获取 Word-level 逐字同步歌词（网易云 YRC、酷狗 KRC、QQ 音乐 QRC、AMLL TTML）
- **人工确认**：写入前预览 + 可编辑，避免错配和覆盖优质本地歌词
- **SPL 标准**：输出符合 [Salt Player Lyrics 规范](https://moriafly.com/standards/spl.html)

### 与播放器歌词加载的关键区别

本工具是**批量预处理工具**，不是播放器插件，设计思路不同：

| 对比维度 | 播放器内歌词加载（如 `lyricLoader.ts`） | lyricGeter（本项目） |
|---------|----------------------------------------|---------------------|
| **使用场景** | 播放时实时加载，立即展示 | 批量预处理，一次性完成整个音乐库 |
| **交互模式** | 自动后台获取，无需人工介入 | 逐文件确认 + 可编辑，防止错配 |
| **本地优先级** | 内嵌 > 外部文件（内嵌便于携带） | **外部 > 内嵌**（外部是用户手动放置，优先尊重） |
| **平台策略** | byId（歌曲来自平台，精确匹配）+ byQuery | **仅 byQuery**（本地文件无平台 ID） |
| **智能升级** | 有本地歌词时，仅当在线格式更优才请求 | **总是请求在线**，由用户决定是否覆盖 |
| **TTML 支持** | 异步加载叠加层，运行时解析 | **转换为 SPL**，一次写入（✅ AMLL 数据库） |

**关键差异：文件内嵌优先级最低**  
播放器中内嵌歌词便于携带（文件移动时歌词跟随），因此优先读取。但批处理工具中，外部 `.lrc`/`.spl` 文件通常是用户手动编辑或下载的精校版本，应优先保留，内嵌歌词仅作兜底。

**参考实现**：`example/lyricLoader.ts` 是播放器内逻辑，本项目仅借鉴其格式优先级和策略思路，但执行逻辑完全不同。

## 设计原则

### 1. 优先复用成熟库

- **音频标签**：`mutagen`（读写 MP3/FLAC/Ogg 标签）
- **歌词获取**：`syncedlyrics`（多平台封装）
- **终端 UI**：`rich`（彩色输出）+ `questionary`（交互）
- **相似度评分**：`rapidfuzz`（字符串匹配）

**不从零实现已有功能**，除非现有库无法满足需求。

### 2. 交互确认为核心

写入前必须展示 SPL 预览，用户可选择：
- **接受**：直接写入
- **选择翻译来源合并**：从其他候选中挑翻译叠加到当前歌词（跨源翻译合并）
- **跳过**：忽略此文件
- **编辑**：在 `$EDITOR` 中手动修改
- **退出**：终止程序

支持 `--auto` 模式跳过交互，用于信任度高的场景。

**跨源翻译合并**：当某个候选有逐字歌词但无翻译、另一个候选有翻译时，
用户可选择将翻译合并到逐字歌词中。合并算法优先用时间戳容差匹配（±2000ms），
匹配率低于 30% 时自动回退到顺序匹配（按行号 1:1 对齐），解决跨平台时间戳偏移问题。

### 3. 外部歌词优先于内嵌（与播放器相反）

本地歌词检测顺序：
1. 同目录同名 `.lrc` / `.spl` 文件（**外部，最优先**）
2. 音频文件内嵌歌词标签（**内嵌，优先级最低**）

**为何与播放器相反？**
- **播放器场景**：内嵌便于携带（文件移动时歌词跟随），优先读取
- **批处理场景**：外部 `.lrc`/`.spl` 往往是用户手动下载或编辑的精校版，应优先保留；内嵌歌词可能是自动写入的低质量版本

### 4. 格式质量优先级

```
逐字（WORD）> 行级同步（LINE）> 纯文本（PLAIN）
```

对应枚举值：`LyricFormat.WORD = 0 < LINE = 1 < PLAIN = 2`（值越小越优）

## 项目架构

```
lyricGeter/
├── main.py            # CLI 入口（click）
├── scanner.py         # 扫描音乐文件、读取内嵌/外部歌词
├── fetcher/
│   ├── base.py        # 抽象 LyricsFetcher 接口
│   ├── synced.py      # syncedlyrics 封装（兑底）
│   ├── netease.py     # 网易云原生 API（YRC 逐字）
│   ├── kugou.py       # 酷狗原生 API（KRC 逐字）
│   ├── qqmusic.py     # QQ 音乐原生 API（QRC 逐字）
│   ├── amll.py        # AMLL TTML 数据库获取器
│   └── __init__.py
├── parser/
│   ├── yrc.py         # 网易云逐字格式解析
│   ├── krc.py         # 酷狗逐字格式解析
│   ├── qrc.py         # QQ 音乐逐字格式解析
│   ├── ttml.py        # TTML 格式解析（AMLL 数据库）
│   ├── json_lyric.py  # 网易云 JSON 歌词格式
│   └── __init__.py
├── matcher.py         # 格式质量评分、策略调度
├── converter.py       # LRC/YRC/KRC/QRC/TTML → SPL 格式转换
├── writer.py          # 写入 SPL 到音频标签
├── ui.py              # 终端确认/编辑界面
└── example/
    └── lyricLoader.ts # TypeScript 参考实现（仅供参考）
```

## SPL 格式规范

SPL 基于增强型 LRC，核心结构：

```
[mm:ss.xx]歌词文本
```

### 时间戳规则

- 格式：`[分:秒.毫秒]`
- 分：1–3 位
- 秒：1–2 位（≤59）
- 毫秒：1–6 位，不足 3 位时**后位补 0**（`5` → `500ms`）

### 三种行类型

```spl
# 1. 显式结尾（行末附结束时间戳）
[00:01.00]文本[00:02.00]

# 2. 隐式结尾（结束时间 = 下一行开始时间）
[00:01.00]文本

# 3. 重复行（多时间戳合并）
[00:01.00][00:05.00]文本
```

### 逐字歌词（行内插入中间时间戳）

时间戳必须**严格递增**，否则降级为行级格式：

```spl
[05:20.22]你好[05:23.22]椒盐音乐[05:24.22]
```

### 延迟逐字（`<>` 包裹）

支持行到达但首字未开始的场景：

```spl
[05:20.22]<05:21.22>你好<05:23.22>椒盐音乐[05:24.22]
```

### 翻译行

同时间戳，主歌词在前，翻译紧跟其后（可省略时间戳）：

```spl
[00:01.00]こんにちは
你好
```

### 标签写入

- **MP3**：`USLT` (ID3v2)
- **FLAC / Ogg**：`lyrics` (Vorbis Comment)

使用 `mutagen` 操作，写入前自动备份原歌词到 `.lrc.bak`。

## 核心模块说明

### `scanner.py` - 音乐文件扫描

**职责**：
- 扫描文件/目录，返回 `TrackInfo` 列表
- 读取音频元数据（标题、艺术家）
- 检测内嵌歌词和外部 `.lrc`/`.spl` 文件
- 判断歌词格式（逐字/行级/纯文本）

**关键逻辑**：
- `best_local_lyric` 属性返回**外部优先于内嵌**的本地歌词
- 格式检测：行内多个时间戳 → 逐字；单个时间戳 → 行级；无时间戳 → 纯文本

### `fetcher/` - 歌词获取

**抽象接口** (`base.py`)：
```python
class LyricsFetcher(ABC):
    @abstractmethod
    def search(self, title: str, artist: str) -> LyricResult | None:
        """搜索歌词，失败返回 None。"""
```

**当前实现** (`synced.py`)：
- 封装 `syncedlyrics` 库
- 支持网易云、Lrclib、Musixmatch
- 并行获取主歌词 + 翻译（ThreadPoolExecutor）
- 自动检测逐字格式（行内两个或以上时间戳）

**已知限制**：
- `syncedlyrics` 只返回歌词文本，**不返回匹配到的歌曲元数据**
- 无法计算准确的相似度（因为不知道匹配到的歌曲标题/艺术家）
- 当前版本**暂时禁用相似度过滤**，信任库的内部排序

**TODO**：
- 实现平台原生 API（`fetcher/netease.py` 等），返回完整搜索结果
- 支持 YRC/QRC/KRC 等平台专有逐字格式

### `matcher.py` - 策略调度

**职责**：
- 调用多个 fetcher，按格式质量排序
- 处理 `prefer_local` 逻辑（优先本地 vs 优先在线）
- 返回最优 `LyricResult`

**核心参数**：
- `prefer_local=False`（默认）：优先在线，本地仅作兜底
- `prefer_local=True`：有本地逐字歌词时跳过在线，否则查询

**已知问题**：
- 相似度过滤暂时禁用（见 `fetcher/` 说明）
- `threshold` 参数保留但不生效

### `converter.py` - SPL 转换

**职责**：
- LRC/YRC/KRC/QRC/TTML → SPL 格式转换
- 补全显式结尾时间戳（每行 end = 下一行 start）
- 逐字时间戳严格递增校验（不合格降级为行级）
- 翻译行合并（时间戳容差匹配 ±2000ms + 顺序匹配回退）
- 跨源翻译提取与合并（支持网易云 LRC 和酷狗 KRC 两种翻译来源）
- AMLL TTML → SPL：逐字 span 转 SPL 逐字格式，翻译行紧跟主歌词行

**关键函数**：
- `_parse_lrc(lrc: str) -> list[_LrcLine]`：解析 LRC 行首时间戳
- `_validate_word_level(text: str) -> bool`：校验逐字时间戳递增
- `to_spl(result: LyricResult) -> str`：主转换函数
- `extract_translation_lrc(result: LyricResult) -> str | None`：从任意来源提取翻译 LRC 文本
- `merge_translation(spl: str, translation_lrc: str) -> str`：跨源翻译合并（时间戳匹配为主，顺序匹配回退）

### `writer.py` - 标签写入

**职责**：
- 写入 SPL 到音频文件标签
- 自动备份原有歌词到 `.lrc.bak`
- 支持 MP3/FLAC/Ogg 多格式

**注意**：
- 写入前必须调用 `ui.confirm()` 获取用户确认
- `existing_lyric` 参数用于触发备份

### `ui.py` - 终端交互

**职责**：
- 用 `rich` 渲染 SPL 预览（时间戳高亮）
- 用 `questionary` 实现选择菜单
- 支持在 `$EDITOR` 中手动编辑

**返回值**：
- `str` → 用户接受的 SPL 内容（可能经过编辑）
- `None` → 用户跳过此文件
- 抛出 `SystemExit` → 用户选择退出

## CLI 参数设计

### 歌词来源控制

```bash
--netease / --no-netease      # 启用/禁用网易云（默认启用）
--kugou / --no-kugou          # 启用/禁用酷狗（默认启用）
--qqmusic / --no-qqmusic    # 启用/禁用 QQ 音乐（默认启用）
--amll / --no-amll          # 启用/禁用 AMLL TTML 数据库（默认启用）
--source [netease|lrclib|musixmatch|all]  # syncedlyrics 来源（默认 all）
```

**设计理念**：
- 使用正向参数（`--netease`）而非排除项（`--no-netease`），更直观
- 网易云、酷狗、QQ 音乐、AMLL 默认启用
- AMLL 优先级最高（先搜索网易云/QQ音乐获取歌曲 ID，再从 AMLL DB 下载 TTML）
- `--source` 控制 syncedlyrics 的第三方来源（lrclib、musixmatch 等）

### 交互模式

```bash
--auto        # 自动模式：按权重选择最优结果（格式优先 > 相似度）
--dry-run     # 预览模式：只展示匹配结果，不写入文件
```

**两种工作流**：

1. **交互模式（默认）**：逐文件选择 + 操作循环
   - 第一步：从所有候选中选择（netease、kugou、local 等）
   - 第二步：预览选中歌词（前 30 行，语法高亮）
   - 第三步：操作循环——接受 / 选择翻译来源合并 / 返回重选 / 手动编辑 / 再次搜索 / 跳过 / 退出
     - 合并翻译后重新渲染预览，可继续操作（多次合并或编辑）

2. **自动模式（`--auto`）**：按权重直接写入
   - 排序规则：`(format.value, -score)`
   - 格式优先：逐字 > 行级同步 > 纯文本
   - 相似度次之：分数越高越优

**非交互环境回退**：
- 检测到 `sys.stdin.isatty() == False` 或 `questionary` 失败时自动切换到简单文本输入
- 若文本输入也失败（如 CI 环境），自动回退到 auto 模式

### 其他参数

```bash
--threshold FLOAT    # 相似度阈值 0-100（默认 70.0）
--lang TEXT          # 翻译语言代码（默认 zh，留空则不获取翻译）
--prefer-local       # 优先使用本地内嵌歌词（默认优先在线）
```

## 开发命令

```bash
# 安装依赖
pip install -r requirements.txt

# 处理单个文件（交互模式）
python main.py song.mp3

# 处理目录
python main.py ~/Music/

# 自动模式（跳过确认）
python main.py song.mp3 --auto

# 预览模式（不写入）
python main.py song.mp3 --dry-run

# 仅使用网易云
python main.py song.mp3 --no-kugou --source netease

# 优先本地歌词
python main.py song.mp3 --prefer-local

# 运行测试（TODO：待实现）
pytest

# 代码检查
ruff check .
ruff format .
```

## 当前状态

### ✅ 已完成

- [x] 基础 CLI 框架
- [x] 音频文件扫描和元数据读取
- [x] 多源歌词获取（via syncedlyrics）
- [x] SPL 格式转换
- [x] 交互式预览和确认
- [x] 标签写入和备份
- [x] 外部歌词优先级调整

### ⚠️ 已知限制

1. **相似度过滤已恢复正常**
   - **现状**：网易云和酷狗原生 API 返回匹配歌曲信息，启用相似度评分（默认阈值 70）
   - **局限**：Lrclib、Musixmatch 第三方库不返回匹配信息，信任其内部排序

2. **不支持 byId 精确匹配**
   - **原因**：本地音乐文件不携带平台 ID（网易云歌曲 ID、QQ 音乐 mid 等）
   - **影响**：只能用 byQuery（标题+艺术家搜索），匹配准确度低于播放器内加载
   - **缓解**：使用 `--dry-run` 预览匹配结果，批量写入前检查错配

3. **逐字歌词覆盖率依赖平台**
   - **现状**：网易云 YRC + 酷狗 KRC + QQ 音乐 QRC + AMLL TTML 已完整实现
   - **原因**：部分歌曲仅提供行级同步歌词，即使原生平台也无逐字版本
   - **改进**：四大平台互补，提高逐字覆盖率；AMLL TTML 数据库提供社区人工校验的高质量歌词

### 🚧 下一步（P0 任务）

见 [TODO.md](TODO.md) 和相关技术文档，当前优先级：

1. **✅ 网易云 YRC 支持**（已完成 2026-07-03）
2. **✅ 酷狗 KRC 支持**（已完成 2026-07-03）
3. **✅ 相似度过滤恢复**（已完成 2026-07-03）
4. **✅ QQ 音乐 QRC 支持**（已完成 2026-07-04）
5. **✅ AMLL TTML 数据库支持**（已完成 2026-07-04）
6. **📋 项目文档完善**（进行中）
   - [ ] 更新 README 和 AGENTS.md
   - [ ] 清理调试文件
   - [ ] 提交代码到版本控制
7. **📋 用户文档**（下一步）
   - [ ] 添加使用截图
   - [ ] 编写常见问题解答
   - [ ] 补充贡献指南

## 编码规范

### 类型注解

所有公开函数必须有完整类型注解：

```python
def search(self, title: str, artist: str) -> LyricResult | None:
    """搜索歌词，失败返回 None。"""
```

### 错误处理

- 网络请求失败 → 返回 `None`，由调用方决定是否重试
- 文件 IO 错误 → `try-except` 捕获，记录日志但不中断批处理
- 用户退出 → 抛出 `SystemExit(0)`

### 日志输出

- 使用 `rich.Console` 输出彩色日志
- 错误信息用 `err_console`（红色 stderr）
- 进度条用 `Progress`，`transient=False` 避免覆盖错误信息

### 文件编码

Windows 终端默认 GBK，`main.py` 开头强制 UTF-8：

```python
if sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
```

## 调试技巧

### 查看 syncedlyrics 原始返回

```python
import syncedlyrics
lrc = syncedlyrics.search("title artist", providers=["NetEase"], enhanced=True)
print(lrc)
```

### 测试单个文件

```bash
python main.py input/song.mp3 --dry-run --source netease
```

### 检查 SPL 格式

```python
from converter import to_spl
from fetcher.base import LyricResult, LyricFormat

result = LyricResult(content="[00:01.00]test", format=LyricFormat.LINE, source_name="test")
spl = to_spl(result)
print(spl)
```

## 贡献指南

1. Fork 项目并创建功能分支
2. 保持代码风格一致（`ruff format`）
3. 补充单元测试（如果修改核心逻辑）
4. 更新文档（README.md / TODO.md / AGENTS.md）
5. 提交 PR，说明改动原因和测试结果

欢迎认领 TODO.md 中的任务！
