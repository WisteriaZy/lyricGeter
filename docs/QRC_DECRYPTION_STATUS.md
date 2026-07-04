# QQ 音乐 QRC 解密实现状态

**更新时间**：2026-07-04
**状态**：✅ 已完成 - QRC 解密成功，QQ 音乐逐字歌词功能可用

---

## 完成总结

QQ 音乐 QRC 逐字歌词已完整实现，三大平台（网易云 YRC、酷狗 KRC、QQ 音乐 QRC）的逐字歌词支持全部完成。

### 根因

之前的实现从 LDDC-Android (Kotlin) 移植，`inverse_permutation` 函数存在两处严重错误：

1. **字节排列顺序错误**：原实现按 `data[0]` 到 `data[7]` 顺序排列，正确顺序应为 `data[3], data[2], data[1], data[0], data[7], data[6], data[5], data[4]`
2. **s0/s1 交替顺序错误**：原实现是先 s0 后 s1（每 4 位一组），正确应为 s1 和 s0 交替

### 修复方案

发现 LDDC 实际有完整的 Python 实现（`example/LDDC-main/`），直接移植其 `tripledes.py` 的完整代码替换之前的 Kotlin 移植版本。同时重写 `fetcher/qqmusic.py` 对齐 LDDC 的同步 API 调用方式。

### 验证

- 端到端测试：Take Me Hand - DAISHI DANCE，获取 73 行逐字歌词 + 翻译
- SPL 转换：逐字时间戳和翻译行正确对齐
- 三大平台逐字歌词全覆盖：网易云 YRC + 酷狗 KRC + QQ 音乐 QRC

### 涉及文件

- `decryptor/qrc.py`：3DES-ECB 解密 + zlib 解压（直接移植 LDDC Python）
- `fetcher/qqmusic.py`：QQ 音乐 API 客户端（搜索 + 歌词获取，同步实现）
- `parser/qrc.py`：QRC 格式解析器（XML + LRC 兼容）
- `converter.py`：`_qrc_to_spl` 函数适配新的 LyricsLine 对象格式

---

## 参考资料

- **LDDC**：[github.com/chenmozhijin/LDDC](https://github.com/chenmozhijin/LDDC)
  Python 项目的完整 QRC/KRC/YRC 解密实现
- **3DES 算法**：[en.wikipedia.org/wiki/Triple_DES](https://en.wikipedia.org/wiki/Triple_DES)
- **DES S-Box**：S-Box 表是 DES 算法的核心
