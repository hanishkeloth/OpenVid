"""Run with python -m unittest discover -s tests (no paid API calls)."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import runtime as rt, webapp, providers, documents


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.patch = patch.object(rt, 'DATA_ROOT', Path(self.temp.name))
        self.patch.start()
        self.a = TestClient(webapp.app)
        self.b = TestClient(webapp.app)
        self.a.get('/vids')
        self.b.get('/vids')

    def tearDown(self):
        # Wait only for work submitted by the test; do not shut down the global pool.
        self.patch.stop()
        self.temp.cleanup()

    def first_doc(self, client):
        rows = client.get('/api/vids').json()
        self.assertEqual(len(rows), 6)
        return client.get('/api/vids/' + rows[0]['id']).json()

    def test_examples_private_documents_and_revision_conflicts(self):
        a, b = self.first_doc(self.a), self.first_doc(self.b)
        self.assertNotEqual(a['id'], b['id'])
        for endpoint in ('/api/vids/' + a['id'], '/api/projects/' + a['project_id'], '/api/jobs/' + a['exports'][0]['job_id']):
            self.assertEqual(self.b.get(endpoint).status_code, 404)
        a['document']['name'] = 'Changed in workspace A'
        saved = self.a.put('/api/vids/' + a['id'], json={'revision': 1, 'document': a['document']})
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertEqual(self.a.put('/api/vids/' + a['id'], json={'revision': 1, 'document': a['document']}).status_code, 409)
        self.assertNotEqual(self.b.get('/api/vids/' + b['id']).json()['document']['name'], a['document']['name'])

    def test_encrypted_keys_never_returned_or_shared(self):
        fake = 'sk-test-openvid-unique-key'
        response = self.a.put('/api/providers/openai', json={'key': fake, 'models': {'voice': 'gpt-4o-mini-tts'}})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn(fake, response.text)
        self.assertFalse(next(p for p in self.b.get('/api/providers').json()['providers'] if p['id'] == 'openai')['configured'])
        path = next(Path(self.temp.name).glob('workspaces/*/providers.enc'))
        self.assertNotIn(fake.encode(), path.read_bytes())
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertNotIn(fake, self.a.get('/api/vids/' + self.first_doc(self.a)['id']).text)
        self.a.put('/api/providers/openai', json={'models': {'voice': 'updated-model'}})
        self.assertTrue(next(p for p in self.a.get('/api/providers').json()['providers'] if p['id'] == 'openai')['configured'])
        self.assertEqual(self.a.delete('/api/providers/openai').status_code, 200)

    def test_workspace_media_and_path_traversal(self):
        wid = self.a.cookies['openvid_workspace']
        folder = Path(self.temp.name) / 'workspaces' / wid / 'media'
        folder.mkdir(parents=True)
        (folder / 'private.png').write_bytes(b'private fixture')
        self.assertEqual(self.a.get('/media/private.png').content, b'private fixture')
        self.assertEqual(self.b.get('/media/private.png').status_code, 404)
        for url in ['/media/%2e%2e/providers.enc', '/media/%2e%2e/%2e%2e/.encryption-key', '/media/log.html']:
            self.assertIn(self.a.get(url).status_code, (404, 422))
        self.assertEqual(self.a.post('/api/vids', headers={'origin': 'https://attacker.example'}, json={}).status_code, 403)

    def test_dispatch_defaults_jobs_and_duplicate_requests(self):
        d = self.first_doc(self.a)
        self.a.put('/api/providers/openai', json={'key': 'sk-test-placeholder'})
        self.a.put('/api/provider-defaults', json={'image': 'openai'})
        image = next(l['url'] for s in d['document']['scenes'] for l in s['layers'] if l['kind'] == 'image')
        result = {'url': image, 'kind': 'image', 'provider': 'openai', 'model': 'test-model', 'label': 'OpenAI fixture'}
        payload = {'project_id': d['project_id'], 'request_id': 'dispatch-test-123', 'kind': 'image', 'prompt': 'One image', 'model': 'openai:test-model'}
        with patch.object(providers, 'generate', return_value=result) as generate:
            first = self.a.post('/api/generate', json=payload)
            self.assertEqual(first.status_code, 200, first.text)
            jid = first.json()['jobs'][0]
            self.assertEqual(self.a.post('/api/generate', json=payload).json()['jobs'], [jid])
            for _ in range(100):
                job = self.a.get('/api/jobs/' + jid).json()
                if job['status'] not in ('queued', 'running'):
                    break
                time.sleep(.01)
            self.assertEqual(job['status'], 'done', job)
            generate.assert_called_once()
            self.assertEqual(generate.call_args.kwargs['provider'], 'openai')
            self.assertEqual(self.b.get('/api/jobs/' + jid).status_code, 404)

    def test_assistant_patch_preserves_all_untouched_layers(self):
        source = self.first_doc(self.a)['document']
        result = documents.apply_edit(source, {'patch': [{'op': 'replace', 'path': '/name', 'value': 'Updated'}]})
        self.assertEqual(result['name'], 'Updated')
        self.assertEqual(result['scenes'], source['scenes'])
        self.assertNotEqual(source['name'], 'Updated')
        self.assertEqual(documents.Document.model_validate(result).name, 'Updated')
        with self.assertRaises(ValueError):
            documents.apply_edit(source, {'patch': [{'op': 'replace', 'path': '/scenes/-1/name', 'value': 'Bad'}]})

    def test_custom_provider_validation_and_disabled_generation(self):
        self.assertEqual(self.a.put('/api/providers/compatible', json={'base_url': 'http://127.0.0.1:7777/v1', 'keyless': True}).status_code, 422)
        self.assertEqual(self.a.put('/api/providers/openai', json={'models': {'video': 'not-supported'}}).status_code, 422)
        d = self.first_doc(self.a)
        result = self.a.post('/api/vids/' + d['id'] + '/generate', json={'request_id': 'no-key-test', 'kind': 'voice', 'prompt': 'Hello'})
        self.assertEqual(result.status_code, 422)
        self.assertIn('Connections', result.text)
        self.assertEqual(self.a.post('/api/avatar', json={'project_id': d['project_id']}).status_code, 422)


if __name__ == '__main__':
    unittest.main()
