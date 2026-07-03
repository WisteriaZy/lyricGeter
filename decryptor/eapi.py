"""网易云 EAPI 加密器

EAPI 加密流程：
1. 构建紧凑 JSON（无空格）
2. MD5 签名：md5("nobody{path}use{params}md5forencrypt")
3. AES-ECB 加密："{path}-36cd479b6b5-{params}-36cd479b6b5-{sign}"
4. 十六进制编码
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad


EAPI_KEY = b"e82ckenh8dichen8"


def encrypt_eapi_params(path: str, params: dict[str, Any]) -> str:
    """
    加密 EAPI 请求参数
    
    Args:
        path: API 路径（如 "/api/song/lyric/v1"）
        params: 请求参数字典
    
    Returns:
        加密后的查询字符串（"params=HEX..."）
    """
    # 构建紧凑 JSON（无空格，与 Python json.dumps(separators=(',', ':')) 一致）
    params_json = json.dumps(params, separators=(',', ':'), ensure_ascii=False)
    
    # MD5 签名
    sign_src = f"nobody{path}use{params_json}md5forencrypt"
    sign = hashlib.md5(sign_src.encode('utf-8')).hexdigest()
    
    # AES-ECB 加密
    aes_src = f"{path}-36cd479b6b5-{params_json}-36cd479b6b5-{sign}"
    cipher = AES.new(EAPI_KEY, AES.MODE_ECB)
    encrypted = cipher.encrypt(pad(aes_src.encode('utf-8'), AES.block_size))
    
    # 十六进制编码
    hex_str = encrypted.hex().upper()
    
    return f"params={hex_str}"


def decrypt_eapi_response(encrypted_hex: str) -> str:
    """
    解密 EAPI 响应（如果需要）
    
    Args:
        encrypted_hex: 十六进制加密数据
    
    Returns:
        解密后的 JSON 字符串
    """
    encrypted_data = bytes.fromhex(encrypted_hex)
    cipher = AES.new(EAPI_KEY, AES.MODE_ECB)
    decrypted = cipher.decrypt(encrypted_data)
    
    # 移除 PKCS7 padding
    padding_len = decrypted[-1]
    return decrypted[:-padding_len].decode('utf-8')
