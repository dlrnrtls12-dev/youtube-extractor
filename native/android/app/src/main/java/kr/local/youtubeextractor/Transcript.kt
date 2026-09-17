package kr.local.youtubeextractor

import org.json.JSONObject
import java.net.URI
import java.net.URLDecoder
import java.util.Locale

object Transcript {
    fun canonical(value: String): String {
        val uri = URI(value.trim())
        require(uri.scheme in listOf("https", "http") && uri.rawUserInfo == null && uri.port in listOf(-1,80,443)) { "유튜브 영상 링크를 입력하세요." }
        val id = when (uri.host?.lowercase()) {
            "youtu.be" -> uri.path.trim('/')
            "youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com" -> {
                if (uri.path == "/watch") (uri.rawQuery ?: "").split('&').map { it.split('=', limit=2) }
                    .firstOrNull { it[0] == "v" && it.size == 2 }?.get(1)?.let { URLDecoder.decode(it,"UTF-8") } ?: ""
                else if (Regex("/(shorts|live|embed)/[A-Za-z0-9_-]{11}/?").matches(uri.path)) uri.path.trimEnd('/').substringAfterLast('/') else ""
            }
            else -> ""
        }
        require(Regex("[A-Za-z0-9_-]{11}").matches(id)) { "영상 한 개의 유튜브 링크가 필요합니다." }
        return "https://www.youtube.com/watch?v=$id"
    }
    private fun unescape(text: String): String = Regex("&(#x[0-9a-fA-F]+|#[0-9]+|amp|lt|gt|quot|apos|nbsp);").replace(text) {
        val v = it.groupValues[1]
        when(v) {
            "amp" -> "&"; "lt" -> "<"; "gt" -> ">"; "quot" -> "\""; "apos" -> "'"; "nbsp" -> " "
            else -> runCatching { String(Character.toChars(if(v.startsWith("#x")) v.drop(2).toInt(16) else v.drop(1).toInt())) }.getOrDefault(it.value)
        }
    }
    fun convert(source: String, srt: Boolean): String {
        val events = JSONObject(source).optJSONArray("events") ?: error("저장할 자막이 없습니다.")
        val blocks = mutableListOf<String>()
        var index = 1
        fun stamp(ms: Long) = String.format(Locale.ROOT,"%02d:%02d:%02d,%03d",ms/3600000,ms/60000%60,ms/1000%60,ms%1000)
        for (i in 0 until events.length()) {
            val event = events.getJSONObject(i)
            val segments = event.optJSONArray("segs") ?: continue
            val text = unescape((0 until segments.length()).joinToString("") { segments.getJSONObject(it).optString("utf8") }).trim()
            if (text.isBlank()) continue
            if (srt) {
                val start = event.optLong("tStartMs").coerceAtLeast(0)
                val end = start + event.optLong("dDurationMs",2000).coerceAtLeast(1)
                blocks += "${index++}\n${stamp(start)} --> ${stamp(end)}\n$text"
            } else for (raw in text.lines()) {
                val line = raw.replace(Regex("\\s+")," ").trim()
                if (line.isEmpty()) continue
                if (blocks.isEmpty() || Regex("^(>>\\s*|[\\p{L}_][\\p{L}\\p{N}_ .-]{0,29}[:：]\\s*)").containsMatchIn(line)) blocks += line
                else blocks[blocks.lastIndex] = blocks.last() + " " + line
            }
        }
        check(blocks.isNotEmpty()) { "저장할 자막이 없습니다." }
        return blocks.joinToString("\n\n") + "\n"
    }
}
