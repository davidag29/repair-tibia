"""S-Repair for Tibia - S. Tensen. Español / English.
Abre el ejecutable para ver la descripción: L cambia idioma y R abre respaldos.
Open the executable for the description: L changes language and R opens backups.
Código fuente / Source: python src/srepair.py --menu
"""
import argparse
import contextlib
import hashlib
import io
import json
import lzma
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import urllib.parse
import urllib.request
import uuid

ORIGIN = 'https://static.tibia.com/launcher/'
PROTECTED = {'conf', 'minimap', 'characterdata', 'screenshots', 'log', 'cache'}
APP_NAME = 'S-Repair for Tibia'
AUTHOR = 'S. Tensen'
VERSION = '1'
LANGUAGE = 'es'


def t(spanish, english):
    return spanish if LANGUAGE == 'es' else english


def ask(prompt):
    try:
        return input(prompt).strip()
    except EOFError:
        return ''


def choose_language():
    global LANGUAGE
    if keyboard_available():
        selected = native_select([('Español', 'es'), ('English', 'en'),
                                  (t('Volver', 'Back'), None)],
                                 'Language: English / Español', default=0 if LANGUAGE == 'es' else 1)
        if selected is not None:
            LANGUAGE = selected
            return True
        return False
    print('\n' + APP_NAME + ' ' + VERSION + ' | ' + AUTHOR, flush=True)
    print('\n[1] Español\n[2] English\n[0] Volver / Back', flush=True)
    while True:
        answer = ask('\nIdioma / Language [' + ('1' if LANGUAGE == 'es' else '2') + ']: ').lower()
        if not answer:
            return True
        if answer in ('1', 'es', 'español'):
            LANGUAGE = 'es'
            return True
        if answer in ('2', 'en', 'english'):
            LANGUAGE = 'en'
            return True
        if answer == '0':
            return False
        print('Elige 1, 2 o 0 / Choose 1, 2 or 0.', flush=True)


def console_colors():
    if not sys.stdout.isatty():
        return False
    if os.name != 'nt':
        return True
    try:
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetStdHandle.argtypes = [wintypes.DWORD]
        kernel.GetStdHandle.restype = wintypes.HANDLE
        kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        kernel.SetConsoleTitleW.argtypes = [wintypes.LPCWSTR]
        kernel.SetConsoleTitleW(APP_NAME + ' - ' + AUTHOR)
        handle = kernel.GetStdHandle(-11 & 0xffffffff)
        mode = wintypes.DWORD()
        return bool(kernel.GetConsoleMode(handle, ctypes.byref(mode)) and
                    kernel.SetConsoleMode(handle, mode.value | 0x0004))
    except (OSError, AttributeError):
        return False


def keyboard_available():
    return os.name == 'nt' and sys.stdin.isatty() and sys.stdout.isatty() and console_colors()


def read_key():
    import msvcrt
    key = msvcrt.getwch()
    if key in ('\x00', '\xe0'):
        return {'H': 'up', 'P': 'down', 'G': 'home', 'O': 'end',
                'I': 'pageup', 'Q': 'pagedown'}.get(msvcrt.getwch(), '')
    if key == '\x03':
        raise KeyboardInterrupt()
    return {'\r': 'enter', '\n': 'enter', '\x1b': 'escape'}.get(key, key.lower())


def native_select(options, heading='', default=0, shortcuts=None, render=None, detail_marker=None):
    """Lista de Windows: flechas/Enter/Esc. No escribe en la instalación."""
    selected, offset = default, 0
    try:
        print('\033[?25l', end='', flush=True)
        while True:
            height = max(shutil.get_terminal_size((100, 32)).lines, 10)
            width = max(shutil.get_terminal_size((100, 32)).columns - 1, 40)
            if render:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    render(selected)
                lines = output.getvalue().splitlines()
                split = next((i for i, line in enumerate(lines) if detail_marker and detail_marker in line), len(lines))
                head, body = lines[:split], lines[split:]
                room = max(height - len(head) - 2, 1)
                offset = min(offset, max(len(body) - room, 0))
                visible = head + body[offset:offset + room]
            else:
                head = []
                for line in heading.splitlines():
                    head.extend(textwrap.wrap(line, width=width) or [''])
                room = max(height - len(head) - 4, 1)
                first = max(0, min(selected - room + 1, len(options) - room))
                visible = head + ['']
                for index in range(first, min(first + room, len(options))):
                    label = ('> ' if index == selected else '  ') + options[index][0]
                    visible.append(('\033[1;30;106m' + label[:width].ljust(width) + '\033[0m')
                                   if index == selected else label[:width])
            hint = t('↑/↓ elegir · Enter seleccionar · Esc volver/salir',
                     '↑/↓ choose · Enter select · Esc back/exit')
            if render:
                hint += t(' · PgUp/PgDn descripción', ' · PgUp/PgDn description')
            print('\033[2J\033[H' + '\n'.join(visible[:height - 2]) + '\n' + hint[:width], end='', flush=True)
            key = read_key()
            if key == 'up':
                selected = (selected - 1) % len(options)
            elif key == 'down':
                selected = (selected + 1) % len(options)
            elif key == 'home':
                selected = 0
            elif key == 'end':
                selected = len(options) - 1
            elif key == 'pagedown':
                offset += room
            elif key == 'pageup':
                offset = max(0, offset - room)
            elif key == 'enter':
                return options[selected][1]
            elif key == 'escape':
                return None
            elif shortcuts and key in shortcuts:
                return shortcuts[key]
    finally:
        print('\033[0m\033[?25h\n', end='', flush=True)


