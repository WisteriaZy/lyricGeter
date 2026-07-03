package com.example.lddc.common.models.info

import kotlinx.serialization.Serializable

@Serializable
class Artist(
    private val artists: List<String>
) : List<String> by artists {

    constructor(artist: String) : this(listOf(artist))

    override fun toString(): String = artists.joinToString("/")

    fun toString(separator: String): String = artists.joinToString(separator)

    companion object {
        fun fromString(artistStr: String?): Artist {
            if (artistStr.isNullOrBlank()) return Artist(emptyList())

            val uniqueArtists = artistStr
                .split("/", "\\", "&", ",", "、")
                .map { it.trim() }
                .filter { it.isNotEmpty() }
                .distinct()

            return Artist(uniqueArtists)
        }
    }
}
