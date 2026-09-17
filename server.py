"""Personal LAN YouTube extractor. No AI APIs, accounts or paid services."""
from __future__ import annotations
import html
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
import signal
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import imageio_ffmpeg
import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Literal

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'downloads'
DATA.mkdir(exist_ok=True)
BIN = ROOT / '.tools'
BIN.mkdir(exist_ok=True)
FFMPEG = Path(shutil.which('ffmpeg') or (BIN / ('ffmpeg.exe' if os.name == 'nt' else 'ffmpeg')))
if not FFMPEG.exists():
    shutil.copy2(imageio_ffmpeg.get_ffmpeg_exe(), FFMPEG)
PORT = int(os.environ.get('PORT', os.environ.get('EXTRACTOR_PORT', '8765')))
PUBLIC_URL = os.environ.get('RENDER_EXTERNAL_URL', os.environ.get('EXTRACTOR_PUBLIC_URL', '')).rstrip('/')
BIND_HOST = os.environ.get('EXTRACTOR_BIND', '0.0.0.0')
MAX_SECONDS = 15 * 60
MAX_JOB_BYTES = 256 * 1024 * 1024
JOBS: dict[str, dict] = {}
LOCK = threading.Lock()
SLOT = threading.BoundedSemaphore(1)
CREATE_FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


def canonical_url(value: str) -> str:
    p = urlparse(value.strip())
    if p.scheme not in ('http', 'https') or p.username or p.password or p.port not in (None, 80, 443):
        raise ValueError('올바른 유튜브 영상 링크를 입력해 주세요.')
    host = (p.hostname or '').lower()
    if host == 'youtu.be':
        vid = p.path.strip('/')
    elif host in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
        if p.path == '/watch':
            vid = parse_qs(p.query).get('v', [''])[0]
        elif re.fullmatch(r'/(shorts|live|embed)/[\w-]{11}/?', p.path):
            vid = p.path.split('/')[2]
        else:
            vid = ''
    else:
        vid = ''
    if not re.fullmatch(r'[A-Za-z0-9_-]{11}', vid):
        raise ValueError('유튜브 영상 한 개의 링크를 입력해 주세요. 재생목록은 지원하지 않습니다.')
    return 'https://www.youtube.com/watch?v=' + vid


def addresses():
    result = {'127.0.0.1'}
    try:
        result.update(socket.gethostbyname_ex(socket.gethostname())[2])
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(('8.8.8.8', 80))
            result.add(s.getsockname()[0])
    except OSError:
        pass
    return sorted(x for x in result if ':' not in x and not x.startswith('169.254.'))


HOSTS = set(addresses()) | {'localhost'}
if PUBLIC_URL:
    HOSTS.add(urlparse(PUBLIC_URL).hostname)


def shared_url():
    if PUBLIC_URL:
        return PUBLIC_URL + '/'
    candidates = [ip for ip in addresses() if not ip.startswith('127.')]
    return f'http://{candidates[0]}:{PORT}/' if candidates else None


@app.middleware('http')
async def protect(request: Request, call_next):
    # LAN-only Host allowlist also prevents browser DNS rebinding.
    host = (request.headers.get('host', '').split(':')[0]).lower()
    if host not in HOSTS:
        return JSONResponse({'detail': '허용되지 않은 접속 주소입니다.'}, status_code=403)
    if request.url.path == '/' and request.method == 'GET' and host in ('127.0.0.1', 'localhost'):
        common = shared_url()
        if common:
            return RedirectResponse(common, status_code=307)
    if request.method not in ('GET', 'HEAD'):
        origin = request.headers.get('origin')
        allowed_origins = {f'{request.url.scheme}://{request.headers.get("host")}'}
        if PUBLIC_URL:
            allowed_origins.add(PUBLIC_URL)
        if origin and origin not in allowed_origins:
            return JSONResponse({'detail': '다른 사이트에서의 요청은 허용하지 않습니다.'}, status_code=403)
    response = await call_next(request)
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['Cache-Control'] = 'no-store'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    return response