def show_welcome(root, selected=None):
    colors = console_colors() if selected is None else True
    def style(text, color):
        return f'\033[{color}m{text}\033[0m' if colors else text
    width = min(max(shutil.get_terminal_size((78, 25)).columns - 2, 42), 76)
    inner = width - 4
    border = '+' + '-' * (width - 2) + '+'
    def row(text='', color=None, center=False):
        for line in textwrap.wrap(text, width=inner) or ['']:
            content = '| ' + (line.center(inner) if center else line.ljust(inner)) + ' |'
            print(style(content, color) if color else content, flush=True)
    print('\n' + style(border, '36'), flush=True)
    row(APP_NAME, '1;36', center=True)
    row(t('ASISTENTE DE REPARACIÓN', 'REPAIR ASSISTANT'), '1;36', center=True)
    row(t('Autor: ', 'Author: ') + AUTHOR + ' | ' + VERSION, center=True)
    row(t('Archivos oficiales / Respaldo automático', 'Official files / Automatic backup'), center=True)
    print(style(border, '36'), flush=True)
    row()
    choices = [(t('[S] Reparar', '[Y] Repair'), '1;37'),
               ('[L] Language: English / Español', '1;96'),
               (t('[R] Respaldos / Restaurar', '[R] Backups / Restore'), None),
               (t('[N] Salir', '[N] Exit'), None)]
    for index, (label, color) in enumerate(choices):
        row(('> ' if selected == index else '  ') + label,
            '1;30;106' if selected == index else color, center=True)
    row(t('Selecciona Reparar para confirmar e iniciar.', 'Select Repair to confirm and start.'), center=True)
    row()
    row(t('QUÉ HARÁ EL ASISTENTE', 'WHAT THE ASSISTANT WILL DO'), '1;37')
    row(t('1. Esperar a que cierres Tibia y comprobar la instalación.', '1. Wait for you to close Tibia and check the installation.'))
    row(t('2. Descargar los archivos necesarios del servidor oficial, evitando la caché antigua.', '2. Download the required files from the official server, bypassing stale cache.'))
    row(t('3. Verificar cada descarga con SHA-256 y crear un respaldo.', '3. Verify each download with SHA-256 and create a backup.'))
    row(t('4. Reemplazar los archivos desactualizados o dañados y verificar el resultado.', '4. Replace outdated or damaged files and verify the result.'))
    row()
    row(t('Se conservan tus mapas, atajos de teclado, configuraciones y capturas.', 'Your maps, hotkeys, settings and screenshots are preserved.'), '32')
    row()
    row(t('ARCHIVOS OFICIALES Y BATTLEYE', 'OFFICIAL FILES AND BATTLEYE'), '1;33')
    row(t('Restauramos copias oficiales: no incorporamos cambios propios al código del juego, no modificamos su memoria ni desactivamos BattlEye.', 'We restore official copies: we do not add custom game code, modify game memory or disable BattlEye.'))
    row(t('Herramienta independiente, sin aprobación de CipSoft o BattlEye. No podemos garantizar ausencia de bloqueos o incompatibilidades.', 'Independent tool, not approved by CipSoft or BattlEye. We cannot guarantee freedom from blocks or compatibility issues.'))
    row()
    row(t('Instalación: ', 'Installation: ') + str(root))
    row(t('Los respaldos se guardan junto a esta carpeta. Usa [R] para restaurarlos.', 'Backups are saved beside this folder. Use [R] to restore them.'))
    row()
    print(style(border, '36'), flush=True)


def welcome_choice(root):
    while True:
        if keyboard_available():
            choice = native_select([(t('Reparar', 'Repair'), 'repair'), ('Language', 'language'),
                                    (t('Respaldos', 'Backups'), 'restore'), (t('Salir', 'Exit'), None)],
                                   shortcuts={'s': 'repair', 'y': 'repair', 'l': 'language', 'r': 'restore', 'n': None},
                                   render=lambda selected: show_welcome(root, selected),
                                   detail_marker=t('QUÉ HARÁ EL ASISTENTE', 'WHAT THE ASSISTANT WILL DO'))
            if choice == 'language':
                choose_language()
                continue
            return choice
        show_welcome(root)
        while True:
            choice = ask(t('\nTu elección [S/N/L/R]: ', '\nYour choice [Y/N/L/R]: ')).lower()
            if choice == 'l':
                choose_language()
                break
            if choice == 'r':
                return 'restore'
            if choice in ('y', 's', 'sí', 'si', 'yes'):
                print(t('\nConfirmado. Iniciando comprobación y reparación...\n', '\nConfirmed. Starting checks and repair...\n'), flush=True)
                return 'repair'
            if choice in ('', 'n', '0'):
                print(t('\nOperación cancelada. No se modificó ningún archivo.', '\nCancelled. No files were changed.'), flush=True)
                return None
            print(t('Escribe S para reparar, L para idioma, R para respaldos o N para salir.',
                    'Enter Y to repair, L for language, R for backups or N to exit.'), flush=True)


