package com.example.lddc.common.models.info

import com.example.lddc.common.models.enums.Source

data class LyricInfo(
    val source: Source,
    val songinfo: SongInfo,
    val id: String? = null,
    val accesskey: String? = null,
    val duration: Int? = null,
    val creator: String? = null,
    val score: Int? = null,
    val path: String? = null,
    val cached: Boolean = false
)