class ExtractRequest(BaseModel):
    url: str = Field(max_length=2048)
    kind: Literal['video', 'audio', 'subtitle']
    quality: Literal['360', '720', '1080'] = '720'
    language: str = Field(default='ko', pattern=r'^[A-Za-z0-9-]{2,24}$')
    subtitle_format: Literal['srt', 'txt'] = 'srt'


def base_command():
    cmd = [sys.executable, '-m', 'yt_dlp', '--ignore-config', '--no-playlist', '--no-plugin-dirs',
           '--no-colors', '--socket-timeout', '20', '--retries', '2', '--fragment-retries', '2',
           '--ffmpeg-location', str(FFMPEG.parent), '--max-filesize', '120M', '--concurrent-fragments', '1']
    if shutil.which('node'):
        cmd += ['--js-runtimes', 'node']
    return cmd


def update(job_id, **values):
    with LOCK:
        JOBS[job_id].update(values)


def run_process(job_id, command, timeout=1800):
    folder = DATA / job_id
    log = folder / 'process.log'
    with log.open('w', encoding='utf-8') as output:
        child_env = dict(os.environ, PYTHONIOENCODING='utf-8')
        proc = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT,
                                cwd=folder, creationflags=CREATE_FLAGS, env=child_env,
                                start_new_session=os.name != 'nt')
        update(job_id, process=proc)
        start = time.monotonic()
        while proc.poll() is None:
            with LOCK:
                cancelled = JOBS[job_id]['cancelled']
            if cancelled or time.monotonic() - start > timeout:
                stop_process(proc)
                proc.wait()
                raise RuntimeError('작업을 취소했습니다.' if cancelled else '처리 시간이 초과되었습니다. 짧은 영상으로 다시 시도해 주세요.')
            if sum(p.stat().st_size for p in folder.iterdir() if p.is_file()) > MAX_JOB_BYTES:
                stop_process(proc)
                proc.wait()
                raise RuntimeError('무료 운영용 작업 용량 제한을 넘었습니다. 짧은 영상이나 낮은 화질로 시도해 주세요.')
            time.sleep(0.4)
        update(job_id, process=None)
    text = log.read_text(encoding='utf-8', errors='replace')
    if proc.returncode:
        lowered = text.lower()
        if 'sign in' in lowered or 'bot' in lowered:
            raise RuntimeError('유튜브에서 접근을 제한했습니다. 로그인·봇 확인이 필요한 영상은 현재 지원하지 않습니다.')
        if 'private' in lowered or 'unavailable' in lowered:
            raise RuntimeError('비공개이거나 사용할 수 없는 영상입니다.')
        if 'requested format' in lowered:
            raise RuntimeError('선택한 화질로 저장할 수 없습니다. 더 낮은 화질을 선택해 주세요.')
        if '429' in lowered:
            raise RuntimeError('유튜브 요청 제한입니다. 잠시 뒤 다시 시도해 주세요.')
        errors = [x for x in text.splitlines() if 'ERROR:' in x]
        raise RuntimeError(('추출 실패: ' + (errors[-1].split('ERROR:', 1)[1].strip() if errors else '영상 처리에 실패했습니다.'))[:450])
    return text


def stop_process(proc):
    if proc.poll() is not None:
        return
    if os.name == 'nt':
        result = subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_FLAGS)
        if result.returncode and proc.poll() is None:
            proc.kill()
    else:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


@app.on_event('shutdown')
def shutdown():
    with LOCK:
        processes = [job['process'] for job in JOBS.values() if job.get('process')]
        for job in JOBS.values():
            job['cancelled'] = True
    for proc in processes:
        stop_process(proc)


