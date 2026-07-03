package com.example.lddc.domain.convert

import com.example.lddc.common.models.enums.LyricsFormat
import com.example.lddc.common.models.lyrics.Lyrics

class ConvertLyricsUseCase {

    operator fun invoke(
        lyrics: Lyrics,
        targetFormat: LyricsFormat,
        languages: List<String> = listOf("orig")
    ): String {
        return lyrics.toFormat(targetFormat, languages)
    }

    fun getAvailableFormats(): List<LyricsFormat> {
        return listOf(
            LyricsFormat.VERBATIMLRC,
            LyricsFormat.LINEBYLINELRC,
            LyricsFormat.ENHANCEDLRC,
            LyricsFormat.SRT,
            LyricsFormat.ASS
        )
    }

}
