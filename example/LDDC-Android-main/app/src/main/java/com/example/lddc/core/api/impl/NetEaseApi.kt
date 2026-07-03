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
import com.example.lddc.core.api.NetEaseDeviceIds
import com.example.lddc.core.api.base.BaseLyricsApi
import com.example.lddc.core.decryptor.EapiDecryptor
import com.example.lddc.core.parser.LrcParser
import com.example.lddc.core.parser.YrcParser
import io.ktor.client.HttpClient
import io.ktor.client.engine.cio.CIO
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.headers
import io.ktor.client.request.post
import io.ktor.client.request.setBody
import io.ktor.client.statement.readBytes
import io.ktor.http.ContentType
import io.ktor.http.content.TextContent
import io.ktor.http.setCookie
import io.ktor.serialization.kotlinx.json.json
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

class NetEaseApi : BaseLyricsApi {

    companion object {
        private const val TAG = "NetEaseApi"
        private const val BASE_URL = "https://interface.music.163.com"
        private const val APP_VERSION = "3.1.3.203419"

        private val DEVICE_MODELS = listOf(
            "MS-iCraft B760M WIFI",
            "ASUS ROG STRIX Z790",
            "MSI MAG B550 TOMAHAWK",
            "ASRock X670E Taichi"
        )
    }

