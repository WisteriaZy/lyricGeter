package com.example.lddc.core.decryptor

import java.util.zip.Inflater

object KrcDecryptor {

    private val KRC_KEY = byteArrayOf(
        '@'.code.toByte(), 'G'.code.toByte(), 'a'.code.toByte(), 'w'.code.toByte(),
        '^'.code.toByte(), '2'.code.toByte(), 't'.code.toByte(), 'G'.code.toByte(),
        'Q'.code.toByte(), '6'.code.toByte(), '1'.code.toByte(), '-'.code.toByte(),
        0xce.toByte(), 0xd2.toByte(), 'n'.code.toByte(), 'i'.code.toByte()
    )

    fun decrypt(data: ByteArray): String {
        if (data.size < 4) {
            return ""
        }

        // 跳过前4个字节的magic header
        val encryptedData = data.copyOfRange(4, data.size)

        // XOR解密
        val decryptedData = ByteArray(encryptedData.size)
        for (i in encryptedData.indices) {
            decryptedData[i] =
                (encryptedData[i].toInt() xor KRC_KEY[i % KRC_KEY.size].toInt()).toByte()
        }

        // zlib解压
        val inflater = Inflater()
        inflater.setInput(decryptedData)

        val buffer = ByteArray(1024 * 1024) // 1MB buffer
        val result = mutableListOf<Byte>()

        try {
            while (!inflater.finished()) {
                val count = inflater.inflate(buffer)
                if (count > 0) {
                    result.addAll(buffer.take(count))
                }
            }
        } catch (e: Exception) {
            // 解压失败，返回空字符串
            return ""
        } finally {
            inflater.end()
        }

        return String(result.toByteArray(), Charsets.UTF_8)
    }

    fun decryptString(data: ByteArray): String {
        return decrypt(data)
    }
}
