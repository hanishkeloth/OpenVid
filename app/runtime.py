"""Workspace isolation, encrypted provider settings, local media and durable jobs."""
from __future__ import annotations

import contextvars
import copy
import hashlib
import json
import os
import re
import secrets
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from cryptography.fernet import Fernet
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parent.parent
DATA_ROOT = Path(os.environ.get('OPENVID_DATA_DIR', str(ROOT / 'data'))).resolve()
WORKSPACE = contextvars.ContextVar('openvid_workspace', default=None)
JOB = contextvars.ContextVar('openvid_job', default=None)
LOCK = threading.RLock()
EXECUTOR = ThreadPoolExecutor(max_workers=3, thread_name_prefix='openvid')
ID = re.compile(r'^[a-f0-9]{12}$')


def uid():
    return uuid.uuid4().hex[:12]


def workspace_dir():
    wid = WORKSPACE.get()
    if not wid or not re.fullmatch(r'[a-f0-9]{64}', wid):
        raise HTTPException(401, 'Open your OpenVid workspace first')
    path = DATA_ROOT / 'workspaces' / wid
    path.mkdir(parents=True, exist_ok=True)
    return path


class WorkspacePath:
    def __init__(self, suffix):
        self.suffix = suffix

    def resolve(self):
        path = workspace_dir() / self.suffix
        path.mkdir(parents=True, exist_ok=True)
        return path

    def __truediv__(self, name):
        return self.resolve() / name


MEDIA = WorkspacePath('media')
DATA = WorkspacePath('')


def write_json(path, data, private=False):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.' + uid() + '.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2))
    if private:
        temporary.chmod(0o600)
    temporary.replace(path)


def read_json(path, fallback=None):
    return json.loads(path.read_text()) if path.exists() else copy.deepcopy(fallback)


def cipher():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    path = DATA_ROOT / '.encryption-key'
    with LOCK:
        if not path.exists():
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as out:
                out.write(Fernet.generate_key())
        return Fernet(path.read_bytes())


def credentials():
    path = workspace_dir() / 'providers.enc'
    if not path.exists():
        return {'providers': {}, 'defaults': {}}
    try:
        return json.loads(cipher().decrypt(path.read_bytes()))
    except Exception:
        raise HTTPException(500, 'Provider settings could not be decrypted. Restore the instance encryption key.') from None


def save_credentials(data):
    with LOCK:
        path = workspace_dir() / 'providers.enc'
        temporary = path.with_suffix('.tmp')
        temporary.write_bytes(cipher().encrypt(json.dumps(data).encode()))
        temporary.chmod(0o600)
        temporary.replace(path)


def provider(name):
    return credentials()['providers'].get(name, {})


def local_path(url):
    if not re.fullmatch(r'/media/[\w./-]+', url or '') or '..' in url:
        raise ValueError('Choose an uploaded project asset')
    relative = url.removeprefix('/media/')
    base = ROOT / 'examples/business/media' if relative.startswith('samples/') else MEDIA.resolve()
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()) or not path.is_file():
        raise ValueError('This media file is unavailable in your workspace')
    return str(path)


def mirror(path):
    """The standalone distribution uses its persistent local volume."""
    return None


def project_path(pid):
    if not ID.fullmatch(pid):
        raise HTTPException(404, 'Project not found')
    return workspace_dir() / 'projects' / (pid + '.json')


def load_project(pid):
    path = project_path(pid)
    if not path.exists():
        raise HTTPException(404, 'Project not found in this workspace')
    return read_json(path)


def save_project(project):
    with LOCK:
        write_json(project_path(project['id']), project)


def make_asset(url, kind, prompt, label, cost=0, **extra):
    from .media import probe
    asset = {'id': uid(), 'url': url, 'kind': kind, 'prompt': prompt, 'model_label': label,
             'cost_usd': cost, 'created': time.time(), **extra}
    if kind in ('audio', 'video'):
        info = probe(local_path(url))
        asset['duration'] = info['duration']
        if kind == 'video':
            from .media import poster
            asset['poster'] = poster(url)
    return asset


