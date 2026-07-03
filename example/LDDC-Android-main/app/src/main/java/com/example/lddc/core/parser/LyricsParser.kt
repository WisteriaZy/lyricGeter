package com.example.lddc.core.parser

import com.example.lddc.common.models.lyrics.LyricsLine

interface LyricsParser {
    fun parse(content: String): List<LyricsLine>
    fun supports(format: String): Boolean
}
