import importlib.util
import json
import lzma
from pathlib import Path
import tempfile
import io
from unittest.mock import patch

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
        assert 'QUIERES REPARAR TIBIA?' in output.getvalue()
        assert 'S-Repair for Tibia' in output.getvalue()
        assert 'Autor: S. Tensen' in output.getvalue()
        assert 'no cuenta con aprobacion' in output.getvalue()
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
    assert 'Reiniciando comprobacion' in output.getvalue()
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
print('PASS: replacement, hashes, restoration, partial markers, corrupted download, protected paths')
