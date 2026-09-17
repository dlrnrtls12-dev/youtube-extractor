package kr.local.youtubeextractor

import android.app.Activity
import android.content.ClipDescription
import android.content.ClipboardManager
import android.content.Context
import android.content.res.ColorStateList
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.RippleDrawable
import android.view.View
import android.view.ViewGroup
import android.widget.*

class AppDesign(private val activity: Activity) {
    private val accent=Color.rgb(202,239,121)
    private val ink=Color.rgb(244,245,242)
    private val muted=Color.rgb(158,168,150)
    private val surface=Color.rgb(25,27,30)
    private val edge=Color.rgb(52,58,63)
    private fun dp(v: Int)=(v*activity.resources.displayMetrics.density).toInt()
    private fun shape(color: Int, radius: Int=16, stroke: Int=Color.TRANSPARENT) = GradientDrawable().apply { setColor(color); cornerRadius=dp(radius).toFloat(); if(stroke != Color.TRANSPARENT) setStroke(dp(1),stroke) }
    private fun text(value: String,size: Float=14f,color: Int=ink,bold: Boolean=false) = TextView(activity).apply {
        text=value;textSize=size;setTextColor(color);typeface=Typeface.create("sans-serif",if(bold) Typeface.BOLD else Typeface.NORMAL);includeFontPadding=false
    }
    private fun stack()=LinearLayout(activity).apply { orientation=LinearLayout.VERTICAL }
    private fun LinearLayout.add(view: View, top: Int=0, height: Int=ViewGroup.LayoutParams.WRAP_CONTENT) {
        addView(view,LinearLayout.LayoutParams(-1,if(height<0) height else dp(height)).apply { topMargin=dp(top) })
    }
    private fun button(label: String, primary: Boolean=false)=Button(activity).apply {
        text=label;isAllCaps=false;textSize=15f;typeface=Typeface.create("sans-serif-medium",Typeface.NORMAL)
        backgroundTintList=null;stateListAnimator=null;minimumHeight=0;minHeight=0;minimumWidth=0;minWidth=0
        background=RippleDrawable(ColorStateList.valueOf(0x334B6020),shape(if(primary)accent else Color.rgb(37,42,46),14),null)
        setTextColor(ColorStateList(arrayOf(intArrayOf(-android.R.attr.state_enabled),intArrayOf()),intArrayOf(Color.rgb(111,122,102),if(primary)Color.rgb(23,33,13) else ink)))
    }
    val root=ScrollView(activity).apply { setBackgroundColor(Color.rgb(16,17,19)); isFillViewport=true; clipToPadding=false }
    private val body=stack().apply { setPadding(dp(22),dp(26),dp(22),dp(22));root.addView(this) }
    val url=EditText(activity)
    val kind=Spinner(activity)
    val language: Spinner
    val format: Spinner
    val quality: Spinner
    val start=button("자막 추출하기   ↓",true)
    val cancel=button("취소")
    val save=button("파일에 저장   ↗")
    val upgrade=button("추출 엔진 업데이트")
    val status=text("링크를 넣으면 바로 시작할 수 있어요.",13f,muted)
    private val paste=button("붙여넣기")
    private val modes=mutableListOf<Button>()
    private val subtitleBox=stack()
    private val videoBox=stack()
    private val hint=text("시간 없이 이어 읽기 · 원본 화자 표시 유지\n자동 화자 판별은 하지 않습니다.",12f,muted)
    private val progress=ProgressBar(activity,null,android.R.attr.progressBarStyleHorizontal).apply { progressTintList=ColorStateList.valueOf(accent); indeterminateTintList=ColorStateList.valueOf(accent); progressBackgroundTintList=ColorStateList.valueOf(edge);max=100;progress=0 }

