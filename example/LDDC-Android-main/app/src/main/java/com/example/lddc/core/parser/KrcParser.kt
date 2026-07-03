package com.example.lddc.core.parser

import android.util.Base64
import com.example.lddc.common.models.enums.LyricsType
import com.example.lddc.common.models.lyrics.LyricsLine
import com.example.lddc.common.models.lyrics.LyricsWord
import org.json.JSONObject

class KrcParser : LyricsParser {

    companion object {

        private val tagPattern = Regex("""^\[(\w+):([^\]]*)\]$""")
        private val linePattern = Regex("""^\[(\d+),(\d+)\](.*)$""")
        private val wordPattern = Regex("""<(\d+),(\d+),\d+>([^<]*)""")
    }

    fun parseWithTags(content: String): Triple<Map<String, String>, Map<String, List<LyricsLine>>, Map<String, LyricsType>> {
        val tags = mutableMapOf<String, String>()
        val origLines = mutableListOf<LyricsLine>()
        val romaLines = mutableListOf<LyricsLine>()
        val tsLines = mutableListOf<LyricsLine>()

        content.lineSequence().forEach { rawLine ->
            val line = rawLine.trim()
            if (line.isEmpty()) return@forEach

            tagPattern.matchEntire(line)?.let { match ->
                val key = match.groupValues[1]
                val value = match.groupValues[2]
                tags[key] = value
                return@forEach
            }

            linePattern.matchEntire(line)?.let { match ->
                val lineStart = match.groupValues[1].toInt()
                val lineDuration = match.groupValues[2].toInt()
                val lineEnd = lineStart + lineDuration
                val lineContent = match.groupValues[3]

                val words = wordPattern.findAll(lineContent).map { wordMatch ->
                    val wordStart = lineStart + wordMatch.groupValues[1].toInt()
                    val wordDuration = wordMatch.groupValues[2].toInt()
                    LyricsWord(
                        start = wordStart,
                        end = wordStart + wordDuration,
                        text = wordMatch.groupValues[3]
                    )
                }.toList()

                val finalWords = words.ifEmpty {
                    listOf(LyricsWord(lineStart, lineEnd, lineContent))
                }

                origLines.add(LyricsLine(lineStart, lineEnd, finalWords))
            }
        }

        tags["language"]?.let { langTag ->
            try {
                val langJson = JSONObject(String(Base64.decode(langTag.trim(), Base64.DEFAULT)))
                val contentArray = langJson.getJSONArray("content")

                for (i in 0 until contentArray.length()) {
                    val langObj = contentArray.getJSONObject(i)
                    val type = langObj.getInt("type")
                    val lyricContent = langObj.getJSONArray("lyricContent")

                    when (type) {
                        0 -> { // 罗马音
                            var offset = 0
                            for (j in 0 until lyricContent.length()) {
                                if (j - offset >= origLines.size) break

                                val origLine = origLines[j - offset]
                                if (origLine.words.all { it.text.isEmpty() }) {
                                    offset++
                                    continue
                                }

                                val romaWords = lyricContent.getJSONArray(j)
                                val romaLineWords = origLine.words.mapIndexed { index, word ->
                                    LyricsWord(
                                        start = word.start,
                                        end = word.end,
                                        text = if (index < romaWords.length()) {
                                            romaWords.getString(index)
                                        } else ""
                                    )
                                }

                                romaLines.add(
                                    LyricsLine(
                                        origLine.start,
                                        origLine.end,
                                        romaLineWords
                                    )
                                )
                            }
                        }

                        1 -> { // 翻译
                            for (j in 0 until lyricContent.length()) {
                                if (j >= origLines.size) break

                                val origLine = origLines[j]
                                val tsText = lyricContent.getJSONArray(j).getString(0)

                                tsLines.add(
                                    LyricsLine(
                                        origLine.start,
                                        origLine.end,
                                        listOf(
                                            LyricsWord(
                                                start = origLine.start,
                                                end = origLine.end,
                                                text = tsText
                                            )
                                        )
                                    )
                                )
                            }
                        }
                    }
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }

        val result = mutableMapOf("orig" to origLines)
        if (romaLines.isNotEmpty()) result["roma"] = romaLines
        if (tsLines.isNotEmpty()) result["ts"] = tsLines

        // 计算歌词类型
        val types = mutableMapOf<String, LyricsType>()

        // 原文类型：检查是否有逐字时间戳
        val origType = if (origLines.isNotEmpty() && origLines.all { line ->
                line.words.isNotEmpty() && line.words.first().start != null
            }) {
            LyricsType.VERBATIM
        } else {
            LyricsType.LINEBYLINE
        }
        types["orig"] = origType

        // 罗马音类型：与原文一致
        if (romaLines.isNotEmpty()) {
            types["roma"] = origType
        }

        // 翻译类型：通常是逐行
        if (tsLines.isNotEmpty()) {
            types["ts"] = LyricsType.LINEBYLINE
        }

        return Triple(tags, result, types)
    }

    override fun parse(content: String): List<LyricsLine> {
        return parseWithTags(content).second["orig"] ?: emptyList()
    }

    override fun supports(format: String): Boolean =
        format.equals("krc", ignoreCase = true)
}
