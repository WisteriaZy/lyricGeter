package com.example.lddc.core.api.base

import com.example.lddc.common.models.enums.SearchType
import com.example.lddc.common.models.info.AlbumInfo
import com.example.lddc.common.models.info.PlaylistInfo
import com.example.lddc.common.models.info.SongInfo
import com.example.lddc.common.models.lyrics.Lyrics

interface BaseLyricsApi {
    val source: com.example.lddc.common.models.enums.Source
    val supportedSearchTypes: List<SearchType>

    suspend fun search(
        keyword: String,
        searchType: SearchType,
        page: Int = 1
    ): List<SongInfo>

    suspend fun getLyrics(songInfo: SongInfo): Lyrics

    suspend fun getAlbum(albumId: String): AlbumInfo

    suspend fun getPlaylist(playlistId: String): PlaylistInfo
}
