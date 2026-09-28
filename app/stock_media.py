"""Server-only Pexels/Pixabay adapters; no credentials or provider error bodies leave here."""
import hashlib
import json
import os
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from fastapi import HTTPException

from . import runtime as eb

CACHE = eb.DATA_ROOT / 'stock-cache'
CACHE_LOCK = threading.RLock()
PER_PAGE = 16
MAX_BYTES = 200_000_000
NAMES = {'pexels': 'Pexels', 'pixabay': 'Pixabay', 'commons': 'Wikimedia Commons'}
HOSTS = {
    'pexels': {'images.pexels.com', 'videos.pexels.com', 'static-videos.pexels.com', 'player.vimeo.com'},
    'pixabay': {'pixabay.com', 'cdn.pixabay.com', 'videos.pexels.com'},
    'commons': {'upload.wikimedia.org'},
}


def available():
    return {p: bool(eb.provider(p).get('key')) for p in ('pexels', 'pixabay')} | {'commons': True}


def safe_media_url(url, provider):
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ''
        allowed = host in HOSTS[provider]
        if provider == 'pexels':
            allowed |= host.endswith('.vimeocdn.com') or host.endswith('.akamaized.net')
        return parsed.scheme == 'https' and allowed and not parsed.username and not parsed.password and parsed.port in (None, 443)
    except (ValueError, TypeError):
        return False


def _source(url, provider):
    p = urlparse(url or '')
    return url if p.scheme == 'https' and p.hostname in {provider + '.com', 'www.' + provider + '.com'} and not p.username else ''


def _api(provider, path, params):
    key = eb.provider(provider).get('key')
    if not key:
        raise HTTPException(503, f'{NAMES[provider]} needs a key in Connections')
    headers = {'User-Agent': 'OpenVid/1.0'}
    params = dict(params)
    if provider == 'pexels':
        base = 'https://api.pexels.com'
        headers['Authorization'] = key
    else:
        base = 'https://pixabay.com'
        params['key'] = key
    try:
        response = requests.get(base + path, params=params, headers=headers, timeout=30, allow_redirects=False)
        if response.status_code in (401, 403):
            raise HTTPException(503, f'{NAMES[provider]} rejected its API key. Check Connections.')
        if response.status_code == 429:
            raise HTTPException(429, f'{NAMES[provider]} search limit reached. Please try again later.')
        if response.status_code == 404:
            raise HTTPException(404, 'This stock item is no longer available')
        if response.status_code != 200:
            raise HTTPException(502, f'{NAMES[provider]} search is temporarily unavailable')
        return response.json()
    except (requests.RequestException, ValueError):
        # Requests exceptions include the full Pixabay URL, including its key.
        raise HTTPException(502, f'{NAMES[provider]} could not be reached. Try again.') from None


def _cached(provider, identity, fetch):
    if not available()[provider]:
        raise HTTPException(503, f'{NAMES[provider]} needs a key in Connections')
    # Cache normalized public metadata, never request URLs/headers or raw responses.
    digest = hashlib.sha256(json.dumps([provider, identity], sort_keys=True).encode()).hexdigest()
    path = CACHE / (digest + '.json')
    with CACHE_LOCK:
        try:
            saved = json.loads(path.read_text())
            if time.time() - saved['at'] < 86400:
                return saved['data']
        except (OSError, ValueError, KeyError):
            pass
        data = fetch()
        CACHE.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.' + uuid.uuid4().hex + '.tmp')
        temp.write_text(json.dumps({'at': time.time(), 'data': data}))
        temp.replace(path)
        return data


def _video_file(files, provider):
    candidates = []
    for f in files:
        url = f.get('link') or f.get('url') or ''
        w, h = f.get('width') or 0, f.get('height') or 0
        if (w > 0 and h > 0 and max(w, h) <= 2048 and min(w, h) <= 1080
                and Path(urlparse(url).path).suffix.lower() == '.mp4'
                and f.get('size', 0) <= MAX_BYTES and safe_media_url(url, provider)):
            candidates.append({**f, 'url': url})
    return max(candidates, key=lambda f: f['width'] * f['height'], default=None)


