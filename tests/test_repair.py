import importlib.util
import json
import lzma
from pathlib import Path
import tempfile
import io
import sys
from unittest.mock import patch

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

spec = importlib.util.spec_from_file_location('repair', Path(__file__).resolve().parents[1] / 'src' / 'srepair.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
original_require_closed = m.require_closed
original_fetch = m.fetch
m.require_closed = lambda root: None

# Carpeta alternativa, rutas entre comillas, reintentos y salida vacia.
with tempfile.TemporaryDirectory() as temp:
    valid = Path(temp) / 'Tibia alternativo'
    valid.mkdir()
    (valid / 'Tibia.exe').write_bytes(b'test')
    missing = Path(temp) / 'No instalado'
    with patch('builtins.input') as input_mock:
        assert m.locate_installation(valid) == valid
        input_mock.assert_not_called()
    for reply in [str(valid), '"' + str(valid) + '"', str(valid / 'Tibia.exe')]:
        with patch('builtins.input', return_value=reply), patch('sys.stdout', new_callable=io.StringIO):
            assert m.locate_installation(missing) == valid
    with patch('builtins.input', side_effect=['Z:/no-existe-tibia-123', str(valid)]), \
         patch('sys.stdout', new_callable=io.StringIO):
        assert m.locate_installation(missing) == valid
    with patch.object(m.sys, 'argv', ['RepararTibia.exe', '--repair', '--root', str(missing)]), \
         patch('builtins.input', return_value=''), patch('sys.stdout', new_callable=io.StringIO), \
         patch.object(m, 'plans') as plans, patch.object(m, 'confirm_repair') as confirm:
        assert m.main() is False
        plans.assert_not_called()
        confirm.assert_not_called()

# La bienvenida requiere consentimiento antes de consultar o reparar.
for reply, expected_result in [('Y', True), ('y', True), ('s', True), ('N', False), ('', False)]:
    with patch('builtins.input', return_value=reply), patch('sys.stdout', new_callable=io.StringIO) as output:
        assert m.confirm_repair(Path('Tibia')) is expected_result
        assert '¿QUIERES REPARAR TIBIA?' in output.getvalue()
        assert 'S-Repair for Tibia' in output.getvalue()
        assert 'Autor: S. Tensen' in output.getvalue()
        assert 'sin aprobación' in output.getvalue()
with patch('builtins.input', side_effect=['invalido', 'N']), patch('sys.stdout', new_callable=io.StringIO):
    assert m.confirm_repair(Path('Tibia')) is False
with tempfile.TemporaryDirectory() as temp:
    valid = Path(temp)
    (valid / 'Tibia.exe').write_bytes(b'test')
    with patch.object(m.sys, 'argv', ['S-Repair for Tibia.exe', '--repair', '--root', str(valid)]), \
         patch('builtins.input', return_value='N'), \
         patch.object(m, 'plans') as plans, patch.object(m, 'repair') as repair, \
         patch.object(m, 'running') as running, patch('sys.stdout', new_callable=io.StringIO):
        assert m.main() is False
        plans.assert_not_called()
        repair.assert_not_called()
        running.assert_not_called()

# Esperar sin cerrar el programa ni forzar el cierre del juego.
active = [{'Name': 'client.exe', 'ProcessId': 123}]
with patch.object(m, 'running', side_effect=[active, active, []]), \
     patch.object(m.time, 'sleep') as sleep, \
     patch('sys.stdout', new_callable=io.StringIO) as output:
    assert original_require_closed(Path('Tibia')) is True
    assert sleep.call_count == 2
    assert 'Reiniciando comprobación' in output.getvalue()
with patch.object(m, 'running', return_value=[]):
    assert original_require_closed(Path('Tibia')) is False

# Barras con porcentajes y unidades legibles.
with patch('sys.stdout', new_callable=io.StringIO) as output:
    progress = m.Progress('Descarga', 1024, byte_units=True)
    progress.update(512, '1/2 prueba.dll')
    progress.finish()
    assert '50.0%' in output.getvalue() and '100.0%' in output.getvalue()
    assert 'KB' in output.getvalue()

# La descarga informa bytes recibidos sin alterar el contenido.
class FakeResponse(io.BytesIO):
    url = 'https://static.tibia.com/launcher/test.bin'
    headers = {'Content-Length': str(600000)}

reports = []
with patch.object(m.urllib.request, 'urlopen', return_value=FakeResponse(b'x' * 600000)):
    received = original_fetch('test.bin', progress=lambda done, total: reports.append((done, total)))
    assert received == b'x' * 600000
    assert len(reports) == 3 and reports[-1] == (600000, 600000)

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp) / 'Tibia'
    root.mkdir()
    target = root / 'Tibia.exe'
    target.write_bytes(b'old version')
    partial = root / 'partial.package.json.version'
    partial.write_bytes(b'old partial')
    new = b'new verified version'
    packed = lzma.compress(new, format=lzma.FORMAT_ALONE)
    entry = dict(localfile='Tibia.exe', url='Tibia.exe.lzma', packedhash=m.digest(packed),
                 packedsize=len(packed), unpackedhash=m.digest(new), unpackedsize=len(new))
    wrapped = bytes(32) + packed[:5] + len(packed).to_bytes(8, 'little') + packed[13:]
    wrapped_entry = dict(entry, packedhash=m.digest(wrapped), packedsize=len(wrapped))
    assert m.decode_verified(wrapped, wrapped_entry) == new
    assert m.decode_verified(packed, entry) == new
    raw = json.dumps({'version': 'new', 'files': [entry]}).encode()
    bundle = dict(label='test', folder=root, base='test/', raw=raw, name='package.json',
                  marker='new', marker_name='package.json.version', changes=[entry])
    m.fetch = lambda name, **kwargs: packed if name.endswith('.lzma') else raw
    m.repair(root, [bundle])
    assert target.read_bytes() == new and not partial.exists()
    backup = next(Path(temp).glob('Tibia-respaldo-*'))
    m.restore(root, backup)
    assert target.read_bytes() == b'old version'
    assert partial.read_bytes() == b'old partial'
    assert not (root / 'package.json').exists()
    m.fetch = lambda name, **kwargs: b'corrupt' if name.endswith('.lzma') else raw
    try:
        m.repair(root, [bundle])
        raise AssertionError('Corrupt download accepted')
    except ValueError:
        assert target.read_bytes() == b'old version'
    for relative in ['../outside', '/absolute', 'C:/outside', 'conf/settings.json']:
        try:
            m.safe_path(root, relative)
            raise AssertionError('Unsafe path accepted')
        except ValueError:
            pass
