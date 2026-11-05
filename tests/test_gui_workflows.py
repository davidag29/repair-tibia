"""Exercise real repair/restore from Tk with local fixtures and a mocked server."""
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import tkinter as tk
from tkinter import ttk
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import srepair as engine
import srepair_gui as gui


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name) / 'Tibia test with spaces'
        self.folder.mkdir()
        self.client = self.folder / 'packages' / 'Tibia'
        self.client.mkdir(parents=True)
        self.documents = {}
        self.new = {}
        for base, relative, folder, assets in [
                ('launcher-windows-current/', 'Tibia.exe', self.folder, False),
                ('tibiaclient-windows-current/', 'client.dll', self.client, False),
                ('assets-current/', 'asset.dat', self.client, True)]:
            content = ('new ' + relative).encode()
            (folder / relative).write_bytes(('old ' + relative).encode())
            self.new[folder / relative] = content
            entry = dict(localfile=relative, url=relative, packedsize=len(content), packedhash=engine.digest(content))
            raw = json.dumps({'version': 'test', 'files': [entry]}).encode()
            name = 'assets.json' if assets else 'package.json'
            self.documents[base + name] = raw
            self.documents[base + ('assets.json.sha256' if assets else 'package.json.version')] = (
                engine.digest(raw) if assets else 'test').encode()
            self.documents[base + relative] = content
        self.before = self.snapshot()
        self.root = tk.Tk()
        self.app = gui.DiagnosticApp(self.root)
        self.app.path.set(str(self.folder))
        self.addCleanup(self.root.destroy)
        self.server_patch = patch.object(engine, 'fetch', side_effect=self.fetch)
        self.server_patch.start()
        self.addCleanup(self.server_patch.stop)
        self.closed_patch = patch.object(engine, 'require_closed', return_value=False)
        self.closed_patch.start()
        self.addCleanup(self.closed_patch.stop)

    def snapshot(self):
        return {str(path.relative_to(self.folder)): path.read_bytes()
                for path in self.folder.rglob('*') if path.is_file()}

    def fetch(self, relative, progress=None, cancel=None):
        engine.check_cancel(cancel)
        data = self.documents[relative]
        if progress:
            progress(len(data), len(data))
        return data

    def pump(self):
        deadline = time.monotonic() + 10
        while self.app.busy and time.monotonic() < deadline:
            self.root.update()
            time.sleep(.005)
        self.assertFalse(self.app.busy, 'Worker did not finish')
        self.root.update()

    def repair(self, accepted=True):
        with patch.object(gui.messagebox, 'askyesno', return_value=accepted) as question:
            self.app.start('repair')
            self.pump()
        return question

    def test_repair_then_restore_from_backup_dialog(self):
        for language in ('es', 'en'):
            with self.subTest(language=language):
                self.app.language_choice.current(0 if language == 'es' else 1)
                self.app.change_language()
                question = self.repair()
                self.assertTrue(question.called)
                for path, data in self.new.items():
                    self.assertEqual(path.read_bytes(), data)
                self.assertTrue((self.app.last_backup / 'restore.json').is_file())
                self.app.choose_backup()
                dialog = next(widget for widget in self.root.winfo_children() if isinstance(widget, tk.Toplevel))
                def descendants(widget):
                    for child in widget.winfo_children():
                        yield child
                        yield from descendants(child)
                button = next(widget for widget in descendants(dialog)
                              if isinstance(widget, ttk.Button) and widget.cget('text') == self.app.text('restore_action'))
                with patch.object(gui.messagebox, 'askyesno', return_value=True):
                    button.invoke()
                    self.pump()
                self.assertEqual(self.snapshot(), self.before)
                self.assertTrue(self.app.last_backup.exists())

    def test_confirmation_rejected_changes_nothing(self):
        self.repair(False)
        self.assertEqual(self.snapshot(), self.before)
        self.assertEqual(engine.find_backups(self.folder), [])

    def test_reopened_game_requires_fresh_confirmation(self):
        with patch.object(engine, 'require_closed', side_effect=[False, True]), \
             patch.object(gui.messagebox, 'askyesno', side_effect=[True, False]) as question:
            self.app.start('repair')
            self.pump()
        self.assertEqual(question.call_count, 2)
        self.assertEqual(self.snapshot(), self.before)
        self.assertEqual(engine.find_backups(self.folder), [])

    def test_clean_installation_does_not_create_another_backup(self):
        self.repair()
        backups = engine.find_backups(self.folder)
        repaired = self.snapshot()
        question = self.repair()
        self.assertFalse(question.called)
        self.assertEqual(engine.find_backups(self.folder), backups)
        self.assertEqual(self.snapshot(), repaired)
        self.assertEqual(self.app.status.cget('text'), self.app.text('no_changes'))

    def test_stale_metadata_is_repaired_even_when_content_matches(self):
        self.repair()
        (self.folder / 'package.json.version').write_bytes(b'old version marker')
        question = self.repair()
        self.assertTrue(question.called)
        self.assertEqual((self.folder / 'package.json.version').read_bytes(), b'test')
        for path, data in self.new.items():
            self.assertEqual(path.read_bytes(), data)

    def test_confirmation_precedes_first_write(self):
        def confirm(*args, **kwargs):
            self.assertEqual(self.snapshot(), self.before)
            self.assertEqual(engine.find_backups(self.folder), [])
            self.assertIn('3', args[1])
            self.assertEqual(kwargs['default'], 'no')
            return True
        with patch.object(gui.messagebox, 'askyesno', side_effect=confirm):
            self.app.start('repair')
            self.pump()

    def test_corrupt_download_does_not_write(self):
        self.documents['launcher-windows-current/Tibia.exe'] = b'corrupt'
        self.repair()
        self.assertEqual(self.snapshot(), self.before)
        self.assertIsNone(self.app.last_backup)
        self.assertEqual(self.app.status.cget('text'), self.app.text('error'))

    def test_cancellation_during_download(self):
        original = self.fetch
        def cancel_fetch(relative, **kwargs):
            if relative.endswith('/Tibia.exe'):
                self.app.cancel.set()
                engine.check_cancel(self.app.cancel)
            return original(relative, **kwargs)
        with patch.object(engine, 'fetch', side_effect=cancel_fetch):
            self.repair()
        self.assertEqual(self.snapshot(), self.before)
        self.assertEqual(self.app.status.cget('text'), self.app.text('operation_cancelled'))

    def test_write_failure_recovers_originals(self):
        original = engine.shutil.copyfileobj
        def broken_copy(source, destination, *args):
            if Path(destination.name) == self.folder / 'Tibia.exe':
                destination.write(b'partial')
                raise PermissionError('Simulated failed write')
            return original(source, destination, *args)
        with patch.object(engine.shutil, 'copyfileobj', side_effect=broken_copy):
            self.repair()
        self.assertEqual(self.snapshot(), self.before)
        self.assertIn(self.app.text('recovered'), self.app.log.get('1.0', 'end'))
        self.assertTrue(self.app.last_backup.exists())

    def test_failure_keeps_window_open_after_close_request(self):
        handle = self.app.handle_event
        def close_during_install(event):
            handle(event)
            if event['kind'] == 'critical' and event['phase'] == 'install':
                self.app.request_close()
        with patch.object(self.app, 'handle_event', side_effect=close_during_install), \
             patch.object(engine.shutil, 'copyfileobj', side_effect=OSError('Simulated failure')):
            self.repair()
        self.assertFalse(self.app.closing)
        self.assertTrue(self.root.winfo_exists())
        self.assertEqual(self.app.status.cget('text'), self.app.text('error'))

    def test_incomplete_recovery_keeps_backup_and_reports_pending(self):
        original = engine.shutil.copy2
        def deny_rollback(source, target, *args, **kwargs):
            if Path(target) == self.folder / 'Tibia.exe':
                raise PermissionError('Simulated rollback lock')
            return original(source, target, *args, **kwargs)
        with patch.object(engine.shutil, 'copyfileobj', side_effect=OSError('Simulated disk failure')), \
             patch.object(engine.shutil, 'copy2', side_effect=deny_rollback):
            self.repair()
        self.assertIn(self.app.text('recovery_failed'), self.app.log.get('1.0', 'end'))
        self.assertIn(str(self.folder / 'Tibia.exe'), self.app.log.get('1.0', 'end'))
        self.assertTrue((self.app.last_backup / 'restore.json').exists())
        self.app.start('restore', self.app.last_backup)
        self.pump()
        self.assertEqual(self.snapshot(), self.before)

    def test_corrupt_backup_is_rejected_before_restore_writes(self):
        self.repair()
        repaired = self.snapshot()
        (self.app.last_backup / 'files' / 'Tibia.exe').write_bytes(b'corrupt backup')
        self.app.start('restore', self.app.last_backup)
        self.pump()
        self.assertEqual(self.snapshot(), repaired)
        self.assertEqual(self.app.status.cget('text'), self.app.text('error'))

    def test_server_changed_before_backup(self):
        original = self.fetch
        calls = 0
        def changed(relative, **kwargs):
            nonlocal calls
            if relative == 'launcher-windows-current/package.json':
                calls += 1
                if calls > 1:
                    return b'new server version'
            return original(relative, **kwargs)
        with patch.object(engine, 'fetch', side_effect=changed):
            self.repair()
        self.assertEqual(self.snapshot(), self.before)
        self.assertEqual(engine.find_backups(self.folder), [])

    def test_cancellation_during_install_is_deferred(self):
        def receive(event):
            if event['kind'] == 'critical':
                self.app.cancel.set()
        self.closed_patch.stop()
        with patch.object(engine, 'require_closed', return_value=False):
            bundles = engine.plans(self.folder, receiver=lambda event: None)
            with engine.operation_events(receive, self.app.cancel):
                engine.repair(self.folder, bundles)
        for path, data in self.new.items():
            self.assertEqual(path.read_bytes(), data)

    def test_process_wait_and_cancel(self):
        self.closed_patch.stop()
        cancel = threading.Event()
        events = []
        active = [{'Name': 'Tibia.exe'}]
        with engine.operation_events(events.append, cancel), \
             patch.object(engine, 'running', side_effect=[active, []]), \
             patch.object(cancel, 'wait', return_value=False):
            self.assertTrue(engine.require_closed(self.folder))
        self.assertTrue(any(event['kind'] == 'waiting' for event in events))
        cancel.set()
        with engine.operation_events(events.append, cancel):
            with self.assertRaises(engine.DiagnosisCancelled):
                engine.require_closed(self.folder)


if __name__ == '__main__':
    unittest.main()
