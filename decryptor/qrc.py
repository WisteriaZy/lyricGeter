"""QQ 音乐 QRC 歌词解密器

完整移植自 LDDC-Android QrcDecryptor.kt
使用自定义 3DES 实现
"""

import zlib
import logging

logger = logging.getLogger(__name__)


class QrcDecryptor:
    """QRC 解密器 - 自定义 3DES-ECB + zlib 解压"""
    
    QRC_KEY = b"!@#)(*$%123ZXC!@!@#)(NHL"
    
    # S-Box 表
    SBOX = [
        [
            14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7,
            0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8,
            4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0,
            15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13
        ],
        [
            15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10,
            3, 13, 4, 7, 15, 2, 8, 15, 12, 0, 1, 10, 6, 9, 11, 5,
            0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15,
            13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9
        ],
        [
            10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8,
            13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1,
            13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7,
            1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12
        ],
        [
            7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15,
            13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9,
            10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4,
            3, 15, 0, 6, 10, 10, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14
        ],
        [
            2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9,
            14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6,
            4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14,
            11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3
        ],
        [
            12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11,
            10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8,
            9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6,
            4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13
        ],
        [
            4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1,
            13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6,
            1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2,
            6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12
        ],
        [
            13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7,
            1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2,
            7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8,
            2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11
        ]
    ]
    
    ENCRYPT = 1
    DECRYPT = 0
    
    @classmethod
    def _bitnum(cls, data: bytes, bit: int, pos: int) -> int:
        """从字节数组中提取指定位（与 Kotlin 的 bitnum 完全一致）"""
        byte_idx = (bit // 32) * 4 + 3 - (bit % 32) // 8
        byte_value = data[byte_idx]
        return ((byte_value >> (7 - bit % 8)) & 1) << pos
    
    @classmethod
    def _bitnum_intl(cls, data: int, bit: int, pos: int) -> int:
        """从整数中提取指定位"""
        return ((data >> bit) & 1) << pos
    
    @classmethod
    def _bitnum_intr(cls, data: int, bit: int, pos: int) -> int:
        """从整数中提取指定位（反向）"""
        return ((data >> (31 - bit)) & 1) << pos
    
    @classmethod
    def _sbox_bit(cls, value: int) -> int:
        """S-Box 位处理（与 Kotlin 的 sboxBit 完全一致）"""
        return (value & 32) | ((value & 31) >> 1) | ((value & 1) << 4)
    
    @classmethod
    def _initial_permutation(cls, data: bytes) -> tuple[int, int]:
        """初始置换（直接从字节数组中提取位）"""
        s0 = (cls._bitnum(data, 57, 31) | cls._bitnum(data, 49, 30) |
              cls._bitnum(data, 41, 29) | cls._bitnum(data, 33, 28) |
              cls._bitnum(data, 25, 27) | cls._bitnum(data, 17, 26) |
              cls._bitnum(data, 9, 25) | cls._bitnum(data, 1, 24) |
              cls._bitnum(data, 59, 23) | cls._bitnum(data, 51, 22) |
              cls._bitnum(data, 43, 21) | cls._bitnum(data, 35, 20) |
              cls._bitnum(data, 27, 19) | cls._bitnum(data, 19, 18) |
              cls._bitnum(data, 11, 17) | cls._bitnum(data, 3, 16) |
              cls._bitnum(data, 61, 15) | cls._bitnum(data, 53, 14) |
              cls._bitnum(data, 45, 13) | cls._bitnum(data, 37, 12) |
              cls._bitnum(data, 29, 11) | cls._bitnum(data, 21, 10) |
              cls._bitnum(data, 13, 9) | cls._bitnum(data, 5, 8) |
              cls._bitnum(data, 63, 7) | cls._bitnum(data, 55, 6) |
              cls._bitnum(data, 47, 5) | cls._bitnum(data, 39, 4) |
              cls._bitnum(data, 31, 3) | cls._bitnum(data, 23, 2) |
              cls._bitnum(data, 15, 1) | cls._bitnum(data, 7, 0))
        
        s1 = (cls._bitnum(data, 56, 31) | cls._bitnum(data, 48, 30) |
              cls._bitnum(data, 40, 29) | cls._bitnum(data, 32, 28) |
              cls._bitnum(data, 24, 27) | cls._bitnum(data, 16, 26) |
              cls._bitnum(data, 8, 25) | cls._bitnum(data, 0, 24) |
              cls._bitnum(data, 58, 23) | cls._bitnum(data, 50, 22) |
              cls._bitnum(data, 42, 21) | cls._bitnum(data, 34, 20) |
              cls._bitnum(data, 26, 19) | cls._bitnum(data, 18, 18) |
              cls._bitnum(data, 10, 17) | cls._bitnum(data, 2, 16) |
              cls._bitnum(data, 60, 15) | cls._bitnum(data, 52, 14) |
              cls._bitnum(data, 44, 13) | cls._bitnum(data, 36, 12) |
              cls._bitnum(data, 28, 11) | cls._bitnum(data, 20, 10) |
              cls._bitnum(data, 12, 9) | cls._bitnum(data, 4, 8) |
              cls._bitnum(data, 62, 7) | cls._bitnum(data, 54, 6) |
              cls._bitnum(data, 46, 5) | cls._bitnum(data, 38, 4) |
              cls._bitnum(data, 30, 3) | cls._bitnum(data, 22, 2) |
              cls._bitnum(data, 14, 1) | cls._bitnum(data, 6, 0))
        
        return s0, s1
    
    @classmethod
    def _inverse_permutation(cls, s0: int, s1: int) -> bytes:
        """逆置换"""
        data = bytearray(8)
        
        data[3] = (cls._bitnum_intr(s1, 7, 7) | cls._bitnum_intr(s0, 7, 6) |
                   cls._bitnum_intr(s1, 15, 5) | cls._bitnum_intr(s0, 15, 4) |
                   cls._bitnum_intr(s1, 23, 3) | cls._bitnum_intr(s0, 23, 2) |
                   cls._bitnum_intr(s1, 31, 1) | cls._bitnum_intr(s0, 31, 0))
        
        data[2] = (cls._bitnum_intr(s1, 6, 7) | cls._bitnum_intr(s0, 6, 6) |
                   cls._bitnum_intr(s1, 14, 5) | cls._bitnum_intr(s0, 14, 4) |
                   cls._bitnum_intr(s1, 22, 3) | cls._bitnum_intr(s0, 22, 2) |
                   cls._bitnum_intr(s1, 30, 1) | cls._bitnum_intr(s0, 30, 0))
        
        data[1] = (cls._bitnum_intr(s1, 5, 7) | cls._bitnum_intr(s0, 5, 6) |
                   cls._bitnum_intr(s1, 13, 5) | cls._bitnum_intr(s0, 13, 4) |
                   cls._bitnum_intr(s1, 21, 3) | cls._bitnum_intr(s0, 21, 2) |
                   cls._bitnum_intr(s1, 29, 1) | cls._bitnum_intr(s0, 29, 0))
        
        data[0] = (cls._bitnum_intr(s1, 4, 7) | cls._bitnum_intr(s0, 4, 6) |
                   cls._bitnum_intr(s1, 12, 5) | cls._bitnum_intr(s0, 12, 4) |
                   cls._bitnum_intr(s1, 20, 3) | cls._bitnum_intr(s0, 20, 2) |
                   cls._bitnum_intr(s1, 28, 1) | cls._bitnum_intr(s0, 28, 0))
        
        data[7] = (cls._bitnum_intr(s1, 3, 7) | cls._bitnum_intr(s0, 3, 6) |
                   cls._bitnum_intr(s1, 11, 5) | cls._bitnum_intr(s0, 11, 4) |
                   cls._bitnum_intr(s1, 19, 3) | cls._bitnum_intr(s0, 19, 2) |
                   cls._bitnum_intr(s1, 27, 1) | cls._bitnum_intr(s0, 27, 0))
        
        data[6] = (cls._bitnum_intr(s1, 2, 7) | cls._bitnum_intr(s0, 2, 6) |
                   cls._bitnum_intr(s1, 10, 5) | cls._bitnum_intr(s0, 10, 4) |
                   cls._bitnum_intr(s1, 18, 3) | cls._bitnum_intr(s0, 18, 2) |
                   cls._bitnum_intr(s1, 26, 1) | cls._bitnum_intr(s0, 26, 0))
        
        data[5] = (cls._bitnum_intr(s1, 1, 7) | cls._bitnum_intr(s0, 1, 6) |
                   cls._bitnum_intr(s1, 9, 5) | cls._bitnum_intr(s0, 9, 4) |
                   cls._bitnum_intr(s1, 17, 3) | cls._bitnum_intr(s0, 17, 2) |
                   cls._bitnum_intr(s1, 25, 1) | cls._bitnum_intr(s0, 25, 0))
        
        data[4] = (cls._bitnum_intr(s1, 0, 7) | cls._bitnum_intr(s0, 0, 6) |
                   cls._bitnum_intr(s1, 8, 5) | cls._bitnum_intr(s0, 8, 4) |
                   cls._bitnum_intr(s1, 16, 3) | cls._bitnum_intr(s0, 16, 2) |
                   cls._bitnum_intr(s1, 24, 1) | cls._bitnum_intr(s0, 24, 0))
        
        return bytes(data)
    
    @classmethod
    def _f(cls, state: int, key: list[int]) -> int:
        """F 函数"""
        t1 = (cls._bitnum_intl(state, 31, 0) | ((state & 0xf0000000) >> 1) |
              cls._bitnum_intl(state, 4, 5) | cls._bitnum_intl(state, 3, 6) |
              ((state & 0x0f000000) >> 3) | cls._bitnum_intl(state, 8, 11) |
              cls._bitnum_intl(state, 7, 12) | ((state & 0x00f00000) >> 5) |
              cls._bitnum_intl(state, 12, 17) | cls._bitnum_intl(state, 11, 18) |
              ((state & 0x000f0000) >> 7) | cls._bitnum_intl(state, 16, 23))
        
        t2 = (cls._bitnum_intl(state, 15, 0) | ((state & 0x0000f000) << 15) |
              cls._bitnum_intl(state, 20, 5) | cls._bitnum_intl(state, 19, 6) |
              ((state & 0x00000f00) << 13) | cls._bitnum_intl(state, 24, 11) |
              cls._bitnum_intl(state, 23, 12) | ((state & 0x000000f0) << 11) |
              cls._bitnum_intl(state, 28, 17) | cls._bitnum_intl(state, 27, 18) |
              ((state & 0x0000000f) << 9) | cls._bitnum_intl(state, 0, 23))
        
        lrgstate = [
            (t1 >> 24) & 0xff,
            (t1 >> 16) & 0xff,
            (t1 >> 8) & 0xff,
            (t2 >> 24) & 0xff,
            (t2 >> 16) & 0xff,
            (t2 >> 8) & 0xff
        ]
        
        for i in range(6):
            lrgstate[i] ^= key[i]
        
        sbox_result = ((cls.SBOX[0][cls._sbox_bit(lrgstate[0] >> 2)] << 28) |
                       (cls.SBOX[1][cls._sbox_bit(((lrgstate[0] & 0x03) << 4) | (lrgstate[1] >> 4))] << 24) |
                       (cls.SBOX[2][cls._sbox_bit(((lrgstate[1] & 0x0f) << 2) | (lrgstate[2] >> 6))] << 20) |
                       (cls.SBOX[3][cls._sbox_bit(lrgstate[2] & 0x3f)] << 16) |
                       (cls.SBOX[4][cls._sbox_bit(lrgstate[3] >> 2)] << 12) |
                       (cls.SBOX[5][cls._sbox_bit(((lrgstate[3] & 0x03) << 4) | (lrgstate[4] >> 4))] << 8) |
                       (cls.SBOX[6][cls._sbox_bit(((lrgstate[4] & 0x0f) << 2) | (lrgstate[5] >> 6))] << 4) |
                       cls.SBOX[7][cls._sbox_bit(lrgstate[5] & 0x3f)])
        
        return (cls._bitnum_intl(sbox_result, 15, 0) | cls._bitnum_intl(sbox_result, 6, 1) |
                cls._bitnum_intl(sbox_result, 19, 2) | cls._bitnum_intl(sbox_result, 20, 3) |
                cls._bitnum_intl(sbox_result, 28, 4) | cls._bitnum_intl(sbox_result, 11, 5) |
                cls._bitnum_intl(sbox_result, 27, 6) | cls._bitnum_intl(sbox_result, 16, 7) |
                cls._bitnum_intl(sbox_result, 0, 8) | cls._bitnum_intl(sbox_result, 14, 9) |
                cls._bitnum_intl(sbox_result, 22, 10) | cls._bitnum_intl(sbox_result, 25, 11) |
                cls._bitnum_intl(sbox_result, 4, 12) | cls._bitnum_intl(sbox_result, 17, 13) |
                cls._bitnum_intl(sbox_result, 30, 14) | cls._bitnum_intl(sbox_result, 9, 15) |
                cls._bitnum_intl(sbox_result, 1, 16) | cls._bitnum_intl(sbox_result, 7, 17) |
                cls._bitnum_intl(sbox_result, 23, 18) | cls._bitnum_intl(sbox_result, 13, 19) |
                cls._bitnum_intl(sbox_result, 31, 20) | cls._bitnum_intl(sbox_result, 26, 21) |
                cls._bitnum_intl(sbox_result, 2, 22) | cls._bitnum_intl(sbox_result, 8, 23) |
                cls._bitnum_intl(sbox_result, 18, 24) | cls._bitnum_intl(sbox_result, 12, 25) |
                cls._bitnum_intl(sbox_result, 29, 26) | cls._bitnum_intl(sbox_result, 5, 27) |
                cls._bitnum_intl(sbox_result, 21, 28) | cls._bitnum_intl(sbox_result, 10, 29) |
                cls._bitnum_intl(sbox_result, 3, 30) | cls._bitnum_intl(sbox_result, 24, 31))
    
    @classmethod
    def _crypt(cls, input_data: bytes, key: list[list[int]]) -> bytes:
        """DES 加密/解密"""
        s0, s1 = cls._initial_permutation(input_data)
        
        for idx in range(15):
            previous_s1 = s1
            s1 = cls._f(s1, key[idx]) ^ s0
            s0 = previous_s1
        
        s0 = cls._f(s1, key[15]) ^ s0
        
        return cls._inverse_permutation(s0, s1)
    
    @classmethod
    def _key_schedule(cls, key: bytes, mode: int) -> list[list[int]]:
        """密钥调度"""
        schedule = [[0] * 6 for _ in range(16)]
        key_rnd_shift = [1, 1, 2, 2, 2, 2, 2, 2, 1, 2, 2, 2, 2, 2, 2, 1]
        key_perm_c = [
            56, 48, 40, 32, 24, 16, 8, 0, 57, 49, 41, 33, 25, 17, 9, 1,
            58, 50, 42, 34, 26, 18, 10, 2, 59, 51, 43, 35
        ]
        key_perm_d = [
            62, 54, 46, 38, 30, 22, 14, 6, 61, 53, 45, 37, 29, 21, 13, 5,
            60, 52, 44, 36, 28, 20, 12, 4, 27, 19, 11, 3
        ]
        key_compression = [
            13, 16, 10, 23, 0, 4, 2, 27, 14, 5, 20, 9, 22, 18, 11, 3,
            25, 7, 15, 6, 26, 19, 12, 1, 40, 51, 30, 36, 46, 54, 29, 39,
            50, 44, 32, 47, 43, 48, 38, 55, 33, 52, 45, 41, 49, 35, 28, 31
        ]
        
        c = 0
        for i in range(28):
            c |= cls._bitnum(key, key_perm_c[i], 31 - i)
        
        d = 0
        for i in range(28):
            d |= cls._bitnum(key, key_perm_d[i], 31 - i)
        
        for i in range(16):
            c = ((c << key_rnd_shift[i]) | (c >> (28 - key_rnd_shift[i]))) & 0xfffffff0
            d = ((d << key_rnd_shift[i]) | (d >> (28 - key_rnd_shift[i]))) & 0xfffffff0
            
            togen = 15 - i if mode == cls.DECRYPT else i
            
            for j in range(24):
                schedule[togen][j // 8] |= cls._bitnum_intr(c, key_compression[j], 7 - (j % 8))
            
            for j in range(24, 48):
                schedule[togen][j // 8] |= cls._bitnum_intr(d, key_compression[j] - 27, 7 - (j % 8))
        
        return schedule
    
    @classmethod
    def _tripledes_key_setup(cls, key: bytes, mode: int) -> list[list[list[int]]]:
        """3DES 密钥设置"""
        if mode == cls.ENCRYPT:
            return [
                cls._key_schedule(key[0:8], cls.ENCRYPT),
                cls._key_schedule(key[8:16], cls.DECRYPT),
                cls._key_schedule(key[16:24], cls.ENCRYPT)
            ]
        else:
            return [
                cls._key_schedule(key[16:24], cls.DECRYPT),
                cls._key_schedule(key[8:16], cls.ENCRYPT),
                cls._key_schedule(key[0:8], cls.DECRYPT)
            ]
    
    @classmethod
    def _tripledes_crypt(cls, data: bytes, key: list[list[list[int]]]) -> bytes:
        """3DES 加密/解密（只处理前 8 字节）"""
        # 确保至少有 8 字节
        if len(data) < 8:
            data = data + b'\x00' * (8 - len(data))
        
        # 只取前 8 字节
        block = data[:8]
        result = block
        for i in range(3):
            result = cls._crypt(result, key[i])
        return result
    
    @classmethod
    def decrypt(cls, encrypted_hex: str) -> str:
        """解密 QRC 歌词
        
        Args:
            encrypted_hex: 十六进制编码的加密数据
            
        Returns:
            解密后的明文歌词（XML 格式）
        """
        if not encrypted_hex or not encrypted_hex.strip():
            raise ValueError("没有可解密的数据")
        
        logger.debug(f"开始解密 QRC，输入长度: {len(encrypted_hex)}")
        
        try:
            # 1. 十六进制解码
            encrypted_data = bytes.fromhex(encrypted_hex)
            logger.debug(f"十六进制解码完成，字节数: {len(encrypted_data)}")
            
            # 2. 设置密钥
            key = cls._tripledes_key_setup(cls.QRC_KEY, cls.DECRYPT)
            logger.debug("密钥调度完成")
            
            # 3. 解密数据（按 8 字节块）
            decrypted_data = bytearray()
            block_count = 0
            
            for i in range(0, len(encrypted_data), 8):
                # 关键：传递从位置 i 到结尾的所有字节
                block = encrypted_data[i:]
                result = cls._tripledes_crypt(block, key)
                decrypted_data.extend(result)
                block_count += 1
            
            logger.debug(f"解密完成，块数: {block_count}，输出大小: {len(decrypted_data)}")
            logger.debug(f"前 20 字节: {decrypted_data[:20].hex()}")
            
            # 4. zlib 解压
            try:
                # 先尝试标准 zlib 格式
                decompressed = zlib.decompress(bytes(decrypted_data))
                logger.debug(f"zlib 解压成功（标准格式），输出大小: {len(decompressed)}")
            except zlib.error:
                # 回退到原始 DEFLATE 格式
                logger.debug("标准 zlib 失败，尝试原始 DEFLATE 格式")
                decompressed = zlib.decompress(bytes(decrypted_data), -zlib.MAX_WBITS)
                logger.debug(f"原始 DEFLATE 解压成功，输出大小: {len(decompressed)}")
            
            return decompressed.decode('utf-8')
        
        except Exception as e:
            logger.error(f"QRC 解密失败: {e}")
            raise


def decrypt_qrc(encrypted_hex: str) -> str:
    """便捷函数：解密 QRC 歌词"""
    return QrcDecryptor.decrypt(encrypted_hex)
