package com.example.lddc.core.api.impl

import android.util.Log
import com.example.lddc.common.models.enums.LyricsType
import com.example.lddc.common.models.enums.SearchType
import com.example.lddc.common.models.enums.Source
import com.example.lddc.common.models.info.AlbumInfo
import com.example.lddc.common.models.info.Artist
import com.example.lddc.common.models.info.LyricInfo
import com.example.lddc.common.models.info.PlaylistInfo
import com.example.lddc.common.models.info.SongInfo
import com.example.lddc.common.models.lyrics.Lyrics
import com.example.lddc.common.models.lyrics.LyricsLine
import com.example.lddc.core.api.base.BaseLyricsApi
import com.example.lddc.core.decryptor.QrcDecryptor
import com.example.lddc.core.parser.QrcParser
import io.ktor.client.HttpClient
import io.ktor.client.engine.cio.CIO
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.plugins.defaultRequest
import io.ktor.client.request.header
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.bodyAsText
import io.ktor.http.ContentType
import io.ktor.http.contentType
import io.ktor.serialization.kotlinx.json.json
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.int
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put
import kotlinx.serialization.json.putJsonObject

class QQMusicApi : BaseLyricsApi {

    companion object {
        private const val TAG = "QQMusicApi"
        private const val BASE_URL = "https://u.y.qq.com/cgi-bin/musicu.fcg"
    }

    override val source = Source.QM
    override val supportedSearchTypes = listOf(
        SearchType.SONG,
        SearchType.ALBUM,
        SearchType.SONGLIST
    )

    private val client = HttpClient(CIO) {
        install(ContentNegotiation) {
            json(Json {
                ignoreUnknownKeys = true
                isLenient = true
            })
        }
        defaultRequest {
            header("Cookie", "tmeLoginType=-1;")
            header("User-Agent", "okhttp/3.14.9")
        }
    }

    private var comm: MutableMap<String, String> = mutableMapOf(
        "ct" to "11",
        "cv" to "1003006",
        "v" to "1003006",
        "os_ver" to "15",
        "phonetype" to "24122RKC7C",
        "rom" to "Redmi/miro/miro:15/AE3A.240806.005/OS2.0.105.0.VOMCNXM:user/release-keys",
        "tmeAppID" to "qqmusiclight",
        "nettype" to "NETWORK_WIFI",
        "udid" to "0"
    )

    private var session: SessionData? = null
    private val initMutex = Mutex()

    data class SessionData(
        val uid: String,
        val sid: String,
        val userip: String
    )

    private suspend fun ensureInitialized() {
        if (session != null) return

        initMutex.withLock {
            if (session != null) return

            Log.d(TAG, "初始化QQ音乐Session...")

            val param = buildJsonObject {
                put("caller", 0)
                put("uid", "0")
                put("vkey", 0)
            }

            // 直接发送请求，不经过 makeRequest 避免递归
            val requestBody = buildJsonObject {
                putJsonObject("comm") {
                    comm.forEach { (k, v) -> put(k, v) }
                }
                putJsonObject("request") {
                    put("method", "GetSession")
                    put("module", "music.getSession.session")
                    put("param", param)
                }
            }

            try {
                val response = client.post(BASE_URL) {
                    contentType(ContentType.Application.Json)
                    setBody(requestBody.toString())
                }

                val responseText = response.bodyAsText()
                Log.d(TAG, "Session响应: ${responseText.take(300)}")

                val responseData = Json.parseToJsonElement(responseText).jsonObject

                val code = responseData["code"]?.jsonPrimitive?.int ?: -1
                val requestCode =
                    responseData["request"]?.jsonObject?.get("code")?.jsonPrimitive?.int ?: -1

                if (code != 0 || requestCode != 0) {
                    throw Exception("QQ音乐Session初始化失败: code=$code, requestCode=$requestCode")
                }

                val data = responseData["request"]?.jsonObject?.get("data")?.jsonObject
                val sessionData = data?.get("session")?.jsonObject

                session = SessionData(
                    uid = sessionData?.get("uid")?.jsonPrimitive?.content ?: "0",
                    sid = sessionData?.get("sid")?.jsonPrimitive?.content ?: "",
                    userip = sessionData?.get("userip")?.jsonPrimitive?.content ?: ""
                )

                comm["uid"] = session!!.uid
                comm["sid"] = session!!.sid
                comm["userip"] = session!!.userip

                Log.i(TAG, "Session初始化成功: uid=${session!!.uid}")
            } catch (e: Exception) {
                Log.e(TAG, "Session初始化失败", e)
                throw e
            }
        }
    }

