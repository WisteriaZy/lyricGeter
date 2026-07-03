package com.example.lddc.core.api.impl

import android.util.Base64
import android.util.Log
import com.example.lddc.common.models.enums.SearchType
import com.example.lddc.common.models.enums.Source
import com.example.lddc.common.models.info.AlbumInfo
import com.example.lddc.common.models.info.Artist
import com.example.lddc.common.models.info.LyricInfo
import com.example.lddc.common.models.info.PlaylistInfo
import com.example.lddc.common.models.info.SongInfo
import com.example.lddc.common.models.lyrics.Lyrics
import com.example.lddc.core.api.base.BaseLyricsApi
import com.example.lddc.core.decryptor.KrcDecryptor
import com.example.lddc.core.parser.KrcParser
import io.ktor.client.HttpClient
import io.ktor.client.engine.cio.CIO
import io.ktor.client.plugins.HttpRequestRetry
import io.ktor.client.plugins.contentnegotiation.ContentNegotiation
import io.ktor.client.request.get
import io.ktor.client.request.header
import io.ktor.client.request.parameter
import io.ktor.client.request.post
import io.ktor.client.statement.bodyAsText
import io.ktor.serialization.kotlinx.json.json
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import java.security.MessageDigest

class KugouApi : BaseLyricsApi {

    companion object {
        private const val TAG = "KugouApi"
        private const val SIGNATURE_KEY = "LnT6xpN3khm36zse0QzvmgTZ3waWdRSA"
        private const val CLIENT_VER = "11070"
    }

