# QQ 音乐 QRC 解密实现状态

**更新时间**：2026-07-03  
**状态**：⚠️ 阻塞中 - 解密算法调试未完成

---

## 已完成工作 ✅

### 1. QQ 音乐 API 集成 (`fetcher/qqmusic.py`)
- ✅ Session 初始化（`GetSession`）
- ✅ 歌曲搜索（`DoSearchForQQMusicDesktop` + `music.search.SearchCgiService`）
- ✅ 歌词获取（`GetPlayLyricInfo` + `music.musichallSong.PlayLyricInfo`）
- ✅ 支持原文、翻译、罗马音三路歌词

**关键修复**：
- 使用 Base64 编码歌曲信息（title, artist, album）
- 传递完整 `song_info` 对象而非单独字段

### 2. QRC 格式解析器 (`parser/qrc.py`)
- ✅ 支持 XML 格式的 QRC 歌词解析
- ✅ 解析格式：`[行开始ms,行持续ms]文字(字开始ms,字持续ms)...`
- ✅ 智能检测 XML/纯文本格式（`parse_smart`）

### 3. SPL 转换 (`converter.py`)
- ✅ 实现 `_qrc_to_spl()` 函数
- ✅ 支持逐字时间戳转换
- ✅ 支持翻译和罗马音

### 4. 自定义 3DES 实现 (`decryptor/qrc.py`)
完整移植了 LDDC-Android 的自定义 3DES-ECB 实现：

- ✅ 8 组 S-Box 表（每组 64 个元素）
- ✅ 初始置换（Initial Permutation）- 64 位位重排
- ✅ 逆置换（Inverse Permutation）- 恢复原始字节顺序
- ✅ F 函数（Feistel function）- 扩展置换 + S-Box 替换 + P-Box 置换
- ✅ 密钥调度（Key Schedule）- 生成 16 轮子密钥
- ✅ 3DES 模式（DES-EDE3）- 加密-解密-加密三次迭代
- ✅ 位操作工具函数：
  - `_bitnum(data, bit, pos)` - 从字节数组提取位（特殊索引计算）
  - `_bitnum_intl(data, bit, pos)` - 从整数提取位（左起编号）
  - `_bitnum_intr(data, bit, pos)` - 从整数提取位（右起编号）
  - `_sbox_bit(value)` - S-Box 索引转换

**关键修复历史**：
1. ✅ `_bitnum` 索引计算：`(bit // 32) * 4 + 3 - (bit % 32) // 8`（与 Kotlin 一致）
2. ✅ `_initial_permutation` 直接从字节数组提取而非从大端整数
3. ✅ `_inverse_permutation` 按字节索引构建而非位拼接大整数
4. ✅ `_sbox_bit` 实现：`(value & 32) | ((value & 31) >> 1) | ((value & 1) << 4)`
5. ✅ `_tripledes_crypt` 只处理前 8 字节

---

## 当前问题 ❌

### 症状
解密后的数据无法被 zlib 解压，报错：
```
zlib.error: Error -3 while decompressing data: invalid code lengths set
```

### 测试数据
- **输入**：`input/我愛你-上海蟹- - カニ研究会.mp3`
- **加密数据**：4032 字符 hex → 2016 字节
- **解密输出**：2016 字节
- **前 20 字节**：`9dc0f69fa3ad08da4764aa878a193846a22d4dfd`

### 可能原因

#### 1. 密钥调度 (`_key_schedule`)
- Kotlin 代码中的移位和掩码操作可能有细微差异
- 子密钥生成的 16 轮迭代顺序或移位量可能不对

#### 2. F 函数 (`_f`)
- 扩展置换（E-box）的位重排
- S-Box 索引计算和替换
- P-Box 置换的位重排
- 任何一步的位操作错误都会导致雪崩效应

#### 3. 整数符号问题
- Kotlin 的 `Int` 是有符号 32 位，Python 的 `int` 是任意精度
- 位移操作在负数时行为可能不同
- 需要确保所有中间值在 `0x00000000` ~ `0xFFFFFFFF` 范围内

#### 4. 字节序问题
- 虽然已经修复 `_bitnum` 的索引计算，但可能还有其他地方有字节序假设
- 大端/小端转换可能在某些中间步骤缺失

#### 5. 轮函数迭代
- `_crypt` 函数中 16 轮 Feistel 网络的状态交换逻辑
- 最后一轮是否需要特殊处理

---

## 后续建议 🔧

### 短期方案（推荐）

#### 方案 A：使用 Python 已有的 QRC 解密库
搜索 GitHub 是否有现成的 Python QRC 解密实现，直接集成。

#### 方案 B：跳过 QRC，优先完成其他功能
- QRC 是三大逐字格式中实现难度最高的
- 网易云 YRC 和酷狗 KRC 已经完成，覆盖大部分需求
- 将 QRC 标记为"已知限制"，后续单独攻克

#### 方案 C：寻求社区帮助
- 在 LDDC 项目提 Issue，询问是否有 Python 移植经验
- 或请求 Kotlin 代码的详细调试日志（每个块的输入输出）

### 中期方案（如果继续调试）

#### 1. 逐块对比验证
修改 Kotlin 代码，打印每个 8 字节块的：
- 初始置换后的 s0, s1
- 16 轮 Feistel 每轮的 s0, s1
- 最终解密输出

然后用 Python 重现，逐步定位差异点。

#### 2. 单元测试已知样例
如果 LDDC 项目有单元测试用例（输入 hex + 期望输出 XML），可以直接验证。

#### 3. 使用 Kotlin/JVM 库
通过 `jpype` 或 `pyjnius` 调用 LDDC-Android 的 Kotlin 解密代码，绕过 Python 移植问题。

---

## 测试文件

当前调试产物（保留用于后续调试）：

```
debug_raw_api.py          - 检查 API 返回的原始数据格式
debug_orig_raw.txt        - API 返回的加密歌词（hex）
debug_trans_raw.txt       - API 返回的加密翻译（hex）
test_decrypt_methods.py   - 测试直接解压 vs 解密后解压
debug_first_block.py      - 测试第一个 8 字节块的解密
debug_permutation.py      - 测试初始置换和逆置换正确性
debug_bitnum.py           - 测试 bitnum 函数实现
check_if_plaintext.py     - 检查数据是否已是明文
test_new_qrc.py           - 完整流程测试
```

---

## 参考资料

- **LDDC-Android**：[github.com/chenmozhijin/LDDC](https://github.com/chenmozhijin/LDDC)  
  完整的 QRC/KRC/YRC 解密实现（Kotlin）

- **3DES 算法**：[en.wikipedia.org/wiki/Triple_DES](https://en.wikipedia.org/wiki/Triple_DES)  
  标准 3DES 算法说明（注意 LDDC 使用的是**自定义实现**）

- **DES S-Box**：S-Box 表是 DES 算法的核心，任何错误都会导致完全错误的输出

---

## 结论

QRC 解密是本项目最大的技术难点，自定义 3DES 实现极易出错。建议优先完成其他功能（网易云 YRC + 酷狗 KRC 已足够），将 QRC 作为长期优化目标。

如果用户强烈需要 QQ 音乐逐字歌词，可以：
1. 引导用户使用 QQ 音乐客户端自带的歌词下载功能
2. 或使用第三方工具（如 LDDC 桌面版）先下载，再用本工具写入