def jobs_path():
    return workspace_dir() / 'jobs.json'


class WorkspaceJobs:
    def get(self, key, default=None):
        return read_json(jobs_path(), {}).get(key, default)


JOBS = WorkspaceJobs()


def persist_job(job):
    with LOCK:
        jobs = read_json(jobs_path(), {})
        jobs[job['id']] = job
        write_json(jobs_path(), jobs)


def provider_task(provider_id, request_id, endpoint=None):
    job = JOB.get()
    if job is not None:
        job.setdefault('provider_tasks', []).append({'provider': provider_id, 'request_id': request_id, 'endpoint': endpoint})
        persist_job(job)


def submit(pid, prompt, kind, work):
    load_project(pid)
    job = {'id': uid(), 'project_id': pid, 'prompt': prompt, 'kind': kind, 'status': 'queued',
           'started': time.time(), 'assets': [], 'progress': {}}
    persist_job(job)
    context = contextvars.copy_context()

    def run():
        JOB.set(job)
        job['status'] = 'running'
        persist_job(job)
        try:
            assets = work(job)
            with LOCK:
                project = load_project(pid)
                seen = {a['id'] for a in project['assets']}
                project['assets'] = [a for a in assets if a['id'] not in seen] + project['assets']
                project['spend_usd'] = project.get('spend_usd', 0) + sum(a.get('cost_usd', 0) for a in assets)
                save_project(project)
            job.pop('partial_assets', None)
            job.update(status='done', assets=assets, finished=time.time())
        except Exception as exc:
            # Provider clients raise sanitized errors. Never persist raw HTTP headers/URLs.
            message = str(exc)
            for settings in credentials()['providers'].values():
                for field in ('key', 'secret'):
                    value = settings.get(field)
                    if value:
                        message = message.replace(value, '[redacted]')
            partial = job.pop('partial_assets', [])
            if partial:
                with LOCK:
                    project = load_project(pid)
                    seen = {a['id'] for a in project['assets']}
                    project['assets'] = [a for a in partial if a['id'] not in seen] + project['assets']
                    save_project(project)
            job.update(status='error', error=message[:900], assets=partial, finished=time.time())
        persist_job(job)

    EXECUTOR.submit(context.run, run)
    return job['id']


def seed_samples():
    destination = workspace_dir() / 'documents'
    marker = workspace_dir() / '.samples-v1'
    with LOCK:
        if marker.exists():
            return
        index = ROOT / 'examples/business/manifest.json'
        if not index.exists():
            return
        if index.exists():
            bundle = read_json(index)
            for entry in bundle['projects']:
                source = read_json(ROOT / 'examples/business' / entry['file'])
                did, pid = uid(), uid()
                save_project({'id': pid, 'name': source['document']['name'], 'assets': source['assets'],
                              'created': time.time(), 'spend_usd': 0, 'source': 'openvid-example', 'character_ids': []})
                exports = []
                for asset in source['assets']:
                    if asset.get('source') == 'vids-export':
                        jid = uid()
                        asset = {**asset, 'vids_id': did, 'vids_revision': 1}
                        persist_job({'id': jid, 'project_id': pid, 'status': 'done', 'prompt': source['document']['name'],
                                     'kind': 'video', 'started': time.time(), 'finished': time.time(), 'assets': [asset]})
                        exports.append({'job_id': jid, 'settings': {'revision': 1, 'resolution': '1080p', 'fps': 30, 'format': 'mp4'}, 'at': time.time()})
                write_json(destination / (did + '.json'), {'id': did, 'project_id': pid, 'revision': 1,
                    'created': time.time(), 'updated': time.time(), 'document': source['document'],
                    'history': [], 'comments': [], 'exports': exports, 'requests': {}})
        marker.write_text('Seeded bundled examples; new user content remains private to this workspace.\n')
