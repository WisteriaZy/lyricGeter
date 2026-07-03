# 翻译功能实现与修复记录

## 问题描述

网易云 API 返回的逐字歌词（YRC）和翻译歌词（tlyric）时间戳**不完全同步**，导致直接精确匹配无法合并翻译。

### 时间戳差异示例

**主歌词（逐字格式）**：
```
[30,1170](30,390,0)我(420,390,0)愛(810,390,0)你
```
- 行首时间戳：30ms

**翻译歌词（LRC 格式）**：
```
[00:00.30]我爱你
```
- 时间戳：300ms

**差异**：300ms - 30ms = **270ms**

## 解决方案

使用**容差匹配**（Tolerance Matching）算法，允许 ±500ms 的时间戳误差。

### 实现逻辑

```python
def _merge_translation_to_spl(spl_content: str, trans_lrc: str) -> str:
    # 1. 解析翻译 LRC，构建 [(时间戳, 翻译文本)] 列表
    trans_list: list[tuple[int, str]] = []
    for line in _parse_lrc(trans_lrc):
        if line.text.strip():
            trans_list.append((line.stamps[0], line.text.strip()))
    
    # 2. 遍历 SPL 主歌词每一行
    for spl_line in spl_content.splitlines():
        # 提取行首时间戳
        line_start_ms = _parse_ms(...)
        
        # 3. 容差匹配：找到最接近的翻译（±500ms 范围内）
        best_trans = None
        min_diff = 500  # 最大容差
        
        for trans_ms, trans_text in trans_list:
            diff = abs(trans_ms - line_start_ms)
            if diff < min_diff:
                min_diff = diff
                best_trans = trans_text
        
        # 4. 如果找到匹配的翻译，插入到主歌词后
        if best_trans:
            out_lines.append(best_trans)
```

## 测试验证

### 测试文件
- `input/我愛你-上海蟹- - カニ研究会.mp3`
  - ✅ 有逐字歌词
  - ✅ 有中文翻译

### 输出结果

```spl
[00:00.03]我<00:00.42>愛<00:00.81>你[00:01.32]
我爱你
[00:01.32]君<00:01.82>は<00:02.15>気<00:02.48>づ<00:02.80>い<00:02.96>て<00:03.14>な<00:03.41>い<00:03.58>で<00:03.84>し<00:03.98>ょ[00:06.48]
你没有注意到吧
[00:06.48]我<00:06.85>愛<00:07.23>你[00:07.64]
我爱你
```

**格式说明**：
- 主歌词行：`[行首]字<中间>字[行尾]`（SPL 延迟逐字标记）
- 翻译行：紧跟主歌词后，**无时间戳**（符合 SPL 标准）

## 关键修改

**文件**：`converter.py`

**函数**：`_merge_translation_to_spl()`

**修改前**：
```python
# 精确匹配（无容差）
if line_start_ms in trans_map:
    out_lines.append(trans_map[line_start_ms])
```

**修改后**：
```python
# 容差匹配（±500ms）
for trans_ms, trans_text in trans_list:
    diff = abs(trans_ms - line_start_ms)
    if diff < min_diff:
        min_diff = diff
        best_trans = trans_text

if best_trans:
    out_lines.append(best_trans)
```

## 覆盖场景

| 格式类型 | 翻译支持 | 测试状态 |
|---------|---------|---------|
| 网易云逐字（YRC） | ✅ 支持 | ✅ 已验证 |
| 网易云行级（LRC） | ✅ 支持 | ✅ 已验证 |
| 其他平台 | ✅ 支持 | 🔄 待测试 |

## 已知限制

1. **容差阈值**：当前设为 500ms，可能需要根据实际情况调整
2. **多语言翻译**：目前仅支持单一翻译（网易云 API 返回的 `tlyric` 字段）
3. **翻译质量**：依赖网易云用户上传的翻译，质量参差不齐

## 后续优化

- [ ] 支持多语言翻译（如同时显示英文+中文）
- [ ] 可配置的容差阈值
- [ ] 翻译质量评分与过滤

---

**更新时间**：2026-07-03  
**状态**：✅ 已完成并验证
