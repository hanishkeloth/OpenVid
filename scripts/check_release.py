"""Validate the portable examples and the public source allowlist without network access."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FILES = ['README.md', 'LICENSE', 'NOTICE.md', 'CONTRIBUTING.md', 'SECURITY.md', 'Dockerfile', 'docker-entrypoint.sh', 'compose.yaml',
         'railway.json', 'package.json', 'package-lock.json', 'requirements.txt', 'requirements-dev.txt',
         '.gitignore', '.dockerignore', '.env.example']
FOLDERS = ['app', 'web', 'scripts', 'tests', 'docs', 'examples', '.github', 'brag-output']
BLOCKED = {'.env', '.git', 'data', 'node_modules', '.venv', '__pycache__', '.pytest_cache', '.hyperframes', '.thumbnails', 'snapshots', 'brag.mp4', 'brag.jpg'}


def source_files():
    result = [ROOT / name for name in FILES]
    for folder in FOLDERS:
        result.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and not any(x in BLOCKED for x in p.relative_to(ROOT).parts))
    return sorted(set(result))


def check():
    errors = []
    for path in source_files():
        if not path.exists():
            errors.append(f'Missing source file: {path.relative_to(ROOT)}')
            continue
        if path.is_symlink():
            errors.append(f'Symlinks are not allowed in release: {path.relative_to(ROOT)}')
        if path.stat().st_size > 90_000_000:
            errors.append(f'File exceeds repository limit: {path.relative_to(ROOT)}')
        if path.suffix in ('.py', '.js', '.json', '.md', '.txt', '.yaml', '.sh', '.html', '.css', '.mjs'):
            content = path.read_text()
            # Deliberately report paths only, never matched credential values.
            if re.search(r'(?:sk-proj-|sk-ant-api\d*-)[A-Za-z0-9_-]{20,}|AIza[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{25,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----', content):
                errors.append(f'Possible credential: {path.relative_to(ROOT)}')
            if ('/' + 'Users/') in content or ('/private/' + 'tmp/') in content or ('studio.' + 'pltt.dev') in content:
                errors.append(f'Private environment reference: {path.relative_to(ROOT)}')
    examples = ROOT / 'examples/business'
    index = json.loads((examples / 'manifest.json').read_text())
    assert len(index['projects']) == 6
    media_count = 0
    for entry in index['projects']:
        source = json.loads((examples / entry['file']).read_text())
        urls = {a['url'] for a in source['assets']}
        urls |= {l['url'] for s in source['document']['scenes'] for l in s['layers'] if l.get('url')}
        urls |= {l['url'] for l in source['document']['audio'] if l.get('url')}
        for url in urls:
            path = examples / 'media' / url.removeprefix('/media/')
            if not url.startswith('/media/samples/') or not path.is_file():
                errors.append(f'Missing or non-portable asset in {entry["file"]}')
        media_count += len(urls)
    if errors:
        raise SystemExit('\n'.join(errors))
    print(json.dumps({'source_files': len(source_files()), 'sample_projects': 6, 'referenced_assets': media_count, 'release_check': 'passed'}))


if __name__ == '__main__':
    check()
