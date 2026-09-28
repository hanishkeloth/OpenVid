"""Bring-your-own-key providers. Credentials never enter project JSON or browser replies."""
from __future__ import annotations

import base64
import json
import os
import re
import time
from pathlib import Path

import fal_client
import requests
from fastapi import HTTPException

from . import media, runtime as rt

CATALOG = {
    'openai': {'name': 'OpenAI', 'capabilities': ['text', 'image', 'voice', 'captions'], 'base_url': 'https://api.openai.com/v1',
               'text_model': 'gpt-4.1-mini', 'image_model': 'gpt-image-2.5-flare', 'voice_model': 'gpt-4o-mini-tts', 'captions_model': 'whisper-1'},
    'anthropic': {'name': 'Anthropic', 'capabilities': ['text'], 'base_url': 'https://api.anthropic.com/v1', 'text_model': 'claude-fable-5-1'},
    'google': {'name': 'Google Gemini', 'capabilities': ['text'], 'base_url': 'https://generativelanguage.googleapis.com/v1beta', 'text_model': 'gemini-3.8-flash'},
    'elevenlabs': {'name': 'ElevenLabs', 'capabilities': ['voice', 'captions'], 'base_url': 'https://api.elevenlabs.io/v1', 'voice_model': 'eleven_v3', 'captions_model': 'scribe_v2'},
    'fal': {'name': 'fal.ai', 'capabilities': ['image', 'video', 'voice', 'music', 'captions', 'edit', 'avatar'],
            'edit_model': 'google/gemini-omni-flash/v1.1/edit', 'avatar_model': 'fal-ai/bytedance/omnihuman/v1.5',
            'image_model': 'google/nano-banana-2-lite', 'video_model': 'google/gemini-omni-flash/v1.1/text-to-video',
            'voice_model': 'fal-ai/elevenlabs/tts/eleven-v3', 'music_model': 'sonilo/v1.1/text-to-music', 'captions_model': 'fal-ai/elevenlabs/speech-to-text/scribe-v2'},
    'replicate': {'name': 'Replicate', 'capabilities': ['image', 'video', 'voice', 'music'], 'base_url': 'https://api.replicate.com/v1',
                  'image_model': '', 'video_model': '', 'voice_model': '', 'music_model': ''},
    'compatible': {'name': 'OpenAI-compatible endpoint', 'capabilities': ['text', 'image', 'voice', 'captions'],
                   'base_url': '', 'text_model': '', 'image_model': '', 'voice_model': '', 'captions_model': ''},
    'pexels': {'name': 'Pexels', 'capabilities': ['stock'], 'base_url': 'https://api.pexels.com'},
    'pixabay': {'name': 'Pixabay', 'capabilities': ['stock'], 'base_url': 'https://pixabay.com'},
}
MODEL_FIELDS = [kind + '_model' for kind in ('text', 'image', 'video', 'voice', 'music', 'captions')]
PRESET_VOICES = ['Rachel', 'Aria', 'Roger', 'Sarah', 'Laura', 'Charlie', 'George', 'Callum', 'River', 'Liam', 'Charlotte', 'Alice', 'Matilda', 'Will', 'Jessica', 'Eric', 'Chris', 'Brian', 'Daniel', 'Lily', 'Bill']


def config(name):
    return {**CATALOG.get(name, {}), **rt.provider(name)}


def ready(name, kind=None):
    settings = config(name)
    if not settings.get('key') and not (name == 'compatible' and settings.get('base_url') and settings.get('keyless')):
        return False
    return not kind or (kind in settings.get('capabilities', []) and (kind == 'stock' or bool(settings.get(kind + '_model'))))


def choose(kind, provider=None):
    selected = provider or rt.credentials()['defaults'].get(kind)
    if selected:
        if not ready(selected, kind):
            raise ValueError(f'Configure a {kind} model and key for {CATALOG.get(selected, {}).get("name", selected)} in Connections')
        return selected, config(selected)
    order = {'text': ['anthropic', 'openai', 'google', 'compatible'], 'voice': ['elevenlabs', 'openai', 'fal', 'compatible'],
             'image': ['openai', 'fal', 'replicate', 'compatible'], 'video': ['fal', 'replicate'],
             'music': ['fal', 'replicate'], 'captions': ['elevenlabs', 'openai', 'fal', 'compatible']}
    for name in order.get(kind, []):
        if ready(name, kind):
            return name, config(name)
    raise ValueError(f'Add a provider for {kind} in Connections. Editing and exporting existing media do not require an API key.')