def human_bytes(value):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if value < 1024 or unit == 'GB':
            return f'{value:.1f}{unit}'
        value /= 1024


class Progress:
    def __init__(self, label, total, byte_units=False):
        self.label, self.total, self.byte_units = label, max(total, 0), byte_units
        self.start = time.monotonic()
        self.last = 0
        self.bucket = -1
        self.width = 0
        self.tty = sys.stdout.isatty()

    def update(self, done, detail='', force=False):
        now = time.monotonic()
        fraction = min(max(done / self.total, 0), 1) if self.total else 1
        bucket = int(fraction * 4)
        if not force and ((self.tty and now - self.last < .12) or
                          (not self.tty and bucket == self.bucket)):
            return
        self.last, self.bucket = now, bucket
        filled = int(fraction * 20)
        bar = '#' * filled + '-' * (20 - filled)
        counts = (f'{human_bytes(done)}/{human_bytes(self.total)}' if self.byte_units
                  else f'{done}/{self.total}')
        text = f'{self.label} [{bar}] {fraction:5.1%}  {counts}'
        if self.byte_units and done:
            rate = done / max(now - self.start, .01)
            remaining = int(max(self.total - done, 0) / rate)
            text += f'  {human_bytes(rate)}/s  ~{remaining // 60:02d}:{remaining % 60:02d}'
        if detail:
            text += '  | ' + detail
        width = max(shutil.get_terminal_size((110, 25)).columns - 1, 40)
        text = text[:width]
        if self.tty:
            print('\r' + text.ljust(self.width), end='', flush=True)
            self.width = len(text)
        else:
            print(text, flush=True)

    def finish(self, detail=None):
        detail = detail or t('Listo', 'Done')
        self.update(self.total, detail, force=True)
        if self.tty:
            print(flush=True)

    def clear(self):
        if self.tty and self.width:
            print('\r' + ' ' * self.width + '\r', end='', flush=True)
        self.width = 0


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fetch(relative, progress=None):
    url = urllib.parse.urljoin(ORIGIN, relative)
    if urllib.parse.urlsplit(url).netloc != 'static.tibia.com':
        raise ValueError(t('Servidor no permitido: ', 'Server not allowed: ') + url)
    url += ('&' if '?' in url else '?') + 'repair=' + uuid.uuid4().hex
    last = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'TibiaRepair/1.0'})
            with urllib.request.urlopen(request, timeout=60) as response:
                final = urllib.parse.urlsplit(response.url)
                if final.scheme != 'https' or final.netloc != 'static.tibia.com':
                    raise ValueError(t('Redirección no permitida', 'Redirect not allowed'))
                chunks, received = [], 0
                total = int(response.headers.get('Content-Length', 0))
                while chunk := response.read(256 * 1024):
                    chunks.append(chunk)
                    received += len(chunk)
                    if progress:
                        progress(received, total)
                return b''.join(chunks)
        except Exception as exc:
            last = exc
            if attempt < 2:
                time.sleep(1)
    raise RuntimeError(t('No se pudo descargar ', 'Could not download ') + relative) from last


def safe_path(root, relative):
    clean = relative.replace('\\', '/')
    parts = clean.split('/')
    if not clean or any(p in ('', '.', '..') or ':' in p for p in parts):
        raise ValueError(t('Ruta no permitida: ', 'Path not allowed: ') + relative)
    if parts[0].lower() in PROTECTED:
        raise ValueError(t('El manifiesto intenta modificar datos personales: ', 'Manifest attempts to modify personal data: ') + relative)
    target = root.joinpath(*parts).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(t('Ruta fuera de la instalación: ', 'Path outside the installation: ') + relative)
    return target


def running(root):
    command = "Get-CimInstance Win32_Process | Where-Object ExecutablePath | Select-Object Name,ProcessId,ExecutablePath | ConvertTo-Json -Compress"
    result = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command', command],
                            capture_output=True, text=True, check=True,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    rows = json.loads(result.stdout or '[]')
    if isinstance(rows, dict):
        rows = [rows]
    prefix = str(root.resolve()).lower() + os.sep
    own_exe = str(Path(sys.executable).resolve()).lower()
    return [r for r in rows if r['ExecutablePath'].lower().startswith(prefix)
            and r['ExecutablePath'].lower() != own_exe]


def require_closed(root):
    active = running(root)
    if not active:
        return False
    print(t('\nTIBIA ESTÁ ABIERTO', '\nTIBIA IS RUNNING'), flush=True)
    print(t('Cierra el juego y su iniciador normalmente. No cierres esta ventana.', 'Close the game and its launcher normally. Keep this window open.'), flush=True)
    print(t('Al cerrarlos, la comprobación se reiniciará automáticamente aquí.', 'Once they close, checks will restart automatically in this window.'), flush=True)
    print(t('Puedes cancelar con Ctrl+C. No se forzará el cierre del juego.\n', 'Press Ctrl+C to cancel. The game will not be forcibly closed.\n'), flush=True)
    start = time.monotonic()
    previous_names = None
    while active:
        names = ', '.join(sorted({r['Name'] for r in active}))
        if sys.stdout.isatty():
            text = t('Esperando cierre...', 'Waiting for the game to close...') + f' {int(time.monotonic() - start)}s | {names}'
            width = max(shutil.get_terminal_size((110, 25)).columns - 1, 40)
            print('\r' + text[:width].ljust(width), end='', flush=True)
        elif names != previous_names:
            print(t('Esperando cierre: ', 'Waiting for: ') + names, flush=True)
        previous_names = names
        time.sleep(2)
        active = running(root)
    if sys.stdout.isatty():
        print(flush=True)
    print(t('\n[OK] Tibia está cerrado. Reiniciando comprobación...\n', '\n[OK] Tibia is closed. Restarting checks...\n'), flush=True)
    return True


