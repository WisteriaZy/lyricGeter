# 酷狗 KRC 支持实现总结

**日期**: 2026-07-03  
**提交**: 4ce7e6d

---

## 实现概述

成功添加酷狗音乐 KRC 格式逐字歌词支持，包括解密、解析、API 调用和 SPL 转换完整流程。

---

## 新增文件

### 1. `decryptor/krc.py` - KRC 解密器

**加密流程（逆向）**：
```
明文 → zlib 压缩 → XOR 加密（密钥：@Gaw^2tGQ61-Íni）→ 加上 4 字节 magic header → Base64 编码
```

**解密步骤**：
1. Base64 解码
2. 跳过前 4 字节 magic header
3. XOR 解密（16 字节循环密钥）
4. zlib 解压
5. UTF-8 解码

**关键代码**：
```python
KRC_KEY = bytes([
    0x40, 0x47, 0x61, 0x77,  # @Gaw
    0x5e, 0x32, 0x74, 0x47,  # ^2tG
    0x51, 0x36, 0x31, 0x2d,  # Q61-
    0xce, 0xd2, 0x6e, 0x69   # Íni
])

for i in range(len(encrypted_data)):
    decrypted_data[i] = encrypted_data[i] ^ KRC_KEY[i % len(KRC_KEY)]
```

### 2. `parser/krc.py` - KRC 解析器

**KRC 格式**：
```
[开始时间ms,持续时间ms]<相对偏移ms,持续ms,0>字<...>
```

**关键特征**：
- 行时间戳：`[start, duration]`
- 逐字时间戳：`<offset, duration, reserved>` —— offset 是**相对行开始的偏移**
- 元数据标签：`[key:value]`
- 翻译/罗马音：`[language:BASE64编码的JSON]`

**language 标签结构**：
```json
{
  "content": [
    {"type": 0, "lyricContent": [[罗马音1, 罗马音2, ...], ...]},  // 罗马音
    {"type": 1, "lyricContent": [[翻译1], [翻译2], ...]}         // 翻译
  ]
}
```

**解析输出**：
```python
{
    "orig": [LyricsLine(...)],  # 原文
    "ts": [LyricsLine(...)],    # 翻译（可选）
    "roma": [LyricsLine(...)]   # 罗马音（可选）
}
```

### 3. `fetcher/kugou.py` - 酷狗 API 客户端

**API 流程（两步获取）**：

**步骤 1: 搜索歌曲**
```
GET http://mobilecdn.kugou.com/api/v3/search/song
参数: keyword, page, pagesize, signature（MD5 签名）
返回: hash, title, artist, album, duration
```

**步骤 2: 搜索歌词候选**
```
GET https://krcs.kugou.com/search
参数: hash, clienttime, mid, signature
返回: id, accesskey
```

**步骤 3: 下载加密歌词**
```
GET http://lyrics.kugou.com/download
参数: id, accesskey, fmt=krc, charset=utf8
返回: content（Base64 编码的加密 KRC）
```

**签名算法**：
```python
SIGNATURE_KEY = "LnT6xpN3khm36zse0QzvmgTZ3waWdRSA"
sorted_params = sorted(params.items())
param_str = ''.join(f"{k}={v}" for k, v in sorted_params)
signature = md5(f"{SIGNATURE_KEY}{param_str}{SIGNATURE_KEY}")
```

**KugouFetcher 适配器**：
- 实现 `LyricsFetcher` 接口
- 返回 `LyricResult` 结构，content 是解析后的字典（不是字符串）
- 自动检测是否有逐字时间戳

### 4. `converter.py` - SPL 转换扩展

**新增函数**: `_krc_to_spl(lyrics_data, has_translation)`

**转换规则**：
- 行首时间戳：`[]`
- 中间逐字时间戳：`<>`（SPL 延迟逐字标记）
- 行尾时间戳：`[]`（下一行开始时间）
- 翻译行：紧跟主歌词，无时间戳

