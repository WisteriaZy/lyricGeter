package com.example.lddc.core.parser

import com.example.lddc.common.models.enums.LyricsType
import com.example.lddc.common.models.lyrics.LyricsLine
import com.example.lddc.common.models.lyrics.LyricsWord

class LrcParser : LyricsParser {

    // 修复：使用正确的正则表达式，不需要双反斜杠
    private val tagPattern = Regex("""^\[(\w+):([^\]]*)\]$""")
    private val linePattern = Regex("""^(\[\d+:[\d.]+\])+(.+)$""")
    private val timePattern = Regex("""\[(\d+):([\d.]+)\]""")

    override fun supports(format: String): Boolean {
        return format.equals("lrc", ignoreCase = true) ||
                format.equals("plain", ignoreCase = true)
    }

    fun parseWithTags(content: String): Triple<Map<String, String>, List<LyricsLine>, LyricsType> {
        val tags = mutableMapOf<String, String>()
        val lines = mutableListOf<LyricsLine>()

        content.lineSequence().forEach { rawLine ->
            val line = rawLine.trim()
            if (line.isEmpty()) return@forEach

            // 解析标签 [ar:艺术家] [ti:标题] 等
            tagPattern.matchEntire(line)?.let { match ->
                tags[match.groupValues[1]] = match.groupValues[2]
                return@forEach
            }

            // 解析歌词行 [mm:ss.xx]歌词内容
            linePattern.matchEntire(line)?.let { match ->
                val timeTags = match.groupValues[1]
                val text = match.groupValues[2]

                val times = timePattern.findAll(timeTags).map { timeMatch ->
                    val minutes = timeMatch.groupValues[1].toInt()
                    val seconds = timeMatch.groupValues[2].toFloat()
                    (minutes * 60 + seconds) * 1000
                }.toList()

                if (times.isNotEmpty()) {
                    lines.add(
                        LyricsLine(
                            start = times.first().toInt(),
                            words = listOf(
                                LyricsWord(
                                    start = times.first().toInt(),
                                    text = text
                                )
                            )
                        )
                    )
                }
            }
        }

        val sortedLines = lines.sortedBy { it.start }

        val linesWithEnd = sortedLines.mapIndexed { index, line ->
            val end = if (index < sortedLines.size - 1) {
                sortedLines[index + 1].start
            } else {
                line.start?.plus(5000) ?: 0
            }
            line.copy(end = end)
        }

        return Triple(tags, linesWithEnd, LyricsType.LINEBYLINE)
    }

    override fun parse(content: String): List<LyricsLine> {
        return parseWithTags(content).second
    }

    fun parseWithType(content: String): Pair<List<LyricsLine>, LyricsType> {
        val result = parseWithTags(content)
        return result.second to result.third
    }

}