def normalize(row, provider, kind):
    if provider == 'pexels':
        source = _source(row.get('url'), provider)
        if kind == 'image':
            src = row.get('src') or {}
            url, thumb = src.get('original', ''), src.get('medium', '')
            title, artist = row.get('alt') or 'Pexels photo', row.get('photographer', '')
            width, height = row.get('width', 0), row.get('height', 0)
        else:
            f = _video_file(row.get('video_files', []), provider)
            if not f:
                return None
            url, thumb = f['url'], row.get('image', '')
            title = Path(urlparse(source).path).name.rsplit('-', 1)[0].replace('-', ' ').capitalize() or 'Pexels video'
            artist = (row.get('user') or {}).get('name', '')
            width, height = f['width'], f['height']
        license_name, license_url = 'Pexels License', 'https://www.pexels.com/license/'
    else:
        source = _source(row.get('pageURL'), provider)
        title, artist = row.get('tags') or 'Pixabay stock', row.get('user', '')
        if kind == 'image':
            url = row.get('fullHDURL') or row.get('largeImageURL') or ''
            thumb = row.get('webformatURL') or row.get('previewURL') or ''
            # Standard API access supplies a 1280px download, not the original dimensions.
            width, height = row.get('imageWidth', 0), row.get('imageHeight', 0)
            cap = 1920 if row.get('fullHDURL') else 1280
            factor = min(1, cap / max(width, height, 1))
            width, height = round(width * factor), round(height * factor)
        else:
            f = _video_file((row.get('videos') or {}).values(), provider)
            if not f:
                return None
            url, thumb = f['url'], f.get('thumbnail', '')
            width, height = f['width'], f['height']
        license_name, license_url = 'Pixabay Content License', 'https://pixabay.com/service/license-summary/'
    if not source or not safe_media_url(url, provider):
        return None
    return {'id': row['id'], 'provider': provider, 'kind': kind, 'title': title[:500],
            'url': url, 'thumb': thumb if safe_media_url(thumb, provider) else '',
            'source': source, 'artist': artist[:500], 'license': license_name,
            'license_url': license_url, 'width': width, 'height': height,
            'duration': row.get('duration', 0) if kind == 'video' else 0}


def search(provider, kind, query, page=1):
    if kind not in ('image', 'video'):
        raise HTTPException(422, f'{NAMES[provider]} supports stock photos and videos. Choose Wikimedia Commons for audio.')
    def fetch():
        if provider == 'pexels':
            data = _api(provider, '/v1/search' if kind == 'image' else '/v1/videos/search',
                        {'query': query, 'page': page, 'per_page': PER_PAGE})
            rows, total = data.get('photos' if kind == 'image' else 'videos', []), data.get('total_results', 0)
        else:
            data = _api(provider, '/api/' if kind == 'image' else '/api/videos/',
                        {'q': query, 'page': page, 'per_page': PER_PAGE, 'safesearch': 'true'})
            rows, total = data.get('hits', []), data.get('totalHits', 0)
        return {'items': [item for row in rows if (item := normalize(row, provider, kind))],
                'provider': provider, 'kind': kind, 'page': page, 'total': total,
                'has_more': page * PER_PAGE < total}
    return _cached(provider, ['search', kind, query, page], fetch)


def get_item(provider, kind, item_id):
    if kind not in ('image', 'video'):
        raise HTTPException(422, 'Choose an image or video')
    def fetch():
        if provider == 'pexels':
            row = _api(provider, f'/v1/photos/{item_id}' if kind == 'image' else f'/v1/videos/videos/{item_id}', {})
        else:
            data = _api(provider, '/api/' if kind == 'image' else '/api/videos/', {'id': item_id})
            row = next((r for r in data.get('hits', []) if r.get('id') == item_id), None)
        item = normalize(row, provider, kind) if row else None
        if not item or item['id'] != item_id:
            raise HTTPException(404, 'This stock item has no supported download')
        return item
    return _cached(provider, ['item', kind, item_id], fetch)


def download(item, dest):
    """Resolve every redirect against provider CDN hosts; never forward API credentials."""
    url, provider = item['url'], item.get('provider', 'commons')
    if provider == 'commons':
        url = url.split('?', 1)[0]
    try:
        for _ in range(6):
            if not safe_media_url(url, provider):
                raise HTTPException(502, 'The stock provider returned an unsupported download host')
            with requests.get(url, headers={'User-Agent': 'OpenVid/1.0 (local media editor)'},
                              timeout=(15, 90), stream=True, allow_redirects=False) as response:
                if response.status_code in (301, 302, 303, 307, 308):
                    url = urljoin(url, response.headers.get('Location', ''))
                    continue
                response.raise_for_status()
                if int(response.headers.get('Content-Length') or 0) > MAX_BYTES:
                    raise HTTPException(413, 'Choose a stock file smaller than 200 MB')
                size = 0
                with dest.open('wb') as output:
                    for chunk in response.iter_content(65536):
                        size += len(chunk)
                        if size > MAX_BYTES:
                            raise HTTPException(413, 'Choose a stock file smaller than 200 MB')
                        output.write(chunk)
                if not size:
                    raise HTTPException(502, 'The stock file was empty')
                return
        raise HTTPException(502, 'The stock download redirected too many times')
    except (requests.RequestException, ValueError):
        dest.unlink(missing_ok=True)
        raise HTTPException(502, 'Stock download failed. Try another result or retry.') from None
    except Exception:
        dest.unlink(missing_ok=True)
        raise