def expected(entry):
    return entry.get('unpackedhash') or entry['packedhash']


def decode_verified(packed, entry):
    if digest(packed) != entry['packedhash'] or len(packed) != entry['packedsize']:
        raise ValueError(t('La descarga no coincide con SHA-256/tamaño: ', 'Downloaded SHA-256/size mismatch: ') + entry['localfile'])
    def valid(data):
        return (digest(data) == expected(entry) and
                len(data) == entry.get('unpackedsize', entry['packedsize']))
    if valid(packed):
        return packed
    # Tibia usa una envoltura de 32 bytes seguida de propiedades LZMA,
    # un campo de 8 bytes y el flujo comprimido. Ese campo no representa
    # el tamano descomprimido de un archivo LZMA-alone estandar.
    candidates = [packed]
    if len(packed) > 45:
        candidates.append(packed[32:37] + b'\xff' * 8 + packed[45:])
    for candidate in candidates:
        try:
            data = lzma.decompress(candidate)
        except lzma.LZMAError:
            continue
        if valid(data):
            return data
    raise ValueError(t('Archivo descomprimido inválido: ', 'Invalid decompressed file: ') + entry['localfile'])


def matches(path, entry):
    if not path.is_file():
        return False
    size = entry.get('unpackedsize', entry.get('packedsize'))
    if size is not None and path.stat().st_size != size:
        return False
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() == expected(entry)


def plans(root):
    print(t('\n[1/4] COMPROBAR ARCHIVOS\nConsultando la versión oficial sin caché...', '\n[1/4] CHECK FILES\nChecking the official version without stale cache...'), flush=True)
    client = root / 'packages' / 'Tibia'
    result = []
    for label, base, folder in [('launcher', 'launcher-windows-current/', root),
                                 ('cliente', 'tibiaclient-windows-current/', client),
                                 ('assets', 'assets-current/', client)]:
        display_label = {'launcher': t('iniciador', 'launcher'), 'cliente': t('cliente', 'client'),
                         'assets': t('recursos', 'assets')}[label]
        name = 'assets.json' if label == 'assets' else 'package.json'
        raw = fetch(base + name)
        manifest = json.loads(raw)
        if not isinstance(manifest.get('files'), list) or not manifest['files']:
            raise ValueError(t('Manifiesto vacío o inválido: ', 'Empty or invalid manifest: ') + display_label)
        marker_name = 'assets.json.sha256' if label == 'assets' else 'package.json.version'
        marker = fetch(base + marker_name).decode('ascii').strip()
        if label == 'assets':
            if marker != digest(raw):
                raise ValueError(t('El hash del manifiesto de recursos no coincide; vuelve a intentar.', 'Assets manifest hash mismatch; please try again.'))
        elif marker != manifest['version']:
            raise ValueError(t('La versión cambió durante la consulta; vuelve a intentar.', 'The version changed while checking; please try again.'))
        entries = [e for e in manifest['files']
                   if e['localfile'].replace('\\', '/').split('/')[0].lower() not in PROTECTED]
        changes = []
        progress = Progress(t('Revisando ', 'Checking ') + display_label, len(entries))
        for index, entry in enumerate(entries, 1):
            progress.update(index - 1, entry['localfile'])
            if not matches(safe_path(folder, entry['localfile']), entry):
                changes.append(entry)
        progress.finish()
        print(t('{label}: versión {version}; {count} de {total} archivos requieren reemplazo.',
                '{label}: version {version}; {count} of {total} files need replacement.').format(
                    label=display_label, version=manifest.get('version', marker[:12]), count=len(changes), total=len(manifest['files'])), flush=True)
        result.append(dict(label=label, base=base, folder=folder, raw=raw, name=name,
                           marker=marker, marker_name=marker_name, changes=changes))
    return result


