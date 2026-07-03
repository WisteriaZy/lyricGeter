# 相似度过滤功能实现文档

## 概述

相似度过滤是 lyricGeter 的核心功能之一，用于解决歌词搜索不精确的问题（例如搜索"我愛你"却返回"你还要我怎样"）。

## 实现日期

2026-07-03

## 设计思路

### 问题背景

- 酷狗、网易云等平台的搜索 API 并非总是精确匹配
- 第三方库（如 `syncedlyrics`）不返回匹配歌曲的元数据，无法事后验证
- 需要一种机制来评估搜索结果的相关性

### 解决方案

1. **扩展 `LyricResult` 数据结构**
   - 添加 `matched_title` 和 `matched_artist` 字段
   - 记录平台实际返回的歌曲信息

2. **修改 Fetcher 返回值**
   - `NetEaseFetcher` 和 `KugouFetcher` 返回匹配歌曲信息
   - 为后续相似度计算提供数据

3. **在 `matcher.py` 中实现过滤逻辑**
   - 使用 `rapidfuzz.fuzz.WRatio` 计算相似度（0-100）
   - 默认阈值 70 分
   - 区分原生 API 和第三方库

## 技术细节

### 相似度算法

使用 `rapidfuzz.fuzz.WRatio`，计算用户查询和平台返回的相似度：

```python
def _similarity(title: str, artist: str, query_result: str) -> float:
    """用标题+艺术家与搜索词的相似度打分。"""
    combined = f"{title} {artist}".strip()
    return fuzz.WRatio(combined.lower(), query_result.lower())
```

**为什么选择 WRatio？**
- 对词序不敏感（"ANU 飞" vs "飞 ANU"）
- 容忍部分匹配（"FLY ANU" vs "飞 ANU"）
- 对长度差异有较好的鲁棒性

### 过滤策略

```python
# 原生 API（网易云、酷狗）：启用相似度过滤
if result.matched_title or result.matched_artist:
    result.score = _similarity(
        track.title,
        track.artist,
        f"{result.matched_title} {result.matched_artist}".strip()
    )
    if result.score < threshold:
        continue  # 过滤掉低相似度结果

# 第三方库（syncedlyrics）：信任其内部排序
else:
    result.score = 100.0
```

**设计权衡**：
- 原生 API 可以事后验证，因此启用过滤
- 第三方库黑盒，假设其内部已做优化，给予满分信任

### 阈值选择

- **默认值**：70 分
- **测试验证**：
  - 精确匹配：95-100 分（如"我愛你-上海蟹- カニ研究会"）
  - 部分匹配：70-95 分（如"飞 ANU" vs "FLY ANU"）
  - 完全不匹配：0-50 分（如"飞 ANU" vs "你还要我怎样 薛之谦"）

70 分的阈值在保证召回率的同时，有效过滤错误结果。

## 代码改动

### 1. `fetcher/base.py`

```python
@dataclass
class LyricResult:
    content: str | dict              # 主歌词（LRC/纯文本）或解析后的字典（KRC）
    format: LyricFormat
    source_name: str                 # 来源名称，如 "netease", "kugou"
    translation: str | None = None   # 翻译歌词
    matched_title: str = ""          # 平台返回的歌曲标题（用于相似度评分）
    matched_artist: str = ""         # 平台返回的艺术家（用于相似度评分）
    score: float = 0.0               # rapidfuzz 相似度分 (0-100)
```

### 2. `fetcher/netease.py`

- `_search_song()` 返回字典：`{"id": int, "title": str, "artist": str}`
- `_get_lyrics()` 接收 `matched_title` 和 `matched_artist` 参数
- `LyricResult` 填充匹配信息

### 3. `fetcher/kugou.py`

- `KugouFetcher.search()` 填充 `matched_title` 和 `matched_artist`
- 使用搜索结果中的歌曲信息

### 4. `matcher.py`

- 启用相似度计算逻辑（之前被注释掉）
- 区分原生 API 和第三方库

## 测试验证

### 测试脚本：`test_similarity.py`

测试覆盖：
1. 相似度计算函数的正确性
2. 阈值过滤逻辑
3. 不同匹配程度的得分范围

### 实际测试结果

```
✓ 标题: 我愛你-上海蟹-, 艺术家: カニ研究会
  匹配结果: 我愛你-上海蟹- カニ研究会
  相似度: 100.0 (预期: 95-100)

✓ 标题: 飞, 艺术家: ANU
  匹配结果: FLY ANU
  相似度: 71.2 (预期: 70-95)

✓ 标题: 飞, 艺术家: ANU
  匹配结果: 你还要我怎样 薛之谦
  相似度: 20.0 (预期: 0-50)
```

### 端到端测试

```bash
# 网易云测试（精确匹配）
python main.py "input/我愛你-上海蟹- - カニ研究会.mp3" --dry-run --auto
# 结果：相似度 100

# 酷狗测试（部分匹配）
python main.py "input/飞 - ANU.mp3" --dry-run --auto --no-netease
# 结果：相似度 90，成功过滤无关结果
```

## 用户体验改进

### 预览界面显示相似度

```
╭─────── 我愛你-上海蟹-  —  カニ研究会 来源: netease  逐字  相似度: 100 ───────╮
│ [00:00.03]我<00:00.42>愛<00:00.81>你[00:01.32]                               │
│ ...                                                                          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

用户可以直观看到匹配质量，决定是否接受。

### 日志输出

```python
# matcher.py 中的调试信息（可选）
print(f"[{result.source_name}] 相似度: {result.score:.1f} - {result.matched_title}")
```

## 后续优化方向

### 1. CLI 参数支持

```bash
# 自定义阈值
python main.py song.mp3 --threshold 80

# 显示被过滤的结果（调试模式）
python main.py song.mp3 --show-filtered
```

### 2. 多字段加权

当前只使用标题+艺术家，未来可以加入：
- 专辑名称
- 发行年份
- 歌曲时长

### 3. 容错匹配

- 繁简体转换（"我爱你" vs "我愛你"）
- 全半角转换（"FLY" vs "ＦＬＹ"）
- 音译匹配（"ANU" vs "阿牛"）

### 4. 用户反馈学习

记录用户接受/拒绝的决策，调整阈值和权重。

## 相关文件

- `fetcher/base.py` - 数据结构定义
- `fetcher/netease.py` - 网易云实现
- `fetcher/kugou.py` - 酷狗实现
- `matcher.py` - 匹配逻辑
- `test_similarity.py` - 测试脚本
- `TODO.md` - 任务清单

## Git 提交

- `fe86281`: feat: 实现相似度过滤功能
- `0613c66`: docs: 更新 TODO - 标记相似度过滤完成

## 总结

相似度过滤功能已经完整实现并通过测试，成功解决了搜索不精确的问题。核心优势：

1. **准确性**：使用 WRatio 算法，对各种匹配场景表现良好
2. **灵活性**：区分原生 API 和第三方库，采用不同策略
3. **可维护性**：清晰的数据流和职责分离
4. **用户体验**：界面显示相似度，便于决策

下一步可以开始 QQ 音乐 QRC 支持的开发。
