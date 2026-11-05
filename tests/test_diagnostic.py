"""Read-only diagnostic integration tests, using small official-format fixtures."""
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import srepair as engine


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'Installation with spaces'
        self.root.mkdir()
        (self.root / 'Tibia.exe').write_bytes(b'launcher')
        self.client = self.root / 'packages' / 'Tibia'
        self.client.mkdir(parents=True)
        (self.client / 'client.dll').write_bytes(b'client')
        (self.client / 'asset.dat').write_bytes(b'asset')
        self.documents = {}
        for base, file, content, assets in [
                ('launcher-windows-current/', 'Tibia.exe', b'launcher', False),
                ('tibiaclient-windows-current/', 'client.dll', b'client', False),
                ('assets-current/', 'asset.dat', b'asset', True)]:
            entry = dict(localfile=file, url=file, packedsize=len(content), packedhash=engine.digest(content))
            protected = dict(entry, localfile='conf/settings.json')
            raw = json.dumps({'version': 'test', 'files': [entry, protected]}).encode()
            name = 'assets.json' if assets else 'package.json'
            self.documents[base + name] = raw
            self.documents[base + ('assets.json.sha256' if assets else 'package.json.version')] = (
                engine.digest(raw) if assets else 'test').encode()
        self.events = []
        self.cancel = threading.Event()

    def snapshot(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*') if p.is_file()}

    def run_diagnosis(self):
        before = self.snapshot()
        with patch.object(engine, 'fetch', side_effect=lambda relative, **kwargs: self.documents[relative]), \
             patch('sys.stdout', new_callable=io.StringIO) as stdout:
            result = engine.diagnose(self.root, self.events.append, self.cancel)
            self.assertEqual(stdout.getvalue(), '')
        self.assertEqual(before, self.snapshot())
        self.assertEqual(list(self.root.parent.glob('Tibia-respaldo-*')), [])
        return result

    def test_clean_and_changed_in_both_languages(self):
        for language in ('es', 'en'):
            engine.LANGUAGE = language
            self.assertEqual(self.run_diagnosis()['files'], 0)
        (self.client / 'client.dll').write_bytes(b'wrong!')
        (self.client / 'asset.dat').unlink()
        result = self.run_diagnosis()
        self.assertEqual(result['files'], 2)
        self.assertEqual(result['bytes'], 11)
        self.assertTrue(any('client.dll' in file for file in result['changes']))
        self.assertTrue(any(e['kind'] == 'progress' and e['done'] == e['total'] for e in self.events))

    def test_missing_directory(self):
        engine.diagnose(self.root / 'missing', self.events.append, self.cancel)
        self.assertEqual(self.events[-1]['kind'], 'error')

    def test_malformed_manifest(self):
        for raw in (b'[]', b'{}', b'{invalid'):
            self.documents['launcher-windows-current/package.json'] = raw
            self.assertIsNone(self.run_diagnosis())
            self.assertEqual(self.events[-1]['kind'], 'error')

    def test_network_error(self):
        with patch.object(engine, 'fetch', side_effect=RuntimeError('Network unavailable')):
            engine.diagnose(self.root, self.events.append, self.cancel)
        self.assertEqual(self.events[-1], {'kind': 'error', 'text': 'Network unavailable'})

    def test_cancellation_during_checking(self):
        before = self.snapshot()
        def receive(event):
            self.events.append(event)
            if event['kind'] == 'progress':
                self.cancel.set()
        with patch.object(engine, 'fetch', side_effect=lambda relative, **kwargs: self.documents[relative]):
            engine.diagnose(self.root, receive, self.cancel)
        self.assertEqual(self.events[-1]['kind'], 'cancelled')
        self.assertFalse(any(e['kind'] == 'result' for e in self.events))
        self.assertEqual(before, self.snapshot())

    def test_unsafe_paths_rejected(self):
        name = 'launcher-windows-current/package.json'
        manifest = json.loads(self.documents[name])
        manifest['files'][0]['localfile'] = '../outside.exe'
        self.documents[name] = json.dumps(manifest).encode()
        self.run_diagnosis()
        self.assertEqual(self.events[-1]['kind'], 'error')

    def test_download_cancellation_not_retried(self):
        self.cancel.set()
        with patch.object(engine.urllib.request, 'urlopen') as open_url:
            with self.assertRaises(engine.DiagnosisCancelled):
                engine.fetch('test.json', cancel=self.cancel)
            open_url.assert_not_called()


if __name__ == '__main__':
    unittest.main()