def json3_text(source: Path, target: Path, fmt: str):
    events = json.loads(source.read_text(encoding='utf-8')).get('events', [])
    cues = []
    for event in events:
        value = html.unescape(''.join(seg.get('utf8', '') for seg in event.get('segs', []))).strip()
        if not value:
            continue
        start = max(0, int(event.get('tStartMs', 0)))
        end = start + max(1, int(event.get('dDurationMs', 2000)))
        cues.append((start, end, value))
    if not cues:
        raise RuntimeError('저장할 수 있는 자막이 없습니다.')
    def timestamp(ms):
        return f'{ms // 3600000:02}:{ms // 60000 % 60:02}:{ms // 1000 % 60:02},{ms % 1000:03}'
    if fmt == 'srt':
        content = '\n\n'.join(f'{i}\n{timestamp(s)} --> {timestamp(e)}\n{v}' for i, (s, e, v) in enumerate(cues, 1))
    else:
        lines = []
        for _, _, value in cues:
            if not lines or lines[-1] != value:
                lines.append(value)
        content = '\n'.join(lines)
    target.write_text(content + '\n', encoding='utf-8-sig')


def extract(job_id, spec):
    folder = DATA / job_id
    try:
        update(job_id, status='running', message='영상 정보를 확인하고 있습니다.')
        metadata_text = run_process(job_id, base_command() + ['--skip-download', '--dump-single-json', '--', spec.url], 120)
        info = next((json.loads(line) for line in reversed(metadata_text.splitlines()) if line.startswith('{')), None)
        if not info:
            raise RuntimeError('영상 정보를 읽지 못했습니다.')
        if info.get('is_live'):
            raise RuntimeError('진행 중인 실시간 방송은 지원하지 않습니다.')
        if (info.get('duration') or 0) > MAX_SECONDS:
            raise RuntimeError('무료 운영용 버전은 15분 이하의 영상을 지원합니다.')
        title = str(info.get('title') or 'YouTube')
        update(job_id, title=title, message='파일을 내려받고 있습니다.')
        cmd = base_command() + ['--newline', '-o', str(folder / 'source.%(ext)s')]
        if spec.kind == 'subtitle':
            languages = (info.get('subtitles') or {}) | (info.get('automatic_captions') or {})
            if spec.language not in languages:
                available = ', '.join(list(languages)[:12]) or '없음'
                raise RuntimeError(f'선택한 언어의 자막이 없습니다. 제공 언어: {available}')
            cmd += ['--skip-download', '--write-subs', '--write-auto-subs', '--sub-langs', spec.language, '--sub-format', 'json3']
            run_process(job_id, cmd + ['--', spec.url])
            sources = list(folder.glob('source.*.json3'))
            if not sources:
                raise RuntimeError('이 영상에서 자막을 내려받을 수 없습니다.')
            result = folder / ('result.' + spec.subtitle_format)
            json3_text(sources[0], result, spec.subtitle_format)
        elif spec.kind == 'audio':
            run_process(job_id, cmd + ['-f', 'bestaudio/best', '--', spec.url])
            source = next((p for p in folder.glob('source.*') if p.suffix not in ('.part', '.ytdl')), None)
            if source is None:
                raise RuntimeError('오디오 파일을 받지 못했습니다.')
            update(job_id, message='MP3로 변환하고 있습니다.')
            result = folder / 'result.mp3'
            run_process(job_id, [str(FFMPEG), '-nostdin', '-y', '-i', str(source), '-vn', '-threads', '1', '-codec:a', 'libmp3lame', '-b:a', '192k', str(result)])
        else:
            fmt = f'bv*[height<={spec.quality}][ext=mp4]+ba[ext=m4a]/b[height<={spec.quality}][ext=mp4]'
            run_process(job_id, cmd + ['-f', fmt, '--merge-output-format', 'mp4', '--', spec.url])
            source = folder / 'source.mp4'
            if not source.exists():
                raise RuntimeError('선택한 화질의 MP4를 만들지 못했습니다.')
            result = folder / 'result.mp4'
            source.rename(result)
        with LOCK:
            if JOBS[job_id]['cancelled']:
                raise RuntimeError('작업을 취소했습니다.')
        name = re.sub(r'[\\/:*?"<>|\x00-\x1f]', '_', title).strip('. ')[:120] or 'YouTube'
        update(job_id, status='done', message='저장할 준비가 되었습니다.', filename=name + result.suffix,
               result=str(result), size=result.stat().st_size)
        for p in folder.glob('source.*'):
            p.unlink(missing_ok=True)
    except Exception as error:
        update(job_id, status='cancelled' if JOBS[job_id]['cancelled'] else 'error', message=str(error))
        for p in folder.glob('source.*'):
            try:
                p.unlink(missing_ok=True)
            except OSError:
                pass
    finally:
        update(job_id, process=None)
        SLOT.release()


