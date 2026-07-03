package com.example.lddc.common.models.lyrics

data class LyricsWord(
    val start: Int? = null,
    val end: Int? = null,
    val text: String
)

data class FSLyricsWord(
    val start: Int,
    val end: Int,
    val text: String
)
