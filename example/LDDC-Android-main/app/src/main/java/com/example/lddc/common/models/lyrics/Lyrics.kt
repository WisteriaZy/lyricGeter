package com.example.lddc.common.models.lyrics

import com.example.lddc.common.models.enums.LyricsFormat
import com.example.lddc.common.models.enums.LyricsType
import com.example.lddc.common.models.enums.Source
import com.example.lddc.common.models.info.Artist
import com.example.lddc.common.models.info.LyricInfo

data class Lyrics(
    val info: LyricInfo,
    val types: Map<String, LyricsType> = emptyMap(),
    val tags: Map<String, String> = emptyMap(),
    val data: Map<String, List<LyricsLine>> = emptyMap()
) {
    val source: Source get() = info.source
    val title: String? get() = info.songinfo.title ?: tags["ti"]
    val artist: Artist? get() = info.songinfo.artist ?: tags["ar"]?.let { Artist.fromString(it) }
    val album: String? get() = info.songinfo.album ?: tags["al"]
    val id: String? get() = info.id ?: info.songinfo.id

    fun isEmpty(): Boolean = data.isEmpty() || data.values.all { it.isEmpty() }

    fun isNotEmpty(): Boolean = !isEmpty()

    fun toFormat(format: LyricsFormat, langs: List<String> = listOf("orig")): String {
        return when (format) {
            LyricsFormat.VERBATIMLRC -> toVerbatimLrc(langs)
            LyricsFormat.LINEBYLINELRC -> toLineByLineLrc(langs)
            LyricsFormat.ENHANCEDLRC -> toEnhancedLrc(langs)
            LyricsFormat.SRT -> toSrt(langs)
            LyricsFormat.ASS -> toAss(langs)
            else -> toLineByLineLrc(langs)
        }
    }

    private fun toVerbatimLrc(langs: List<String>): String {
        val sb = StringBuilder()

        tags.forEach { (key, value) ->
            if (key in listOf("ti", "ar", "al", "by", "offset")) {
                sb.append("[$key:$value]\n")
            }
        }
        sb.append("\n")

        if (langs.size == 1) {
            // 只有一种语言，按原方式处理
            val lang = langs[0]
            val lines = data[lang]
            if (lines != null) {
                val hasWordTimestamps = lines.any { line ->
                    line.words.isNotEmpty() && line.words.first().start != null
                }

                lines.forEach { line ->
                    line.start?.let { sb.append(formatTime(it)) }

                    if (hasWordTimestamps) {
                        line.words.forEach { word ->
                            word.start?.let { sb.append(formatTime(it)) }
                            sb.append(word.text)
                            word.end?.let { sb.append(formatTime(it)) }
                        }
                    } else {
                        sb.append(line.words.joinToString("") { it.text })
                    }

                    sb.append("\n")
                }
            }
        } else {
            // 多种语言，按时间顺序混合显示
            val allLines = mutableListOf<Triple<Int, String, LyricsLine>>()

            langs.forEach { lang ->
                data[lang]?.forEach { line ->
                    line.start?.let { start ->
                        allLines.add(Triple(start, lang, line))
                    }
                }
            }

            // 按时间排序
            allLines.sortBy { it.first }

            // 按排序后的顺序显示
            allLines.forEach { (_, _, line) ->
                val hasWordTimestamps = line.words.isNotEmpty() && line.words.first().start != null

                line.start?.let { sb.append(formatTime(it)) }

                if (hasWordTimestamps) {
                    line.words.forEach { word ->
                        word.start?.let { sb.append(formatTime(it)) }
                        sb.append(word.text)
                        word.end?.let { sb.append(formatTime(it)) }
                    }
                } else {
                    sb.append(line.words.joinToString("") { it.text })
                }

                sb.append("\n")
            }
        }

        return sb.toString()
    }

    private fun toLineByLineLrc(langs: List<String>): String {
        val sb = StringBuilder()

        tags.forEach { (key, value) ->
            if (key in listOf("ti", "ar", "al", "by", "offset")) {
                sb.append("[$key:$value]\n")
            }
        }
        sb.append("\n")

        if (langs.size == 1) {
            // 只有一种语言，按原方式处理
            val lang = langs[0]
            data[lang]?.forEach { line ->
                val text = line.words.joinToString("") { it.text }.trim()
                if (text.isNotBlank() && text != "//") {
                    line.start?.let { sb.append(formatTime(it)) }
                    sb.append(text)
                    sb.append("\n")
                }
            }
        } else {
            // 多种语言，按时间顺序混合显示
            val allLines = mutableListOf<Triple<Int, String, LyricsLine>>()

            langs.forEach { lang ->
                data[lang]?.forEach { line ->
                    line.start?.let { start ->
                        val text = line.words.joinToString("") { it.text }.trim()
                        if (text.isNotBlank() && text != "//") {
                            allLines.add(Triple(start, lang, line))
                        }
                    }
                }
            }

            // 按时间排序
            allLines.sortBy { it.first }

            // 按排序后的顺序显示
            allLines.forEach { (_, _, line) ->
                val text = line.words.joinToString("") { it.text }.trim()
                if (text.isNotBlank() && text != "//") {
                    line.start?.let { sb.append(formatTime(it)) }
                    sb.append(text)
                    sb.append("\n")
                }
            }
        }

        return sb.toString()
    }

    private fun toEnhancedLrc(langs: List<String>): String {
        val sb = StringBuilder()

        tags.forEach { (key, value) ->
            if (key in listOf("ti", "ar", "al", "by", "offset")) {
                sb.append("[$key:$value]\n")
            }
        }
        sb.append("\n")

        if (langs.size == 1) {
            // 只有一种语言，按原方式处理
            val lang = langs[0]
            val lines = data[lang]
            if (lines != null) {
                val hasWordTimestamps = lines.any { line ->
                    line.words.isNotEmpty() && line.words.first().start != null
                }

                lines.forEach { line ->
                    line.start?.let { sb.append(formatTime(it)) }

                    if (hasWordTimestamps) {
                        line.words.forEach { word ->
                            word.start?.let { sb.append("<${formatTime(it, 2).trim('[', ']')}>") }
                            sb.append(word.text)
                        }
                    } else {
                        sb.append(line.words.joinToString("") { it.text })
                    }

                    sb.append("\n")
                }
            }
        } else {
            // 多种语言，按时间顺序混合显示
            val allLines = mutableListOf<Triple<Int, String, LyricsLine>>()

            langs.forEach { lang ->
                data[lang]?.forEach { line ->
                    line.start?.let { start ->
                        allLines.add(Triple(start, lang, line))
                    }
                }
            }

            // 按时间排序
            allLines.sortBy { it.first }

            // 按排序后的顺序显示
            allLines.forEach { (_, _, line) ->
                val hasWordTimestamps = line.words.isNotEmpty() && line.words.first().start != null

                line.start?.let { sb.append(formatTime(it)) }

                if (hasWordTimestamps) {
                    line.words.forEach { word ->
                        word.start?.let { sb.append("<${formatTime(it, 2).trim('[', ']')}>") }
                        sb.append(word.text)
                    }
                } else {
                    sb.append(line.words.joinToString("") { it.text })
                }

                sb.append("\n")
            }
        }

        return sb.toString()
    }

    private fun toSrt(langs: List<String>): String {
        val sb = StringBuilder()
        var index = 1

        if (langs.size == 1) {
            // 只有一种语言，按原方式处理
            val lang = langs[0]
            data[lang]?.forEach { line ->
                val startTime = line.start ?: return@forEach
                val endTime = line.end ?: (startTime + 5000)

                sb.appendLine(index++)
                sb.appendLine("${formatSrtTime(startTime)} --> ${formatSrtTime(endTime)}")
                sb.appendLine(line.words.joinToString("") { it.text })
                sb.appendLine()
            }
        } else {
            // 多种语言，按时间顺序混合显示
            val allLines = mutableListOf<Triple<Int, String, LyricsLine>>()

            langs.forEach { lang ->
                data[lang]?.forEach { line ->
                    line.start?.let { start ->
                        allLines.add(Triple(start, lang, line))
                    }
                }
            }

            // 按时间排序
            allLines.sortBy { it.first }

            // 按排序后的顺序显示
            allLines.forEach { (_, _, line) ->
                val startTime = line.start ?: return@forEach
                val endTime = line.end ?: (startTime + 5000)

                sb.appendLine(index++)
                sb.appendLine("${formatSrtTime(startTime)} --> ${formatSrtTime(endTime)}")
                sb.appendLine(line.words.joinToString("") { it.text })
                sb.appendLine()
            }
        }

        return sb.toString()
    }

    private fun toAss(langs: List<String>): String {
        val sb = StringBuilder()

        sb.appendLine("[Script Info]")
        sb.appendLine("Title: ${title ?: "Unknown"}")
        sb.appendLine("Original Script: LDDC")
        sb.appendLine("ScriptType: v4.00+")
        sb.appendLine()

        sb.appendLine("[V4+ Styles]")
        sb.appendLine("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding")
        sb.appendLine("Style: Default,Arial,20,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,2,2,10,10,10,1")
        sb.appendLine()

        sb.appendLine("[Events]")
        sb.appendLine("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")

        if (langs.size == 1) {
            // 只有一种语言，按原方式处理
            val lang = langs[0]
            data[lang]?.forEach { line ->
                val startTime = line.start ?: return@forEach
                val endTime = line.end ?: (startTime + 5000)
                val text = line.words.joinToString("") { it.text }

                sb.appendLine("Dialogue: 0,${formatAssTime(startTime)},${formatAssTime(endTime)},Default,,0,0,0,,$text")
            }
        } else {
            // 多种语言，按时间顺序混合显示
            val allLines = mutableListOf<Triple<Int, String, LyricsLine>>()

            langs.forEach { lang ->
                data[lang]?.forEach { line ->
                    line.start?.let { start ->
                        allLines.add(Triple(start, lang, line))
                    }
                }
            }

            // 按时间排序
            allLines.sortBy { it.first }

            // 按排序后的顺序显示
            allLines.forEach { (_, _, line) ->
                val startTime = line.start ?: return@forEach
                val endTime = line.end ?: (startTime + 5000)
                val text = line.words.joinToString("") { it.text }

                sb.appendLine("Dialogue: 0,${formatAssTime(startTime)},${formatAssTime(endTime)},Default,,0,0,0,,$text")
            }
        }

        return sb.toString()
    }

    private fun formatTime(ms: Int, decimalDigits: Int = 2): String {
        val minutes = ms / 1000 / 60
        val seconds = (ms / 1000) % 60
        val milliseconds = ms % 1000

        return when (decimalDigits) {
            2 -> String.format("[%02d:%02d.%02d]", minutes, seconds, milliseconds / 10)
            3 -> String.format("[%02d:%02d.%03d]", minutes, seconds, milliseconds)
            else -> String.format("[%02d:%02d]", minutes, seconds)
        }
    }

    private fun formatSrtTime(ms: Int): String {
        val hours = ms / 1000 / 60 / 60
        val minutes = (ms / 1000 / 60) % 60
        val seconds = (ms / 1000) % 60
        val milliseconds = ms % 1000

        return String.format("%02d:%02d:%02d,%03d", hours, minutes, seconds, milliseconds)
    }

    private fun formatAssTime(ms: Int): String {
        val hours = ms / 1000 / 60 / 60
        val minutes = (ms / 1000 / 60) % 60
        val seconds = (ms / 1000) % 60
        val centiseconds = (ms % 1000) / 10

        return String.format("%d:%02d:%02d.%02d", hours, minutes, seconds, centiseconds)
    }

    companion object
}
