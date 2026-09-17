package kr.local.youtubeextractor
import org.junit.Test
import org.junit.Assert.*
class TranscriptTest {
    @Test fun rejectsOtherHosts() {
        for (value in listOf("https://youtube.com.evil.org/watch?v=HrdLYO5vwh0","https://user@youtube.com/watch?v=HrdLYO5vwh0","file:///etc/passwd")) {
            try { Transcript.canonical(value); fail(value) } catch (_: IllegalArgumentException) {}
        }
        assertEquals("https://www.youtube.com/watch?v=HrdLYO5vwh0",Transcript.canonical("https://youtu.be/HrdLYO5vwh0?t=1"))
    }
    @Test fun continuousTextAndSpeakers() {
        val input="""{"events":[{"segs":[{"utf8":"Alice: Hello &amp;"}]},{"segs":[{"utf8":"welcome."}]},{"segs":[{"utf8":"Bob: Hi."}]}]}"""
        assertEquals("Alice: Hello & welcome.\n\nBob: Hi.\n",Transcript.convert(input,false))
        assertTrue(Transcript.convert(input,true).contains("00:00:00,000 --> 00:00:02,000"))
    }
}