def read_backup(root, backup):
    try:
        journal = json.loads((backup / 'restore.json').read_text(encoding='utf-8'))
        if Path(journal['root']).resolve() != root.resolve():
            raise ValueError(t('El respaldo pertenece a otra instalación.', 'The backup belongs to another installation.'))
        if not isinstance(journal['files'], list) or not journal['files']:
            raise ValueError(t('El respaldo no contiene un registro de archivos válido.', 'The backup does not contain a valid file record.'))
        return journal
    except (OSError, KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(t('No se puede leer el respaldo: ', 'Cannot read backup: ') + str(backup)) from exc


def find_backups(root):
    backups = []
    for candidate in root.parent.glob('Tibia-respaldo-*'):
        try:
            read_backup(root, candidate)
        except (ValueError, OSError):
            continue
        backups.append(candidate)
    return sorted(backups, key=lambda p: p.name, reverse=True)


def restore_hint(root, backup):
    print(t('\nUbicación del respaldo: ', '\nBackup location: ') + str(backup), flush=True)
    print(t('Para restaurarlo, vuelve a abrir el programa y elige [R] Respaldos.',
            'To restore it, reopen the program and choose [R] Backups.'), flush=True)
    print(t('También puedes usar este comando en PowerShell:', 'You can also use this PowerShell command:'), flush=True)
    exe = Path(sys.executable) if getattr(sys, 'frozen', False) else Path(__file__).resolve()
    prefix = '& ' if getattr(sys, 'frozen', False) else 'python '
    quote = lambda value: "'" + str(value).replace("'", "''") + "'"
    print(prefix + quote(exe) + ' --root ' + quote(root) + ' --restore ' + quote(backup), flush=True)


def select_backup(root):
    backups = find_backups(root)[:20]
    if keyboard_available():
        error = ''
        while True:
            heading = (t('RESTAURAR UN RESPALDO\nCarpeta de respaldos: ', 'RESTORE A BACKUP\nBackup folder: ')
                       + str(root.parent) + ('\n' + error if error else ''))
            options = [(p.name, p) for p in backups]
            options += [(t('Indicar otra carpeta de respaldo…', 'Enter another backup folder…'), 'manual'),
                        (t('Volver / Salir', 'Back / Exit'), None)]
            selected = native_select(options, heading)
            if selected is None:
                return None
            try:
                if selected == 'manual':
                    answer = ask(t('Ruta del respaldo (vacío cancela): ', 'Backup path (empty cancels): '))
                    if not answer:
                        return None
                    selected = Path(os.path.expandvars(answer.strip('\"\''))).expanduser().resolve()
                    if selected.name == 'restore.json':
                        selected = selected.parent
                read_backup(root, selected)
                return selected
            except (OSError, ValueError, RuntimeError):
                error = t('Respaldo no válido para esta instalación.', 'Invalid backup for this installation.')
    print(t('\nRESTAURAR UN RESPALDO', '\nRESTORE A BACKUP'), flush=True)
    print(t('Los respaldos se guardan junto a la instalación, en:\n  ', 'Backups are stored beside the installation, in:\n  ') + str(root.parent), flush=True)
    print('  Tibia-respaldo-AAAAMMDD-HHMMSS-*', flush=True)
    if backups:
        print(t('\nRespaldos de esta instalación (más recientes primero):', '\nBackups for this installation (newest first):'), flush=True)
        for index, backup in enumerate(backups, 1):
            print(f'[{index}] {backup}', flush=True)
    else:
        print(t('\nNo encontramos respaldos para esta instalación.', '\nNo backups were found for this installation.'), flush=True)
    print(t('\nEscribe un número de la lista o pega la ruta de una carpeta de respaldo.',
            '\nEnter a number from the list or paste a backup folder path.'), flush=True)
    print(t('Enter sin escribir nada sale sin cambios.', 'Press Enter without typing to exit without changes.'), flush=True)
    while True:
        answer = ask(t('\nRespaldo: ', '\nBackup: '))
        if not answer:
            return None
        try:
            if answer.isdecimal():
                index = int(answer) - 1
                if not 0 <= index < len(backups):
                    raise ValueError()
                candidate = backups[index]
            else:
                candidate = Path(os.path.expandvars(answer.strip('\"\''))).expanduser().resolve()
                if candidate.name == 'restore.json':
                    candidate = candidate.parent
            read_backup(root, candidate)
            return candidate
        except (OSError, ValueError, RuntimeError):
            print(t('Respaldo no válido para esta instalación. Intenta otra ruta o pulsa Enter para salir.',
                    'Invalid backup for this installation. Try another path or press Enter to exit.'), flush=True)


def confirm_restore(root, backup):
    if keyboard_available():
        heading = t('¿Restaurar este respaldo?\nSe recuperarán archivos anteriores; el cliente puede volver a una versión antigua.\n',
                    'Restore this backup?\nPrevious files will be recovered; the client may revert to an older version.\n')
        heading += t('Instalación: ', 'Installation: ') + str(root) + '\n' + t('Respaldo: ', 'Backup: ') + str(backup)
        return native_select([(t('Sí, restaurar', 'Yes, restore'), True),
                              (t('Cancelar', 'Cancel'), False)], heading, default=1,
                             shortcuts={'s': True, 'y': True, 'n': False}) is True
    print(t('\nSe restaurarán los archivos del respaldo y se quitarán los archivos que no existían antes de esa reparación.',
            '\nFiles will be restored from this backup. Files created by that repair will be removed.'), flush=True)
    print(t('Esto puede devolver el cliente a una versión anterior. Se conservará la carpeta del respaldo.',
            'This may revert the client to an older version. The backup folder will be kept.'), flush=True)
    print(t('Instalación: ', 'Installation: ') + str(root), flush=True)
    print(t('Respaldo: ', 'Backup: ') + str(backup), flush=True)
    while True:
        answer = ask(t('\n¿Restaurar este respaldo? [S/N]: ', '\nRestore this backup? [Y/N]: ')).lower()
        if answer in ('s', 'y', 'si', 'sí', 'yes'):
            return True
        if answer in ('', 'n', 'no'):
            print(t('Restauración cancelada. No se modificó ningún archivo.', 'Restore cancelled. No files were changed.'), flush=True)
            return False
        print(t('Escribe S para restaurar o N para cancelar.', 'Enter Y to restore or N to cancel.'), flush=True)


def validate_backup(root, backup):
    journal = read_backup(root, backup)
    checked, seen = [], set()
    progress = Progress(t('Verificando respaldo', 'Verifying backup'), len(journal['files']))
    try:
        for index, item in enumerate(journal['files'], 1):
            relative = item['path']
            if not isinstance(relative, str) or type(item['existed']) is not bool:
                raise ValueError(t('Registro de respaldo inválido.', 'Invalid backup record.'))
            normalized = relative.replace('\\', '/').lower()
            if normalized in seen or (normalized.startswith('packages/tibia/') and
                                       normalized.split('/')[2] in PROTECTED):
                raise ValueError(t('El respaldo contiene rutas duplicadas o protegidas.', 'Backup contains duplicate or protected paths.'))
            seen.add(normalized)
            target = safe_path(root, relative)
            source = None
            if item['existed']:
                source = safe_path(backup / 'files', relative)
                if digest(source.read_bytes()) != item['backup_hash']:
                    raise ValueError(t('Respaldo dañado: ', 'Damaged backup: ') + relative)
            checked.append((item, target, source))
            progress.update(index, relative)
    except BaseException:
        progress.clear()
        raise
    progress.finish()
    return checked


def restore(root, backup):
    require_closed(root)
    # Verificar TODOS los archivos antes de la primera escritura.
    checked = validate_backup(root, backup)
    require_closed(root)
    progress = Progress(t('Restaurando', 'Restoring'), len(checked))
    failures = []
    try:
        for index, (item, target, source) in enumerate(reversed(checked), 1):
            try:
                if source is not None:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
                    if digest(target.read_bytes()) != item['backup_hash']:
                        raise OSError(t('No se pudo verificar el archivo restaurado.', 'Restored file verification failed.'))
                elif target.exists():
                    target.unlink()
            except OSError:
                failures.append(item['path'])
            progress.update(index, item['path'])
    except BaseException:
        progress.clear()
        restore_hint(root, backup)
        raise
    progress.finish()
    if failures:
        restore_hint(root, backup)
        raise RuntimeError(t('Restauración incompleta. Cierra Tibia, comprueba los permisos y vuelve a intentarlo. Archivos pendientes: ',
                             'Restore incomplete. Close Tibia, check permissions and try again. Remaining files: ') + ', '.join(failures))
    print(t('\n[OK] RESTAURACIÓN COMPLETADA. El respaldo se conserva.', '\n[OK] RESTORE COMPLETED. The backup has been kept.'), flush=True)


def repair(root, bundles, verify_only=False):
    if not verify_only:
        if require_closed(root):
            bundles = plans(root)
    total_files = sum(len(b['changes']) for b in bundles)
    total_bytes = sum(e['packedsize'] for b in bundles for e in b['changes'])
    print(t('\n[2/4] DESCARGAR Y VERIFICAR\n{count} archivos | {size} de descarga',
            '\n[2/4] DOWNLOAD AND VERIFY\n{count} files | {size} to download').format(count=total_files, size=human_bytes(total_bytes)), flush=True)
    download_progress = Progress(t('Descarga', 'Download'), total_bytes, byte_units=True)
    completed_bytes, completed_files = 0, 0
    with tempfile.TemporaryDirectory(prefix='tibia-repair-') as temp:
        stage = Path(temp)
        replacements = {}
        for bundle in bundles:
            for index, entry in enumerate(bundle['changes'], 1):
                detail = f'{completed_files + 1}/{total_files} {entry["localfile"]}'
                download_progress.update(completed_bytes, detail, force=True)
                def on_chunk(received, total):
                    download_progress.update(completed_bytes + received, detail)
                try:
                    packed = fetch(bundle['base'] + entry['url'], progress=on_chunk)
                    data = decode_verified(packed, entry)
                except BaseException:
                    download_progress.clear()
                    raise
                completed_bytes += len(packed)
                completed_files += 1
                target = safe_path(bundle['folder'], entry['localfile'])
                staged = stage / str(len(replacements))
                staged.write_bytes(data)
                replacements[target] = staged
            for name, data in [(bundle['name'], bundle['raw']),
                               (bundle['marker_name'], bundle['marker'].encode('ascii'))]:
                target = safe_path(bundle['folder'], name)
                staged = stage / str(len(replacements))
                staged.write_bytes(data)
                replacements[target] = staged
        download_progress.finish(t('{count} archivos verificados con SHA-256', '{count} files verified with SHA-256').format(count=completed_files))
        # No escribir si CipSoft publico otra version mientras se descargaba.
        for bundle in bundles:
            if digest(fetch(bundle['base'] + bundle['name'])) != digest(bundle['raw']):
                raise RuntimeError(t('La actualización cambió en el servidor. Vuelve a ejecutar el programa.', 'The update changed on the server. Run the program again.'))
        if verify_only:
            print(t('Todas las descargas se descomprimieron y verificaron. No se modificó la instalación.', 'All downloads were decompressed and verified. The installation was not changed.'))
            return
        if require_closed(root):
            return repair(root, plans(root))
        print(t('\n[3/4] CREAR RESPALDO', '\n[3/4] CREATE BACKUP'), flush=True)
        backup = root.parent / ('Tibia-respaldo-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
        backup.mkdir()
        journal = {'root': str(root), 'files': [], 'app_version': VERSION,
                   'created_at': time.strftime('%Y-%m-%d %H:%M:%S')}
        partials = [folder / 'partial.package.json.version' for folder in
                    [root, root / 'packages' / 'Tibia'] if (folder / 'partial.package.json.version').exists()]
        backup_targets = list(replacements) + partials
        backup_progress = Progress(t('Creando respaldo', 'Backing up'), len(backup_targets))
        for backup_index, target in enumerate(backup_targets, 1):
            relative = target.relative_to(root).as_posix()
            item = {'path': relative, 'existed': target.exists()}
            if item['existed']:
                saved = safe_path(backup / 'files', relative)
                saved.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, saved)
                item['backup_hash'] = digest(saved.read_bytes())
            journal['files'].append(item)
            backup_progress.update(backup_index, relative)
        backup_progress.finish()
        (backup / 'restore.json').write_text(json.dumps(journal, indent=2), encoding='utf-8')
        print(t('Respaldo: ', 'Backup: ') + str(backup), flush=True)
        # Volver a comprobar antes de la primera escritura en la instalacion.
        if require_closed(root):
            return repair(root, plans(root))
        print(t('\n[4/4] INSTALAR Y VERIFICAR', '\n[4/4] INSTALL AND VERIFY'), flush=True)
        install_progress = Progress(t('Instalando', 'Installing'), len(replacements))
        touched = []
        try:
            for install_index, (target, staged) in enumerate(replacements.items(), 1):
                target.parent.mkdir(parents=True, exist_ok=True)
                touched.append(target)
                with staged.open('rb') as source, target.open('wb') as destination:
                    shutil.copyfileobj(source, destination)
                if digest(target.read_bytes()) != digest(staged.read_bytes()):
                    raise RuntimeError(t('Falló la verificación después de escribir: ', 'Verification failed after writing: ') + str(target))
                install_progress.update(install_index, target.name)
            for partial in partials:
                touched.append(partial)
                partial.unlink()
        except (Exception, KeyboardInterrupt):
            install_progress.clear()
            print(t('Falló la instalación. Intentando restaurar los archivos modificados...', 'Installation failed. Attempting to restore modified files...'), flush=True)
            lookup = {root / i['path']: i for i in journal['files']}
            rollback_failures = []
            for target in reversed(touched):
                item = lookup[target]
                try:
                    if item['existed']:
                        shutil.copy2(backup / 'files' / item['path'], target)
                        if digest(target.read_bytes()) != item['backup_hash']:
                            raise OSError()
                    elif target.exists():
                        target.unlink()
                except OSError:
                    rollback_failures.append(str(target))
            if rollback_failures:
                print(t('RESTAURACIÓN AUTOMÁTICA INCOMPLETA. Archivos pendientes:', 'AUTOMATIC RESTORE INCOMPLETE. Remaining files:'), flush=True)
                for target in rollback_failures:
                    print('  ' + target, flush=True)
            else:
                print(t('Los archivos modificados se restauraron desde el respaldo.', 'Modified files were restored from the backup.'), flush=True)
            restore_hint(root, backup)
            raise
        install_progress.finish()
        print(t('\n[OK] REPARACIÓN COMPLETADA\nCierra este reparador y abre Tibia desde su acceso directo habitual.', '\n[OK] REPAIR COMPLETED\nClose this tool and launch Tibia from its usual shortcut.'), flush=True)
        restore_hint(root, backup)


def locate_installation(root):
    def recognizable(folder):
        return ((folder / 'Tibia.exe').is_file() or
                (folder / 'packages' / 'Tibia' / 'package.json').is_file() or bool(find_backups(folder)))
    if recognizable(root):
        return root
    print(t('\nNO ENCONTRAMOS LA CARPETA DE TIBIA', '\nTIBIA FOLDER NOT FOUND'), flush=True)
    print(t('No encontramos Tibia en la ubicación habitual o indicada:\n  ', 'Tibia was not found in the usual or specified location:\n  ') + str(root), flush=True)
    print(t('Si está en otra ubicación, indica la carpeta que contiene Tibia.exe.', 'If it is installed elsewhere, enter the folder containing Tibia.exe.'), flush=True)
    print(t('Puedes pegar la ruta entre comillas. Enter sin escribir nada cierra el reparador.\n', 'You can paste a quoted path. Press Enter without typing to close this tool.\n'), flush=True)
    while True:
        answer = ask(t('Carpeta de Tibia: ', 'Tibia folder: '))
        if not answer:
            print(t('\nNo se indicó una carpeta. Cerrando sin realizar cambios.', '\nNo folder was provided. Closing without changes.'), flush=True)
            return None
        try:
            candidate = Path(os.path.expandvars(answer.strip('\"\''))).expanduser().resolve()
            if candidate.name.lower() == 'tibia.exe' and candidate.is_file():
                candidate = candidate.parent
            if recognizable(candidate):
                print(t('\n[OK] Instalación encontrada: ', '\n[OK] Installation found: ') + str(candidate), flush=True)
                return candidate
        except (OSError, ValueError, RuntimeError):
            pass
        print(t('No encontramos Tibia en esa ruta. Intenta otra carpeta o pulsa Enter para salir.', 'Tibia was not found at that path. Try another folder or press Enter to exit.'), flush=True)


class LocalizedParser(argparse.ArgumentParser):
    def format_usage(self):
        return super().format_usage().replace('usage:', t('uso:', 'usage:'), 1)

    def format_help(self):
        return super().format_help().replace('usage:', t('uso:', 'usage:'), 1)

    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(2, t('\nOpciones incorrectas o incompletas. Usa --ayuda para ver los comandos.\n',
                       '\nInvalid or incomplete options. Use --help to list commands.\n'))


def main():
    global LANGUAGE
    interactive = bool(getattr(sys, 'frozen', False)) and len(sys.argv) == 1
    preliminary = LocalizedParser(add_help=False)
    preliminary.add_argument('--language', '--idioma', choices=('es', 'en'), default=None)
    early, _ = preliminary.parse_known_args()
    if early.language:
        LANGUAGE = early.language
    parser = LocalizedParser(description=APP_NAME + ' ' + VERSION + ' - ' + t('Autor: ', 'Author: ') + AUTHOR,
                             add_help=False, usage=t('%(prog)s [opciones]', '%(prog)s [options]'))
    parser._optionals.title = t('opciones', 'options')
    parser.add_argument('-h', '--help', '--ayuda', action='help', help=t('Mostrar esta ayuda y salir', 'Show this help and exit'))
    parser.add_argument('--language', '--idioma', choices=('es', 'en'), help=t('Idioma de la interfaz', 'Interface language'))
    parser.add_argument('--root', '--ruta', type=Path, default=Path(os.environ.get('LOCALAPPDATA', '.')) / 'Tibia',
                        metavar=t('CARPETA', 'FOLDER'), help=t('Carpeta de instalación de Tibia', 'Tibia installation folder'))
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--menu', action='store_true', help=t('Abrir la presentación con las opciones L y R', 'Open the welcome screen with L and R options'))
    action.add_argument('--diagnose', '--diagnostico', action='store_true', help=t('Revisar sin modificar archivos', 'Check without modifying files'))
    action.add_argument('--verify-downloads', '--verificar-descargas', action='store_true', help=t('Verificar descargas sin instalar', 'Verify downloads without installing'))
    action.add_argument('--repair', '--reparar', action='store_true', help=t('Solicitar confirmación y reparar', 'Ask for confirmation and repair'))
    action.add_argument('--restore', '--restaurar', type=Path, nargs='?', const=True, metavar=t('RESPALDO', 'BACKUP'),
                        help=t('Restaurar un respaldo; sin ruta, mostrar los disponibles', 'Restore a backup; omit the path to list available backups'))
    args = parser.parse_args()
    operation = ('restore' if args.restore else 'repair' if args.repair else
                 'verify' if args.verify_downloads else 'diagnose')
    root = args.root.resolve()
    if interactive or args.menu or operation == 'repair':
        operation = welcome_choice(root)
        if operation is None:
            return False
    root = locate_installation(root)
    if root is None:
        return False
    if operation == 'restore':
        backup = (args.restore.resolve() if isinstance(args.restore, Path) else select_backup(root))
        if backup is None or not confirm_restore(root, backup):
            return False
        restore(root, backup)
        return
    if operation == 'repair':
        require_closed(root)
    print(t('Instalación: ', 'Installation: ') + str(root), flush=True)
    bundles = plans(root)
    if operation in ('repair', 'verify'):
        repair(root, bundles, verify_only=(operation == 'verify'))
    else:
        print(t('Diagnóstico terminado. No se modificó la instalación. Usa --reparar para aplicar.',
                'Diagnosis complete. The installation was not changed. Use --repair to apply.'))


def error_message(exc):
    if isinstance(exc, subprocess.CalledProcessError):
        return t('No se pudieron comprobar los procesos de Tibia con Windows PowerShell.',
                 'Could not check Tibia processes using Windows PowerShell.')
    if isinstance(exc, FileNotFoundError):
        return t('No se encontró un archivo o una carpeta necesarios: ', 'A required file or folder was not found: ') + str(exc.filename or '')
    if isinstance(exc, OSError):
        location = str(exc.filename or '')
        return t('Windows no permitió acceder a un archivo o una carpeta. Cierra Tibia y comprueba los permisos. ',
                 'Windows could not access a file or folder. Close Tibia and check permissions. ') + location
    if isinstance(exc, (json.JSONDecodeError, KeyError, TypeError)):
        return t('El manifiesto o registro del respaldo tiene un formato inválido. No continúes con ese archivo.',
                 'The manifest or backup record has an invalid format. Do not continue with that file.')
    return str(exc)


if __name__ == '__main__':
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    interactive_exe = bool(getattr(sys, 'frozen', False)) and len(sys.argv) == 1
    exit_code = 0
    result = None
    try:
        result = main()
    except KeyboardInterrupt:
        print(t('\nOperación cancelada por el usuario.', '\nOperation cancelled by the user.'), flush=True)
        exit_code = 1
    except Exception as exc:
        print('ERROR: ' + error_message(exc), file=sys.stderr)
        exit_code = 1
    if interactive_exe and result is not False:
        try:
            input(t('\nPresiona Enter para cerrar...', '\nPress Enter to close...'))
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(exit_code)
