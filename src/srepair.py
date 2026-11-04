"""S-Repair for Tibia - Autor: S. Tensen.
Reparacion desde static.tibia.com con respaldo automatico.

Abre S-Repair for Tibia.exe con doble clic para reparar.
Diagnostico: "S-Repair for Tibia.exe" --diagnose
Restaurar:   "S-Repair for Tibia.exe" --restore RUTA_DEL_RESPALDO
"""
import argparse
import hashlib
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


def confirm_repair(root):
    colors = console_colors()
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
    row('ASISTENTE DE REPARACION', '1;36', center=True)
    row('Autor: ' + AUTHOR, center=True)
    row('Archivos oficiales / Respaldo automatico', center=True)
    print(style(border, '36'), flush=True)
    row()
    row('QUE HARA EL ASISTENTE', '1;37')
    row('1. Esperar a que cierres Tibia y comprobar la instalacion.')
    row('2. Descargar los archivos necesarios del servidor oficial, evitando la cache antigua.')
    row('3. Verificar cada descarga con SHA-256 y crear un respaldo.')
    row('4. Reemplazar los archivos desactualizados o danados y verificar el resultado.')
    row()
    row('Se conservan tus mapas, hotkeys, configuraciones y capturas.', '32')
    row()
    row('INFORMACION SOBRE LOS ARCHIVOS Y BATTLEYE', '1;33')
    row('Restauramos copias oficiales: no incorporamos cambios propios al codigo del juego, no modificamos su memoria ni desactivamos BattlEye.')
    row('Esta herramienta es independiente y no cuenta con aprobacion de CipSoft o BattlEye. No podemos garantizar ausencia de bloqueos o incompatibilidades.')
    row()
    row('Instalacion: ' + str(root))
    row()
    row('QUIERES REPARAR TIBIA?', '1;36', center=True)
    row('[Y] Confirmar e iniciar     [N] Salir', '1;37', center=True)
    row('Enter sin elegir cancela la operacion.', center=True)
    print(style(border, '36'), flush=True)
    while True:
        try:
            choice = input('\nTu eleccion [Y/N]: ').strip().lower()
        except EOFError:
            choice = ''
        if choice in ('y', 's'):
            print(style('\nConfirmado. Iniciando comprobacion y reparacion...\n', '1;32'), flush=True)
            return True
        if choice in ('', 'n'):
            print('\nOperacion cancelada. No se modifico ningun archivo.', flush=True)
            return False
        print('Escribe Y para iniciar o N para salir.', flush=True)


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

    def finish(self, detail='Listo'):
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
        raise ValueError('Servidor no permitido: ' + url)
    url += ('&' if '?' in url else '?') + 'repair=' + uuid.uuid4().hex
    last = None
    for attempt in range(3):
        try:
            request = urllib.request.Request(url, headers={'Cache-Control': 'no-cache', 'User-Agent': 'TibiaRepair/1.0'})
            with urllib.request.urlopen(request, timeout=60) as response:
                final = urllib.parse.urlsplit(response.url)
                if final.scheme != 'https' or final.netloc != 'static.tibia.com':
                    raise ValueError('Redireccion no permitida')
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
    raise RuntimeError('No se pudo descargar ' + relative) from last


def safe_path(root, relative):
    clean = relative.replace('\\', '/')
    parts = clean.split('/')
    if not clean or any(p in ('', '.', '..') or ':' in p for p in parts):
        raise ValueError('Ruta no permitida: ' + relative)
    if parts[0].lower() in PROTECTED:
        raise ValueError('El manifiesto intenta modificar datos personales: ' + relative)
    target = root.joinpath(*parts).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('Ruta fuera de la instalacion: ' + relative)
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
    print('\nTIBIA ESTA ABIERTO', flush=True)
    print('Cierra el juego y su launcher normalmente. No cierres esta ventana.', flush=True)
    print('Al cerrarlos, la comprobacion se reiniciara automaticamente aqui.', flush=True)
    print('Puedes cancelar con Ctrl+C. No se forzara el cierre del juego.\n', flush=True)
    start = time.monotonic()
    previous_names = None
    while active:
        names = ', '.join(sorted({r['Name'] for r in active}))
        if sys.stdout.isatty():
            text = f'Esperando cierre... {int(time.monotonic() - start)}s | {names}'
            width = max(shutil.get_terminal_size((110, 25)).columns - 1, 40)
            print('\r' + text[:width].ljust(width), end='', flush=True)
        elif names != previous_names:
            print('Esperando cierre: ' + names, flush=True)
        previous_names = names
        time.sleep(2)
        active = running(root)
    if sys.stdout.isatty():
        print(flush=True)
    print('\n[OK] Tibia esta cerrado. Reiniciando comprobacion...\n', flush=True)
    return True