    init {
        val header=LinearLayout(activity).apply { gravity=android.view.Gravity.CENTER_VERTICAL }
        header.addView(text("▶",23f,Color.rgb(23,33,13),true).apply { gravity=android.view.Gravity.CENTER;background=shape(accent,14) },LinearLayout.LayoutParams(dp(48),dp(48)))
        header.addView(stack().apply { add(text("유튜브 추출기",25f,ink,true));add(text("영상, 소리, 문장을 내 기기에.",12f,muted),6) },LinearLayout.LayoutParams(0,-2,1f).apply { leftMargin=dp(14) })
        body.add(header)
        body.add(text("●  기기에서 직접 실행",12f,accent).apply { background=shape(Color.rgb(34,43,28),10);setPadding(dp(12),dp(9),dp(12),dp(9)) },18)
        val card=stack().apply { background=shape(surface,22,Color.rgb(42,45,49));setPadding(dp(18),dp(20),dp(18),dp(20)) }
        body.add(card,20)
        card.add(text("01   링크 입력",13f,ink,true))
        url.apply { hint="유튜브 링크를 붙여넣으세요";setTextColor(ink);setHintTextColor(Color.rgb(124,133,119));textSize=14f;setSingleLine(true);background=shape(Color.rgb(16,18,20),12,edge);setPadding(dp(14),0,dp(14),0);inputType=android.text.InputType.TYPE_CLASS_TEXT or android.text.InputType.TYPE_TEXT_VARIATION_URI }
        card.add(url,12,54)
        card.add(paste,8,40)
        paste.setOnClickListener {
            val clipboard=activity.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val clip=clipboard.primaryClip
            if(clip != null && clip.itemCount>0) url.setText(clip.getItemAt(0).coerceToText(activity).toString().trim())
            else status.text="복사된 링크가 없습니다."
        }
        card.add(text("02   저장할 형식",13f,ink,true),22)
        kind.adapter=ArrayAdapter(activity,android.R.layout.simple_spinner_dropdown_item,arrayOf("자막","영상","음성"))
        val row=LinearLayout(activity)
        card.add(row,12)
        listOf("≡  자막\nTXT / SRT","▶  영상\nMP4","♫  음성\nMP3").forEachIndexed { i,label ->
            val b=button(label).apply { textSize=13f;setPadding(0,0,0,0);setOnClickListener { select(i) } }
            row.addView(b,LinearLayout.LayoutParams(0,dp(80),1f).apply { if(i<2) rightMargin=dp(8) });modes.add(b)
        }
        fun selector(parent: LinearLayout, label: String, values: Array<String>): Spinner {
            parent.add(text(label,12f,muted),14)
            val spinner=Spinner(activity,Spinner.MODE_DROPDOWN).apply {
                background=shape(Color.rgb(37,41,45),10);setPadding(dp(6),0,dp(6),0);setPopupBackgroundDrawable(shape(Color.rgb(37,41,45),12,edge))
                adapter=object: ArrayAdapter<String>(activity,android.R.layout.simple_spinner_dropdown_item,values) {
                    override fun getView(position: Int,convertView: View?,parent: ViewGroup): View = text(values[position]+"  ▾",14f).apply { gravity=android.view.Gravity.CENTER_VERTICAL;setPadding(dp(10),0,dp(6),0) }
                    override fun getDropDownView(position: Int,convertView: View?,parent: ViewGroup): View = text(values[position],14f).apply {setPadding(dp(18),dp(16),dp(18),dp(16));setBackgroundColor(Color.rgb(37,41,45))}
                }
            }
            parent.add(spinner,8,46);return spinner
        }
        card.add(subtitleBox)
        language=selector(subtitleBox,"자막 언어",arrayOf("한국어","영어","일본어","중국어 간체"))
        format=selector(subtitleBox,"파일 형식",arrayOf("TXT · 텍스트만","SRT · 시간 포함"))
        card.add(videoBox)
        quality=selector(videoBox,"최대 화질",arrayOf("720p · 기본","360p · 가볍게","1080p · 선명하게"))
        card.add(hint,16)
        body.add(start,18,54)
        body.add(cancel,8,42)
        val stateCard=stack().apply { background=shape(Color.rgb(25,29,27),16);setPadding(dp(18),dp(18),dp(18),dp(18)) }
        body.add(stateCard,16)
        stateCard.add(text("●  진행 상태",13f,accent,true))
        stateCard.add(status,10);stateCard.add(progress,12,4);stateCard.add(save,14,44)
        body.add(text("추출 중에는 앱을 화면에 열어 두세요.",12f,muted),14)
        body.add(upgrade,14,40)
        body.add(text("내 기기에서 직접 처리  ·  v1.1\n본인 소유 또는 저장 허가를 받은 콘텐츠에 사용하세요.",11f,muted).apply { gravity=android.view.Gravity.CENTER;setLineSpacing(dp(5).toFloat(),1f) },22)
        select(0)
    }
    private fun select(index: Int) {
        kind.setSelection(index)
        modes.forEachIndexed { i,b ->
            val selected=i==index
            b.background=RippleDrawable(ColorStateList.valueOf(0x334B6020),shape(if(selected)Color.rgb(41,53,30) else Color.rgb(32,36,40),14,if(selected)accent else edge),null)
            b.setTextColor(if(selected)accent else muted);b.isSelected=selected
        }
        subtitleBox.visibility=if(index==0)View.VISIBLE else View.GONE
        videoBox.visibility=if(index==1)View.VISIBLE else View.GONE
        hint.text=arrayOf("시간 없이 이어 읽기 · 원본 화자 표시 유지\n자동 화자 판별은 하지 않습니다.","원본에서 제공하는 화질까지 MP4로 저장합니다.","192 kbps MP3로 저장합니다.")[index]
        start.text=arrayOf("자막","영상","음성")[index]+" 추출하기   ↓"
    }
    fun setBusy(busy: Boolean) {
        listOf<View>(url,paste,language,format,quality).plus(modes).forEach { it.isEnabled=!busy;it.alpha=if(busy)0.55f else 1f }
        progress.isIndeterminate=busy
        if(!busy) progress.progress=if(status.text.startsWith("완료") || status.text.startsWith("파일 저장 완료"))100 else 0
    }
}

