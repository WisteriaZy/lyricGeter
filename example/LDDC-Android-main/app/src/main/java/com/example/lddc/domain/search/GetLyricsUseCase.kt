package com.example.lddc.domain.search

import com.example.lddc.common.models.info.SongInfo
import com.example.lddc.common.models.lyrics.Lyrics
import com.example.lddc.data.repository.LyricsRepository

class GetLyricsUseCase(
    private val lyricsRepository: LyricsRepository
) {
    suspend operator fun invoke(
        songInfo: SongInfo,
        useCache: Boolean = true
    ): Result<Lyrics> {
        return lyricsRepository.getLyrics(songInfo, useCache)
    }

}
