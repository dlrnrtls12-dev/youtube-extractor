'use strict';
const $ = id => document.getElementById(id);
sessionStorage.removeItem('extractor-code');
let kind = 'video', currentJob = null, polling = false;
const fragment = new URLSearchParams(location.hash.slice(1));
if (fragment.has('code')) history.replaceState(null, '', location.pathname);
async function api(path, options = {}) {
  const response = await fetch(path, {...options, headers: {'Content-Type': 'application/json', ...options.headers}});
  let data; try { data = await response.json(); } catch (_) { throw new Error('서버가 준비 중이거나 일시적으로 연결되지 않습니다. 잠시 후 다시 연결해 주세요.'); }
  if (!response.ok) { const error = new Error(typeof data.detail === 'string' ? data.detail : '입력값을 확인해 주세요.'); error.status = response.status; throw error; }
  return data;
}
async function connect() {
  try {
    const data = await api('/api/status');
    $('access-help').textContent = data.internet ? 'PC·휴대폰에서 같은 주소로 사용합니다. 개인 PC를 켜 둘 필요가 없습니다.' : '현재 배포 전 로컬 점검 중입니다.';
    $('controls').disabled = !!currentJob;
    $('connection').textContent = data.node ? '서버에 연결되었습니다. 추출할 링크를 입력하세요.' : '서버에 연결되었습니다. 유튜브 지원을 위해 서버 설정을 확인해야 합니다.';
    $('addresses').replaceChildren();
    for (const address of data.addresses) {
      const link = document.createElement('a'); link.href = address; link.textContent = address;
      $('addresses').append(link);
    }
    if (!data.addresses.length) $('addresses').textContent = '배포 후 공용 주소가 표시됩니다.';
    const saved = sessionStorage.getItem('extractor-job');
    if (saved && !polling) { currentJob = saved; poll(); }
  } catch (error) { $('connection').textContent = error.message; $('controls').disabled = true; }
}
$('reconnect').addEventListener('click', connect);
function setKind(value) {
  if (!['video', 'audio', 'subtitle'].includes(value) || currentJob) return;
  kind = value;
  document.querySelectorAll('.mode').forEach(button => { const selected = button.dataset.kind === kind; button.classList.toggle('selected', selected); button.setAttribute('aria-pressed', String(selected)); });
  for (const name of ['video', 'audio', 'subtitle']) $(name + '-options').hidden = name !== kind;
  $('start').textContent = ({video:'영상', audio:'음성', subtitle:'자막'})[kind] + ' 추출하기 ↓';
}
document.querySelectorAll('.mode').forEach(button => button.addEventListener('click', () => setKind(button.dataset.kind)));
function showState(message, error = false) {
  $('status').hidden = false; $('status').classList.toggle('error', error);
  $('message').textContent = message;
}
$('extract').addEventListener('submit', async event => {
  event.preventDefault();
  if (currentJob) return;
  $('controls').disabled = true; $('download').hidden = true; $('job-title').textContent = '';
  $('progress').hidden = false; $('cancel').hidden = true; $('state-label').textContent = '진행 중';
  showState('작업을 요청하고 있습니다.');
  try {
    const data = await api('/api/jobs', {method:'POST', body:JSON.stringify({url:$('url').value, kind, quality:$('quality').value, language:$('language').value, subtitle_format:$('subtitle-format').value})});
    currentJob = data.id; sessionStorage.setItem('extractor-job', currentJob); poll();
  } catch (error) { showState(error.message, true); $('progress').hidden = true; $('controls').disabled = false; $('state-label').textContent = '확인해 주세요'; }
});
async function poll() {
  if (polling) return;
  polling = true; $('controls').disabled = true;
  try {
    while (currentJob) {
      let job;
      try { job = await api('/api/jobs/' + currentJob); }
      catch (error) { showState('상태를 확인할 수 없습니다. 연결 버튼으로 다시 확인해 주세요. ' + error.message, true); $('cancel').hidden = true; $('progress').hidden = true; if(error.status === 404) {currentJob = null; sessionStorage.removeItem('extractor-job'); $('controls').disabled = false;} return; }
      showState(job.message, job.status === 'error'); $('job-title').textContent = job.title || '';
      const active = ['queued', 'running'].includes(job.status);
      $('progress').hidden = !active; $('cancel').hidden = !active; $('cancel').disabled = false;
      $('state-label').textContent = active ? '진행 중' : job.status === 'done' ? '완료' : job.status === 'cancelled' ? '취소됨' : '확인해 주세요';
      if (!active) {
        if (job.status === 'done') { $('download').href = job.download; $('download').download = job.filename; $('download').hidden = false; $('download').textContent = '파일 저장하기 · ' + (job.size / 1048576).toFixed(1) + ' MB ↓'; }
        currentJob = null; sessionStorage.removeItem('extractor-job'); $('controls').disabled = false; break;
      }
      await new Promise(resolve => setTimeout(resolve, 1500));
    }
  } finally { polling = false; }
}
$('cancel').addEventListener('click', async () => { if (!currentJob) return; $('cancel').disabled = true; try { await api('/api/jobs/' + currentJob + '/cancel', {method:'POST'}); showState('작업을 취소하고 있습니다.'); } catch (error) { showState(error.message, true); $('cancel').disabled = false; } });
if (document.modelContext?.registerTool) {
  try { Promise.resolve(document.modelContext.registerTool({name:'prepare_extraction',title:'추출 준비',description:'링크와 추출 종류를 화면에 입력합니다. 다운로드를 시작하지 않습니다.',inputSchema:{type:'object',properties:{url:{type:'string'},kind:{type:'string',enum:['video','audio','subtitle']}},required:['url','kind'],additionalProperties:false},annotations:{readOnlyHint:false},execute(input){if(currentJob) throw new Error('작업이 진행 중입니다.');if(!input || typeof input.url !== 'string' || !['video','audio','subtitle'].includes(input.kind)) throw new Error('올바른 링크와 종류를 입력하세요.');const url=new URL(input.url);if(!['https:','http:'].includes(url.protocol)||!['youtube.com','www.youtube.com','m.youtube.com','music.youtube.com','youtu.be'].includes(url.hostname))throw new Error('유튜브 링크가 필요합니다.');$('url').value=input.url;setKind(input.kind);return {prepared:true,started:false};}})).catch(()=>{}); } catch (_) {}
}
connect();
