package com.example.lddc.data.local.database.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.example.lddc.data.local.database.entity.LyricsCacheEntity

@Dao
interface LyricsCacheDao {

    @Query("SELECT * FROM lyrics_cache WHERE songId = :songId AND source = :source")
    suspend fun getLyrics(songId: String, source: String): LyricsCacheEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(lyricsCache: LyricsCacheEntity)

    @Query("DELETE FROM lyrics_cache WHERE songId = :songId AND source = :source")
    suspend fun delete(songId: String, source: String)

    @Query("DELETE FROM lyrics_cache WHERE timestamp < :timestamp")
    suspend fun deleteOlderThan(timestamp: Long)

    @Query("SELECT * FROM lyrics_cache WHERE title LIKE '%' || :keyword || '%' OR artist LIKE '%' || :keyword || '%'")
    suspend fun searchByKeyword(keyword: String): List<LyricsCacheEntity>
}
