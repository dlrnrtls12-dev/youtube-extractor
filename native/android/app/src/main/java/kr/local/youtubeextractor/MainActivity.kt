package kr.local.youtubeextractor

import android.app.Activity
import android.content.Intent
import android.graphics.Color
import android.os.Bundle
import android.view.WindowManager
import android.widget.*
import com.yausername.youtubedl_android.YoutubeDL
import com.yausername.youtubedl_android.YoutubeDLRequest
import com.yausername.ffmpeg.FFmpeg
import java.io.File
import java.util.UUID
import java.util.concurrent.Executors

class MainActivity : Activity() {
    private lateinit var design: AppDesign
    private val worker = Executors.newSingleThreadExecutor()
    private lateinit var url: EditText
    private lateinit var kind: Spinner
    private lateinit var language: Spinner
    private lateinit var quality: Spinner
    private lateinit var format: Spinner
    private lateinit var status: TextView
    private lateinit var start: Button
    private lateinit var cancel: Button
    private lateinit var save: Button
    private lateinit var upgrade: Button
    private var result: File? = null
    @Volatile private var active: String? = null
    @Volatile private var cancelled = false
    @Volatile private var busy = false

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        window.statusBarColor = Color.rgb(16,17,19)
        design=AppDesign(this)
        setContentView(design.root)
        design.root.setOnApplyWindowInsetsListener { view,insets ->
            view.setPadding(insets.systemWindowInsetLeft,insets.systemWindowInsetTop,insets.systemWindowInsetRight,insets.systemWindowInsetBottom)
            insets
        }
        url=design.url;kind=design.kind;language=design.language;format=design.format;quality=design.quality
        status=design.status;start=design.start;cancel=design.cancel;save=design.save;upgrade=design.upgrade
        start.setOnClickListener { extract() }
        cancel.isEnabled=false
        cancel.setOnClickListener { cancelled=true;active?.let { YoutubeDL.destroyProcessById(it) };status.text="취소 중…" }
        save.isEnabled=false;save.setOnClickListener { export() }
        upgrade.setOnClickListener { updateEngine() }
        if(intent.action == Intent.ACTION_SEND) url.setText(Regex("https?://\\S+").find(intent.getStringExtra(Intent.EXTRA_TEXT) ?: "")?.value ?: "")
        state?.getString("url")?.let { url.setText(it) }
        state?.getString("result")?.let { path -> File(path).takeIf { it.isFile && it.canonicalPath.startsWith(filesDir.canonicalPath+File.separator) }?.let { result=it; save.isEnabled=true; status.text="이전 결과를 저장할 수 있습니다." } }
    }

    private fun setBusy(value: Boolean) {
        busy=value
        design.setBusy(value)
        start.isEnabled=!value; upgrade.isEnabled=!value; cancel.isEnabled=value
        save.isEnabled=!value && result?.isFile == true
        if(value) window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) else window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
    }
    private fun initEngine() { YoutubeDL.init(applicationContext); FFmpeg.getInstance().init(applicationContext) }
    private fun report(message: String) { runOnUiThread { if(!isDestroyed) status.text=message } }

    private fun extract() {
        if(busy) return
        val link = try { Transcript.canonical(url.text.toString()) } catch(e: Exception) { status.text=e.message ?: "링크를 확인하세요."; return }
        val mode=kind.selectedItemPosition
        val lang=arrayOf("ko","en","ja","zh-Hans")[language.selectedItemPosition]
        val srt=format.selectedItemPosition == 1
        val height=arrayOf("720","360","1080")[quality.selectedItemPosition]
        val id=UUID.randomUUID().toString()
        val folder=File(filesDir,"jobs/$id")
        cancelled=false; active=id
        setBusy(true); status.text="추출 엔진 준비 중…"
        worker.execute {
            try {
                initEngine()
                check(!cancelled) { "작업을 취소했습니다." }
                check(folder.mkdirs()) { "작업 폴더를 만들 수 없습니다." }
                val request=YoutubeDLRequest(link)
                request.addOption("--ignore-config")
                request.addOption("--no-playlist")
                request.addOption("--no-colors")
                request.addOption("--socket-timeout","20")
                request.addOption("--retries","2")
                request.addOption("--fragment-retries","2")
                request.addOption("--max-filesize","2G")
                request.addOption("-o",File(folder,"%(id)s.%(ext)s").absolutePath)
                when(mode) {
                    0 -> { request.addOption("--skip-download"); request.addOption("--ignore-no-formats-error"); request.addOption("--write-subs"); request.addOption("--write-auto-subs"); request.addOption("--sub-langs",lang); request.addOption("--sub-format","json3") }
                    1 -> { request.addOption("-f","bv*[height<=$height][ext=mp4]+ba[ext=m4a]/b[height<=$height][ext=mp4]"); request.addOption("--merge-output-format","mp4") }
                    2 -> { request.addOption("-f","bestaudio/best"); request.addOption("-x"); request.addOption("--audio-format","mp3"); request.addOption("--audio-quality","192K") }
                }
                report("기기에서 직접 추출 중…")
                YoutubeDL.execute(request,id) { progress, _, line -> report(if(progress >= 0) "${progress.toInt()}% · ${line.takeLast(140)}" else line.takeLast(200)) }
                check(!cancelled) { "작업을 취소했습니다." }
                val output = if(mode == 0) {
                    val source=folder.listFiles()?.firstOrNull { it.extension == "json3" } ?: error("선택한 언어의 자막이 없습니다.")
                    File(folder,source.nameWithoutExtension+if(srt) ".srt" else ".txt").apply { writeText("\uFEFF"+Transcript.convert(source.readText(),srt)) }
                } else folder.listFiles()?.firstOrNull { it.extension == if(mode == 1) "mp4" else "mp3" } ?: error("완료 파일이 없습니다.")
                runOnUiThread { if(!isDestroyed) { result=output; status.text="완료 · ${output.name}\n‘파일에 저장’을 눌러 저장 위치를 선택하세요." } }
            } catch(e: Exception) {
                val raw=e.message ?: "추출 실패"
                report(if(cancelled) "작업을 취소했습니다." else if(raw.contains("not a bot",true)) "유튜브가 이 기기 접속에도 봇 확인을 요구했습니다. 잠시 후 다시 시도하세요." else raw.takeLast(700))
                folder.listFiles()?.filter { it.isFile }?.forEach { it.delete() }
                folder.delete()
            } finally { active=null; runOnUiThread { if(!isDestroyed) setBusy(false) } }
        }
    }
    private fun updateEngine() {
        if(busy) return
        setBusy(true); cancel.isEnabled=false; status.text="공식 배포처에서 엔진 업데이트 중…"
        worker.execute {
            try { initEngine(); YoutubeDL.updateYoutubeDL(applicationContext); report("추출 엔진이 최신 상태입니다.") }
            catch(e: Exception) { report("업데이트 실패: ${e.message}") }
            finally { runOnUiThread { if(!isDestroyed) setBusy(false) } }
        }
    }
    private fun export() {
        val file=result ?: return
        val mime=when(file.extension) { "mp4" -> "video/mp4"; "mp3" -> "audio/mpeg"; else -> "text/plain" }
        startActivityForResult(Intent(Intent.ACTION_CREATE_DOCUMENT).apply { addCategory(Intent.CATEGORY_OPENABLE); type=mime; putExtra(Intent.EXTRA_TITLE,file.name) },100)
    }
    @Deprecated("Platform compatibility")
    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode,resultCode,data)
        if(requestCode != 100 || resultCode != RESULT_OK) return
        val uri=data?.data ?: return
        val file=result ?: return
        setBusy(true); cancel.isEnabled=false; status.text="파일 저장 중…"
        worker.execute {
            try { contentResolver.openOutputStream(uri)?.use { out -> file.inputStream().use { it.copyTo(out) } } ?: error("저장 위치를 열 수 없습니다."); report("파일 저장 완료") }
            catch(e: Exception) { report("저장 실패: ${e.message}") }
            finally { runOnUiThread { if(!isDestroyed) setBusy(false) } }
        }
    }
    override fun onSaveInstanceState(out: Bundle) { out.putString("url",url.text.toString()); result?.let { out.putString("result",it.absolutePath) }; super.onSaveInstanceState(out) }
    override fun onDestroy() { cancelled=true; active?.let { YoutubeDL.destroyProcessById(it) }; worker.shutdown(); super.onDestroy() }
}