def expected(entry):
    return entry.get('unpackedhash') or entry['packedhash']


def decode_verified(packed, entry):
    if digest(packed) != entry['packedhash'] or len(packed) != entry['packedsize']:
        raise ValueError('Descarga no coincide con SHA-256/tamano: ' + entry['localfile'])
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
    raise ValueError('Archivo descomprimido invalido: ' + entry['localfile'])


def matches(path, entry):
    if not path.is_file():
        return False
    size = entry.get('unpackedsize', entry.get('packedsize'))
    if size is not None and path.stat().st_size != size:
        return False
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() == expected(entry)


def plans(root):
    print('\n[1/4] COMPROBAR ARCHIVOS\nConsultando la version oficial sin cache...', flush=True)
    client = root / 'packages' / 'Tibia'
    result = []
    for label, base, folder in [('launcher', 'launcher-windows-current/', root),
                                 ('cliente', 'tibiaclient-windows-current/', client),
                                 ('assets', 'assets-current/', client)]:
        name = 'assets.json' if label == 'assets' else 'package.json'
        raw = fetch(base + name)
        manifest = json.loads(raw)
        if not isinstance(manifest.get('files'), list) or not manifest['files']:
            raise ValueError('Manifiesto vacio o invalido: ' + label)
        marker_name = 'assets.json.sha256' if label == 'assets' else 'package.json.version'
        marker = fetch(base + marker_name).decode('ascii').strip()
        if label == 'assets':
            if marker != digest(raw):
                raise ValueError('El hash del manifiesto de assets no coincide; vuelve a intentar.')
        elif marker != manifest['version']:
            raise ValueError('La version cambio durante la consulta; vuelve a intentar.')
        entries = [e for e in manifest['files']
                   if e['localfile'].replace('\\', '/').split('/')[0].lower() not in PROTECTED]
        changes = []
        progress = Progress('Revisando ' + label, len(entries))
        for index, entry in enumerate(entries, 1):
            progress.update(index - 1, entry['localfile'])
            if not matches(safe_path(folder, entry['localfile']), entry):
                changes.append(entry)
        progress.finish()
        print(f'{label}: version {manifest.get("version", marker[:12])}; {len(changes)} de {len(manifest["files"])} archivos requieren reemplazo.', flush=True)
        result.append(dict(label=label, base=base, folder=folder, raw=raw, name=name,
                           marker=marker, marker_name=marker_name, changes=changes))
    return result


def restore(root, backup):
    journal = json.loads((backup / 'restore.json').read_text(encoding='utf-8'))
    if Path(journal['root']).resolve() != root.resolve():
        raise ValueError('El respaldo pertenece a otra instalacion.')
    require_closed(root)
    for item in reversed(journal['files']):
        target = safe_path(root, item['path'])
        if item['existed']:
            source = safe_path(backup / 'files', item['path'])
            if digest(source.read_bytes()) != item['backup_hash']:
                raise ValueError('Respaldo danado: ' + item['path'])
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        elif target.exists():
            target.unlink()
    print('Restauracion terminada.')