def available(kind):
    try:
        choose(kind)
        return True
    except ValueError:
        return False


def public_config():
    saved = rt.credentials()
    out = []
    for name, default in CATALOG.items():
        entry = config(name)
        out.append({'id': name, 'name': default['name'], 'capabilities': default['capabilities'],
                    'configured': ready(name), 'key_hint': ('••••' + entry['key'][-4:]) if entry.get('key') else '',
                    'base_url': entry.get('base_url', ''), 'keyless': entry.get('keyless', False),
                    'models': {kind: entry.get(kind + '_model', '') for kind in default['capabilities'] if kind != 'stock'},
                    'inputs': entry.get('inputs', {})})
    return {'providers': out, 'defaults': saved['defaults'], 'capabilities': {k: available(k) for k in ('text', 'image', 'video', 'voice', 'music', 'captions')}}


def request(name, method, path, **kwargs):
    settings = config(name)
    base = settings.get('base_url', '').rstrip('/')
    if not base:
        raise ValueError('Set a provider base URL in Connections')
    if name == 'compatible':
        media.safe_url(base, allow_local=os.environ.get('OPENVID_ALLOW_LOCAL_PROVIDERS') == 'true')
    headers = {'User-Agent': 'OpenVid/0.1', **kwargs.pop('headers', {})}
    key = settings.get('key', '')
    if name == 'anthropic':
        headers.update({'x-api-key': key, 'anthropic-version': '2023-06-01'})
    elif name == 'google':
        headers['x-goog-api-key'] = key
    elif name == 'elevenlabs':
        headers['xi-api-key'] = key
    elif key:
        headers['Authorization'] = 'Bearer ' + key
    try:
        result = requests.request(method, base + path, headers=headers, timeout=kwargs.pop('timeout', 180), allow_redirects=False, **kwargs)
    except requests.RequestException:
        raise ValueError(f'{CATALOG[name]["name"]} could not be reached. The request was not retried automatically.') from None
    if not result.ok:
        reason = {401: 'Check your API key.', 403: 'Your account does not have access to this operation.',
                  402: 'Check your provider balance.', 429: 'The provider rate or balance limit was reached.',
                  404: 'Check the configured model or endpoint.', 400: 'The model rejected these input settings.',
                  422: 'The model rejected these input settings.'}.get(result.status_code, 'Try again after checking provider status.')
        raise ValueError(f'{CATALOG[name]["name"]} returned HTTP {result.status_code}. {reason}')
    return result


def test_connection(name):
    if name not in CATALOG:
        raise ValueError('Unknown provider')
    if name == 'fal':
        # Read-only account check; does not submit or bill a model request.
        try:
            response = requests.get('https://api.fal.ai/v1/models', params={'limit': 1}, headers={'Authorization': 'Key ' + config(name).get('key', '')}, timeout=25)
        except requests.RequestException:
            raise ValueError('fal.ai could not be reached') from None
        if response.status_code != 200:
            raise ValueError(f'fal.ai returned HTTP {response.status_code}')
        return {'ok': True, 'message': 'Connected; model access is checked when you generate.'}
    if name in ('pexels', 'pixabay'):
        from . import stock_media
        stock_media.search(name, 'image', 'nature', 1)
        return {'ok': True, 'message': 'Stock search connected.'}
    path = {'elevenlabs': '/user', 'replicate': '/account'}.get(name, '/models')
    result = request(name, 'GET', path, timeout=30).json()
    models = result.get('data', result.get('models', []))
    return {'ok': True, 'message': 'Connected.', 'models': [m.get('id', m.get('name', '')) for m in models[:100]]}


def fal_run(endpoint, payload):
    if not ready('fal'):
        raise ValueError('Add your fal.ai key in Connections')
    client = fal_client.SyncClient(key=config('fal')['key'])
    try:
        handle = client.submit(endpoint, arguments=payload)
        rt.provider_task('fal', handle.request_id, endpoint)
        return handle.get(interval=2)
    except Exception as exc:
        # fal exceptions can include payloads and signed URLs; keep public errors bounded.
        status = getattr(getattr(exc, 'response', None), 'status_code', None)
        raise ValueError(f'fal.ai generation failed{f" (HTTP {status})" if status else ""}. Check the model inputs and your provider dashboard; the request was not retried.') from None


def fal_upload(path):
    if not ready('fal'):
        raise ValueError('Add your fal.ai key in Connections')
    return fal_client.SyncClient(key=config('fal')['key']).upload_file(path)


