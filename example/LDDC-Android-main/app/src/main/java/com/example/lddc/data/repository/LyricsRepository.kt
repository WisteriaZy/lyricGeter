package com.example.lddc.data.repository

import android.util.Log
import com.example.lddc.common.models.enums.SearchType
import com.example.lddc.common.models.enums.Source
import com.example.lddc.common.models.info.SongInfo
import com.example.lddc.common.models.lyrics.Lyrics
import com.example.lddc.common.models.lyrics.LyricsLine
import com.example.lddc.common.models.lyrics.LyricsWord
import com.example.lddc.core.api.LyricsApiManager
import com.example.lddc.data.local.database.dao.LyricsCacheDao
import com.example.lddc.data.local.database.entity.LyricsCacheEntity
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.addJsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonArray

class LyricsRepository(
    private val apiManager: LyricsApiManager,
    private val lyricsCacheDao: LyricsCacheDao
) {
    companion object {
        private const val TAG = "LyricsRepository"
        private const val CACHE_DURATION_MS = 7 * 24 * 60 * 60 * 1000L // 7天
    }

    /**
     * 多线程并行搜索歌词
     * 根据CPU核心数动态决定线程数
     */
    fun searchLyrics(
        keyword: String,
        source: Source = Source.MULTI,
        searchType: SearchType = SearchType.SONG,
        enabledSources: List<Source> = listOf(Source.NE, Source.QM, Source.KG),
        page: Int = 1
    ): Flow<SearchResult> = flow {
        emit(SearchResult.Loading)

        try {
            val results = if (source == Source.MULTI) {
                // 使用多线程并行搜索多个平台
                searchMultiSourceParallel(keyword, searchType, enabledSources, page)
            } else {
                // 检查单个源是否启用
                if (source in enabledSources) {
                    mapOf(source to apiManager.searchFromSource(source, keyword, searchType, page))
                } else {
                    emptyMap()
                }
            }

            emit(SearchResult.Success(results))
        } catch (e: Exception) {
            Log.e(TAG, "搜索失败", e)
            emit(SearchResult.Error(e.message ?: "搜索失败"))
        }
    }

    /**
     * 并行搜索多个平台
     * 使用协程并行搜索，线程数等于实际启用的源数量
     */
    private suspend fun searchMultiSourceParallel(
        keyword: String,
        searchType: SearchType,
        enabledSources: List<Source>,
        page: Int = 1
    ): Map<Source, List<SongInfo>> {
        // 过滤掉 MULTI，只保留实际搜索源
        val actualSources = enabledSources.filter { it != Source.MULTI && it != Source.LOCAL }

        if (actualSources.isEmpty()) {
            return emptyMap()
        }

        // 线程数等于实际启用的源数量
        val threadCount = actualSources.size
        Log.d(TAG, "使用 $threadCount 个协程并行搜索 ${actualSources.size} 个平台，第 $page 页")

        return coroutineScope {
            // 使用 async 并行搜索所有平台
            val deferredResults = actualSources.map { searchSource ->
                async {
                    try {
                        Log.d(TAG, "开始搜索: $searchSource, 第 $page 页")
                        val sourceResults = apiManager.searchFromSource(searchSource, keyword, searchType, page)
                        if (sourceResults.isNotEmpty()) {
                            Log.d(TAG, "搜索完成: $searchSource, 第 $page 页, 找到 ${sourceResults.size} 首歌曲")
                            searchSource to sourceResults
                        } else {
                            null
                        }
                    } catch (e: Exception) {
                        Log.e(TAG, "搜索失败: $searchSource, 第 $page 页", e)
                        null
                    }
                }
            }

            // 等待所有搜索完成并收集结果
            deferredResults.awaitAll()
                .filterNotNull()
                .toMap()
        }.also {
            Log.d(TAG, "并行搜索完成，共找到 ${it.size} 个平台的结果")
        }
    }

    suspend fun getLyrics(songInfo: SongInfo, useCache: Boolean = true): Result<Lyrics> {
        // 检查缓存
        if (useCache) {
            val cachedLyrics = getCachedLyrics(songInfo)
            if (cachedLyrics != null) {
                Log.d(TAG, "使用缓存歌词: ${songInfo.title}")
                return Result.success(cachedLyrics)
            }
        }

        // 从API获取
        return try {
            val lyrics = apiManager.getLyrics(songInfo)

            // 缓存歌词
            if (lyrics.isNotEmpty()) {
                cacheLyrics(songInfo, lyrics)
            }

            Result.success(lyrics)
        } catch (e: Exception) {
            Log.e(TAG, "获取歌词失败", e)
            Result.failure(e)
        }
    }

    suspend fun getLyricsFromAll(songInfo: SongInfo): Map<Source, Result<Lyrics>> {
        return apiManager.getLyricsFromAll(songInfo).mapValues { (_, lyrics) ->
            if (lyrics.isNotEmpty()) {
                Result.success(lyrics)
            } else {
                Result.failure(Exception("未找到歌词"))
            }
        }
    }

    private suspend fun getCachedLyrics(songInfo: SongInfo): Lyrics? {
        val cached = lyricsCacheDao.getLyrics(
            songId = songInfo.id ?: return null,
            source = songInfo.source.name
        ) ?: return null

        // 检查缓存是否过期
        if (System.currentTimeMillis() - cached.timestamp > CACHE_DURATION_MS) {
            lyricsCacheDao.delete(cached.songId, cached.source)
            return null
        }

        // 检查 lyricsJson 是否为 null 或 "null" 字符串
        if (cached.lyricsJson.isNullOrBlank() || cached.lyricsJson == "null") {
            lyricsCacheDao.delete(cached.songId, cached.source)
            return null
        }

        val lyrics = parseLyricsFromJson(cached.lyricsJson, songInfo)
        // 如果解析失败，删除损坏的缓存
        if (lyrics == null) {
            lyricsCacheDao.delete(cached.songId, cached.source)
            Log.d(TAG, "删除损坏的缓存: ${songInfo.title}")
        }
        return lyrics
    }

    private suspend fun cacheLyrics(songInfo: SongInfo, lyrics: Lyrics) {
        try {
            val lyricsJson = lyricsToJson(lyrics)

            val entity = LyricsCacheEntity(
                songId = songInfo.id ?: return,
                source = songInfo.source.name,
                title = songInfo.title,
                artist = songInfo.artist?.toString(),
                album = songInfo.album,
                lyricsJson = lyricsJson
            )

            lyricsCacheDao.insert(entity)
            Log.d(TAG, "歌词已缓存: ${songInfo.title}")
        } catch (e: Exception) {
            Log.e(TAG, "缓存歌词失败", e)
        }
    }

    private fun lyricsToJson(lyrics: Lyrics): String {
        return buildJsonObject {
            put("info", buildJsonObject {
                put("source", lyrics.source.name)
                put("id", lyrics.id)
                put("title", lyrics.title)
                put("artist", lyrics.artist?.toString())
                put("album", lyrics.album)
            })
            put(
                "tags",
                JsonObject(lyrics.tags.mapValues { (_, v) ->
                    kotlinx.serialization.json.JsonPrimitive(v)
                })
            )
            put("types", buildJsonObject {
                lyrics.types.forEach { (lang, type) ->
                    put(lang, type.name)
                }
            })
            put("data", buildJsonObject {
                lyrics.data.forEach { (lang, lines) ->
                    putJsonArray(lang) {
                        lines.forEach { line ->
                            addJsonObject {
                                put("start", line.start)
                                put("end", line.end)
                                putJsonArray("words") {
                                    line.words.forEach { word ->
                                        addJsonObject {
                                            put("start", word.start)
                                            put("end", word.end)
                                            put("text", word.text)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            })
        }.toString()
    }

    private fun parseLyricsFromJson(json: String, songInfo: SongInfo): Lyrics? {
        return try {
            val jsonObject = Json.parseToJsonElement(json).jsonObject
            val dataObject = jsonObject["data"]?.jsonObject ?: return null

            val lyricsData = mutableMapOf<String, List<LyricsLine>>()
            val lyricsTypes =
                mutableMapOf<String, com.example.lddc.common.models.enums.LyricsType>()

            // 解析types
            jsonObject["types"]?.jsonObject?.forEach { (lang, typeJson) ->
                val typeName = typeJson.jsonPrimitive.content
                val type = com.example.lddc.common.models.enums.LyricsType.valueOf(typeName)
                lyricsTypes[lang] = type
            }

            dataObject.forEach { (lang, linesJson) ->
                val lines = (linesJson as? JsonArray)?.map { lineJson ->
                    val lineObj = lineJson.jsonObject
                    val words = (lineObj["words"] as? JsonArray)?.map { wordJson ->
                        val wordObj = wordJson.jsonObject
                        LyricsWord(
                            start = wordObj["start"]?.let { if (it is JsonNull) null else it.jsonPrimitive.int },
                            end = wordObj["end"]?.let { if (it is JsonNull) null else it.jsonPrimitive.int },
                            text = wordObj["text"]?.jsonPrimitive?.content ?: ""
                        )
                    } ?: emptyList()

                    LyricsLine(
                        start = lineObj["start"]?.let { if (it is JsonNull) null else it.jsonPrimitive.int },
                        end = lineObj["end"]?.let { if (it is JsonNull) null else it.jsonPrimitive.int },
                        words = words
                    )
                } ?: emptyList()

                lyricsData[lang] = lines
            }

            Lyrics(
                info = com.example.lddc.common.models.info.LyricInfo(
                    source = songInfo.source,
                    songinfo = songInfo
                ),
                types = lyricsTypes,
                data = lyricsData
            )
        } catch (e: Exception) {
            Log.e(TAG, "解析缓存歌词失败", e)
            null
        }
    }

    sealed class SearchResult {
        object Loading : SearchResult()
        data class Success(val results: Map<Source, List<SongInfo>>) : SearchResult()
        data class Error(val message: String) : SearchResult()
    }
}
