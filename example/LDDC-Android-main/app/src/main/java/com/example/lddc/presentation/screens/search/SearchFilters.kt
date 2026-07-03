package com.example.lddc.presentation.screens.search

import com.example.lddc.common.models.enums.Source

/**
 * 搜索筛选条件
 *
 * @param keyword 搜索关键词
 * @param songName 按歌曲名筛选
 * @param artist 按歌手名筛选
 * @param album 按专辑名筛选
 * @param platforms 平台筛选（多选）
 */
data class SearchFilters(
    val keyword: String = "",
    val songName: String = "",
    val artist: String = "",
    val album: String = "",
    val platforms: Set<Source> = emptySet()
) {
    /**
     * 检查是否有活跃的筛选条件
     */
    fun hasActiveFilters(): Boolean {
        return songName.isNotBlank() ||
                artist.isNotBlank() ||
                album.isNotBlank() ||
                platforms.isNotEmpty()
    }

    /**
     * 获取活跃筛选条件的数量
     */
    fun getActiveFilterCount(): Int {
        var count = 0
        if (songName.isNotBlank()) count++
        if (artist.isNotBlank()) count++
        if (album.isNotBlank()) count++
        if (platforms.isNotEmpty()) count++
        return count
    }
}