    private suspend fun makeRequest(method: String, module: String, param: JsonObject): JsonObject {
        Log.d(TAG, "makeRequest: method=$method, module=$module")
        ensureInitialized()

        val requestBody = buildJsonObject {
            putJsonObject("comm") {
                comm.forEach { (k, v) -> put(k, v) }
            }
            putJsonObject("request") {
                put("method", method)
                put("module", module)
                put("param", param)
            }
        }

        Log.d(TAG, "请求体: ${requestBody.toString().take(200)}")

        try {
            val response = client.post(BASE_URL) {
                contentType(ContentType.Application.Json)
                setBody(requestBody.toString())
            }

            Log.d(TAG, "响应状态: ${response.status}")

            val responseText = response.bodyAsText()
            Log.d(TAG, "响应内容: ${responseText.take(500)}")

            val responseData = Json.parseToJsonElement(responseText).jsonObject

            val code = responseData["code"]?.jsonPrimitive?.int ?: -1
            val requestCode =
                responseData["request"]?.jsonObject?.get("code")?.jsonPrimitive?.int ?: -1

            Log.d(TAG, "响应code: $code, requestCode: $requestCode")

            if (code != 0 || requestCode != 0) {
                throw Exception("QQ音乐API请求错误: code=$code, requestCode=$requestCode")
            }

            return responseData["request"]?.jsonObject?.get("data")?.jsonObject
                ?: throw Exception("响应数据为空")
        } catch (e: Exception) {
            Log.e(TAG, "请求失败: method=$method", e)
            throw e
        }
    }

    override suspend fun search(
        keyword: String,
        searchType: SearchType,
        page: Int
    ): List<SongInfo> {
        return when (searchType) {
            SearchType.SONG -> searchSongs(keyword, page)
            SearchType.ALBUM -> searchAlbums()
            SearchType.SONGLIST -> searchPlaylists()
            else -> emptyList()
        }
    }

    private fun generateSearchId(): String {
        val random = java.util.Random()
        val part1 = (random.nextInt(20) * 18014398509481984L)
        val part2 = (random.nextInt(4194304) * 4294967296L)
        val part3 = (System.currentTimeMillis() % 86400000L)
        return (part1 + part2 + part3).toString()
    }

    private suspend fun searchSongs(keyword: String, page: Int): List<SongInfo> {
        Log.d(TAG, "搜索QQ音乐: keyword=$keyword, page=$page")

        val param = buildJsonObject {
            put("search_id", generateSearchId())
            put("remoteplace", "search.android.keyboard")
            put("query", keyword)
            put("search_type", 0)
            put("num_per_page", 20)
            put("page_num", page)
            put("highlight", 0)
            put("nqc_flag", 0)
            put("page_id", 1)
            put("grp", 1)
        }

        val response = makeRequest("DoSearchForQQMusicLite", "music.search.SearchCgiService", param)
        Log.d(TAG, "QQ音乐搜索响应: $response")

        val body = response["body"]?.jsonObject
        val itemSong = body?.get("item_song")?.jsonArray
        Log.d(TAG, "item_song: ${itemSong?.size ?: 0} items")

        if (itemSong == null) {
            Log.w(TAG, "QQ音乐搜索返回空结果")
            return emptyList()
        }

        return itemSong.mapNotNull { item ->
            val song = item.jsonObject
            val id = song["id"]?.jsonPrimitive?.content
            val mid = song["mid"]?.jsonPrimitive?.content ?: ""
            val title = song["title"]?.jsonPrimitive?.content ?: ""
            val subtitle = song["subtitle"]?.jsonPrimitive?.content ?: ""
            val singer = song["singer"]?.jsonArray?.joinToString("/") {
                it.jsonObject["name"]?.jsonPrimitive?.content ?: ""
            } ?: ""
            val album = song["album"]?.jsonObject?.get("name")?.jsonPrimitive?.content ?: ""
            val albumMid = song["album"]?.jsonObject?.get("mid")?.jsonPrimitive?.content
            val interval = song["interval"]?.jsonPrimitive?.intOrNull

            if (id.isNullOrEmpty()) {
                Log.w(TAG, "跳过没有ID的歌曲: $title")
                return@mapNotNull null
            }

            // 构建图片 URL - 使用专辑 mid
            val imageUrl = if (!albumMid.isNullOrEmpty()) {
                "https://y.qq.com/music/photo_new/T002R800x800M000${albumMid}.jpg?max_age=2592000"
            } else {
                ""
            }

            Log.d(TAG, "解析歌曲: id=$id, title=$title")

            SongInfo(
                source = source,
                id = id,
                mid = mid,
                title = title,
                subtitle = subtitle,
                artist = Artist.fromString(singer),
                album = album,
                duration = interval?.times(1000),
                imageUrl = imageUrl
            )
        }
    }