# Idiomas y menús: confirmar, salir y reintentar respuestas incorrectas.
for language, confirm_word in [('es', '¿QUIERES REPARAR TIBIA?'), ('en', 'DO YOU WANT TO REPAIR TIBIA?')]:
    m.LANGUAGE = language
    with patch('builtins.input', return_value='N'), patch('sys.stdout', new_callable=io.StringIO) as output:
        assert m.confirm_repair(Path('Tibia')) is False
        assert confirm_word in output.getvalue()
    for option, expected_action in [('1', 'repair'), ('2', 'restore'), ('', None), ('0', None)]:
        with patch('builtins.input', return_value=option), patch('sys.stdout', new_callable=io.StringIO):
            assert m.choose_action() == expected_action
for option, language in [('1', 'es'), ('2', 'en'), ('', 'es')]:
    with patch('builtins.input', return_value=option), patch('sys.stdout', new_callable=io.StringIO):
        assert m.choose_language() is True and m.LANGUAGE == language
m.LANGUAGE = 'es'

# Respaldo 1.0 sin metadatos nuevos: listado, selección, confirmación y restauración.
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp) / 'Tibia'
    root.mkdir()
    (root / 'Tibia.exe').write_bytes(b'current')
    backup = Path(temp) / 'Tibia-respaldo-20260101-000000-prueba'
    (backup / 'files').mkdir(parents=True)
    (backup / 'files' / 'Tibia.exe').write_bytes(b'original')
    (backup / 'files' / 'other.dll').write_bytes(b'original dll')
    (root / 'other.dll').write_bytes(b'current dll')
    journal = {'root': str(root), 'files': [
        {'path': 'Tibia.exe', 'existed': True, 'backup_hash': m.digest(b'original')},
        {'path': 'other.dll', 'existed': True, 'backup_hash': m.digest(b'original dll')}]}
    (backup / 'restore.json').write_text(json.dumps(journal), encoding='utf-8')
    assert m.find_backups(root) == [backup]
    for choice in ['1', '"' + str(backup) + '"', str(backup / 'restore.json')]:
        with patch('builtins.input', return_value=choice), patch('sys.stdout', new_callable=io.StringIO):
            assert m.select_backup(root) == backup
    with patch('builtins.input', side_effect=['0', '']), patch('sys.stdout', new_callable=io.StringIO):
        assert m.select_backup(root) is None
    with patch('builtins.input', return_value='N'), patch('sys.stdout', new_callable=io.StringIO):
        assert m.confirm_restore(root, backup) is False
    # Si un archivo del respaldo está dañado, ninguno de los destinos cambia.
    (backup / 'files' / 'Tibia.exe').write_bytes(b'corrupt')
    with patch('sys.stdout', new_callable=io.StringIO):
        try:
            m.restore(root, backup)
            raise AssertionError('Corrupt backup accepted')
        except ValueError:
            pass
    assert (root / 'Tibia.exe').read_bytes() == b'current'
    assert (root / 'other.dll').read_bytes() == b'current dll'
    (backup / 'files' / 'Tibia.exe').write_bytes(b'original')
    # Detectar bloqueos por archivo y conservar el respaldo para reintentar.
    copy2 = m.shutil.copy2
    def locked_copy(source, target):
        if Path(target).name == 'Tibia.exe':
            raise PermissionError('simulated lock')
        return copy2(source, target)
    with patch.object(m.shutil, 'copy2', side_effect=locked_copy), patch('sys.stdout', new_callable=io.StringIO) as output:
        try:
            m.restore(root, backup)
            raise AssertionError('Locked restore succeeded')
        except RuntimeError as exc:
            assert 'incompleta' in str(exc)
            assert str(backup) in output.getvalue()
    assert backup.exists() and (root / 'other.dll').read_bytes() == b'original dll'
    # Menú de restauración completo: no consultar el servidor ni reparar.
    with patch.object(m.sys, 'argv', ['S-Repair for Tibia.exe', '--language', 'en', '--root', str(root), '--menu']), \
         patch('builtins.input', side_effect=['2', '1', 'Y']), patch.object(m, 'plans') as plans, \
         patch('sys.stdout', new_callable=io.StringIO) as output:
        m.main()
        plans.assert_not_called()
        assert 'RESTORE COMPLETED' in output.getvalue()
    assert (root / 'Tibia.exe').read_bytes() == b'original'
    assert backup.exists()
    # También reconocer la instalación si Tibia.exe falta después de un fallo.
    (root / 'Tibia.exe').unlink()
    assert m.locate_installation(root) == root
    with patch('sys.stdout', new_callable=io.StringIO):
        m.restore(root, backup)
    assert (root / 'Tibia.exe').read_bytes() == b'original'