**示例输出**：
```
[00:00.00]ANU <00:00.14>- <00:00.29>FLY[00:00.44]
[00:21.26]འ<00:21.47>ཕ<00:21.64>ུ<00:21.78>ར[00:22.70]
飞
```

### 5. `main.py` - 集成到主流程

**新增选项**：
```bash
--no-kugou  # 禁用酷狗 API（默认启用）
```

**优先级顺序**：
1. 网易云 API（`--no-netease` 禁用）
2. 酷狗 API（`--no-kugou` 禁用）
3. syncedlyrics（兜底）

**调用示例**：
```bash
# 使用所有来源（默认）
python main.py song.mp3 --dry-run

# 只使用酷狗
python main.py song.mp3 --no-netease --dry-run

# 禁用酷狗
python main.py song.mp3 --no-kugou --dry-run
```

---

## 测试结果

### 测试用例 1: 藏文歌曲（带翻译）
**文件**: `input/飞 - ANU.mp3`  
**结果**:
- ✅ 搜索成功：FLY-飞 - ANU
- ✅ 获取 KRC 成功：67 行
- ✅ 逐字时间戳：100% 覆盖
- ✅ 翻译：67 行中文翻译
- ✅ SPL 转换：正确使用 `<>` 标记

**SPL 预览**：
```
[00:00.00]ANU <00:00.14>- <00:00.29>FLY[00:00.44]
[00:21.26]འ<00:21.47>ཕ<00:21.64>ུ<00:21.78>ར[00:22.70]
飞
[00:22.70]འ<00:22.89>ཕ<00:23.06>ུ<00:23.22>ར<00:23.35>་<00:23.48>འ<00:23.64>ད<00:23.76>ོ<00:23.91>ད<00:24.04>་<00:24.16>ད<00:24.29>ུ<00:24.44>ས<00:24.56>།[00:25.81]
当你想展翅翱翔之时
```

### 测试用例 2: 日文歌曲（VOCALOID）
**文件**: `input/CHO-DARI- - 23.exe, 初音ミク.mp3`  
**结果**:
- ✅ 搜索成功（禁用网易云后）
- ✅ 获取 KRC 成功：52 行
- ✅ 逐字时间戳：日文假名级别精度
- ✅ SPL 转换：正确处理假名和汉字

**SPL 预览**：
```
[00:14.07]ヤ<00:14.22>リ<00:14.41>タ<00:14.54>カ<00:14.66>ネ<00:14.83>ー<00:15.23>ヤ<00:15.35>リ<00:15.47>タ<00:15.61>カ<00:15.77>ネ<00:15.92>ー[00:16.36]
[00:16.36]楽<00:16.55>し<00:16.71>い<00:17.09>を<00:17.29>蹴<00:17.57>っ<00:17.71>て<00:17.85>得<00:17.98>る<00:18.25>は<00:18.38>し<00:18.53>た<00:18.66>金[00:20.04]
```

### 测试用例 3: 优先级测试
**文件**: `input/我愛你-上海蟹- - カニ研究会.mp3`  
**结果**:
- ✅ 网易云先返回（优先级生效）
- ✅ 酷狗作为备选可用
- ✅ 多源策略正常工作

---

## 技术亮点

### 1. 相对时间戳转换
KRC 的逐字时间戳是**相对行开始的偏移**，需转换为绝对时间：
```python
word_start = line_start + word_offset  # 绝对时间
```

### 2. 翻译对齐
酷狗的翻译已嵌入 KRC 数据结构（`language` 标签），按行索引对齐：
```python
if has_translation and i < len(ts_lines):
    ts_text = ts_lines[i].words[0].text
    out_lines.append(ts_text)  # 紧跟主歌词，无时间戳
```

### 3. SPL 兼容性
严格遵守 SPL 格式规范：
- 行首/行尾：`[mm:ss.xx]`
- 中间逐字：`<mm:ss.xx>`（延迟逐字标记）
- 翻译行：省略时间戳

