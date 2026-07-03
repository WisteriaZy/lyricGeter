package com.example.lddc.data.local.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "lyrics_cache")
data class LyricsCacheEntity(
    @PrimaryKey
    val songId: String,
    val source: String,
    val title: String?,
    val artist: String?,
    val album: String?,
    val lyricsJson: String,
    val timestamp: Long = System.currentTimeMillis()
)
