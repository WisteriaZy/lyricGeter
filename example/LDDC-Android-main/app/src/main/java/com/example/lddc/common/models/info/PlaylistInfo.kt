package com.example.lddc.common.models.info

import com.example.lddc.common.models.enums.Source

data class PlaylistInfo(
    val source: Source,
    val id: String,
    val name: String,
    val creator: String? = null,
    val imageUrl: String? = null,
    val description: String? = null,
    val songs: List<SongInfo> = emptyList()
)
