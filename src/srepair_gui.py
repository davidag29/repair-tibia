"""Portable Tkinter interface for diagnosis, repair and backup restoration."""
import os
from pathlib import Path
import queue
import random
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import srepair as engine


# Original palette inspired by the classic client's stone panels and raised controls.
THEME = {
    'background': '#414141', 'panel': '#484848', 'inset': '#282828',
    'text': '#d2d2d2', 'muted': '#aaaaaa', 'gold': '#c6c6c6',
    'edge': '#777777', 'button': '#515151', 'active': '#606060',
    'disabled': '#a2a399', 'primary': '#415b6a', 'primary_active': '#526f80',
}


COPY = {
    'title': ('Asistente de reparación', 'Repair assistant'),
    'repair': ('Reparar Tibia', 'Repair Tibia'),
    'backups': ('Respaldos / Restaurar', 'Backups / Restore'),
    'exit': ('Salir', 'Exit'),
    'description': ('Descarga archivos oficiales, verifica su integridad y crea un respaldo antes de reemplazarlos.',
                    'Downloads official files, verifies their integrity and backs them up before replacement.'),
    'preview': ('Comprueba primero o elige Reparar. Siempre se pedirá confirmación antes de continuar.',
                'Check first or choose Repair. You will always be asked to confirm before proceeding.'),
    'installation': ('Instalación de Tibia', 'Tibia installation'),
    'browse': ('Examinar…', 'Browse…'),
    'check': ('Comprobar instalación', 'Check installation'),
    'progress': ('Estado de la operación', 'Operation status'),
    'ready': ('Listo. Comprobar no modifica archivos; Reparar requiere confirmación.',
              'Ready. Check does not modify files; Repair requires confirmation.'),
    'missing': ('No encontramos Tibia en la ubicación habitual. Indica otra carpeta o usa Examinar.',
                'Tibia was not found in the usual location. Enter another folder or use Browse.'),
    'choose': ('Selecciona la carpeta de instalación de Tibia', 'Select the Tibia installation folder'),
    'empty': ('Indica una carpeta de Tibia para comenzar.', 'Enter a Tibia folder to begin.'),
    'query': ('Consultando manifiestos oficiales…', 'Requesting official manifests…'),
    'checking': ('Comprobando integridad de archivos…', 'Checking file integrity…'),
    'current': ('Archivo / grupo actual', 'Current file / group'),
    'total': ('Progreso de la etapa', 'Stage progress'),
    'preserved': ('Se conservan tus mapas, atajos y configuraciones.',
                  'Your maps, hotkeys and settings are preserved.'),
    'disclaimer': ('Herramienta independiente, sin aprobación de CipSoft o BattlEye.',
                   'Independent tool, not approved by CipSoft or BattlEye.'),
    'cancel_question': ('¿Solicitar cierre? Si ya se están reemplazando archivos, se terminará la operación o su recuperación antes de cerrar.',
                        'Request close? If files are being replaced, the operation or its recovery will finish before closing.'),
    'closing': ('Esperando un punto seguro para cerrar…', 'Waiting for a safe point to close…'),
    'error': ('No se pudo completar la operación. Revisa el registro.', 'The operation could not be completed. Check the log.'),
    'complete': ('Diagnóstico terminado. No se modificó la instalación.',
                  'Diagnostic complete. The installation was not changed.'),
    'clean': ('Los archivos comprobados están actualizados.', 'The checked files are up to date.'),
    'summary': ('{files} archivos requieren reemplazo · Descarga estimada: {size}',
                 '{files} files need replacement · Estimated download: {size}'),
    'pending': ('Archivos pendientes:', 'Pending files:'),
    'cancelled': ('Diagnóstico cancelado. No se modificó la instalación.',
                   'Diagnostic cancelled. The installation was not changed.'),
    'cancel': ('Cancelar operación', 'Cancel operation'),
    'cancelling': ('Cancelación solicitada. Esperando un punto seguro…', 'Cancellation requested. Waiting for a safe point…'),
    'operation_cancelled': ('Operación cancelada antes de reemplazar archivos.', 'Operation cancelled before replacing files.'),
    'waiting': ('Cierra Tibia y su iniciador. Continuaremos aquí automáticamente.',
                 'Close Tibia and its launcher. This window will continue automatically.'),
    'confirm_repair': ('¿Reparar esta instalación?\n\n{files} archivos del juego requieren reemplazo.\nDescarga estimada: {size}.\nTambién se sincronizarán los metadatos oficiales.\n\nInstalación: {root}\nRespaldo: {parent}\\Tibia-respaldo-FECHA-*\n\nSe descargarán y verificarán los archivos oficiales, se creará el respaldo y después se aplicarán los cambios. Se conservan tus datos personales.',
                        'Repair this installation?\n\n{files} game files need replacement.\nEstimated download: {size}.\nOfficial metadata will also be synchronized.\n\nInstallation: {root}\nBackup: {parent}\\Tibia-respaldo-DATE-*\n\nOfficial files will be downloaded and verified, backed up, then replaced. Your personal data is preserved.'),
    'repair_complete': ('Reparación completada. Abre Tibia desde tu acceso directo habitual.',
                         'Repair completed. Start Tibia from your usual shortcut.'),
    'restore_complete': ('Restauración completada. Se conserva el respaldo.', 'Restore completed. The backup is retained.'),
    'no_changes': ('No se requieren cambios; archivos y metadatos están actualizados.',
                    'No changes needed; files and metadata are up to date.'),
    'backup_folder': ('Abrir carpeta del respaldo', 'Open backup folder'),
    'choose_backup': ('Selecciona un respaldo', 'Select a backup'),
    'backup_location': ('Los respaldos se guardan junto a Tibia:', 'Backups are stored beside Tibia:'),
    'restore_action': ('Restaurar seleccionado', 'Restore selected'),
    'back': ('Volver', 'Back'),
    'manual_backup': ('Buscar otra carpeta…', 'Browse another folder…'),
    'no_backups': ('No hay respaldos disponibles para esta instalación.', 'No backups are available for this installation.'),
    'confirm_restore': ('¿Restaurar este respaldo?\n\nInstalación: {root}\nRespaldo: {backup}\n\nSe recuperarán los archivos anteriores y se quitarán los creados por esa reparación. Esto puede devolver Tibia a una versión antigua. Se conservará el respaldo.',
                         'Restore this backup?\n\nInstallation: {root}\nBackup: {backup}\n\nPrevious files will be recovered and files created by that repair removed. Tibia may revert to an older version. The backup will be retained.'),
    'install': ('Instalando y verificando. Espera a que termine antes de cerrar.',
                 'Installing and verifying. Wait for completion before closing.'),
    'restore': ('Restaurando archivos. Espera a que termine antes de cerrar.',
                 'Restoring files. Wait for completion before closing.'),
    'rollback': ('Recuperando los archivos originales tras un fallo…', 'Recovering original files after a failure…'),
    'recovered': ('Recuperación automática completada.', 'Automatic recovery completed.'),
    'recovery_failed': ('Recuperación incompleta. Conserva el respaldo y reintenta Restaurar. Archivos pendientes:',
                         'Recovery incomplete. Keep the backup and retry Restore. Pending files:'),
}