### 4. 类型安全
`LyricResult.content` 在 KRC 场景下传递字典结构，而非字符串：
```python
if isinstance(result.content, dict) and 'orig' in result.content:
    return _krc_to_spl(result.content, has_translation)
```

---

## 与网易云 YRC 的对比

| 特性 | 网易云 YRC | 酷狗 KRC |
|------|-----------|---------|
| **逐字精度** | 中文：字级别<br>日文：假名级别 | 中文：字级别<br>日文：假名级别 |
| **翻译支持** | 独立 LRC 文件<br>需容差匹配（±500ms） | 内嵌 JSON<br>索引对齐（精确） |
| **罗马音** | ❌ 不支持 | ✅ 支持（type=0） |
| **加密方式** | EAPI（AES-ECB + 自定义填充） | XOR + zlib（较简单） |
| **API 稳定性** | 高（官方接口） | 中（逆向接口） |
| **覆盖率** | 高（华语流行） | 高（全语言） |

---

## 已知限制

### 1. 搜索精度
- 酷狗搜索不如网易云精确（如"我愛你"搜到"你还要我怎样"）
- 需后续添加相似度评分过滤（rapidfuzz）

### 2. 罗马音未使用
- 解析器已支持罗马音（`lyrics_data['roma']`）
- 但 SPL 转换器暂未集成（TODO: 考虑作为第三行输出）

### 3. API 限流风险
- 无请求间隔控制
- 高频请求可能触发限流
- TODO: 添加重试机制和指数退避

---

## 后续计划

### P0 - 本周完成
- [ ] 恢复相似度过滤（在 `KugouFetcher.search()` 中返回歌曲元数据）
- [ ] 添加更多测试用例（中文流行、英文、韩文）
- [ ] 更新 README 和用户文档

### P1 - 下周
- [ ] QQ 音乐 QRC 支持（3DES-ECB + zlib，难度 ⭐⭐⭐⭐）
- [ ] 请求间隔和重试机制
- [ ] 缓存机制（避免重复请求）

### P2 - 优化
- [ ] 罗马音输出选项（`--include-romaji`）
- [ ] 性能优化（并行请求多个平台）
- [ ] 日志系统（`--verbose`）

---

## 参考资源

- **LDDC-Android 项目**: https://github.com/chenmozhijin/LDDC
  - `KugouApi.kt`: API 调用和签名算法
  - `KrcDecryptor.kt`: XOR 解密密钥
  - `KrcParser.kt`: 解析逻辑和 language 标签处理
- **SPL 格式规范**: `docs/SPL 格式（Salt Player Lyrics）语法标准.md`
- **酷狗 API 文档**: 无官方文档，完全逆向

---

## 提交信息

```
feat: 添加酷狗 KRC 逐字歌词支持

- 新增 decryptor/krc.py：KRC 解密器（Base64 + XOR + zlib）
- 新增 parser/krc.py：KRC 解析器（支持逐字、翻译、罗马音）
- 新增 fetcher/kugou.py：酷狗 API 客户端 + LyricsFetcher 适配器
- 扩展 converter.py：添加 _krc_to_spl() 转换函数
- 更新 main.py：添加 --no-kugou 选项，默认启用酷狗 API
- 新增 test_krc.py：KRC 功能测试脚本

特性：
- 支持逐字时间戳（延迟逐字标记 <>）
- 支持翻译（紧跟主歌词，无时间戳）
- 支持罗马音（可选）
- 兼容 SPL 格式规范

测试通过：
- input/飞 - ANU.mp3：藏文歌曲，67 行逐字 + 翻译
- input/CHO-DARI- - 23.exe, 初音ミク.mp3：日文歌曲，52 行逐字

参考：LDDC-Android KugouApi.kt, KrcDecryptor.kt, KrcParser.kt
```

**Commit Hash**: `4ce7e6d`
