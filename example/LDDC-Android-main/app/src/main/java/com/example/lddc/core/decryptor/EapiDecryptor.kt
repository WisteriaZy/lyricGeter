package com.example.lddc.core.decryptor

import android.util.Base64
import java.security.MessageDigest
import javax.crypto.Cipher
import javax.crypto.spec.SecretKeySpec

object EapiDecryptor {

    private const val EAPI_KEY = "e82ckenh8dichen8"
    private const val DEVICEID_XOR_KEY = "3go8&$8*3*3h0k(2)2"

    fun encryptParams(path: String, params: Map<String, Any?>): String {
        // 使用紧凑JSON格式（无空格，与Python一致）
        val paramsJson = buildCompactJson(params)
        val signSrc = "nobody${path}use${paramsJson}md5forencrypt"
        val sign = md5(signSrc)

        val aesSrc = "$path-36cd479b6b5-$paramsJson-36cd479b6b5-$sign"
        val encrypted = aesEncrypt(aesSrc.toByteArray(), EAPI_KEY.toByteArray())

        return "params=${bytesToHex(encrypted).uppercase()}"
    }

    /**
     * 构建紧凑JSON字符串（无空格，与Python的separators=(',', ':')一致）
     */
    private fun buildCompactJson(params: Map<String, Any?>): String {
        val entries = params.entries.joinToString(",") { (key, value) ->
            val jsonValue = when (value) {
                is String -> "\"${escapeJson(value)}\""
                is Number -> value.toString()
                is Boolean -> value.toString()
                else -> "\"${escapeJson(value.toString())}\""
            }
            "\"${key}\":$jsonValue"
        }
        return "{$entries}"
    }

    /**
     * 转义JSON字符串中的特殊字符
     */
    private fun escapeJson(str: String): String {
        return str.replace("\\", "\\\\")
            .replace("\"", "\\\"")
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t")
    }

    fun decryptResponse(encryptedData: ByteArray): String {
        return String(aesDecrypt(encryptedData, EAPI_KEY.toByteArray()))
    }

    fun getAnonymousUsername(deviceId: String): String {
        val xoredChars = deviceId.mapIndexed { i, ch ->
            (ch.code xor DEVICEID_XOR_KEY[i % DEVICEID_XOR_KEY.length].code).toChar()
        }.joinToString("")

        val md5Bytes = md5Bytes(xoredChars)
        val combined = "$deviceId ${Base64.encodeToString(md5Bytes, Base64.NO_WRAP)}"

        return Base64.encodeToString(combined.toByteArray(), Base64.NO_WRAP)
    }

    private fun aesEncrypt(data: ByteArray, key: ByteArray): ByteArray {
        val cipher = Cipher.getInstance("AES/ECB/PKCS5Padding")
        val keySpec = SecretKeySpec(key, "AES")
        cipher.init(Cipher.ENCRYPT_MODE, keySpec)
        return cipher.doFinal(data)
    }

    private fun aesDecrypt(data: ByteArray, key: ByteArray): ByteArray {
        val cipher = Cipher.getInstance("AES/ECB/PKCS5Padding")
        val keySpec = SecretKeySpec(key, "AES")
        cipher.init(Cipher.DECRYPT_MODE, keySpec)
        return cipher.doFinal(data)
    }

    private fun md5(input: String): String {
        val md = MessageDigest.getInstance("MD5")
        val digest = md.digest(input.toByteArray())
        return digest.joinToString("") { "%02x".format(it) }
    }

    private fun md5Bytes(input: String): ByteArray {
        val md = MessageDigest.getInstance("MD5")
        return md.digest(input.toByteArray())
    }

    private fun bytesToHex(bytes: ByteArray): String {
        return bytes.joinToString("") { "%02x".format(it) }
    }
}
