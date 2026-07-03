package com.example.lddc.domain.search

import com.example.lddc.common.models.enums.SearchType
import com.example.lddc.common.models.enums.Source
import com.example.lddc.data.repository.LyricsRepository
import com.example.lddc.data.repository.SearchHistoryRepository
import kotlinx.coroutines.flow.Flow

class SearchSongsUseCase(
    private val lyricsRepository: LyricsRepository,
    private val searchHistoryRepository: SearchHistoryRepository
) {
    operator fun invoke(
        keyword: String,
        source: Source = Source.MULTI,
        searchType: SearchType = SearchType.SONG,
        enabledSources: List<Source> = listOf(Source.NE, Source.QM, Source.KG),
        page: Int = 1
    ): Flow<LyricsRepository.SearchResult> {
        return lyricsRepository.searchLyrics(keyword, source, searchType, enabledSources, page)
    }

    suspend fun saveSearchHistory(keyword: String, searchType: SearchType) {
        if (keyword.isNotBlank()) {
            searchHistoryRepository.addSearchHistory(keyword, searchType)
        }
    }
}
