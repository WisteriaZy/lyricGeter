package com.example.lddc.core.parser

import com.example.lddc.common.models.enums.LyricsType
import com.example.lddc.common.models.lyrics.LyricsLine
import com.example.lddc.common.models.lyrics.LyricsWord

class QrcParser : LyricsParser {

    companion object {

        private val qrcContentPattern = Regex(
            """<Lyric_1 LyricType="1" LyricContent="(.*?)"/>""",
            RegexOption.DOT_MATCHES_ALL
        )
        private val tagPattern = Regex("""^\[(\w+):([^\]]*)\]$""")
        private val linePattern = Regex("""^\[(\d+),(\d+)\](.*)$""")
        private val wordPattern = Regex("""([^\(]*)\((\d+),(\d+)\)""")
    }

    fun parseWithTags(content: String): Triple<Map<String, String>, List<LyricsLine>, LyricsType> {
        val tags = mutableMapOf<String, String>()
        val lines = mutableListOf<LyricsLine>()
        var hasWordTimestamps = false

        val qrcMatch = qrcContentPattern.find(content)
        val qrcContent = qrcMatch?.groupValues?.get(1) ?: content

        qrcContent.lineSequence().forEach { rawLine ->
            val line = rawLine.trim()
            if (line.isEmpty()) return@forEach

            tagPattern.matchEntire(line)?.let { match ->
                tags[match.groupValues[1]] = match.groupValues[2]
                return@forEach
            }

            linePattern.matchEntire(line)?.let { match ->
                val lineStart = match.groupValues[1].toInt()
                val lineDuration = match.groupValues[2].toInt()
                val lineEnd = lineStart + lineDuration
                val lineContent = match.groupValues[3]

                if (lineContent == "($lineStart,$lineDuration)") {
                    lines.add(LyricsLine(lineStart, lineEnd, emptyList()))
                    return@forEach
                }

                val words = wordPattern.findAll(lineContent).map { wordMatch ->
                    hasWordTimestamps = true
                    val wordText = wordMatch.groupValues[1]
                    val wordStart = wordMatch.groupValues[2].toInt()
                    val wordDuration = wordMatch.groupValues[3].toInt()
                    LyricsWord(
                        start = wordStart,
                        end = wordStart + wordDuration,
                        text = wordText
                    )
                }.toList()

                val finalWords = words.ifEmpty {
                    listOf(LyricsWord(lineStart, lineEnd, lineContent))
                }

                lines.add(LyricsLine(lineStart, lineEnd, finalWords))
            }
        }

        val type = if (hasWordTimestamps) LyricsType.VERBATIM else LyricsType.LINEBYLINE
        return Triple(tags, lines, type)
    }

    override fun parse(content: String): List<LyricsLine> {
        return parseWithTags(content).second
    }

    override fun supports(format: String): Boolean =
        format.equals("qrc", ignoreCase = true)

    /**
     * 智能解析歌词，支持 QRC、LRC 格式
     * 参考 PC 端的 qrc_str_parse 函数
     */
    fun parseSmart(content: String): Pair<Map<String, String>, List<LyricsLine>> {
        // 先尝试 QRC 格式
        val qrcMatch = qrcContentPattern.find(content)
        if (qrcMatch != null) {
            val result = parseWithTags(content)
            return Pair(result.first, result.second)
        }

        // 如果不是 QRC 格式，尝试 LRC 格式
        return try {
            val lrcParser = LrcParser()
            val result = lrcParser.parseWithTags(content)
            Pair(result.first, result.second)
        } catch (e: Exception) {
            // 如果都失败，返回空
            Pair(emptyMap(), emptyList())
        }
    }
}