@app.get('/api/status')
def status():
    common = shared_url()
    return {'ready': True, 'addresses': [common] if common else [],
            'node': bool(shutil.which('node')), 'max_minutes': 15, 'internet': bool(PUBLIC_URL)}


@app.get('/healthz')
def health():
    return {'ok': True}


@app.post('/api/jobs')
def create_job(spec: ExtractRequest):
    try:
        spec.url = canonical_url(spec.url)
    except ValueError as error:
        raise HTTPException(400, str(error))
    if not SLOT.acquire(blocking=False):
        raise HTTPException(409, '다른 추출 작업이 진행 중입니다. 완료 후 다시 시도해 주세요.')
    job_id = secrets.token_hex(16)
    try:
        (DATA / job_id).mkdir()
        with LOCK:
            JOBS[job_id] = dict(id=job_id, status='queued', message='작업을 시작합니다.', title='',
                                cancelled=False, process=None, token=secrets.token_urlsafe(24), created=time.time())
        threading.Thread(target=extract, args=(job_id, spec), daemon=True).start()
    except Exception:
        SLOT.release()
        raise
    return {'id': job_id}


@app.get('/api/jobs/{job_id}')
def job_status(job_id: str):
    with LOCK:
        job = JOBS.get(job_id)
        if not job:
            raise HTTPException(404, '작업을 찾을 수 없습니다. 서버가 재시작되었을 수 있습니다.')
        public = {k: v for k, v in job.items() if k not in ('process', 'result', 'token')}
        if job['status'] == 'done':
            public['download'] = f'/download/{job_id}/{job["token"]}'
        return public


@app.post('/api/jobs/{job_id}/cancel')
def cancel(job_id: str):
    with LOCK:
        if job_id not in JOBS:
            raise HTTPException(404, '작업을 찾을 수 없습니다.')
        if JOBS[job_id]['status'] in ('queued', 'running'):
            JOBS[job_id]['cancelled'] = True
    return {'ok': True}


@app.get('/download/{job_id}/{token}')
def download(job_id: str, token: str):
    with LOCK:
        job = JOBS.get(job_id)
        if not job or not secrets.compare_digest(token, job['token']) or job['status'] != 'done':
            raise HTTPException(404, '다운로드를 찾을 수 없습니다.')
        return FileResponse(job['result'], filename=job['filename'], media_type='application/octet-stream')


app.mount('/', StaticFiles(directory=ROOT / 'dist', html=True), name='web')

if __name__ == '__main__':
    print('\nYouTube Extractor - AI API not used', flush=True)
    common = shared_url() or f'http://127.0.0.1:{PORT}/'
    print(f'Open (PC / Mobile): {common}', flush=True)
    print('Stop: Ctrl+C. Keep this window open while using the app.\n', flush=True)
    if '--open-browser' in sys.argv:
        threading.Timer(1.5, lambda: webbrowser.open(common)).start()
    uvicorn.run(app, host=BIND_HOST, port=PORT, log_level='warning')