    private fun searchAlbums(): List<SongInfo> {
        return emptyList()
    }

    private fun searchPlaylists(): List<SongInfo> {
        return emptyList()
    }

    override suspend fun getLyrics(songInfo: SongInfo): Lyrics {
        // 对字符串进行base64编码
        val albumNameB64 = songInfo.album?.let {
            android.util.Base64.encodeToString(
                it.toByteArray(Charsets.UTF_8),
                android.util.Base64.NO_WRAP
            )
        }
        val singerNameB64 = android.util.Base64.encodeToString(
            songInfo.artist.toString().toByteArray(Charsets.UTF_8), android.util.Base64.NO_WRAP
        )
        val songNameB64 = songInfo.title?.let {
            android.util.Base64.encodeToString(
                it.toByteArray(Charsets.UTF_8),
                android.util.Base64.NO_WRAP
            )
        }

        val param = buildJsonObject {
            put("albumName", albumNameB64)
            put("crypt", 1)
            put("ct", 19)
            put("cv", 2111)
            put("interval", (songInfo.duration ?: 0) / 1000)
            put("lrc_t", 0)
            put("qrc", 1)
            put("qrc_t", 0)
            put("roma", 1)
            put("roma_t", 0)
            put("singerName", singerNameB64)
            put("songID", songInfo.id?.toIntOrNull() ?: 0)
            put("songName", songNameB64)
            put("trans", 1)
            put("trans_t", 0)
            put("type", 0)
        }

        val response = makeRequest("GetPlayLyricInfo", "music.musichallSong.PlayLyricInfo", param)

        val lyric = response["lyric"]?.jsonPrimitive?.content ?: ""
        val trans = response["trans"]?.jsonPrimitive?.content ?: ""
        val roma = response["roma"]?.jsonPrimitive?.content ?: ""
        // 注意：QQ音乐API返回的是 lrc_t 和 qrc_t，不是 lyric_t
        val lrcT = response["lrc_t"]?.jsonPrimitive?.content ?: "0"
        val qrcT = response["qrc_t"]?.jsonPrimitive?.content ?: "0"
        val transT = response["trans_t"]?.jsonPrimitive?.content ?: "0"
        val romaT = response["roma_t"]?.jsonPrimitive?.content ?: "0"

        Log.d(
            TAG,
            "歌词响应: lyric长度=${lyric.length}, trans长度=${trans.length}, roma长度=${roma.length}"
        )
        Log.d(TAG, "lrc_t=$lrcT, qrc_t=$qrcT, trans_t=$transT, roma_t=$romaT")

        val lyricsData = mutableMapOf<String, List<LyricsLine>>()
        val lyricsTypes = mutableMapOf<String, LyricsType>()
        var lyricsTags = mapOf<String, String>()

        // 处理原词 - 使用 qrc_t 或 lrc_t 判断是否有歌词
        val hasLyric = qrcT != "0" || lrcT != "0"
        if (lyric.isNotEmpty() && hasLyric) {
            try {
                val decodedLyric =
                    if (lyric.trimStart().startsWith("<?xml") || lyric.contains("<Lyric_1")) {
                        Log.d(TAG, "歌词是XML格式，无需解密")
                        lyric
                    } else {
                        QrcDecryptor.decryptString(lyric.toByteArray())
                    }
                val (tags, lines) = QrcParser().parseSmart(decodedLyric)
                lyricsData["orig"] = lines
                lyricsTags = tags
                lyricsTypes["orig"] = judgeLyricsType(lines)
                Log.d(TAG, "原词解析完成: ${lines.size}行, 类型=${lyricsTypes["orig"]}")
            } catch (e: Exception) {
                Log.e(TAG, "解析原词失败", e)
            }
        }

        // 处理翻译
        if (trans.isNotEmpty() && transT != "0") {
            try {
                val decodedTrans =
                    if (trans.trimStart().startsWith("<?xml") || trans.contains("<Lyric_1")) {
                        trans
                    } else {
                        QrcDecryptor.decryptString(trans.toByteArray())
                    }
                val (_, lines) = QrcParser().parseSmart(decodedTrans)
                lyricsData["ts"] = lines
                lyricsTypes["ts"] = judgeLyricsType(lines)
                Log.d(TAG, "翻译解析完成: ${lines.size}行, 类型=${lyricsTypes["ts"]}")
            } catch (e: Exception) {
                Log.e(TAG, "解析翻译失败", e)
            }
        }

        // 处理罗马音
        if (roma.isNotEmpty() && romaT != "0") {
            try {
                val decodedRoma =
                    if (roma.trimStart().startsWith("<?xml") || roma.contains("<Lyric_1")) {
                        roma
                    } else {
                        QrcDecryptor.decryptString(roma.toByteArray())
                    }
                val (_, lines) = QrcParser().parseSmart(decodedRoma)
                lyricsData["roma"] = lines
                lyricsTypes["roma"] = judgeLyricsType(lines)
                Log.d(TAG, "罗马音解析完成: ${lines.size}行, 类型=${lyricsTypes["roma"]}")
            } catch (e: Exception) {
                Log.e(TAG, "解析罗马音失败", e)
            }
        }

        val lyricInfo = LyricInfo(
            source = source,
            songinfo = songInfo,
            id = songInfo.id
        )

        Log.d(TAG, "歌词解析完成: 包含语言=${lyricsData.keys}, types=${lyricsTypes}")

        return Lyrics(
            info = lyricInfo,
            types = lyricsTypes,
            tags = lyricsTags,
            data = lyricsData
        )
    }

