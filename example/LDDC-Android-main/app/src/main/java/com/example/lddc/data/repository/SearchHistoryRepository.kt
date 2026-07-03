package com.example.lddc.data.repository

import com.example.lddc.common.models.enums.SearchType
import com.example.lddc.data.local.database.dao.SearchHistoryDao
import com.example.lddc.data.local.database.entity.SearchHistoryEntity
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

class SearchHistoryRepository(
    private val searchHistoryDao: SearchHistoryDao
) {

    fun getRecentSearches(limit: Int = 20): Flow<List<SearchHistoryItem>> {
        return searchHistoryDao.getRecentSearches(limit).map { entities ->
            entities.map { entity ->
                SearchHistoryItem(
                    id = entity.id,
                    keyword = entity.keyword,
                    searchType = SearchType.valueOf(entity.searchType),
                    timestamp = entity.timestamp
                )
            }
        }
    }

    suspend fun addSearchHistory(keyword: String, searchType: SearchType) {
        // 先删除相同关键词的旧记录（去重）
        searchHistoryDao.deleteByKeyword(keyword)

        val entity = SearchHistoryEntity(
            keyword = keyword,
            searchType = searchType.name
        )
        searchHistoryDao.insert(entity)
    }

    suspend fun deleteSearchHistory(id: Long) {
        searchHistoryDao.deleteById(id)
    }

    suspend fun clearAllHistory() {
        searchHistoryDao.clearAll()
    }

}

data class SearchHistoryItem(
    val id: Long,
    val keyword: String,
    val searchType: SearchType,
    val timestamp: Long
)
