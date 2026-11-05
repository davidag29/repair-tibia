param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$projectRoot = $PSScriptRoot
$venvPython = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $venvPython)) {
    & $Python -m venv (Join-Path $projectRoot '.venv')
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear el entorno de compilacion.' }
}
& $venvPython -m pip install -r (Join-Path $projectRoot 'requirements-build.txt')
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias de compilacion.' }
& $venvPython -m PyInstaller --noconfirm --clean --noupx --onefile --windowed `
    --name 'Repair Assistant' `
    --icon (Join-Path $projectRoot 'packaging\srepair.ico') `
    --add-data ((Join-Path $projectRoot 'packaging\srepair.png') + ';assets') `
    --version-file (Join-Path $projectRoot 'packaging\windows-version.txt') `
    --distpath (Join-Path $projectRoot 'dist') `
    --workpath (Join-Path $projectRoot 'build\pyinstaller') `
    --specpath (Join-Path $projectRoot 'build') `
    (Join-Path $projectRoot 'src\srepair_gui.py')
if ($LASTEXITCODE -ne 0) { throw 'Fallo la compilacion del ejecutable.' }
Write-Host ('Ejecutable generado: ' + (Join-Path $projectRoot 'dist\Repair Assistant.exe'))
