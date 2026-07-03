package com.example.lddc.domain.search

import com.example.lddc.data.repository.SearchHistoryRepository
import kotlinx.coroutines.flow.Flow

class GetSearchHistoryUseCase(
    private val searchHistoryRepository: SearchHistoryRepository
) {
    operator fun invoke(limit: Int = 20): Flow<List<com.example.lddc.data.repository.SearchHistoryItem>> {
        return searchHistoryRepository.getRecentSearches(limit)
    }
}
