package com.example.lddc.core.parser

import com.example.lddc.common.models.enums.LyricsType
import com.example.lddc.common.models.lyrics.LyricsLine
import com.example.lddc.common.models.lyrics.LyricsWord

class YrcParser : LyricsParser {

    private val linePattern = Regex("""^\\[(\\d+),(\\d+)\\](.*)$""")
    private val wordPattern = Regex("""\\((\\d+),(\\d+),\\d+\\)([^\\(]*)""")

    fun parseWithType(content: String): Pair<List<LyricsLine>, LyricsType> {
        val lines = mutableListOf<LyricsLine>()
        var hasWordTimestamps = false

        content.lineSequence().forEach { rawLine ->
            val line = rawLine.trim()
            if (!line.startsWith("[")) return@forEach

            linePattern.matchEntire(line)?.let { match ->
                val lineStart = match.groupValues[1].toInt()
                val lineDuration = match.groupValues[2].toInt()
                val lineEnd = lineStart + lineDuration
                val lineContent = match.groupValues[3]

                val words = wordPattern.findAll(lineContent).map { wordMatch ->
                    hasWordTimestamps = true
                    val wordStart = wordMatch.groupValues[1].toInt()
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

                lines.add(LyricsLine(lineStart, lineEnd, finalWords))
            }
        }

        val type = if (hasWordTimestamps) LyricsType.VERBATIM else LyricsType.LINEBYLINE
        return lines to type
    }

    override fun parse(content: String): List<LyricsLine> {
        return parseWithType(content).first
    }

    override fun supports(format: String): Boolean =
        format.equals("yrc", ignoreCase = true)
}
