"""酷狗 KRC 格式解密器

KRC 加密流程：
明文 → zlib 压缩 → XOR 加密 → 加上 4 字节 magic header → Base64 编码

解密流程（逆序）：
Base64 解码 → 跳过前 4 字节 → XOR 解密 → zlib 解压 → 明文
"""

import base64
import zlib
from typing import Optional


class KrcDecryptor:
    """酷狗 KRC 解密器"""
    
    # XOR 密钥（来自 LDDC-Android）
    KRC_KEY = bytes([
        0x40, 0x47, 0x61, 0x77,  # @Gaw
        0x5e, 0x32, 0x74, 0x47,  # ^2tG
        0x51, 0x36, 0x31, 0x2d,  # Q61-
        0xce, 0xd2, 0x6e, 0x69   # Íni (0xce=Í, 0xd2=Ò)
    ])
    
    @classmethod
    def decrypt(cls, encrypted_b64: str) -> Optional[str]:
        """解密 Base64 编码的 KRC 歌词
        
        Args:
            encrypted_b64: Base64 编码的加密 KRC 内容
            
        Returns:
            解密后的明文 KRC 内容，失败返回 None
        """
        try:
            # 步骤 1: Base64 解码
            encrypted_data = base64.b64decode(encrypted_b64)
            
            if len(encrypted_data) < 4:
                return None
            
            # 步骤 2: 跳过前 4 字节的 magic header
            encrypted_data = encrypted_data[4:]
            
            # 步骤 3: XOR 解密
            decrypted_data = bytearray(len(encrypted_data))
            for i in range(len(encrypted_data)):
                decrypted_data[i] = encrypted_data[i] ^ cls.KRC_KEY[i % len(cls.KRC_KEY)]
            
            # 步骤 4: zlib 解压
            decompressed = zlib.decompress(bytes(decrypted_data))
            
            return decompressed.decode('utf-8')
            
        except Exception as e:
            print(f"KRC 解密失败: {e}")
            return None