def repair(root, bundles, verify_only=False):
    if not verify_only:
        if require_closed(root):
            bundles = plans(root)
    total_files = sum(len(b['changes']) for b in bundles)
    total_bytes = sum(e['packedsize'] for b in bundles for e in b['changes'])
    print(f'\n[2/4] DESCARGAR Y VERIFICAR\n{total_files} archivos | {human_bytes(total_bytes)} de descarga', flush=True)
    download_progress = Progress('Descarga', total_bytes, byte_units=True)
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
        download_progress.finish(f'{completed_files} archivos verificados con SHA-256')
        # No escribir si CipSoft publico otra version mientras se descargaba.
        for bundle in bundles:
            if digest(fetch(bundle['base'] + bundle['name'])) != digest(bundle['raw']):
                raise RuntimeError('Cambio la actualizacion en el servidor. Vuelve a ejecutar el script.')
        if verify_only:
            print('Todas las descargas se descomprimieron y verificaron. No se modifico la instalacion.')
            return
        if require_closed(root):
            return repair(root, plans(root))
        print('\n[3/4] CREAR RESPALDO', flush=True)
        backup = root.parent / ('Tibia-respaldo-' + time.strftime('%Y%m%d-%H%M%S') + '-' + uuid.uuid4().hex[:6])
        backup.mkdir()
        journal = {'root': str(root), 'files': []}
        partials = [folder / 'partial.package.json.version' for folder in
                    [root, root / 'packages' / 'Tibia'] if (folder / 'partial.package.json.version').exists()]
        backup_targets = list(replacements) + partials
        backup_progress = Progress('Respaldando', len(backup_targets))
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
        print('Respaldo: ' + str(backup), flush=True)
        # Volver a comprobar antes de la primera escritura en la instalacion.
        if require_closed(root):
            return repair(root, plans(root))
        print('\n[4/4] INSTALAR Y VERIFICAR', flush=True)
        install_progress = Progress('Instalando', len(replacements))
        touched = []
        try:
            for install_index, (target, staged) in enumerate(replacements.items(), 1):
                target.parent.mkdir(parents=True, exist_ok=True)
                touched.append(target)
                with staged.open('rb') as source, target.open('wb') as destination:
                    shutil.copyfileobj(source, destination)
                if digest(target.read_bytes()) != digest(staged.read_bytes()):
                    raise RuntimeError('Fallo la verificacion despues de escribir: ' + str(target))
                install_progress.update(install_index, target.name)
            for partial in partials:
                touched.append(partial)
                partial.unlink()
        except (Exception, KeyboardInterrupt):
            install_progress.clear()
            print('Fallo al instalar. Restaurando los archivos modificados...', flush=True)
            lookup = {root / i['path']: i for i in journal['files']}
            for target in reversed(touched):
                item = lookup[target]
                try:
                    if item['existed']:
                        shutil.copy2(backup / 'files' / item['path'], target)
                    elif target.exists():
                        target.unlink()
                except OSError as exc:
                    print(f'No se pudo restaurar {target}: {exc}. Usa --restore con el respaldo.', flush=True)
            raise
        install_progress.finish()
        print('\n[OK] REPARACION COMPLETADA\nCierra este reparador y abre Tibia desde su acceso directo normal.', flush=True)


def locate_installation(root):
    if (root / 'Tibia.exe').is_file():
        return root
    print('\nNO ENCONTRAMOS LA CARPETA DE TIBIA', flush=True)
    print('No encontramos Tibia en la ubicacion habitual o indicada:\n  ' + str(root), flush=True)
    print('Si esta en otra ubicacion, indica la carpeta que contiene Tibia.exe.', flush=True)
    print('Puedes pegar la ruta entre comillas. Enter sin escribir nada cierra el reparador.\n', flush=True)
    while True:
        try:
            answer = input('Carpeta de Tibia: ').strip()
        except EOFError:
            answer = ''
        if not answer:
            print('\nNo se indico una carpeta. Cerrando sin realizar cambios.', flush=True)
            return None
        try:
            candidate = Path(os.path.expandvars(answer.strip('\"\''))).expanduser().resolve()
            if candidate.name.lower() == 'tibia.exe' and candidate.is_file():
                candidate = candidate.parent
            if (candidate / 'Tibia.exe').is_file():
                print('\n[OK] Instalacion encontrada: ' + str(candidate), flush=True)
                return candidate
        except (OSError, ValueError, RuntimeError):
            pass
        print('No encontramos Tibia.exe en esa ruta. Intenta otra carpeta o pulsa Enter para salir.', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--root', type=Path, default=Path(os.environ.get('LOCALAPPDATA', '.')) / 'Tibia')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--diagnose', action='store_true', help='Revisar sin modificar archivos')
    action.add_argument('--verify-downloads', action='store_true', help='Verificar descargas sin instalar')
    action.add_argument('--repair', action='store_true')
    action.add_argument('--restore', type=Path)
    args = parser.parse_args()
    root = locate_installation(args.root.resolve())
    if root is None:
        return False
    if args.repair and not confirm_repair(root):
        return False
    if args.restore:
        restore(root, args.restore.resolve())
        return
    if args.repair:
        require_closed(root)
    print('Instalacion: ' + str(root), flush=True)
    bundles = plans(root)
    if args.repair or args.verify_downloads:
        repair(root, bundles, verify_only=args.verify_downloads)
    else:
        print('Diagnostico terminado. No se modifico la instalacion. Usa --repair para aplicar.')


if __name__ == '__main__':
    interactive_exe = bool(getattr(sys, 'frozen', False)) and len(sys.argv) == 1
    if interactive_exe:
        sys.argv.append('--repair')
    exit_code = 0
    result = None
    try:
        result = main()
    except KeyboardInterrupt:
        print('\nOperacion cancelada por el usuario.', flush=True)
        exit_code = 1
    except Exception as exc:
        print('ERROR: ' + str(exc), file=sys.stderr)
        exit_code = 1
    if interactive_exe and result is not False:
        try:
            input('\nPresiona Enter para cerrar...')
        except (EOFError, KeyboardInterrupt):
            pass
    sys.exit(exit_code)