class DiagnosticApp:
    def __init__(self, root):
        self.root = root
        self.language = 'es'
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.worker = None
        self.busy = False
        self.closing = False
        self.critical = False
        self.last_backup = None
        self.text_bindings = []
        self.wrap_labels = []
        root.title(self.text('title'))
        root.geometry('740x720')
        root.minsize(680, 600)
        root.configure(background=THEME['background'])
        if os.name == 'nt':
            # Match the native Windows title bar to the dark content, when supported.
            import ctypes
            from ctypes import wintypes
            root.update_idletasks()
            try:
                user = ctypes.windll.user32
                user.GetParent.argtypes = [wintypes.HWND]
                user.GetParent.restype = wintypes.HWND
                handle = user.GetParent(root.winfo_id())
                dark = ctypes.c_int(1)
                set_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
                set_attribute.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
                set_attribute(handle, 20, ctypes.byref(dark), ctypes.sizeof(dark))
            except (AttributeError, OSError):
                pass
        assets = Path(sys._MEIPASS) / 'assets' if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1] / 'packaging'
        self.icon = tk.PhotoImage(master=root, file=str(assets / 'srepair.png'))
        self.small_icon = self.icon.subsample(8, 8)
        root.iconphoto(True, self.icon, self.small_icon)
        root.protocol('WM_DELETE_WINDOW', self.request_close)
        self.configure_style()

        outer = ttk.Frame(root)
        outer.pack(fill='both', expand=True)
        self.canvas = tk.Canvas(outer, highlightthickness=0, background=THEME['background'])
        scroll = ttk.Scrollbar(outer, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.body = ttk.Frame(self.canvas, padding=12)
        self.body.columnconfigure(0, weight=1)
        self.body_id = self.canvas.create_window(0, 0, window=self.body, anchor='nw')
        self.body.bind('<Configure>', lambda event: self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', self.resize)
        root.bind_all('<MouseWheel>', self.mouse_wheel)
        root.bind_all('<FocusIn>', self.reveal_focus, add='+')

        header = self.header = ttk.Frame(self.body, style='Header.TFrame', padding=10)
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        self.header_icon = self.icon.subsample(4, 4)
        self.title_label = ttk.Label(header, style='Title.TLabel',
                                     image=self.header_icon, compound='left', padding=(0, 0, 12, 0))
        self.bind_text(self.title_label, 'title')
        self.title_label.grid(row=0, column=0, rowspan=2, sticky='w')
        language_box = self.language_box = ttk.Frame(header)
        language_box.grid(row=0, column=1, rowspan=2, sticky='ne', padx=(16, 0))
        ttk.Label(language_box, text='Idioma / Language', style='Accent.TLabel').pack(anchor='w', pady=(0, 6))
        self.language_choice = ttk.Combobox(language_box, values=('Español', 'English'), state='readonly', width=17)
        self.language_choice.current(0)
        self.language_choice.pack(fill='x')
        self.language_choice.bind('<<ComboboxSelected>>', self.change_language)

        actions = ttk.Frame(self.body)
        actions.grid(row=1, column=0, sticky='ew', pady=(8, 6))
        for index in range(3):
            actions.columnconfigure(index, weight=1)
        self.repair_button = self.button(actions, 'repair', command=lambda: self.start('repair'))
        self.repair_button.grid(row=0, column=0, sticky='ew', padx=(0, 8))
        self.backups_button = self.button(actions, 'backups', command=self.choose_backup)
        self.backups_button.grid(row=0, column=1, sticky='ew', padx=4)
        self.button(actions, 'exit', command=self.request_close).grid(row=0, column=2, sticky='ew', padx=(8, 0))
        self.wrapped('description', 2)
        self.wrapped('preview', 3, 'Notice.TLabel')

        installation = ttk.LabelFrame(self.body, padding=10, labelanchor='n')
        self.bind_text(installation, 'installation')
        installation.grid(row=4, column=0, sticky='ew', pady=(8, 6))
        installation.columnconfigure(0, weight=1)
        default = Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData' / 'Local'))) / 'Tibia'
        self.path = tk.StringVar(master=root, value=str(default))
        self.path_entry = ttk.Entry(installation, textvariable=self.path)
        self.path_entry.grid(row=0, column=0, sticky='ew', padx=(0, 10))
        self.browse = self.button(installation, 'browse', command=self.choose_folder)
        self.browse.grid(row=0, column=1)
        self.check_button = self.button(installation, 'check', command=self.start, style='Primary.TButton')
        self.check_button.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(10, 0))

        group = ttk.LabelFrame(self.body, padding=10, labelanchor='n')
        self.bind_text(group, 'progress')
        group.grid(row=5, column=0, sticky='ew', pady=(4, 6))
        group.columnconfigure(1, weight=1)
        self.status = ttk.Label(group, style='Strong.TLabel', wraplength=700)
        self.status.grid(row=0, column=0, columnspan=2, sticky='ew')
        self.wrap_labels.append(self.status)
        self.file = ttk.Label(group, text='—', wraplength=700)
        self.file.grid(row=1, column=0, columnspan=2, sticky='ew', pady=(4, 6))
        self.wrap_labels.append(self.file)
        self.label(group, 'current').grid(row=2, column=0, sticky='w', padx=(0, 12))
        self.current = ttk.Progressbar(group, maximum=100)
        self.current.grid(row=2, column=1, sticky='ew', pady=4)
        self.label(group, 'total').grid(row=3, column=0, sticky='w', padx=(0, 12))
        self.total = ttk.Progressbar(group, maximum=3, style='Total.Horizontal.TProgressbar')
        self.total.grid(row=3, column=1, sticky='ew', pady=4)
        log_box = ttk.Frame(group)
        log_box.grid(row=4, column=0, columnspan=2, sticky='ew', pady=(6, 0))
        self.log = tk.Text(log_box, height=4, wrap='word', font=('Tahoma', 10),
                           background=THEME['inset'], foreground=THEME['text'], relief='sunken', borderwidth=2,
                           insertbackground=THEME['gold'], selectbackground=THEME['primary'],
                           padx=8, pady=6, state='disabled')
        log_scroll = ttk.Scrollbar(log_box, orient='vertical', command=self.log.yview)
        self.log.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side='right', fill='y')
        self.log.pack(side='left', fill='both', expand=True)
        buttons = ttk.Frame(group)
        buttons.grid(row=5, column=0, columnspan=2, sticky='ew', pady=(6, 0))
        self.backup_button = self.button(buttons, 'backup_folder', state='disabled', command=self.open_backup)
        self.backup_button.pack(side='left')
        self.cancel_button = self.button(buttons, 'cancel', state='disabled', command=self.request_cancel)
        self.cancel_button.pack(side='right')
        self.wrapped('preserved', 6, 'Accent.TLabel')
        self.wrapped('disclaimer', 7, 'Muted.TLabel')
        self.refresh_text()
        self.status.configure(text=self.text('ready') if engine.recognizable_installation(default) else self.text('missing'))
        self.poll_id = self.root.after(60, self.poll)
        self.root.bind('<Destroy>', self.on_destroy, add='+')

    def on_destroy(self, event):
        if event.widget is self.root:
            self.cancel.set()
            if self.poll_id:
                self.root.after_cancel(self.poll_id)
                self.poll_id = None

    def configure_style(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        style.configure('.', font=('Tahoma', 10), background=THEME['background'], foreground=THEME['text'],
                        bordercolor=THEME['edge'], lightcolor='#686a68', darkcolor='#202223',
                        troughcolor=THEME['inset'], focuscolor=THEME['gold'])
        style.configure('Header.TFrame', background=THEME['background'], relief='ridge', borderwidth=2)
        style.configure('TButton', padding=(10, 5), background=THEME['button'], relief='raised',
                        borderwidth=2, anchor='center')
        style.map('TButton', background=[('disabled', '#3e4143'), ('pressed', '#353b3e'), ('active', THEME['active'])],
                  foreground=[('disabled', THEME['disabled']), ('active', '#fff6df')],
                  relief=[('pressed', 'sunken'), ('!pressed', 'raised')])
        style.configure('TLabel', background=THEME['background'])
        style.configure('TLabelframe', borderwidth=2, relief='ridge')
        style.configure('TLabelframe.Label', foreground='#bcbcbc', font=('Tahoma', 10, 'bold'), padding=(8, 1))
        style.configure('Title.TLabel', font=('Tahoma', 17, 'bold'), foreground='#dedede')
        style.configure('Muted.TLabel', foreground=THEME['muted'])
        style.configure('Accent.TLabel', foreground='#b9c7d0', font=('Tahoma', 10, 'bold'))
        style.configure('Strong.TLabel', font=('Tahoma', 10, 'bold'))
        style.configure('Notice.TLabel', foreground='#c5c0ab', padding=(8, 6), background='#393939',
                        relief='ridge', borderwidth=1)
        style.configure('Primary.TButton', background=THEME['primary'], foreground='#fff5dc',
                        font=('Tahoma', 10, 'bold'))
        style.map('Primary.TButton', background=[('disabled', '#3e4143'), ('pressed', '#304651'),
                  ('active', THEME['primary_active'])], foreground=[('disabled', THEME['disabled'])])
        for control in ('TEntry', 'TCombobox'):
            style.configure(control, fieldbackground=THEME['inset'], background=THEME['button'],
                            foreground=THEME['text'], arrowcolor=THEME['gold'], insertcolor=THEME['gold'],
                            selectbackground=THEME['primary'], selectforeground='#ffffff', padding=5)
            style.map(control, fieldbackground=[('disabled', '#323537'), ('readonly', THEME['inset'])],
                      foreground=[('disabled', THEME['disabled']), ('readonly', THEME['text'])],
                      background=[('active', THEME['active'])])
        style.configure('Vertical.TScrollbar', background=THEME['button'], arrowcolor=THEME['gold'])
        style.map('Vertical.TScrollbar', background=[('active', THEME['active'])])
        style.configure('Horizontal.TProgressbar', background='#6d9955', troughcolor=THEME['inset'],
                        lightcolor='#8aac70', darkcolor='#3e6036', borderwidth=2, thickness=13)
        style.configure('Total.Horizontal.TProgressbar', background='#658bb5',
                        lightcolor='#829fc5', darkcolor='#3c5576')
        self.root.option_add('*TCombobox*Listbox.background', THEME['inset'])
        self.root.option_add('*TCombobox*Listbox.foreground', THEME['text'])
        self.root.option_add('*TCombobox*Listbox.selectBackground', THEME['primary'])
        self.root.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')
        self.install_stone_surfaces(style)

    def install_stone_surfaces(self, style):
        """Small original, deterministic tiles: no external textures or image runtime."""
        self.textures = []
        def stone(name, color, bevel=False, pressed=False):
            rng = random.Random(157)
            base = tuple(int(color[index:index + 2], 16) for index in (1, 3, 5))
            image = tk.PhotoImage(master=self.root, width=96, height=96)
            rows = []
            for y in range(96):
                row = []
                for x in range(96):
                    fiber = ((x - 2 * y) % 19 in (0, 1)) - ((x - 2 * y + 3) % 19 == 0)
                    shade = rng.randrange(-4, 5) + fiber * 3
                    if bevel and (x < 2 or y < 2):
                        shade = -28 if pressed else 30
                    elif bevel and (x >= 94 or y >= 94):
                        shade = 26 if pressed else -30
                    row.append('#' + ''.join(f'{min(255, max(0, value + shade)):02x}' for value in base))
                rows.append('{' + ' '.join(row) + '}')
            image.put(' '.join(rows))
            self.textures.append(image)
            return image

        surface = stone('surface', THEME['background'])
        raised = stone('button', THEME['button'], True)
        pressed = stone('pressed', '#484848', True, True)
        hover = stone('hover', '#606060', True)
        inactive = stone('disabled', '#414141', True)
        blue = stone('blue', '#28536f', True)
        blue_hover = stone('blue-hover', '#346785', True)
        blue_pressed = stone('blue-pressed', '#23465d', True, True)
        style.element_create('Stone.surface', 'image', surface, width=0, height=0, sticky='nsew')
        style.layout('TFrame', [('Stone.surface', {'sticky': 'nsew'})])
        label_layout = [('Stone.surface', {'sticky': 'nsew', 'children': [
            ('Label.padding', {'sticky': 'nsew', 'children': [('Label.label', {'sticky': 'nsew'})]})]})]
        style.layout('TLabel', label_layout)
        # Preserve the explicit preview notice's flat, inset background.
        style.layout('Notice.TLabel', [('Label.border', {'sticky': 'nsew', 'children': [
            ('Label.padding', {'sticky': 'nsew', 'children': [('Label.label', {'sticky': 'nsew'})]})]})])
        style.layout('Header.TFrame', [('Stone.surface', {'sticky': 'nsew'}),
                                       ('Frame.border', {'sticky': 'nsew'})])
        style.layout('TLabelframe', [('Stone.surface', {'sticky': 'nsew'}),
                                     ('Labelframe.border', {'sticky': 'nsew'})])
        for prefix, normal, active, down in [('Stone', raised, hover, pressed),
                                             ('PrimaryStone', blue, blue_hover, blue_pressed)]:
            style.element_create(prefix + '.button', 'image', normal,
                                 ('disabled', inactive), ('pressed', down), ('active', active),
                                 border=2, width=0, height=0, sticky='nsew')
            layout = [(prefix + '.button', {'sticky': 'nsew', 'children': [
                ('Button.focus', {'sticky': 'nsew', 'children': [
                    ('Button.padding', {'sticky': 'nsew', 'children': [('Button.label', {'sticky': 'nsew'})]})]})]})]
            style.layout('TButton' if prefix == 'Stone' else 'Primary.TButton', layout)

    def text(self, key):
        return COPY[key][0 if self.language == 'es' else 1]

    def bind_text(self, widget, key):
        self.text_bindings.append((widget, key))
        widget.configure(text=self.text(key))
        return widget

    def label(self, parent, key, **kwargs):
        return self.bind_text(ttk.Label(parent, **kwargs), key)

    def button(self, parent, key, **kwargs):
        return self.bind_text(ttk.Button(parent, **kwargs), key)

    def wrapped(self, key, row, style='TLabel'):
        label = self.label(self.body, key, style=style, wraplength=800, justify='left')
        label.grid(row=row, column=0, sticky='ew', pady=4)
        self.wrap_labels.append(label)

    def resize(self, event):
        self.canvas.itemconfigure(self.body_id, width=event.width)
        if self.title_label.winfo_reqwidth() + self.language_box.winfo_reqwidth() + 68 > event.width:
            self.language_box.grid_configure(row=2, column=0, columnspan=2, rowspan=1,
                                             sticky='w', padx=0, pady=(8, 0))
        else:
            self.language_box.grid_configure(row=0, column=1, columnspan=1, rowspan=2,
                                             sticky='ne', padx=(16, 0), pady=0)
        for label in self.wrap_labels:
            label.configure(wraplength=max(250, event.width - 90))

    def mouse_wheel(self, event):
        if isinstance(event.widget, (tk.Text, ttk.Combobox)):
            return
        if self.body.winfo_height() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-event.delta / 120), 'units')

    def reveal_focus(self, event):
        widget = event.widget
        if not str(widget).startswith(str(self.body)):
            return
        y = widget.winfo_rooty() - self.body.winfo_rooty()
        top = self.canvas.canvasy(0)
        bottom = top + self.canvas.winfo_height()
        if y < top or y + widget.winfo_height() > bottom:
            target = max(0, y - 24)
            self.canvas.yview_moveto(target / max(self.body.winfo_height(), 1))

    def refresh_text(self):
        self.root.title(self.text('title'))
        for widget, key in self.text_bindings:
            widget.configure(text=self.text(key))

    def change_language(self, event=None):
        if self.busy:
            return
        self.language = 'es' if self.language_choice.current() == 0 else 'en'
        engine.LANGUAGE = self.language
        self.refresh_text()
        self.status.configure(text=self.text('ready'))
        self.file.configure(text='—')
        self.current.stop()
        self.current.configure(mode='determinate', value=0)
        self.total.configure(value=0)
        self.clear_log()

    def choose_folder(self):
        selected = filedialog.askdirectory(parent=self.root, title=self.text('choose'), mustexist=True)
        if selected:
            self.path.set(selected)

    def clear_log(self):
        self.log.configure(state='normal')
        self.log.delete('1.0', 'end')
        self.log.configure(state='disabled')

    def append_log(self, text):
        self.log.configure(state='normal')
        self.log.insert('end', text.strip() + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def installation_folder(self):
        raw = self.path.get().strip().strip('"')
        if not raw:
            self.status.configure(text=self.text('empty'))
            return
        try:
            folder = Path(raw).expanduser().resolve()
            if folder.name.lower() == 'tibia.exe':
                folder = folder.parent
        except (OSError, ValueError) as exc:
            self.status.configure(text=self.text('error'))
            self.append_log(str(exc))
            return
        self.path.set(str(folder))
        return folder

    def confirm_plan(self, bundles, folder):
        response = {'kind': 'confirm_repair', 'bundles': bundles, 'root': folder,
                    'answered': threading.Event(), 'accepted': False}
        self.events.put(response)
        while not response['answered'].wait(.1):
            engine.check_cancel(self.cancel)
        engine.check_cancel(self.cancel)
        return response['accepted']

    def start(self, operation='diagnose', backup=None):
        if self.busy:
            return
        folder = self.installation_folder()
        if folder is None:
            return
        self.busy = True
        self.critical = False
        self.active_operation = operation
        self.cancel.clear()
        engine.LANGUAGE = self.language
        self.clear_log()
        if operation == 'restore' and backup is not None:
            self.last_backup = Path(backup)
            self.backup_button.configure(state='normal')
            self.append_log(str(backup))
        self.status.configure(text=self.text('query'))
        self.file.configure(text='—')
        self.total.configure(maximum=3, value=0)
        self.current.configure(mode='indeterminate')
        self.current.start(15)
        for widget in (self.path_entry, self.browse, self.check_button, self.language_choice,
                       self.repair_button, self.backups_button):
            widget.configure(state='disabled')
        self.cancel_button.configure(state='normal')
        def work():
            try:
                if operation == 'diagnose':
                    engine.diagnose(folder, self.events.put, self.cancel)
                else:
                    with engine.operation_events(self.events.put, self.cancel,
                                                 lambda bundles: self.confirm_plan(bundles, folder)):
                        if not engine.recognizable_installation(folder):
                            raise ValueError(self.text('missing'))
                        engine.require_closed(folder)
                        if operation == 'repair':
                            bundles = engine.plans(folder, receiver=self.events.put, cancel=self.cancel)
                            needed = any(b['changes'] for b in bundles)
                            for bundle in bundles:
                                for name, data in ((bundle['name'], bundle['raw']),
                                                   (bundle['marker_name'], bundle['marker'].encode('ascii'))):
                                    target = engine.safe_path(bundle['folder'], name)
                                    needed = needed or not target.is_file() or target.read_bytes() != data
                            if not needed:
                                self.events.put({'kind': 'no_changes'})
                                return
                            if not self.confirm_plan(bundles, folder):
                                raise engine.DiagnosisCancelled()
                            engine.repair(folder, bundles)
                        else:
                            engine.restore(folder, backup)
                        self.events.put({'kind': 'operation_complete', 'operation': operation})
            except engine.DiagnosisCancelled:
                self.events.put({'kind': 'cancelled'})
            except Exception as exc:
                self.events.put({'kind': 'error', 'text': engine.error_message(exc)})
            finally:
                self.events.put({'kind': 'finished'})
        self.worker = threading.Thread(target=work, name='SRepair-Worker', daemon=False)
        self.worker.start()

    def request_cancel(self):
        if not self.busy or self.critical:
            return
        self.cancel.set()
        self.cancel_button.configure(state='disabled')
        self.status.configure(text=self.text('cancelling'))

    def open_backup(self):
        if self.last_backup:
            try:
                os.startfile(str(self.last_backup))
            except OSError as exc:
                messagebox.showerror(self.text('title'), engine.error_message(exc), parent=self.root)

    def choose_backup(self):
        if self.busy:
            return
        folder = self.installation_folder()
        if folder is None:
            return
        try:
            backups = engine.find_backups(folder)
        except (OSError, ValueError) as exc:
            messagebox.showerror(self.text('title'), str(exc), parent=self.root)
            return
        dialog = tk.Toplevel(self.root)
        dialog.title(self.text('choose_backup'))
        dialog.transient(self.root)
        dialog.geometry('640x360')
        dialog.minsize(620, 320)
        dialog.columnconfigure(0, weight=1)
        content = ttk.Frame(dialog, padding=16)
        content.pack(fill='both', expand=True)
        content.columnconfigure(0, weight=1)
        ttk.Label(content, text=self.text('backup_location'), wraplength=560).grid(row=0, column=0, sticky='w')
        ttk.Label(content, text=str(folder.parent), wraplength=560).grid(row=1, column=0, sticky='w', pady=(4, 12))
        chosen = tk.StringVar(master=dialog, value=str(backups[0]) if backups else '')
        selection = ttk.Combobox(content, state='readonly', values=[p.name for p in backups])
        selection.grid(row=2, column=0, sticky='ew', pady=4)
        if backups:
            selection.current(0)
        selection.bind('<<ComboboxSelected>>', lambda event: chosen.set(str(backups[selection.current()])))
        detail = ttk.Label(content, textvariable=chosen, wraplength=560)
        detail.grid(row=3, column=0, sticky='ew', pady=(4, 12))
        if not backups:
            detail.configure(textvariable='', text=self.text('no_backups'))
        def manual():
            path = filedialog.askdirectory(parent=dialog, title=self.text('choose_backup'), mustexist=True)
            if path:
                selection.set('')
                chosen.set(path)
                detail.configure(textvariable=chosen)
        ttk.Button(content, text=self.text('manual_backup'), command=manual).grid(row=4, column=0, sticky='w')
        def restore_selected():
            if not chosen.get():
                return
            try:
                candidate = Path(chosen.get()).resolve()
                engine.LANGUAGE = self.language
                engine.read_backup(folder, candidate)
            except (ValueError, OSError) as exc:
                messagebox.showerror(self.text('title'), str(exc), parent=dialog)
                return
            question = self.text('confirm_restore').format(root=folder, backup=candidate)
            if messagebox.askyesno(self.text('title'), question, parent=dialog, default='no'):
                dialog.destroy()
                self.start('restore', candidate)
        controls = ttk.Frame(content)
        controls.grid(row=5, column=0, sticky='ew', pady=(16, 0))
        ttk.Button(controls, text=self.text('restore_action'), command=restore_selected).pack(side='left')
        back = ttk.Button(controls, text=self.text('back'), command=dialog.destroy)
        back.pack(side='right')
        back.focus_set()
        dialog.bind('<Escape>', lambda event: dialog.destroy())
        dialog.update_idletasks()
        height = max(360, content.winfo_reqheight() + 12)
        dialog.geometry(f'640x{height}')
        dialog.minsize(620, height)
        dialog.grab_set()

    def show_repair_confirmation(self, event):
        try:
            if self.cancel.is_set() or self.closing:
                return
            bundles = event['bundles']
            files = sum(len(bundle['changes']) for bundle in bundles)
            size = engine.human_bytes(sum(entry['packedsize'] for bundle in bundles for entry in bundle['changes']))
            question = self.text('confirm_repair').format(files=files, size=size, root=event['root'], parent=event['root'].parent)
            event['accepted'] = messagebox.askyesno(self.text('title'), question, parent=self.root, default='no')
        finally:
            event['answered'].set()

    def handle_event(self, event):
        kind = event['kind']
        if kind == 'finished':
            self.busy = False
            self.critical = False
            self.current.stop()
            self.current.configure(mode='determinate')
            for widget in (self.path_entry, self.browse, self.check_button, self.repair_button, self.backups_button):
                widget.configure(state='normal')
            self.language_choice.configure(state='readonly')
            self.cancel_button.configure(state='disabled')
        elif kind == 'confirm_repair':
            self.show_repair_confirmation(event)
        elif kind == 'waiting':
            self.status.configure(text=self.text('waiting'))
            self.file.configure(text=event['names'])
            self.current.configure(mode='indeterminate')
            self.current.start(15)
        elif kind == 'backup':
            self.last_backup = Path(event['path'])
            self.backup_button.configure(state='normal')
            self.append_log(event['path'])
        elif kind == 'critical':
            self.critical = True
            self.cancel_button.configure(state='disabled')
            self.status.configure(text=self.text(event['phase']))
            self.append_log(self.text(event['phase']))
        elif kind == 'recovery':
            self.append_log(self.text('recovered' if event['complete'] else 'recovery_failed'))
            if event['pending']:
                self.append_log('\n'.join(event['pending']))
        elif kind in ('operation_complete', 'no_changes'):
            key = 'no_changes' if kind == 'no_changes' else event['operation'] + '_complete'
            self.status.configure(text=self.text(key))
            self.file.configure(text=str(self.last_backup) if kind != 'no_changes' and self.last_backup else '—')
            self.current.stop()
            self.current.configure(mode='determinate', value=100)
            self.total.configure(maximum=100, value=100)
            self.append_log(self.text(key))
        elif kind == 'operation_phase':
            self.current.stop()
            self.current.configure(mode='determinate', value=0)
            self.total.configure(maximum=100, value=0)
            if not self.critical:
                self.status.configure(text=event['label'])
            self.append_log(event['label'])
        elif kind == 'operation_progress':
            fraction = min(1, event['done'] / event['total']) if event['total'] else 0
            self.total.configure(maximum=100, value=100 * fraction)
            self.file.configure(text=f"{event['label']} · {fraction:.0%} · {event['file']}")
            if not event['bytes']:
                self.current.configure(mode='determinate', value=100 * fraction)
        elif kind == 'file_progress':
            if event['total']:
                self.current.stop()
                self.current.configure(mode='determinate', value=min(100, 100 * event['done'] / event['total']))
            else:
                self.current.configure(mode='indeterminate')
                self.current.start(15)
        elif kind == 'message':
            self.append_log(event['text'])
        elif kind == 'stage':
            self.status.configure(text=self.text('query'))
            self.file.configure(text=event['file'])
            self.current.stop()
            self.current.configure(mode='indeterminate')
            self.current.start(15)
        elif kind == 'progress':
            self.current.stop()
            total = event['total']
            fraction = event['done'] / total if total else 1
            self.current.configure(mode='determinate', value=100 * fraction)
            self.total.configure(value=event['bundle_index'] + fraction)
            self.status.configure(text=self.text('checking'))
            self.file.configure(text=f"{event['bundle']} · {event['done']}/{total} · {event['file']}")
        elif kind == 'result':
            self.total.configure(value=3)
            self.current.stop()
            self.current.configure(mode='determinate', value=100)
            self.status.configure(text=self.text('complete'))
            summary = self.text('summary').format(files=event['files'], size=engine.human_bytes(event['bytes']))
            self.file.configure(text=summary)
            self.append_log(summary)
            self.append_log(self.text('pending') + '\n' + '\n'.join(event['changes']) if event['changes'] else self.text('clean'))
        elif kind in ('error', 'cancelled'):
            if kind == 'error':
                # Keep recovery details visible even if closing was requested during writes.
                self.closing = False
            cancel_key = 'cancelled' if getattr(self, 'active_operation', 'diagnose') == 'diagnose' else 'operation_cancelled'
            self.status.configure(text=self.text('error' if kind == 'error' else cancel_key))
            self.file.configure(text='—')
            self.append_log(event.get('text', self.text(cancel_key)))

    def poll(self):
        for _ in range(150):
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break
            self.handle_event(event)
        if self.closing:
            self.status.configure(text=self.text('closing'))
            if not self.busy and (self.worker is None or not self.worker.is_alive()):
                self.root.destroy()
                return
        self.poll_id = self.root.after(60, self.poll)

    def request_close(self):
        if self.closing:
            return
        if self.busy:
            if not messagebox.askyesno(self.text('title'), self.text('cancel_question'), parent=self.root, default='no'):
                return
            self.closing = True
            self.cancel.set()
            self.status.configure(text=self.text('closing'))
        else:
            self.root.destroy()


def main():
    # Tk's font/DPI scaling remains enabled; the scrollable body handles large text.
    root = tk.Tk()
    DiagnosticApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