def first(result):
    if isinstance(result, str):
        return media.download(result)
    if isinstance(result, list):
        for item in result:
            try:
                return first(item)
            except ValueError:
                pass
    if isinstance(result, dict):
        if result.get('url'):
            return media.download(result['url'])
        for key in ('audio', 'video', 'image', 'images', 'audios', 'output', 'data'):
            if result.get(key):
                return first(result[key])
    raise ValueError('The provider returned no media output')


_first = first


def text(system, prompt, schema=None):
    name, settings = choose('text')
    model = settings['text_model']
    if schema:
        system += '\nReturn one JSON object only, matching this schema: ' + json.dumps(schema)
    if name == 'anthropic':
        data = request(name, 'POST', '/messages', json={'model': model, 'max_tokens': 12000, 'system': system,
                       'messages': [{'role': 'user', 'content': prompt}]}).json()
        output = ''.join(b.get('text', '') for b in data.get('content', []))
    elif name == 'google':
        data = request(name, 'POST', '/interactions', json={'model': model, 'system_instruction': system, 'input': prompt, 'store': False}).json()
        output = data.get('output_text') or ''.join(b.get('text', '') for b in data.get('outputs', []) if b.get('type') == 'text')
    else:
        payload = {'model': model, 'messages': [{'role': 'system', 'content': system}, {'role': 'user', 'content': prompt}]}
        data = request(name, 'POST', '/chat/completions', json=payload).json()
        output = data['choices'][0]['message']['content']
    if not schema:
        return output
    cleaned = re.sub(r'^```(?:json)?\s*|\s*```$', '', output.strip())
    try:
        return json.loads(cleaned)
    except ValueError:
        raise ValueError('The assistant did not return a valid scene document. Try a more focused request.') from None


def voice_names():
    try:
        name, _ = choose('voice')
        if name in ('openai', 'compatible'):
            return ['alloy', 'coral', 'nova', 'onyx', 'sage', 'shimmer']
        if name == 'elevenlabs':
            return [v['name'] for v in request('elevenlabs', 'GET', '/voices', timeout=30).json().get('voices', [])[:80]] or PRESET_VOICES
    except ValueError:
        pass
    return PRESET_VOICES