    /**
     * 判断歌词类型（参考PC端的 judge_lyrics_type）
     */
    private fun judgeLyricsType(lines: List<LyricsLine>): LyricsType {
        for (line in lines) {
            // 如果某一行有多个 word，则是逐字歌词
            if (line.words.size > 1) {
                return LyricsType.VERBATIM
            }
        }
        // 如果有时间戳，则是逐行歌词
        return if (lines.isNotEmpty() && lines.first().start != null) {
            LyricsType.LINEBYLINE
        } else {
            LyricsType.PlainText
        }
    }

    override suspend fun getAlbum(albumId: String): AlbumInfo {
        val param = buildJsonObject {
            put("albumMid", albumId)
        }

        val response = makeRequest("GetAlbumContent", "music.musichallAlbum.AlbumInfoServer", param)

        val albumInfo = response["albumInfo"]?.jsonObject
        val songList = response["songList"]?.jsonArray

        return AlbumInfo(
            source = source,
            id = albumId,
            name = albumInfo?.get("albumName")?.jsonPrimitive?.content ?: "",
            artist = albumInfo?.get("singerName")?.jsonPrimitive?.content?.let { Artist(it) },
            imageUrl = albumInfo?.get("albumPic")?.jsonPrimitive?.content,
            songs = songList?.mapNotNull { formatSongInfo(it.jsonObject) } ?: emptyList()
        )
    }

    override suspend fun getPlaylist(playlistId: String): PlaylistInfo {
        val param = buildJsonObject {
            put("disstid", playlistId)
            put("num", 100)
        }

        val response = makeRequest("GetDiss", "music.playlist.PlaylistBroker", param)

        val cdlist = response["cdlist"]?.jsonArray?.firstOrNull()?.jsonObject
        val songlist = cdlist?.get("songlist")?.jsonArray

        return PlaylistInfo(
            source = source,
            id = playlistId,
            name = cdlist?.get("dissname")?.jsonPrimitive?.content ?: "",
            creator = cdlist?.get("nick")?.jsonPrimitive?.content,
            imageUrl = cdlist?.get("logo")?.jsonPrimitive?.content,
            description = cdlist?.get("desc")?.jsonPrimitive?.content,
            songs = songlist?.mapNotNull { formatSongInfo(it.jsonObject) } ?: emptyList()
        )
    }

    private fun formatSongInfo(song: JsonObject): SongInfo? {
        val id = song["id"]?.jsonPrimitive?.content ?: return null
        val mid = song["mid"]?.jsonPrimitive?.content ?: return null
        val title = song["name"]?.jsonPrimitive?.content ?: return null
        val singer = song["singer"]?.jsonArray?.joinToString("/") {
            it.jsonObject["name"]?.jsonPrimitive?.content ?: ""
        } ?: ""
        val album = song["album"]?.jsonObject?.get("name")?.jsonPrimitive?.content ?: ""
        val albumMid = song["album"]?.jsonObject?.get("mid")?.jsonPrimitive?.content
        val interval = song["interval"]?.jsonPrimitive?.intOrNull

        // 构建图片 URL - 使用专辑 mid
        val imageUrl = if (!albumMid.isNullOrEmpty()) {
            "https://y.qq.com/music/photo_new/T002R800x800M000${albumMid}.jpg?max_age=2592000"
        } else {
            ""
        }

        return SongInfo(
            source = source,
            id = id,
            mid = mid,
            title = title,
            artist = Artist.fromString(singer),
            album = album,
            duration = interval?.times(1000),
            imageUrl = imageUrl
        )
    }
}
