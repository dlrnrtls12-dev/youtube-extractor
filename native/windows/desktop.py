"""Local-only desktop extractor. No HTTP server or remote extraction API."""
import html
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import time
from urllib.parse import urlparse, parse_qs

ROOT = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))


def canonical_url(value):
    p = urlparse(value.strip())
    if p.scheme not in ('https', 'http') or p.username or p.password or p.port not in (None, 80, 443):
        raise ValueError('유튜브 영상 링크를 입력하세요.')
    if p.hostname == 'youtu.be':
        video = p.path.strip('/')
    elif p.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
        video = parse_qs(p.query).get('v', [''])[0] if p.path == '/watch' else p.path.rstrip('/').split('/')[-1] if re.fullmatch(r'/(shorts|live|embed)/[\w-]{11}/?', p.path) else ''
    else:
        video = ''
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', video):
        raise ValueError('영상 한 개의 유튜브 링크가 필요합니다.')
    return 'https://www.youtube.com/watch?v=' + video


def transcript(source, fmt='txt'):
    cues = []
    for e in json.loads(source).get('events', []):
        text = html.unescape(''.join(s.get('utf8', '') for s in e.get('segs', []))).strip()
        if text:
            start = max(0, int(e.get('tStartMs', 0)))
            cues.append((start, start + max(1, int(e.get('dDurationMs', 2000))), text))
    if not cues:
        raise ValueError('저장할 자막이 없습니다.')
    if fmt == 'srt':
        def stamp(ms):
            return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'
        return '\n\n'.join(f'{i}\n{stamp(a)} --> {stamp(b)}\n{t}' for i, (a,b,t) in enumerate(cues, 1)) + '\n'
    paragraphs = []
    for _, _, text in cues:
        for line in text.splitlines():
            line = re.sub(r'\s+', ' ', line).strip()
            if not line:
                continue
            if not paragraphs or re.match(r'^(?:>>\s*|[^\W\d][\w .-]{0,29}[:：]\s*)', line):
                paragraphs.append(line)
            else:
                paragraphs[-1] += ' ' + line
    return '\n\n'.join(paragraphs) + '\n'


def options(url, kind, quality, language, folder):
    args = ['--ignore-config', '--no-plugin-dirs', '--no-playlist', '--no-colors', '--newline',
            '--socket-timeout', '20', '--retries', '2', '--fragment-retries', '2',
            '--max-filesize', '2G', '--restrict-filenames', '-o', str(folder / '%(id)s.%(ext)s')]
    if kind == 'subtitle':
        args += ['--skip-download', '--ignore-no-formats-error', '--write-subs', '--write-auto-subs',
                 '--sub-langs', language, '--sub-format', 'json3']
    elif kind == 'audio':
        args += ['-f', 'bestaudio/best', '-x', '--audio-format', 'mp3', '--audio-quality', '192K']
    else:
        args += ['-f', f'bv*[height<={quality}][ext=mp4]+ba[ext=m4a]/b[height<={quality}][ext=mp4]', '--merge-output-format', 'mp4']
    return args + ['--', canonical_url(url)]


from design import StudioUI


