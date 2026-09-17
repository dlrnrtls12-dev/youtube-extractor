"""Shared visual language: charcoal surfaces, lime accents, generous spacing."""
from pathlib import Path


class StudioUI:
    def setup(self):
        import tkinter as tk
        import customtkinter as ctk
        self.tk = tk
        ctk.set_appearance_mode('dark')
        self.root = ctk.CTk(fg_color='#101113')
        self.root.title('유튜브 추출기')
        self.root.geometry('880x790')
        self.root.minsize(680,620)
        self.accent='#CAEF79'
        font=lambda size=14,weight='normal':('맑은 고딕',size,weight)
        panel=ctk.CTkScrollableFrame(self.root,fg_color='transparent',corner_radius=0,scrollbar_button_color='#303337',scrollbar_button_hover_color='#474B50')
        panel.pack(fill='both',expand=True,padx=26,pady=16)
        panel.grid_columnconfigure(0,weight=1)
        header=ctk.CTkFrame(panel,fg_color='transparent')
        header.grid(row=0,column=0,sticky='ew',pady=(6,24))
        ctk.CTkLabel(header,text='▶',width=46,height=46,corner_radius=14,fg_color=self.accent,text_color='#17210D',font=font(22,'bold')).pack(side='left',padx=(0,14))
        title=ctk.CTkFrame(header,fg_color='transparent');title.pack(side='left')
        ctk.CTkLabel(title,text='유튜브 추출기',font=font(26,'bold'),text_color='#F4F5F2').pack(anchor='w')
        ctk.CTkLabel(title,text='영상, 소리, 문장을 내 기기에.',font=font(13),text_color='#92968E').pack(anchor='w')
        ctk.CTkLabel(header,text='●  기기에서 직접 실행',fg_color='#222B1C',text_color=self.accent,corner_radius=12,font=font(12),height=32,width=148).pack(side='right')
        card=ctk.CTkFrame(panel,fg_color='#191B1E',corner_radius=22,border_width=1,border_color='#2A2D31')
        card.grid(row=1,column=0,sticky='ew');card.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(card,text='01   링크 입력',font=font(14,'bold'),text_color='#DCDFD8').grid(row=0,column=0,sticky='w',padx=24,pady=(20,10))
        linkrow=ctk.CTkFrame(card,fg_color='transparent');linkrow.grid(row=1,column=0,sticky='ew',padx=24);linkrow.grid_columnconfigure(0,weight=1)
        self.url=tk.StringVar()
        self.entry=ctk.CTkEntry(linkrow,textvariable=self.url,placeholder_text='유튜브 링크를 붙여넣으세요',height=52,corner_radius=12,border_width=1,border_color='#373C41',fg_color='#101214',font=font())
        self.entry.grid(row=0,column=0,sticky='ew',padx=(0,10))
        self.paste_button=ctk.CTkButton(linkrow,text='붙여넣기',width=104,height=52,corner_radius=12,fg_color='#2B3035',hover_color='#3D444B',font=font(13,'bold'),command=self.paste)
        self.paste_button.grid(row=0,column=1)
        ctk.CTkLabel(card,text='02   저장할 형식',font=font(14,'bold'),text_color='#DCDFD8').grid(row=2,column=0,sticky='w',padx=24,pady=(22,10))
        modes=ctk.CTkFrame(card,fg_color='transparent');modes.grid(row=3,column=0,sticky='ew',padx=24)
        modes.grid_columnconfigure((0,1,2),weight=1,uniform='mode')
        self.kind=tk.StringVar(value='subtitle');self.mode_buttons={}
        for i,(label,value) in enumerate([('≡   자막\nTXT / SRT','subtitle'),('▶   영상\nMP4','video'),('♫   음성\nMP3','audio')]):
            button=ctk.CTkButton(modes,text=label,height=88,corner_radius=14,border_width=1,font=font(16,'bold'),command=lambda v=value:self.choose_mode(v))
            button.grid(row=0,column=i,sticky='ew',padx=(0,10) if i<2 else 0);self.mode_buttons[value]=button
        opts=ctk.CTkFrame(card,fg_color='transparent');opts.grid(row=4,column=0,sticky='ew',padx=24,pady=(18,0));opts.grid_columnconfigure((0,1),weight=1,uniform='option')
        self.quality,self.language,self.fmt=tk.StringVar(value='720'),tk.StringVar(value='ko'),tk.StringVar(value='txt')
        self.option_boxes={};self.selectors=[]
        for key,label,var,mapping,column in [
            ('language','자막 언어',self.language,{'한국어':'ko','영어':'en','일본어':'ja','중국어 간체':'zh-Hans'},0),
            ('format','파일 형식',self.fmt,{'TXT · 텍스트만':'txt','SRT · 시간 포함':'srt'},1),
            ('quality','최대 화질',self.quality,{'720p · 기본':'720','360p · 가볍게':'360','1080p · 선명하게':'1080'},0)]:
            box=ctk.CTkFrame(opts,fg_color='transparent');box.grid(row=0,column=column,sticky='ew',padx=(0,10) if column==0 else 0);self.option_boxes[key]=box
            ctk.CTkLabel(box,text=label,font=font(12),text_color='#9BA197').pack(anchor='w',pady=(0,6))
            selector=ctk.CTkOptionMenu(box,values=list(mapping),height=42,corner_radius=10,fg_color='#25292D',button_color='#30363A',button_hover_color='#40484D',dropdown_fg_color='#25292D',dropdown_hover_color='#3D4549',font=font(13),dropdown_font=font(13),command=lambda label,v=var,m=mapping:v.set(m[label]))
            selector.pack(fill='x');self.selectors.append(selector)
        self.hint=ctk.CTkLabel(card,text='',font=font(12),text_color='#969D91',anchor='w',justify='left',wraplength=590)
        self.hint.grid(row=5,column=0,sticky='ew',padx=24,pady=(12,20))
        self.folder=Path.home()/'Downloads'/'YouTube Extractor';self.destination=tk.StringVar(value=str(self.folder))
        location=ctk.CTkFrame(panel,fg_color='transparent');location.grid(row=2,column=0,sticky='ew',pady=(16,12));location.grid_columnconfigure(0,weight=1)
        ctk.CTkLabel(location,text='저장 위치',font=font(11),text_color='#92998D').grid(row=0,column=0,sticky='w')
        ctk.CTkLabel(location,textvariable=self.destination,font=font(12),text_color='#B6BDB0',anchor='w',wraplength=430,justify='left').grid(row=1,column=0,sticky='w')
        ctk.CTkButton(location,text='변경',width=62,height=32,fg_color='#24282B',hover_color='#363D40',corner_radius=10,font=font(12),command=self.choose).grid(row=0,column=1,rowspan=2,padx=8)
        ctk.CTkButton(location,text='폴더 열기 ↗',width=105,height=32,fg_color='#24282B',hover_color='#363D40',corner_radius=10,font=font(12),command=self.open_folder).grid(row=0,column=2,rowspan=2)
        buttons=ctk.CTkFrame(panel,fg_color='transparent');buttons.grid(row=3,column=0,sticky='ew',pady=(0,16));buttons.grid_columnconfigure(0,weight=1)
        self.start=ctk.CTkButton(buttons,text='자막 추출하기   ↓',height=52,corner_radius=14,fg_color=self.accent,hover_color='#DDF8A4',text_color='#17210D',font=font(16,'bold'),command=self.begin)
        self.start.grid(row=0,column=0,sticky='ew')
        self.cancel_button=ctk.CTkButton(buttons,text='취소',width=72,height=52,corner_radius=14,fg_color='#282D31',hover_color='#3D454B',state='disabled',command=self.cancel);self.cancel_button.grid(row=0,column=1,padx=(10,0))
        state_card=ctk.CTkFrame(panel,corner_radius=16,fg_color='#191D1B');state_card.grid(row=4,column=0,sticky='ew')
        self.state_label=ctk.CTkLabel(state_card,text='●  준비됨',font=font(13,'bold'),text_color=self.accent);self.state_label.pack(anchor='w',padx=18,pady=(14,2))
        self.status=tk.StringVar(value='링크를 넣으면 바로 시작할 수 있어요.')
        ctk.CTkLabel(state_card,textvariable=self.status,font=font(12),text_color='#A5B09E',wraplength=580,justify='left',anchor='w').pack(fill='x',padx=18,pady=(0,12))
        self.progress=ctk.CTkProgressBar(state_card,height=4,corner_radius=2,fg_color='#2E362B',progress_color=self.accent)
        self.progress.set(0);self.progress.pack(fill='x',padx=18,pady=(0,16))
        ctk.CTkLabel(panel,text='내 기기에서 직접 처리  ·  v1.1\n본인 소유 또는 저장 허가를 받은 콘텐츠에 사용하세요.',font=font(11),text_color='#858C80').grid(row=5,column=0,pady=(16,6))

    def paste(self):
        try: self.url.set(self.root.clipboard_get().strip())
        except self.tk.TclError: self.status.set('클립보드에 복사된 링크가 없습니다.')

    def choose_mode(self,value):
        if self.worker and self.worker.is_alive(): return
        self.kind.set(value)
        for mode,button in self.mode_buttons.items():
            selected=mode==value
            button.configure(fg_color='#29351E' if selected else '#202428',hover_color='#354629' if selected else '#2B3237',border_color=self.accent if selected else '#343A3F',text_color=self.accent if selected else '#AFB6AB')
        for key,box in self.option_boxes.items():
            box.grid() if (value=='subtitle' and key in ('language','format')) or (value=='video' and key=='quality') else box.grid_remove()
        self.hint.configure(text={'subtitle':'시간 없이 이어 읽기 · 원본 화자 표시 유지 (자동 화자 판별 제외)','video':'원본에서 제공하는 화질까지 MP4로 저장합니다.','audio':'192 kbps MP3로 저장합니다.'}[value])
        self.start.configure(text={'subtitle':'자막','video':'영상','audio':'음성'}[value]+' 추출하기   ↓')

    def busy_ui(self,busy):
        state='disabled' if busy else 'normal'
        self.entry.configure(state=state);self.paste_button.configure(state=state)
        for selector in self.selectors: selector.configure(state=state)
        for button in self.mode_buttons.values(): button.configure(state=state)

