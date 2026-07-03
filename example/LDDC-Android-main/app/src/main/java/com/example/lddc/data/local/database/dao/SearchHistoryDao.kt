package com.example.lddc.data.local.database.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.lddc.data.local.database.entity.SearchHistoryEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface SearchHistoryDao {

    @Query("SELECT * FROM search_history ORDER BY timestamp DESC LIMIT :limit")
    fun getRecentSearches(limit: Int = 20): Flow<List<SearchHistoryEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(searchHistory: SearchHistoryEntity)

    @Query("DELETE FROM search_history WHERE id = :id")
    suspend fun deleteById(id: Long)

    @Query("DELETE FROM search_history WHERE keyword = :keyword")
    suspend fun deleteByKeyword(keyword: String)

    @Query("DELETE FROM search_history")
    suspend fun clearAll()

    @Query("DELETE FROM search_history WHERE timestamp < :timestamp")
    suspend fun deleteOlderThan(timestamp: Long)
}