m.LANGUAGE = 'es'

# Fallo realista durante la escritura: recuperar ambos archivos modificados.
with tempfile.TemporaryDirectory() as temp:
    root = Path(temp) / 'Tibia'
    root.mkdir()
    entries, downloads = [], {}
    for name in ['Tibia.exe', 'other.dll']:
        (root / name).write_bytes(b'old ' + name.encode())
        data = b'new ' + name.encode()
        packed = lzma.compress(data, format=lzma.FORMAT_ALONE)
        entries.append(dict(localfile=name, url=name + '.lzma', packedhash=m.digest(packed),
                            packedsize=len(packed), unpackedhash=m.digest(data), unpackedsize=len(data)))
        downloads['test/' + name + '.lzma'] = packed
    raw = json.dumps({'version': 'new', 'files': entries}).encode()
    bundle = dict(label='test', folder=root, base='test/', raw=raw, name='package.json',
                  marker='new', marker_name='package.json.version', changes=entries)
    def fail_second(source, destination):
        if Path(destination.name).name == 'other.dll':
            destination.write(b'partial')
            raise OSError('simulated installation failure')
        return original_copyfileobj(source, destination)
    original_copyfileobj = m.shutil.copyfileobj
    with patch.object(m, 'fetch', side_effect=lambda name, **kw: downloads.get(name, raw)), \
         patch.object(m.shutil, 'copyfileobj', side_effect=fail_second), \
         patch('sys.stdout', new_callable=io.StringIO) as output:
        try:
            m.repair(root, [bundle])
            raise AssertionError('Failure not raised')
        except OSError:
            assert 'se restauraron desde el respaldo' in output.getvalue()
            assert 'Ubicación del respaldo' in output.getvalue()
    for name in ['Tibia.exe', 'other.dll']:
        assert (root / name).read_bytes() == b'old ' + name.encode()
    assert m.find_backups(root)
print('PASS: idiomas, menús, confirmación, rutas, progreso, descompresión, verificación, restauración y recuperación ante fallos')
