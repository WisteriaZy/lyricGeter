"""使用 pycryptodome 实现 QRC 解密"""

import zlib
import logging
from Crypto.Cipher import DES3

logger = logging.getLogger(__name__)

def decrypt_qrc_simple(encrypted_hex: str) -> str:
    """使用标准库解密 QRC
    
    Args:
        encrypted_hex: 十六进制编码的加密数据
        
    Returns:
        解密后的明文歌词
    """
    QRC_KEY = b"!@#)(*$%123ZXC!@!@#)(NHL"
    
    logger.debug(f"开始解密 QRC，输入长度: {len(encrypted_hex)}")
    
    try:
        # 1. 十六进制解码
        encrypted_data = bytes.fromhex(encrypted_hex)
        logger.debug(f"十六进制解码完成，字节数: {len(encrypted_data)}")
        
        # 2. 3DES-ECB 解密（使用标准库）
        cipher = DES3.new(QRC_KEY, DES3.MODE_ECB)
        decrypted_data = cipher.decrypt(encrypted_data)
        logger.debug(f"解密完成，输出大小: {len(decrypted_data)}")
        
        # 3. zlib 解压
        try:
            # 先尝试标准 zlib 格式
            decompressed = zlib.decompress(decrypted_data)
            logger.debug(f"zlib 解压成功（标准格式），输出大小: {len(decompressed)}")
        except zlib.error:
            # 回退到原始 DEFLATE 格式（无 zlib 头）
            logger.debug("标准 zlib 失败，尝试原始 DEFLATE 格式")
            decompressed = zlib.decompress(decrypted_data, -zlib.MAX_WBITS)
            logger.debug(f"原始 DEFLATE 解压成功，输出大小: {len(decompressed)}")
        
        return decompressed.decode('utf-8')
    
    except Exception as e:
        logger.error(f"QRC 解密失败: {e}")
        raise


if __name__ == "__main__":
    # 测试
    logging.basicConfig(level=logging.DEBUG)
    
    # 使用标准库加密测试数据
    test_data = b"Hello, World!" + b"\x00" * 3  # 补齐到 8 字节倍数
    cipher = DES3.new(b"!@#)(*$%123ZXC!@!@#)(NHL", DES3.MODE_ECB)
    encrypted = cipher.encrypt(test_data)
    print(f"加密结果: {encrypted.hex()}")
    
    # 解密验证
    decrypted = cipher.decrypt(encrypted)
    print(f"解密结果: {decrypted}")
    print(f"测试: {'成功' if decrypted == test_data else '失败'}")
