package com.example.lddc.common.models.lyrics

data class LyricsLine(
    val start: Int? = null,
    val end: Int? = null,
    val words: List<LyricsWord> = emptyList()
)