def generate(kind, prompt='', duration=8, voice='Rachel', language='', aspect='16:9', reference=None, asset_url=None, provider=None, model=None):
    name, settings = choose(kind, provider)
    model = model or settings[kind + '_model']
    result = {}
    if name == 'fal':
        if kind == 'voice':
            payload = {'text': prompt, 'voice': voice, 'stability': .5, 'timestamps': True}
            if language:
                payload['language_code'] = language
        elif kind == 'music':
            payload = {'prompt': prompt, 'duration': duration, 'num_samples': 1}
        elif kind == 'captions':
            payload = {'audio_url': fal_upload(rt.local_path(asset_url)), 'tag_audio_events': False, 'diarize': False}
        elif kind == 'image':
            payload = {'prompt': prompt, 'aspect_ratio': aspect, 'num_images': 1}
            if reference:
                if model.endswith('/edit'):
                    payload['image_urls'] = [fal_upload(rt.local_path(reference))]
                else:
                    raise ValueError('Choose a fal image-edit model in Connections to use a reference image')
        else:
            payload = {'prompt': prompt, 'duration': duration, 'aspect_ratio': aspect, 'resolution': '720p'}
            if reference:
                if model.endswith('/text-to-video'):
                    model = model.removesuffix('/text-to-video') + '/image-to-video'
                payload['image_url'] = fal_upload(rt.local_path(reference))
        payload.update(settings.get('inputs', {}).get(kind, {}))
        result = fal_run(model, payload)
        if kind == 'captions':
            return {'transcript': result, 'provider': name, 'model': model}
        url = first(result)
    elif name == 'elevenlabs':
        if kind == 'voice':
            voices = request(name, 'GET', '/voices').json().get('voices', [])
            found = next((v for v in voices if v['voice_id'] == voice or v['name'].lower() == voice.lower()), None)
            if not found:
                raise ValueError('Choose a voice available in your ElevenLabs account')
            payload = {'text': prompt, 'model_id': model, 'voice_settings': {'stability': .5, 'similarity_boost': .8}}
            if language:
                payload['language_code'] = language
            result = request(name, 'POST', '/text-to-speech/' + found['voice_id'] + '/with-timestamps', json=payload).json()
            url = media.save_bytes(base64.b64decode(result['audio_base64']), '.mp3')
            result['timestamps'] = [result.get('normalized_alignment') or result.get('alignment') or {}]
        else:
            with open(rt.local_path(asset_url), 'rb') as source:
                data = request(name, 'POST', '/speech-to-text', data={'model_id': model, 'tag_audio_events': 'false'}, files={'file': source}).json()
            return {'transcript': data, 'provider': name, 'model': model}
    elif name in ('openai', 'compatible'):
        if kind == 'image':
            payload = {'model': model, 'prompt': prompt, 'n': 1, 'size': {'16:9': '1536x1024', '9:16': '1024x1536', '1:1': '1024x1024'}[aspect]}
            if reference:
                with open(rt.local_path(reference), 'rb') as source:
                    data = request(name, 'POST', '/images/edits', data=payload, files={'image': source}).json()
            else:
                data = request(name, 'POST', '/images/generations', json=payload).json()
            image = data['data'][0]
            url = media.save_bytes(base64.b64decode(image['b64_json']), '.png') if image.get('b64_json') else media.download(image['url'])
        elif kind == 'voice':
            if len(prompt) > 4096:
                raise ValueError('This speech provider accepts up to 4,096 characters per clip')
            valid_voice = voice
            if voice not in ['alloy', 'ash', 'ballad', 'coral', 'echo', 'fable', 'nova', 'onyx', 'sage', 'shimmer', 'verse', 'marin', 'cedar']:
                raise ValueError('Select a voice supported by your speech provider')
            data = request(name, 'POST', '/audio/speech', json={'model': model, 'input': prompt, 'voice': valid_voice, 'response_format': 'mp3'})
            url = media.save_bytes(data.content, '.mp3')
        else:
            with open(rt.local_path(asset_url), 'rb') as source:
                data = request(name, 'POST', '/audio/transcriptions', data={'model': model, 'response_format': 'verbose_json', 'timestamp_granularities[]': 'word'}, files={'file': source}).json()
            return {'transcript': data, 'provider': name, 'model': model}
    elif name == 'replicate':
        if not re.fullmatch(r'[\w.-]+/[\w.-]+', model):
            raise ValueError('Use a Replicate model in owner/model format')
        payload = {'prompt': prompt, **settings.get('inputs', {}).get(kind, {})}
        if kind in ('video', 'music'):
            payload.setdefault('duration', duration)
        if reference:
            mime = 'image/png' if reference.endswith('.png') else 'image/jpeg'
            payload['image'] = 'data:' + mime + ';base64,' + base64.b64encode(Path(rt.local_path(reference)).read_bytes()).decode()
        data = request(name, 'POST', '/models/' + model + '/predictions', json={'input': payload}).json()
        rid = data['id']
        rt.provider_task(name, rid, model)
        deadline = time.time() + 1800
        while data['status'] not in ('succeeded', 'failed', 'canceled') and time.time() < deadline:
            time.sleep(3)
            data = request(name, 'GET', '/predictions/' + rid).json()
        if data['status'] != 'succeeded':
            raise ValueError('Replicate did not complete this prediction. Review the saved prediction ID in your provider dashboard before retrying.')
        url = first(data.get('output'))
    else:
        raise ValueError('This provider does not support the requested media operation')
    info = media.probe(rt.local_path(url)) if kind in ('video', 'voice', 'music') else {}
    return {'url': url, 'kind': 'audio' if kind in ('voice', 'music') else kind, 'provider': name, 'model': model,
            'label': CATALOG[name]['name'] + ' · ' + model, 'duration': info.get('duration'), 'timestamps': result.get('timestamps'),
            'cost_usd': 0, 'cost_unknown': True}


def model_options():
    models = []
    for name in CATALOG:
        for kind in ('image', 'video'):
            if ready(name, kind):
                settings = config(name)
                models.append({'id': name + ':' + settings[kind + '_model'], 'label': CATALOG[name]['name'] + ' · ' + settings[kind + '_model'],
                               'kind': kind, 'ready': True, 'price_usd': 0, 'cost_unknown': True, 'tier': 'standard',
                               'supports': ['text', 'frames'], 'min_duration': 3, 'max_duration': 10, 'per_second': False})
    return models


def asset(result, prompt, source):
    return rt.make_asset(result['url'], result['kind'], prompt, result['label'], 0, source=source,
                         provider=result['provider'], model=result['model'], cost_unknown=True,
                         timestamps=result.get('timestamps'))