    override val source = Source.NE
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
        engine {
            requestTimeout = 10000
        }
    }

    private var auth: NetEaseAuth? = null
    private val initMutex = Mutex()

    data class NetEaseAuth(
        val userId: String,
        val cookies: Map<String, String>,
        val expireTime: Long
    ) {
        val isValid: Boolean
            get() = System.currentTimeMillis() < expireTime
    }

    private suspend fun ensureInitialized() = withContext(Dispatchers.IO) {
        if (auth?.isValid == true) return@withContext

        initMutex.withLock {
            if (auth?.isValid == true) return@withLock

            // 使用预定义的设备ID
            val deviceId = NetEaseDeviceIds.getRandomDeviceId()
            val macAddress = generateMacAddress()
            val randomStr = (1..8).map { ('A'..'Z').random() }.joinToString("")
            val hashPart = generateRandomHex(32)
            val clientSign = "$macAddress@@@$randomStr@@@@@@$hashPart"

            val preCookies = mapOf(
                "os" to "pc",
                "deviceId" to deviceId,
                "osver" to "Microsoft-Windows-10--build-${(200..300).random()}00-64bit",
                "clientSign" to clientSign,
                "channel" to "netease",
                "mode" to DEVICE_MODELS.random(),
                "appver" to APP_VERSION
            )

            val params = mapOf(
                "username" to EapiDecryptor.getAnonymousUsername(deviceId),
                "e_r" to true,
                "header" to buildParamsHeader(preCookies)
            )

            val path = "/eapi/register/anonimous"
            val encryptedParams = EapiDecryptor.encryptParams(path.replace("eapi", "api"), params)

            Log.i(TAG, "尝试游客登录")

            try {
                val response = client.post("$BASE_URL$path") {
                    headers {
                        buildHeaders(preCookies).forEach { (key, value) ->
                            append(key, value)
                        }
                    }
                    setBody(TextContent(encryptedParams, ContentType.Application.FormUrlEncoded))
                }

                val responseData = response.readBytes()
                if (responseData.isEmpty()) {
                    throw Exception("网易云音乐API返回空响应")
                }

                val decryptedJson = EapiDecryptor.decryptResponse(responseData)
                val jsonResponse = Json.parseToJsonElement(decryptedJson).jsonObject

                val code = jsonResponse["code"]?.jsonPrimitive?.intOrNull ?: -1
                Log.i(TAG, "游客登录code: $code")

                if (code == 200) {
                    val userId = jsonResponse["userId"]?.jsonPrimitive?.content ?: ""

                    val cookies = mutableMapOf(
                        "WEVNSM" to "1.0.0",
                        "os" to preCookies["os"]!!,
                        "deviceId" to preCookies["deviceId"]!!,
                        "osver" to preCookies["osver"]!!,
                        "clientSign" to preCookies["clientSign"]!!,
                        "channel" to preCookies["channel"]!!,
                        "mode" to preCookies["mode"]!!,
                        "appver" to preCookies["appver"]!!,
                        "WNMCID" to "${
                            (1..6).map { ('a'..'z').random() }.joinToString("")
                        }.${System.currentTimeMillis() - (1000..10000).random()}.01.0"
                    )

                    response.setCookie().forEach { cookie ->
                        cookies[cookie.name] = cookie.value
                    }

                    auth = NetEaseAuth(
                        userId = userId,
                        cookies = cookies,
                        expireTime = System.currentTimeMillis() / 1000 + 864000
                    )

                    Log.i(TAG, "游客登录成功")
                } else {
                    val message = jsonResponse["message"]?.jsonPrimitive?.content ?: "未知错误"
                    throw Exception("游客登录失败: code=$code, message=$message")
                }
            } catch (e: Exception) {
                Log.e(TAG, "游客登录失败", e)
                throw e
            }
        }
    }

    private fun buildParamsHeader(cookies: Map<String, String>): String {
        val clientSign = cookies["clientSign"] ?: ""
        val os = cookies["os"] ?: "pc"
        val appver = cookies["appver"] ?: APP_VERSION
        val deviceId = cookies["deviceId"] ?: ""
        val osver = cookies["osver"] ?: ""
        return "{\"clientSign\":\"$clientSign\",\"os\":\"$os\",\"appver\":\"$appver\",\"deviceId\":\"$deviceId\",\"requestId\":0,\"osver\":\"$osver\"}"
    }

    private fun buildHeaders(cookies: Map<String, String>): Map<String, String> {
        val headers = mutableMapOf(
            "accept" to "*/*",
            "content-type" to "application/x-www-form-urlencoded",
            "mconfig-info" to "{\"IuRPVVmc3WWul9fT\":{\"version\":733184,\"appver\":\"3.1.3.203419\"}}",
            "origin" to "orpheus://orpheus",
            "user-agent" to "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Safari/537.36 Chrome/91.0.4472.164 NeteaseMusicDesktop/3.1.3.203419",
            "sec-ch-ua" to "\"Chromium\";v=\"91\"",
            "sec-ch-ua-mobile" to "?0",
            "sec-fetch-site" to "cross-site",
            "sec-fetch-mode" to "cors",
            "sec-fetch-dest" to "empty",
            "accept-language" to "en-US,en;q=0.9"
        )

        val cookieString = cookies.entries.joinToString("; ") { "${it.key}=${it.value}" }
        headers["cookie"] = cookieString

        return headers
    }

    private suspend fun makeRequest(path: String, params: MutableMap<String, Any?>): JsonObject =
        withContext(Dispatchers.IO) {
            ensureInitialized()

            params["e_r"] = true
            params["header"] = buildParamsHeader(auth!!.cookies)

            val encryptedParams = EapiDecryptor.encryptParams(path.replace("eapi", "api"), params)

            val response = client.post("$BASE_URL$path") {
                headers {
                    buildHeaders(auth!!.cookies).forEach { (key, value) ->
                        append(key, value)
                    }
                }
                setBody(TextContent(encryptedParams, ContentType.Application.FormUrlEncoded))
            }

            val responseData = response.readBytes()
            if (responseData.isEmpty()) {
                throw Exception("网易云音乐API返回空响应")
            }

            val decryptedJson = EapiDecryptor.decryptResponse(responseData)
            val jsonResponse = Json.parseToJsonElement(decryptedJson).jsonObject

            val code = jsonResponse["code"]?.jsonPrimitive?.intOrNull ?: -1
            if (code != 200) {
                val message = jsonResponse["message"]?.jsonPrimitive?.content ?: "未知错误"
                throw Exception("API请求错误: code=$code, message=$message")
            }

            jsonResponse
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

    private suspend fun searchSongs(keyword: String, page: Int): List<SongInfo> {
        val params = mutableMapOf<String, Any?>(
            "keyword" to keyword,
            "scene" to "NORMAL",
            "needCorrect" to "true",
            "offset" to ((page - 1) * 20).toString(),
            "limit" to "20"
        )

        val response = makeRequest("/eapi/search/song/list/page", params)
        val data = response["data"]?.jsonObject ?: return emptyList()
        val resources = data["resources"]?.jsonArray ?: return emptyList()

        return resources.mapNotNull { resourceJson ->
            val resource = resourceJson.jsonObject
            val baseInfo = resource["baseInfo"]?.jsonObject
            val simpleSongData = baseInfo?.get("simpleSongData")?.jsonObject
                ?: baseInfo?.get("songData")?.jsonObject
                ?: return@mapNotNull null

            val id = when (val idValue = simpleSongData["id"]) {
                is kotlinx.serialization.json.JsonPrimitive -> idValue.content
                else -> idValue?.toString() ?: ""
            }
            if (id.isEmpty()) return@mapNotNull null

            val name = simpleSongData["name"]?.jsonPrimitive?.content ?: ""
            val alia = simpleSongData["alia"]?.jsonArray?.firstOrNull()?.jsonPrimitive?.content ?: ""
            val artists = simpleSongData["ar"]?.jsonArray?.mapNotNull {
                it.jsonObject["name"]?.jsonPrimitive?.content
            } ?: emptyList()
            val album = simpleSongData["al"]?.jsonObject?.get("name")?.jsonPrimitive?.content ?: ""
            val albumImage = simpleSongData["al"]?.jsonObject?.get("picUrl")?.jsonPrimitive?.content ?: ""
            val duration = when (val dt = simpleSongData["dt"]) {
                is kotlinx.serialization.json.JsonPrimitive -> dt.intOrNull
                else -> null
            }

            SongInfo(
                source = source,
                id = id,
                title = name,
                subtitle = alia,
                artist = Artist(artists),
                album = album,
                duration = duration,
                imageUrl = albumImage
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
        Log.d(TAG, "获取歌词: songId=${songInfo.id}, title=${songInfo.title}")

        val params = mutableMapOf<String, Any?>(
            "id" to (songInfo.id ?: ""),
            "lv" to "-1",
            "tv" to "-1",
            "rv" to "-1",
            "yv" to "-1"
        )

        val response = makeRequest("/eapi/song/lyric/v1", params)
        Log.d(TAG, "歌词响应: $response")

        val lyricsData = mutableMapOf<String, List<LyricsLine>>()
        val lyricsTypes = mutableMapOf<String, LyricsType>()

        // 使用PC端相同的映射表顺序
        val mappingTable = if (response.containsKey("yrc")) {
            val yrcObj = response["yrc"]?.jsonObject
            val yrcContent = yrcObj?.get("lyric")?.jsonPrimitive?.content
            if (!yrcContent.isNullOrEmpty()) {
                listOf(
                    "orig" to "yrc",
                    "ts" to "tlyric",
                    "roma" to "romalrc",
                    "orig_lrc" to "lrc"
                )
            } else {
                listOf(
                    "orig" to "lrc",
                    "ts" to "tlyric",
                    "roma" to "romalrc"
                )
            }
        } else {
            listOf(
                "orig" to "lrc",
                "ts" to "tlyric",
                "roma" to "romalrc"
            )
        }

        for ((key, value) in mappingTable) {
            if (!response.containsKey(value)) continue

            val lyricObj = response[value]?.jsonObject
            val lyricContent = lyricObj?.get("lyric")?.jsonPrimitive?.content
            Log.d(TAG, "$value 歌词: ${lyricContent?.take(100) ?: "null"}")

            if (!lyricContent.isNullOrEmpty()) {
                try {
                    val (lines, type) = if (value == "yrc") {
                        YrcParser().parseWithType(lyricContent)
                    } else {
                        LrcParser().parseWithType(lyricContent)
                    }
                    lyricsData[key] = lines
                    lyricsTypes[key] = type
                    Log.d(TAG, "$value 解析成功，类型: $type")
                } catch (e: Exception) {
                    Log.e(TAG, "解析$value 失败", e)
                }
            }
        }

        Log.d(TAG, "歌词数据keys: ${lyricsData.keys}")

        val lyricInfo = LyricInfo(
            source = source,
            songinfo = songInfo,
            id = songInfo.id
        )

        return Lyrics(
            info = lyricInfo,
            types = lyricsTypes,
            data = lyricsData
        )
    }

    override suspend fun getAlbum(albumId: String): AlbumInfo {
        val params = mutableMapOf<String, Any?>("id" to albumId)
        val response = makeRequest("/eapi/v3/album", params)

        val album = response["album"]?.jsonObject
        val songs = response["songs"]?.jsonArray

        return AlbumInfo(
            source = source,
            id = albumId,
            name = album?.get("name")?.jsonPrimitive?.content ?: "",
            artist = album?.get("artist")?.jsonObject?.get("name")?.jsonPrimitive?.content?.let {
                Artist(
                    it
                )
            },
            imageUrl = album?.get("picUrl")?.jsonPrimitive?.content,
            songs = songs?.mapNotNull { formatSongInfo(it.jsonObject) } ?: emptyList()
        )
    }

    override suspend fun getPlaylist(playlistId: String): PlaylistInfo {
        val params = mutableMapOf<String, Any?>(
            "id" to playlistId,
            "n" to 100000,
            "s" to 8
        )
        val response = makeRequest("/eapi/v6/playlist/detail", params)

        val playlist = response["playlist"]?.jsonObject
        val tracks = playlist?.get("tracks")?.jsonArray

        return PlaylistInfo(
            source = source,
            id = playlistId,
            name = playlist?.get("name")?.jsonPrimitive?.content ?: "",
            creator = playlist?.get("creator")?.jsonObject?.get("nickname")?.jsonPrimitive?.content,
            imageUrl = playlist?.get("coverImgUrl")?.jsonPrimitive?.content,
            description = playlist?.get("description")?.jsonPrimitive?.content,
            songs = tracks?.mapNotNull { formatSongInfo(it.jsonObject) } ?: emptyList()
        )
    }

    private fun formatSongInfo(song: JsonObject): SongInfo? {
        val id = song["id"]?.jsonPrimitive?.content ?: return null
        val name = song["name"]?.jsonPrimitive?.content ?: return null
        val artists = song["ar"]?.jsonArray?.mapNotNull {
            it.jsonObject["name"]?.jsonPrimitive?.content
        } ?: emptyList()
        val album = song["al"]?.jsonObject?.get("name")?.jsonPrimitive?.content ?: ""
        val albumImage = song["al"]?.jsonObject?.get("picUrl")?.jsonPrimitive?.content ?: ""
        val duration = song["dt"]?.jsonPrimitive?.intOrNull

        return SongInfo(
            source = source,
            id = id,
            title = name,
            artist = Artist(artists),
            album = album,
            duration = duration,
            imageUrl = albumImage
        )
    }

    private fun generateMacAddress(): String {
        return (1..6).joinToString(":") { "%02X".format((0..255).random()) }
    }

    private fun generateRandomHex(length: Int): String {
        val chars = "0123456789abcdef"
        return (1..length).map { chars.random() }.joinToString("")
    }
}