class App(StudioUI):
    def __init__(self):
        import queue
        self.events = queue.Queue()
        self.stop = threading.Event()
        self.worker = None
        self.proc = None
        self.setup()
        self.choose_mode('subtitle')
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.root.after(150, self.poll)

    def choose(self):
        from tkinter import filedialog
        if self.worker and self.worker.is_alive():
            return
        folder = filedialog.askdirectory(initialdir=str(self.folder.parent))
        if folder:
            self.folder = Path(folder)
            self.destination.set(folder)

    def open_folder(self):
        self.folder.mkdir(parents=True, exist_ok=True)
        os.startfile(self.folder)

    def begin(self):
        if self.worker and self.worker.is_alive():
            return
        try:
            url = canonical_url(self.url.get())
        except ValueError as e:
            self.status.set(str(e))
            return
        self.stop.clear()
        self.busy_ui(True)
        self.state_label.configure(text='●  추출 중',text_color=self.accent)
        self.progress.configure(mode='indeterminate'); self.progress.start()
        self.start.configure(state='disabled')
        self.cancel_button.configure(state='normal')
        self.status.set('기기에서 추출을 시작합니다…')
        args = (url,self.kind.get(),self.quality.get(),self.language.get(),self.fmt.get(),self.folder)
        self.worker = threading.Thread(target=self.extract, args=args, daemon=True)
        self.worker.start()

    def extract(self, url, kind, quality, language, fmt, destination):
        folder = None
        try:
            import uuid
            folder = destination / ('작업-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
            folder.mkdir(parents=True)
            command = [str(ROOT/'bin'/'yt-dlp.exe'), '--ffmpeg-location', str(ROOT/'bin'), '--js-runtimes', 'node:' + str(ROOT/'bin'/'node.exe')]
            command += options(url,kind,quality,language,folder)
            with (folder/'진단.log').open('w',encoding='utf-8') as log:
                self.proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                             text=True, encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW,
                                             env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONUTF8='1'))
                if self.stop.is_set():
                    self.kill()
                for line in self.proc.stdout:
                    log.write(line)
                    self.events.put(('status',line.strip()[-350:]))
                code = self.proc.wait()
            if self.stop.is_set():
                raise RuntimeError('작업을 취소했습니다. 일부 파일은 작업 폴더에 남아 있을 수 있습니다.')
            if code:
                detail = (folder/'진단.log').read_text(encoding='utf-8')
                if 'not a bot' in detail.lower():
                    raise RuntimeError('유튜브가 이 기기의 접속에도 봇 확인을 요구했습니다. 잠시 후 다시 시도하세요.')
                raise RuntimeError(next((x for x in reversed(detail.splitlines()) if 'ERROR:' in x), '추출 실패. 작업 폴더의 진단.log를 확인하세요.')[-450:])
            if kind == 'subtitle':
                sources = list(folder.glob('*.json3'))
                if not sources:
                    raise RuntimeError('선택한 언어의 자막이 없습니다. 다른 언어를 선택하세요.')
                for source in sources:
                    source.with_suffix('.'+fmt).write_text(transcript(source.read_text(encoding='utf-8'),fmt),encoding='utf-8-sig')
                    source.unlink()
            outputs = list(folder.glob('*.' + (fmt if kind == 'subtitle' else 'mp3' if kind == 'audio' else 'mp4')))
            if not outputs:
                raise RuntimeError('완료 파일이 없습니다. 진단.log를 확인하세요.')
            self.events.put(('done',f'완료 · {outputs[0].name}\n폴더 열기에서 결과를 확인하세요.'))
        except Exception as e:
            self.events.put(('done',str(e)))
        finally:
            self.proc = None

    def kill(self):
        proc = self.proc
        if proc and proc.poll() is None:
            subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,creationflags=subprocess.CREATE_NO_WINDOW)

    def cancel(self):
        self.stop.set()
        self.cancel_button.configure(state='disabled')
        threading.Thread(target=self.kill, daemon=True).start()

    def close(self):
        self.stop.set()
        self.kill()
        self.root.destroy()

    def poll(self):
        while not self.events.empty():
            kind, text = self.events.get_nowait()
            if kind == 'status':
                match=re.search(r'\[download\]\s+(\d+(?:\.\d+)?)%',text)
                if match:
                    self.progress.stop(); self.progress.configure(mode='determinate')
                    self.progress.set(min(float(match.group(1))/100,0.98))
                    self.status.set('파일을 가져오고 있어요 · '+match.group(1)+'%')
                elif 'Downloading' in text or 'Extracting' in text:
                    self.status.set('영상 정보와 파일을 확인하고 있어요.')
                elif 'ffmpeg' in text.lower() or 'merger' in text.lower():
                    self.status.set('파일을 변환하고 있어요. 조금만 기다려 주세요.')
            if kind == 'done':
                self.status.set(text)
                self.progress.stop(); self.progress.configure(mode='determinate')
                success=text.startswith('완료')
                self.progress.set(1 if success else 0)
                self.state_label.configure(text='✓  저장 완료' if success else '●  확인해 주세요',text_color=self.accent if success else '#FFB49E')
                self.busy_ui(False)
                self.start.configure(state='normal')
                self.cancel_button.configure(state='disabled')
        self.root.after(150,self.poll)


if __name__ == '__main__':
    if '--self-test' in sys.argv:
        assert canonical_url('https://youtu.be/HrdLYO5vwh0?t=1').endswith('HrdLYO5vwh0')
        assert transcript('{"events":[{"segs":[{"utf8":"Hello"}]},{"segs":[{"utf8":"there"}]}]}') == 'Hello there\n'
        for tool in ['yt-dlp.exe','node.exe','ffmpeg.exe']:
            assert (ROOT/'bin'/tool).exists(), tool
    elif '--ui-test' in sys.argv:
        try:
            app=App()
            app.root.update()
            for mode in ['video','audio','subtitle']:
                app.choose_mode(mode)
                app.root.update()
                assert app.kind.get()==mode
            app.root.after(300,app.root.destroy)
            app.root.mainloop()
        except Exception:
            import traceback
            Path('ui-test.log').write_text(traceback.format_exc(),encoding='utf-8')
            sys.exit(1)
    else:
        App().root.mainloop()

