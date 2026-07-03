package com.example.lddc.common.models.info

import com.example.lddc.common.models.enums.Source

data class AlbumInfo(
    val source: Source,
    val id: String,
    val name: String,
    val artist: Artist? = null,
    val imageUrl: String? = null,
    val songs: List<SongInfo> = emptyList()
)