    override val source = Source.KG
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
        install(HttpRequestRetry) {
            retryOnServerErrors(maxRetries = 3)
            exponentialDelay()
        }
    }

    private suspend fun makeRequest(
        url: String,
        params: MutableMap<String, String>,
        module: String,
        isPost: Boolean = false
    ): JsonObject {
        val mid = md5(System.currentTimeMillis().toString())

        val headers = mutableMapOf(
            "User-Agent" to "Android14-1070-11070-201-0-$module-wifi",
            "Connection" to "Keep-Alive",
            "Accept-Encoding" to "identity", // 禁用gzip压缩
            "KG-Rec" to "1",
            "KG-RC" to "1",
            "KG-CLIENTTIMEMS" to System.currentTimeMillis().toString(),
            "mid" to mid
        )

        when (module) {
            "Lyric" -> {
                params["appid"] = "3116"
                params["clientver"] = CLIENT_VER
            }

            "album_song_list" -> {
                params["dfid"] = "-"
                params["appid"] = "3116"
                params["mid"] = mid
                params["clientver"] = CLIENT_VER
                params["clienttime"] = (System.currentTimeMillis() / 1000).toString()
                params["uuid"] = "-"
                headers["KG-TID"] = "221"
            }

            else -> {
                params["userid"] = "0"
                params["appid"] = "3116"
                params["token"] = ""
                params["clienttime"] = (System.currentTimeMillis() / 1000).toString()
                params["iscorrection"] = "1"
                params["uuid"] = "-"
                params["mid"] = mid
                params["dfid"] = "-"
                params["clientver"] = CLIENT_VER
                params["platform"] = "AndroidFilter"
            }
        }

        params["signature"] = generateSignature(params)

        Log.d(TAG, "Request URL: $url")
        Log.d(TAG, "Request params: $params")

        val response = if (isPost) {
            client.post(url) {
                headers.forEach { (k, v) -> header(k, v) }
                params.forEach { (k, v) -> parameter(k, v) }
            }
        } else {
            client.get(url) {
                headers.forEach { (k, v) -> header(k, v) }
                params.forEach { (k, v) -> parameter(k, v) }
            }
        }

        // 直接读取响应文本
        val responseText = response.bodyAsText()

        Log.d(TAG, "Response: ${responseText.take(500)}")

        return Json.parseToJsonElement(responseText).jsonObject
    }

    private fun generateSignature(params: Map<String, String>, data: String = ""): String {
        // 按照PC端的签名方式: key=value 排序后拼接
        val sortedParams = params.toSortedMap()
        val paramString = sortedParams.entries.joinToString("") { "${it.key}=${it.value}" }

        return md5("$SIGNATURE_KEY$paramString$data$SIGNATURE_KEY")
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
        // 首先尝试使用主API
        try {
            return searchWithMainApi(keyword, page)
        } catch (e: Exception) {
            Log.d(TAG, "Main API search failed, using backup API: ${e.message}")
            // 主API失败，使用备用API
            return searchWithBackupApi(keyword, page)
        }
    }

    private suspend fun searchWithMainApi(keyword: String, page: Int): List<SongInfo> {
        val params = mutableMapOf(
            "sorttype" to "0",
            "keyword" to keyword,
            "pagesize" to "20",
            "page" to page.toString()
        )

        val url = "http://complexsearch.kugou.com/v2/search/song"
        Log.d(TAG, "Using main search API: $url")

        val response = makeRequest(url, params, "SearchSong")
        val data = response["data"]?.jsonObject
        val lists = data?.get("lists")?.jsonArray ?: return emptyList()

        return lists.mapNotNull { item ->
            val song = item.jsonObject
            val songId = song["ID"]?.jsonPrimitive?.content ?: ""
            val songName = song["SongName"]?.jsonPrimitive?.content ?: ""
            val albumName = song["AlbumName"]?.jsonPrimitive?.content ?: ""
            val hash = song["FileHash"]?.jsonPrimitive?.content ?: ""
            val image = song["Image"]?.jsonPrimitive?.content ?: ""
            val duration = song["Duration"]?.jsonPrimitive?.intOrNull

            // 处理歌手信息
            val singers = song["Singers"]?.jsonArray?.mapNotNull {
                val singer = it.jsonObject
                val name = singer["name"]?.jsonPrimitive?.content ?: ""
                if (name.isNotEmpty()) Artist(name) else null
            } ?: emptyList()
            val artistName = singers.joinToString("/")

            // 构建图片 URL - 替换size参数为800
            var imageUrl = image.replace("{size}", "800")
            // 确保图片URL包含协议前缀
            if (imageUrl.isNotEmpty() && !imageUrl.startsWith("http://") && !imageUrl.startsWith("https://")) {
                imageUrl = "http://$imageUrl"
            }
            Log.d(TAG, "Kugou main API image URL: $imageUrl")

            SongInfo(
                source = source,
                id = songId,
                hash = hash,
                title = songName,
                artist = Artist.fromString(artistName),
                album = albumName,
                duration = duration?.times(1000),
                imageUrl = imageUrl
            )
        }
    }

    private suspend fun searchWithBackupApi(keyword: String, page: Int): List<SongInfo> {
        val params = mutableMapOf(
            "showtype" to "14",
            "highlight" to "",
            "pagesize" to "20",
            "tag_aggr" to "1",
            "plat" to "0",
            "sver" to "5",
            "keyword" to keyword,
            "correct" to "1",
            "api_ver" to "1",
            "version" to "9108",
            "page" to page.toString()
        )

        val domains = listOf(
            "mobiles.kugou.com",
            "msearchcdn.kugou.com",
            "mobilecdnbj.kugou.com",
            "msearch.kugou.com"
        )

        val domain = domains.random()
        val url = "http://$domain/api/v3/search/song"

        Log.d(TAG, "Using backup search API: $url")

        val response = client.get(url) {
            header("User-Agent", "Android14-1070-11070-201-0-SearchSong-wifi")
            params.forEach { (k, v) -> parameter(k, v) }
        }

        val responseText = response.bodyAsText()
        Log.d(TAG, "Backup search response: ${responseText.take(500)}")

        val jsonObject = Json.parseToJsonElement(responseText).jsonObject
        val data = jsonObject["data"]?.jsonObject
        val infoList = data?.get("info")?.jsonArray ?: return emptyList()

        return infoList.mapNotNull { item ->
            val song = item.jsonObject
            val hash = song["hash"]?.jsonPrimitive?.content ?: return@mapNotNull null
            song["album_id"]?.jsonPrimitive?.content ?: ""
            val songName = song["songname"]?.jsonPrimitive?.content ?: ""
            val singerName = song["singername"]?.jsonPrimitive?.content ?: ""
            val albumName = song["album_name"]?.jsonPrimitive?.content ?: ""
            val image = song["Image"]?.jsonPrimitive?.content ?: ""
            val duration = song["duration"]?.jsonPrimitive?.intOrNull

            // 构建图片 URL - 替换size参数为800
            var imageUrl = image.replace("{size}", "800")
            // 确保图片URL包含协议前缀
            if (imageUrl.isNotEmpty() && !imageUrl.startsWith("http://") && !imageUrl.startsWith("https://")) {
                imageUrl = "http://$imageUrl"
            }
            Log.d(TAG, "Kugou backup API image URL: $imageUrl")

            SongInfo(
                source = source,
                id = song["album_audio_id"]?.jsonPrimitive?.content ?: hash,
                hash = hash,
                title = songName,
                artist = Artist.fromString(singerName),
                album = albumName,
                duration = duration?.times(1000),
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
        val params = mutableMapOf(
            "clienttime" to (System.currentTimeMillis() / 1000).toString(),
            "mid" to md5(System.currentTimeMillis().toString()),
            "clientver" to CLIENT_VER,
            "dfid" to "-",
            "appid" to "3116",
            "keyword" to "%20",
            "bitrate" to "0",
            "album_id" to "0",
            "hash" to (songInfo.hash ?: songInfo.id ?: ""),
            "album_audio_id" to ""
        )

        val response = makeRequest(
            "https://krcs.kugou.com/search",
            params,
            "Lyric"
        )

        val candidates = response["candidates"]?.jsonArray
            ?: throw Exception("未找到歌词")

        if (candidates.isEmpty()) {
            throw Exception("未找到歌词")
        }

        // 获取第一个候选歌词
        val candidate = candidates[0].jsonObject
        val id = candidate["id"]?.jsonPrimitive?.content
            ?: throw Exception("歌词ID为空")
        val accesskey = candidate["accesskey"]?.jsonPrimitive?.content
            ?: throw Exception("AccessKey为空")

        // 下载歌词 - 使用正确的API地址
        val downloadParams = mutableMapOf(
            "accesskey" to accesskey,
            "charset" to "utf8",
            "client" to "mobi",
            "fmt" to "krc",
            "id" to id,
            "ver" to "1"
        )

        // 构建请求参数（不需要signature）
        val downloadResponse = client.get("http://lyrics.kugou.com/download") {
            header("User-Agent", "Android14-1070-11070-201-0-Lyric-wifi")
            downloadParams.forEach { (k, v) -> parameter(k, v) }
        }

        val downloadText = downloadResponse.bodyAsText()

        Log.d(TAG, "Download response: ${downloadText.take(500)}")

        val downloadData = Json.parseToJsonElement(downloadText).jsonObject
        val content = downloadData["content"]?.jsonPrimitive?.content
            ?: throw Exception("歌词内容为空")

        // Base64解码
        val encryptedBytes = Base64.decode(content, Base64.DEFAULT)

        // 解密KRC
        val decryptedContent = KrcDecryptor.decryptString(encryptedBytes)

        if (decryptedContent.isBlank()) {
            throw Exception("歌词解密失败")
        }

        // 解析KRC
        val (tags, lyricsData, types) = KrcParser().parseWithTags(decryptedContent)

        val lyricInfo = LyricInfo(
            source = source,
            songinfo = songInfo,
            id = id,
            accesskey = accesskey
        )

        return Lyrics(
            info = lyricInfo,
            types = types,
            tags = tags,
            data = lyricsData
        )
    }

    override suspend fun getAlbum(albumId: String): AlbumInfo {
        val params = mutableMapOf(
            "albumid" to albumId
        )

        val response = makeRequest(
            "http://mobilecdnbj.kugou.com/api/v3/album/song",
            params,
            "album_song_list"
        )

        val data = response["data"]?.jsonObject
        val info = data?.get("info")?.jsonObject
        val songs = data?.get("list")?.jsonArray

        val imgurl = info?.get("imgurl")?.jsonPrimitive?.content
        var albumImageUrl = imgurl
        // 确保专辑图片URL包含协议前缀
        if (!albumImageUrl.isNullOrEmpty() && !albumImageUrl.startsWith("http://") && !albumImageUrl.startsWith("https://")) {
            albumImageUrl = "http://$albumImageUrl"
        }
        Log.d(TAG, "Kugou album image URL: $albumImageUrl")

        return AlbumInfo(
            source = source,
            id = albumId,
            name = info?.get("albumname")?.jsonPrimitive?.content ?: "",
            artist = info?.get("singername")?.jsonPrimitive?.content?.let { Artist(it) },
            imageUrl = albumImageUrl,
            songs = songs?.mapNotNull { formatSongInfo(it.jsonObject) } ?: emptyList()
        )
    }

    override suspend fun getPlaylist(playlistId: String): PlaylistInfo {
        // 酷狗歌单API实现较复杂，这里简化处理
        return PlaylistInfo(
            source = source,
            id = playlistId,
            name = ""
        )
    }

    private fun formatSongInfo(song: JsonObject): SongInfo? {
        val hash = song["hash"]?.jsonPrimitive?.content ?: return null
        val songName = song["songname"]?.jsonPrimitive?.content ?: ""
        val singerName = song["singername"]?.jsonPrimitive?.content ?: ""
        val albumName = song["album_name"]?.jsonPrimitive?.content ?: ""
        val image = song["Image"]?.jsonPrimitive?.content ?: ""
        val duration = song["duration"]?.jsonPrimitive?.intOrNull

        // 构建图片 URL - 替换size参数为800
        var imageUrl = image.replace("{size}", "800")
        // 确保图片URL包含协议前缀
        if (imageUrl.isNotEmpty() && !imageUrl.startsWith("http://") && !imageUrl.startsWith("https://")) {
            imageUrl = "http://$imageUrl"
        }
        Log.d(TAG, "Kugou album song image URL: $imageUrl")

        return SongInfo(
            source = source,
            id = hash,
            hash = hash,
            title = songName,
            artist = Artist.fromString(singerName),
            album = albumName,
            duration = duration?.times(1000),
            imageUrl = imageUrl
        )
    }

    private fun md5(input: String): String {
        val md = MessageDigest.getInstance("MD5")
        val digest = md.digest(input.toByteArray())
        return digest.joinToString("") { "%02x".format(it) }
    }
}
