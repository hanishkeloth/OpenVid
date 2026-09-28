"""FFmpeg media helpers with bounded, validated downloads."""
import base64
import ipaddress
import json
import socket
import subprocess
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests

from . import runtime as rt


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)], capture_output=True, text=True, timeout=45)
    if result.returncode:
        raise ValueError('The media file could not be decoded')
    data = json.loads(result.stdout)
    streams = data.get('streams', [])
    video = next((s for s in streams if s['codec_type'] == 'video'), {})
    return {'duration': float(data.get('format', {}).get('duration', 0)), 'width': video.get('width', 0),
            'height': video.get('height', 0), 'has_audio': any(s['codec_type'] == 'audio' for s in streams)}


def safe_url(url, allow_local=False):
    p = urlparse(url)
    if p.scheme not in ('http', 'https') or not p.hostname or p.username or p.password:
        raise ValueError('Use an HTTP(S) provider URL without embedded credentials')
    try:
        addresses = socket.getaddrinfo(p.hostname, p.port or (443 if p.scheme == 'https' else 80), type=socket.SOCK_STREAM)
        if not allow_local and any(not ipaddress.ip_address(a[4][0]).is_global for a in addresses):
            raise ValueError('Private network addresses are disabled for this instance')
    except socket.gaierror:
        raise ValueError('The provider host could not be resolved') from None
    return url


def save_bytes(data, suffix):
    if not data or len(data) > 250_000_000:
        raise ValueError('The media output is empty or too large')
    path = rt.MEDIA / (rt.uid() + suffix)
    path.write_bytes(data)
    return '/media/' + path.name


def download(url, suffix=None):
    if url.startswith('/media/'):
        rt.local_path(url)
        return url
    for _ in range(4):
        safe_url(url)
        try:
            response = requests.get(url, timeout=120, stream=True, allow_redirects=False)
        except requests.RequestException:
            raise ValueError('The generated media could not be downloaded') from None
        if response.is_redirect:
            url = urljoin(url, response.headers['Location'])
            continue
        if not response.ok:
            raise ValueError(f'The media download returned HTTP {response.status_code}')
        ext = suffix or Path(urlparse(url).path).suffix.lower()
        if ext not in ('.mp3', '.wav', '.m4a', '.ogg', '.mp4', '.webm', '.png', '.jpg', '.jpeg', '.webp'):
            ext = {'image/png': '.png', 'image/jpeg': '.jpg', 'audio/mpeg': '.mp3', 'video/mp4': '.mp4'}.get(response.headers.get('Content-Type', '').split(';')[0], '.bin')
        path = rt.MEDIA / (rt.uid() + ext)
        size = 0
        try:
            with path.open('wb') as stream:
                for chunk in response.iter_content(1024 * 1024):
                    size += len(chunk)
                    if size > 250_000_000:
                        raise ValueError('Generated media exceeds the 250 MB limit')
                    stream.write(chunk)
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return '/media/' + path.name
    raise ValueError('Too many media download redirects')


def poster(url):
    source = Path(rt.local_path(url))
    # Examples are immutable and already include their artwork.
    if url.startswith('/media/samples/'):
        return None
    dest = source.with_suffix('.poster.jpg')
    result = subprocess.run(['ffmpeg', '-y', '-v', 'error', '-ss', '1', '-i', str(source), '-frames:v', '1', '-vf', 'scale=640:-2', str(dest)], capture_output=True, timeout=45)
    return url.rsplit('.', 1)[0] + '.poster.jpg' if result.returncode == 0 else None


def assess(path, prompt, kind):
    return {'score': None, 'verdict': 'unverified', 'reason': 'No semantic quality model is configured for this standalone project.'}
