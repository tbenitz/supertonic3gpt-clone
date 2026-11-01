"""Private voice-style optimization API for Supertonic 3.

CPU supported by upstream PyTorch training, but may be extremely slow.
NOT an anonymous public voice-cloning service. An admin token is required.
"""
import asyncio
import hmac
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, Form, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(title='Supertonic 3 Voice Style Builder', docs_url=None, redoc_url=None)
origins = [x.strip() for x in os.environ.get('ALLOWED_ORIGINS', '').split(',') if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=['GET','POST'], allow_headers=['authorization','content-type'])
CLONER = Path(os.environ.get('CLONER_DIR', '/app/cloner'))
JOBS_DIR = Path(os.environ.get('JOBS_DIR', '/tmp/voice_jobs'))
TOKEN = os.environ.get('CLONE_API_TOKEN', '')
BACKEND = os.environ.get('CLONE_DEVICE', 'auto').lower()
if BACKEND not in ('auto', 'cpu', 'cuda'):
    raise RuntimeError('CLONE_DEVICE must be auto, cpu, or cuda')
# 600 is a starter setting; more steps may improve similarity, but CPU processing
# can take much longer than the 6-30 minute figures reported for GPU.
DEFAULT_STEPS = int(os.environ.get('CLONE_STEPS', '600'))
if DEFAULT_STEPS < 100 or DEFAULT_STEPS > 3000:
    raise RuntimeError('CLONE_STEPS must be between 100 and 3000')
MAX_SECONDS = int(os.environ.get('CLONE_TIMEOUT_SECONDS', '14400'))
JOBS_DIR.mkdir(parents=True, exist_ok=True)
jobs = {}
semaphore = asyncio.Semaphore(1)


def authorize(value):
    if not TOKEN or not value or not hmac.compare_digest(value, f'Bearer {TOKEN}'):
        raise HTTPException(401, 'Private API token required')


@app.get('/api/health')
def health():
    return {'service':'voice-clone','ready': CLONER.joinpath('train_style.py').is_file(),
            'device': BACKEND, 'steps': DEFAULT_STEPS,
            'message':'CPU can be used but optimization may take hours.'}


@app.post('/api/clone')
async def clone(audio: UploadFile = File(...), consent: bool = Form(False),
                authorization: str | None = Header(None)):
    authorize(authorization)
    if not consent:
        raise HTTPException(400, 'Explicit speaker consent is required')
    if not audio.filename or Path(audio.filename).suffix.lower() not in ('.wav','.mp3','.ogg','.flac','.m4a'):
        raise HTTPException(400, 'Upload WAV, MP3, OGG, FLAC or M4A')
    if len([j for j in jobs.values() if j['status'] in ('waiting','running')]) >= 2:
        raise HTTPException(429, 'Private training queue is full')
    job_id = uuid.uuid4().hex
    folder = JOBS_DIR / job_id
    folder.mkdir(mode=0o700)
    inp = folder / ('reference' + Path(audio.filename).suffix.lower())
    size = 0
    try:
        with inp.open('wb') as f:
            while part := await audio.read(1024 * 1024):
                size += len(part)
                if size > 25 * 1024 * 1024:
                    raise HTTPException(413, 'Audio file exceeds 25 MB')
                f.write(part)
        jobs[job_id] = {'status':'waiting', 'progress':0, 'created':time.time(), 'error':None}
        asyncio.create_task(process_job(job_id, folder, inp))
        return {'job_id':job_id, 'status':'waiting'}
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise


async def process_job(job_id, folder, inp):
    async with semaphore:
        state = jobs[job_id]
        state.update(status='running', progress=1)
        norm = folder / 'clean.wav'
        proc = None
        try:
            cvt = await asyncio.create_subprocess_exec(
                'ffmpeg','-hide_banner','-loglevel','error','-nostdin','-y',
                '-i',str(inp),'-t','120','-ac','1','-ar','22050',str(norm),
                stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.PIPE)
            _, err = await asyncio.wait_for(cvt.communicate(), timeout=120)
            if cvt.returncode != 0 or not norm.is_file():
                raise RuntimeError('Audio conversion failed: ' + err.decode(errors='replace')[:250])
            name = 'style_' + job_id
            # Upstream code selects CUDA if available, else CPU. To force CPU,
            # hide GPUs from the subprocess environment, without rewriting upstream.
            env = os.environ.copy()
            if BACKEND == 'cpu': env['CUDA_VISIBLE_DEVICES'] = ''
            cmd = ['python','-u','train_style.py','--name',name,
                   '--target-wav-path',str(norm),'--reference-style','auto',
                   '--num-steps',str(DEFAULT_STEPS),'--save-steps',str(DEFAULT_STEPS)]
            proc = await asyncio.create_subprocess_exec(
                *cmd,cwd=str(CLONER),env=env,stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT)

            async def watch_output():
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    found = re.search(r'Step\s+(\d+)/'+str(DEFAULT_STEPS), line.decode('utf-8','replace'))
                    if found:
                        state['progress'] = min(99, int(found.group(1)) * 100 // DEFAULT_STEPS)
            await asyncio.wait_for(watch_output(), timeout=MAX_SECONDS)
            await asyncio.wait_for(proc.wait(), timeout=30)
            result = CLONER / 'logs' / name / (name + '.json')
            if proc.returncode != 0 or not result.is_file():
                raise RuntimeError('Voice training did not produce JSON. Verify memory, dependencies and model files.')
            data = json.loads(result.read_text(encoding='utf-8'))
            if not isinstance(data,dict) or not {'style_ttl','style_dp'}.issubset(data):
                raise RuntimeError('Incompatible output from the voice trainer')
            if isinstance(data.get('metadata'), dict):
                data['metadata']['source_file'] = 'user-consented-recording'
            (folder / 'style.json').write_text(json.dumps(data), encoding='utf-8')
            state.update(status='complete', progress=100)
        except Exception as e:
            state.update(status='failed', error=str(e)[:350])
        finally:
            if proc and proc.returncode is None:
                proc.kill()
                await proc.wait()
            inp.unlink(missing_ok=True)
            norm.unlink(missing_ok=True)
            shutil.rmtree(CLONER / 'logs' / ('style_' + job_id), ignore_errors=True)


@app.get('/api/jobs/{job_id}')
def status(job_id: str, authorization: str | None = Header(None)):
    authorize(authorization)
    info = jobs.get(job_id)
    if not info:
        raise HTTPException(404, 'Job not found')
    return {k:v for k,v in info.items() if k!='created'}


@app.get('/api/jobs/{job_id}/voice')
def voice(job_id: str, authorization: str | None = Header(None)):
    authorize(authorization)
    job = jobs.get(job_id)
    if not job or job['status'] != 'complete':
        raise HTTPException(404, 'No completed voice for this job')
    path = JOBS_DIR / job_id / 'style.json'
    if not path.is_file():
        raise HTTPException(410, 'Voice has expired')
    return JSONResponse(content=json.loads(path.read_text(encoding='utf-8')))


@app.on_event('startup')
async def start_cleanup():
    async def loop():
        while True:
            await asyncio.sleep(300)
            now = time.time()
            for key, record in list(jobs.items()):
                if record['status'] in ('complete','failed') and now-record['created']>3600:
                    jobs.pop(key,None)
                    shutil.rmtree(JOBS_DIR / key, ignore_errors=True)
    asyncio.create_task(loop())
