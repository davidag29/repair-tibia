"""Tk integration checks. Uses synthetic diagnostics, never the real installation."""
from pathlib import Path
import sys
import threading
import time
import tkinter as tk
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
import srepair_gui as gui


class GuiTests(unittest.TestCase):
    def setUp(self):
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.app = gui.DiagnosticApp(self.root)
        self.root.update()

    def test_languages_and_layout_at_multiple_scales(self):
        baseline = float(self.root.tk.call('tk', 'scaling'))
        for ratio in (1, 1.25, 1.5):
            root = tk.Tk()
            try:
                root.tk.call('tk', 'scaling', baseline * ratio)
                app = gui.DiagnosticApp(root)
                for geometry in ('740x720', '680x600', '900x700'):
                    root.geometry(geometry)
                    for language in (0, 1):
                        app.language_choice.current(language)
                        app.change_language()
                        root.update()
                        self.assertLessEqual(app.body.winfo_width(), app.canvas.winfo_width())
                        for widget in (app.browse, app.language_choice, app.check_button, app.title_label,
                                       app.backup_button, app.cancel_button):
                            right = widget.winfo_rootx() + widget.winfo_width()
                            self.assertLessEqual(right, app.canvas.winfo_rootx() + app.canvas.winfo_width())
                        app.canvas.yview_moveto(1)
                        root.update()
                        self.assertAlmostEqual(app.canvas.yview()[1], 1, places=2)
            finally:
                root.destroy()

    def test_worker_events_and_controls(self):
        release = threading.Event()
        self.addCleanup(release.set)
        main_thread = threading.get_ident()
        def diagnose(folder, receive, cancel):
            self.assertNotEqual(main_thread, threading.get_ident())
            release.wait(3)
            receive({'kind': 'result', 'files': 1, 'bytes': 42, 'changes': ['example.dll']})
        with patch.object(gui.engine, 'diagnose', side_effect=diagnose):
            self.app.start()
            self.assertTrue(self.app.busy)
            self.assertTrue(self.app.path_entry.instate(['disabled']))
            self.assertTrue(self.app.language_choice.instate(['disabled']))
            release.set()
            deadline = time.monotonic() + 5
            while self.app.busy and time.monotonic() < deadline:
                self.root.update()
                time.sleep(.01)
            self.assertFalse(self.app.busy)
            self.assertTrue(self.app.language_choice.instate(['readonly']))
            self.assertIn('example.dll', self.app.log.get('1.0', 'end'))

    def test_empty_path_and_close_cancellation(self):
        self.app.path.set('')
        self.app.start()
        self.assertFalse(self.app.busy)
        self.app.busy = True
        with patch.object(gui.messagebox, 'askyesno', return_value=False):
            self.app.request_close()
            self.assertFalse(self.app.cancel.is_set())
        with patch.object(gui.messagebox, 'askyesno', return_value=True):
            self.app.request_close()
            self.assertTrue(self.app.cancel.is_set())
            self.assertTrue(self.app.closing)


if __name__ == '__main__':
    unittest.main()
