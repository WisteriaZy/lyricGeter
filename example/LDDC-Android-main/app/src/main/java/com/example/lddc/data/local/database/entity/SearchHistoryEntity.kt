package com.example.lddc.data.local.database.entity

import androidx.room.Entity
import androidx.room.PrimaryKey

@Entity(tableName = "search_history")
data class SearchHistoryEntity(
    @PrimaryKey(autoGenerate = true)
    val id: Long = 0,
    val keyword: String,
    val searchType: String,
    val timestamp: Long = System.currentTimeMillis()
)
