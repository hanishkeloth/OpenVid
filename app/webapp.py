"""Standalone OpenVid HTTP application. Run with one Uvicorn worker."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.requests import Request

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / '.env', override=False)

from . import documents, media, providers, runtime as rt, voices

WEB = rt.ROOT / 'web'
ACCESS = os.environ.get('OPENVID_ACCESS_TOKEN', '')


@asynccontextmanager
async def lifespan(app):
    rt.DATA_ROOT.mkdir(parents=True, exist_ok=True)
    # A lost process must never resubmit paid generations automatically.
    for path in rt.DATA_ROOT.glob('workspaces/*/jobs.json'):
        jobs = rt.read_json(path, {})
        changed = False
        for job in jobs.values():
            if job['status'] in ('queued', 'running'):
                job.update(status='error', error='The server stopped before completion. Check saved provider request IDs before generating again.', finished=time.time())
                changed = True
        if changed:
            rt.write_json(path, jobs)
    yield
    rt.EXECUTOR.shutdown(wait=True)


app = FastAPI(title='OpenVid', version='0.1.0', lifespan=lifespan)


def access_signature(wid):
    return hmac.new(ACCESS.encode(), wid.encode(), hashlib.sha256).hexdigest()


def authorized(request, wid):
    return not ACCESS or hmac.compare_digest(request.cookies.get('openvid_access', ''), access_signature(wid))


@app.middleware('http')
async def workspace(request: Request, call_next):
    wid = request.cookies.get('openvid_workspace', '')
    fresh = not re.fullmatch('[a-f0-9]{64}', wid)
    if fresh:
        wid = secrets.token_hex(32)
    if request.method not in ('GET', 'HEAD', 'OPTIONS'):
        origin = request.headers.get('origin')
        if (origin and origin.rstrip('/') != str(request.base_url).rstrip('/')) or request.headers.get('sec-fetch-site') == 'cross-site':
            return JSONResponse({'detail': 'Cross-origin writes are not allowed'}, 403)
    guarded = request.url.path.startswith(('/api/', '/media/')) and request.url.path not in ('/api/invite/status', '/api/invite/redeem', '/api/health')
    if guarded and not authorized(request, wid):
        return JSONResponse({'detail': 'Enter the instance access token'}, 401)
    token = rt.WORKSPACE.set(wid)
    try:
        response = await call_next(request)
    finally:
        rt.WORKSPACE.reset(token)
    if fresh:
        response.set_cookie('openvid_workspace', wid, httponly=True, secure=request.url.scheme == 'https', samesite='lax', max_age=31536000)
    if request.url.path.startswith(('/api/', '/media/')):
        response.headers['Cache-Control'] = 'private, no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'same-origin'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    return response


@app.exception_handler(ValueError)
async def invalid(request, exc):
    return JSONResponse({'detail': str(exc)[:600]}, 422)


@app.get('/api/health')
def health():
    return {'ok': True, 'app': 'OpenVid', 'version': '0.1.0'}


@app.get('/api/invite/status')
def status(request: Request):
    return {'invited': authorized(request, rt.WORKSPACE.get())}


class AccessReq(BaseModel):
    code: str = Field(max_length=500)


@app.post('/api/invite/redeem')
def redeem(request: Request, body: AccessReq):
    if ACCESS and not hmac.compare_digest(ACCESS, body.code):
        raise HTTPException(401, 'The access token is incorrect')
    response = JSONResponse({'ok': True})
    response.set_cookie('openvid_access', access_signature(rt.WORKSPACE.get()), httponly=True, secure=request.url.scheme == 'https', samesite='lax', max_age=2592000)
    return response


@app.get('/api/providers')
def connections():
    return providers.public_config()


class Connection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    key: str | None = Field(None, max_length=2000)
    base_url: str | None = Field(None, max_length=500)
    keyless: bool = False
    models: dict[str, str] = Field(default_factory=dict)
    inputs: dict[str, dict] = Field(default_factory=dict)


@app.put('/api/providers/{name}')
def save_connection(name: str, body: Connection):
    if name not in providers.CATALOG:
        raise HTTPException(404, 'Unknown provider')
    if any(k not in providers.CATALOG[name]['capabilities'] or (v and not re.fullmatch(r'[A-Za-z0-9._:/@-]{1,200}', v)) for k, v in body.models.items()):
        raise HTTPException(422, 'Invalid provider model settings')
    if len(json.dumps(body.inputs)) > 16000 or any(k not in providers.CATALOG[name]['capabilities'] for k in body.inputs):
        raise HTTPException(422, 'Invalid advanced input settings')
    with rt.LOCK:
        saved = rt.credentials()
        entry = saved['providers'].setdefault(name, {})
        if body.key is not None:
            entry['key'] = body.key.strip()
        if name == 'compatible':
            if body.base_url is not None:
                media.safe_url(body.base_url, allow_local=os.environ.get('OPENVID_ALLOW_LOCAL_PROVIDERS') == 'true')
                entry['base_url'] = body.base_url.rstrip('/')
            entry['keyless'] = body.keyless
        entry.update({kind + '_model': model.strip() for kind, model in body.models.items()})
        entry['inputs'] = body.inputs
        rt.save_credentials(saved)
    return providers.public_config()


@app.delete('/api/providers/{name}')
def remove_connection(name: str):
    with rt.LOCK:
        saved = rt.credentials()
        saved['providers'].pop(name, None)
        saved['defaults'] = {k: v for k, v in saved['defaults'].items() if v != name}
        rt.save_credentials(saved)
    return providers.public_config()


@app.post('/api/providers/{name}/test')
def test_connection(name: str):
    return providers.test_connection(name)


@app.put('/api/provider-defaults')
def defaults(body: dict[str, str]):
    if any(k not in ('text', 'image', 'video', 'voice', 'music', 'captions', 'edit', 'avatar') or (v and not providers.ready(v, k)) for k, v in body.items()):
        raise HTTPException(422, 'Choose a configured provider with a model for this task')
    with rt.LOCK:
        saved = rt.credentials()
        saved['defaults'] = {k: v for k, v in body.items() if v}
        rt.save_credentials(saved)
    return providers.public_config()


@app.get('/api/models')
def models():
    rt.seed_samples()
    return {'models': providers.model_options()}


@app.get('/api/projects/{pid}')
def project(pid: str):
    return rt.load_project(pid)


@app.get('/api/jobs/{jid}')
def job(jid: str):
    result = rt.JOBS.get(jid)
    if not result:
        raise HTTPException(404, 'Job not found in this workspace')
    return result


@app.post('/api/projects/{pid}/upload')
async def upload(pid: str, file: UploadFile = File(...)):
    rt.load_project(pid)
    suffix = Path(file.filename or '').suffix.lower()
    types = {**dict.fromkeys(['.png', '.jpg', '.jpeg', '.webp', '.gif'], 'image'),
             **dict.fromkeys(['.mp4', '.webm', '.mov', '.mkv'], 'video'),
             **dict.fromkeys(['.mp3', '.wav', '.m4a', '.ogg', '.flac', '.aac'], 'audio')}
    if suffix not in types:
        raise HTTPException(422, 'Choose an image, video, or audio file')
    dest = rt.MEDIA / (rt.uid() + suffix)
    size = 0
    try:
        with dest.open('wb') as stream:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > 250_000_000:
                    raise HTTPException(413, 'Media uploads may be up to 250 MB')
                stream.write(chunk)
        info = media.probe(dest)
        kind = 'audio' if types[suffix] == 'video' and not info['width'] and info['has_audio'] else types[suffix]
        result = rt.make_asset('/media/' + dest.name, kind, file.filename or 'Upload', 'Uploaded', source='upload')
        with rt.LOCK:
            p = rt.load_project(pid)
            p['assets'].insert(0, result)
            rt.save_project(p)
        return result
    except Exception:
        dest.unlink(missing_ok=True)
        raise


class GenerateReq(BaseModel):
    project_id: str
    kind: Literal['image', 'video']
    model: str = ''
    prompt: str = Field(min_length=1, max_length=20000)
    duration: int = Field(6, ge=3, le=30)
    aspect_ratio: Literal['16:9', '9:16', '1:1'] = '16:9'
    refs: list[str] = Field(default_factory=list, max_length=1)
    request_id: str = Field(default_factory=rt.uid)


def submit_once(pid, request_id, prompt, kind, work):
    if not re.fullmatch(r'[\w-]{8,80}', request_id):
        raise HTTPException(422, 'Invalid request ID')
    with rt.LOCK:
        p = rt.load_project(pid)
        prior = p.setdefault('requests', {}).get(request_id)
        if prior:
            return {'jobs': [prior]}
        jid = rt.submit(pid, prompt, kind, work)
        p['requests'][request_id] = jid
        rt.save_project(p)
        return {'jobs': [jid]}


@app.post('/api/generate')
def generate(body: GenerateReq):
    p = rt.load_project(body.project_id)
    for url in body.refs:
        if not any(a['url'] == url and a['kind'] == 'image' for a in p['assets']):
            raise HTTPException(422, 'Choose a reference image from this project')
    name, _, model = body.model.partition(':')
    providers.choose(body.kind, name or None)
    def work(job):
        result = providers.generate(body.kind, body.prompt, duration=body.duration, aspect=body.aspect_ratio,
                                     reference=next(iter(body.refs), None), provider=name or None, model=model or None)
        return [providers.asset(result, body.prompt, body.kind)]
    return submit_once(body.project_id, body.request_id, body.prompt, body.kind, work)


class AudioReq(BaseModel):
    project_id: str
    kind: Literal['voice', 'music'] = 'voice'
    prompt: str = Field(min_length=1, max_length=5000)
    voice_profile_id: str | None = None
    voice: str = 'Rachel'
    duration: int = Field(10, ge=3, le=600)
    request_id: str = Field(default_factory=rt.uid)


@app.post('/api/audio')
def audio(body: AudioReq):
    rt.load_project(body.project_id)
    profile = voices.get_for(body.project_id, body.voice_profile_id) if body.voice_profile_id else None
    if not profile:
        providers.choose(body.kind)
    def work(job):
        if profile:
            out = voices.speak(body.prompt, profile, True)
            return [rt.make_asset(out['url'], 'audio', body.prompt, out['label'], 0, source='voice', cost_unknown=True,
                                  voice_profile_id=profile['id'], alignment=out.get('alignment'))]
        return [providers.asset(providers.generate(body.kind, body.prompt, duration=body.duration, voice=body.voice), body.prompt, body.kind)]
    return submit_once(body.project_id, body.request_id, body.prompt, 'audio', work)


@app.get('/api/projects/{pid}/voices')
def project_voices(pid: str):
    p = rt.load_project(pid)
    return {'voices': voices.list_for(pid), 'audio_settings': p.get('audio_settings', {})}


@app.get('/api/voices/config')
def voice_config():
    return voices.config()


@app.get('/api/voices/library')
def voice_library(search: str = '', language: str = '', page: int = 0):
    return voices.library(search, language, page)


@app.post('/api/voices/save')
def voice_save(body: voices.SaveReq):
    return voices.save(body, rt.load_project(body.project_id))


@app.post('/api/voices/design')
def voice_design(body: voices.DesignReq):
    rt.load_project(body.project_id)
    def work(job):
        return [rt.make_asset(r['url'], 'audio', body.text, r['label'], 0, **{k: v for k, v in r.items() if k not in ('url', 'label', 'cost_usd')}, cost_unknown=True) for r in voices.design(body)]
    return {'jobs': [rt.submit(body.project_id, 'Voice design samples', 'audio', work)]}


@app.post('/api/voices/clone')
def voice_clone(body: voices.CloneReq):
    return voices.clone(body, rt.load_project(body.project_id))


@app.get('/api/projects/{pid}/voices/{vid}/status')
def voice_status(pid: str, vid: str):
    rt.load_project(pid)
    return voices.refresh_status(pid, vid)


@app.post('/api/ops')
def video_edit(body: dict):
    p = rt.load_project(body.get('project_id', ''))
    source = next((a for a in p['assets'] if a['id'] == body.get('asset_id') and a['kind'] == 'video'), None)
    if not source or not str(body.get('prompt', '')).strip():
        raise HTTPException(422, 'Choose a video and enter an edit instruction')
    providers.choose('edit', 'fal')
    def work(job):
        endpoint = providers.config('fal')['edit_model']
        payload = {'prompt': str(body['prompt'])[:20000], 'video_url': providers.fal_upload(rt.local_path(source['url']))}
        payload.update(providers.config('fal').get('inputs', {}).get('edit', {}))
        url = providers.first(providers.fal_run(endpoint, payload))
        return [rt.make_asset(url, 'video', body['prompt'], endpoint, source='video-edit', parent_id=source['id'], cost_unknown=True)]
    return submit_once(p['id'], body.get('request_id', rt.uid()), 'Edit video', 'video', work)


@app.post('/api/avatar')
def avatar(body: dict):
    p = rt.load_project(body.get('project_id', ''))
    face = next((a for a in p['assets'] if a['id'] == body.get('image_asset_id') and a['kind'] == 'image'), None)
    audio = next((a for a in p['assets'] if a['id'] == body.get('audio_asset_id') and a['kind'] == 'audio'), None)
    if not face or not audio or not body.get('consent'):
        raise HTTPException(422, 'Choose a portrait and speech audio, and confirm permission to use them')
    providers.choose('avatar', 'fal')
    def work(job):
        endpoint = providers.config('fal')['avatar_model']
        payload = {'image_url': providers.fal_upload(rt.local_path(face['url'])), 'audio_url': providers.fal_upload(rt.local_path(audio['url']))}
        payload.update(providers.config('fal').get('inputs', {}).get('avatar', {}))
        url = providers.first(providers.fal_run(endpoint, payload))
        return [rt.make_asset(url, 'video', body.get('prompt') or 'Speaking avatar', endpoint, source='avatar', cost_unknown=True)]
    return submit_once(p['id'], body.get('request_id', rt.uid()), 'Speaking avatar', 'video', work)


app.include_router(documents.build_router(rt.submit, rt.make_asset, rt.load_project, rt.save_project, rt.JOBS))
app.include_router(documents.stock_router(rt.make_asset, rt.load_project, rt.save_project, rt.LOCK))


@app.get('/media/{path:path}')
def serve_media(path: str):
    try:
        result = Path(rt.local_path('/media/' + path))
    except ValueError:
        raise HTTPException(404, 'Media not found') from None
    if result.suffix.lower() not in ('.mp4', '.webm', '.mov', '.mkv', '.mp3', '.wav', '.m4a', '.aac', '.flac', '.ogg', '.png', '.jpg', '.jpeg', '.webp', '.gif'):
        raise HTTPException(404, 'Media not found')
    return FileResponse(result)


@app.get('/vids-vendor/{name}')
def player(name: str):
    files = {'player.js': 'hyperframes-player.global.js', 'hyperframe-runtime.js': 'hyperframe-runtime.js', 'hyperframe.runtime.iife.js': 'hyperframe.runtime.iife.js'}
    if name not in files:
        raise HTTPException(404, 'Not found')
    return FileResponse(rt.ROOT / 'node_modules/hyperframes/dist' / files[name], media_type='text/javascript')


@app.get('/')
def root():
    return RedirectResponse('/vids')


@app.get('/vids')
@app.get('/vids/{did}')
def index(request: Request, did: str = ''):
    if authorized(request, rt.WORKSPACE.get()):
        rt.seed_samples()
    return FileResponse(WEB / 'vids.html')


@app.get('/{name}')
def static(name: str):
    if not re.fullmatch(r'[\w-]+\.(js|css)', name) or not (WEB / name).is_file():
        raise HTTPException(404, 'Not found')
    return FileResponse(WEB / name)
