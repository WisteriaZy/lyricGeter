package com.example.lddc.core.api

import com.example.lddc.common.models.enums.SearchType
import com.example.lddc.common.models.enums.Source
import com.example.lddc.common.models.info.SongInfo
import com.example.lddc.common.models.lyrics.Lyrics
import com.example.lddc.core.api.base.BaseLyricsApi
import com.example.lddc.core.api.impl.KugouApi
import com.example.lddc.core.api.impl.NetEaseApi
import com.example.lddc.core.api.impl.QQMusicApi
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope

class LyricsApiManager {

    private val apis: Map<Source, BaseLyricsApi> = mapOf(
        Source.NE to NetEaseApi(),
        Source.QM to QQMusicApi(),
        Source.KG to KugouApi()
    )

    suspend fun searchFromSource(
        source: Source,
        keyword: String,
        searchType: SearchType = SearchType.SONG,
        page: Int = 1
    ): List<SongInfo> {
        val api = apis[source] ?: throw IllegalArgumentException("不支持的数据源: $source")

        if (searchType !in api.supportedSearchTypes) {
            throw IllegalArgumentException("数据源 $source 不支持搜索类型: $searchType")
        }

        return api.search(keyword, searchType, page)
    }

    suspend fun getLyrics(songInfo: SongInfo): Lyrics {
        val api = apis[songInfo.source]
            ?: throw IllegalArgumentException("不支持的数据源: ${songInfo.source}")

        return api.getLyrics(songInfo)
    }

    suspend fun getLyricsFromAll(songInfo: SongInfo): Map<Source, Lyrics> {
        return coroutineScope {
            apis.map { (source, api) ->
                async {
                    try {
                        // 创建一个新的SongInfo，使用当前source
                        val searchSongInfo = songInfo.copy(source = source)
                        val results = api.search(searchSongInfo.title ?: "", SearchType.SONG, 1)

                        // 找到最匹配的歌曲
                        val matchedSong = results.firstOrNull { result ->
                            result.title == songInfo.title &&
                                    result.artist.toString() == songInfo.artist.toString()
                        } ?: results.firstOrNull()

                        if (matchedSong != null) {
                            source to api.getLyrics(matchedSong)
                        } else {
                            source to Lyrics(
                                info = com.example.lddc.common.models.info.LyricInfo(
                                    source = source,
                                    songinfo = songInfo
                                ),
                                data = emptyMap()
                            )
                        }
                    } catch (e: Exception) {
                        android.util.Log.e("LyricsApiManager", "获取歌词失败: $source", e)
                        source to Lyrics(
                            info = com.example.lddc.common.models.info.LyricInfo(
                                source = source,
                                songinfo = songInfo
                            ),
                            data = emptyMap()
                        )
                    }
                }
            }.awaitAll().toMap()
        }
    }

}
