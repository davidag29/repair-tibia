# S-Repair for Tibia

**S. Tensen · v1.1.1 · Windows x64 · Español / English**

[Español](#espanol) | [English](#english) | [Descargas / Downloads](https://github.com/davidag29/repair-tibia/releases)

Un único ejecutable con selección de idioma, reparación y restauración de respaldos.

One executable with language selection, repair and backup restoration.

<a id="espanol"></a>
## Español

Asistente independiente para instalaciones de Tibia cuyo cliente no se actualiza correctamente. Puede ayudar cuando aparece **«Tu versión del cliente es demasiado antigua. Reinicia Tibia para actualizar»**, por información de actualización almacenada en una caché antigua o por archivos dañados o desactualizados. No soluciona todas las causas posibles ni sustituye el soporte de CipSoft.

### Descargar y comenzar

Descarga el ejecutable desde [la última versión publicada](https://github.com/davidag29/repair-tibia/releases/latest). El archivo de GitHub se llama **`S-Repair.for.Tibia.exe`**. Incluye Python y sus dependencias; no necesitas instalar Python para utilizarlo.

**¿Windows bloquea la aplicación?** Consulta la [guía con capturas de Control inteligente de aplicaciones](docs/windows-app-control.md#espanol). Explica cómo revisar la configuración y las consecuencias de cambiarla; no es un requisito desactivar la protección.

1. Abre el ejecutable: aparece directamente toda la descripción del proceso y sus avisos, en español.
2. En esa misma pantalla, usa **L — Language: English / Español** para cambiar el idioma, **R — Respaldos / Restaurar**, **S — Confirmar e iniciar** o **N — Salir**. Enter sale sin cambios. Al elegir L, selecciona 1 para español o 2 para inglés; vuelve automáticamente a la descripción. Enter conserva el idioma y 0 vuelve sin cambiarlo.
3. Si no encuentra la instalación habitual, indica la carpeta que contiene `Tibia.exe`. Puedes pegar una ruta con espacios, entre comillas, o la ruta al ejecutable. **Una respuesta vacía cierra el reparador sin cambios.** Si la ruta es incorrecta, puedes reintentarlo.

### Reparar Tibia

Lee la explicación y confirma con **S + Enter**. **N o Enter** cancelan antes de iniciar. La tecla Y también se acepta por compatibilidad con versiones anteriores.

Si Tibia o su iniciador están abiertos, ciérralos normalmente. El reparador mantiene su ventana abierta y reinicia la comprobación cuando se cierran; no fuerza el cierre del juego.

El proceso muestra barras para revisión, descarga, respaldo e instalación, con velocidad y tiempo estimado de descarga:

1. Consulta los manifiestos de `https://static.tibia.com/launcher/` con una URL de consulta única para evitar información almacenada en caché.
2. Compara los archivos locales y descarga solo los que requieren reemplazo.
3. Verifica tamaños y SHA-256 de las descargas, y reconoce la envoltura LZMA utilizada por Tibia.
4. Comprueba que el manifiesto del servidor no haya cambiado durante la descarga.
5. Respalda los archivos que reemplazará, instala las copias oficiales y verifica el resultado.

Al terminar, cierra el reparador y abre Tibia desde su acceso directo habitual.

### ¿Dónde están los respaldos?

Se guardan **junto a la carpeta de instalación de Tibia**, nunca dentro de la carpeta temporal de descarga. Con la instalación habitual, la ubicación es:

```text
%LOCALAPPDATA%\Tibia-respaldo-AAAAMMDD-HHMMSS-identificador
```

Si Tibia está en `D:\Juegos\Tibia`, los respaldos quedan en `D:\Juegos\Tibia-respaldo-*`. El programa muestra **la ruta exacta** al crearlos y al finalizar, además de un comando de restauración para copiar y pegar en PowerShell.

Cada respaldo contiene los archivos que iban a reemplazarse y `restore.json`. **No es una copia completa de toda la instalación.** Se conserva después de restaurar. Los respaldos de la versión 1.0.0 también son compatibles.

### Restaurar con R

1. Abre el programa y, en la pantalla de descripción, pulsa **R — Respaldos / Restaurar**. Puedes cambiar antes el idioma con L.
2. Verás los últimos 20 respaldos de esa instalación, ordenados del más reciente al más antiguo, con sus rutas completas.
3. Escribe el número correspondiente o pega la ruta de otro respaldo. Enter sin escribir nada sale sin cambios.
4. Comprueba las rutas de instalación y respaldo. Confirma con **S + Enter**; **N o Enter** cancelan.
5. Cierra Tibia si sigue abierto. El programa verifica **todos** los archivos del respaldo antes de la primera escritura; si falta alguno o no coincide su hash, no inicia la restauración.
6. Restaura los archivos anteriores y elimina los que fueron creados por esa reparación. Verifica los archivos restaurados y conserva el respaldo.

Restaurar puede devolver el cliente a una versión anterior. Esto permite recuperar el estado previo a la reparación; no garantiza que esa versión pueda conectarse al servidor actual. Usa únicamente respaldos creados por el reparador y correspondientes a esa instalación.

### Si falla la reparación o restauración

- **Fallo de descarga, descompresión o verificación:** no se reemplazan archivos de la instalación.
- **Fallo antes de completar el respaldo:** no se inicia la instalación.
- **Fallo durante la instalación:** intenta restaurar, en orden inverso, los archivos modificados. Verifica las copias recuperadas y muestra la ruta del respaldo y las instrucciones para restaurarlo manualmente.
- **Archivos bloqueados o recuperación incompleta:** indica los archivos pendientes. Cierra Tibia, comprueba los permisos y reintenta desde **Restaurar un respaldo**. No borres el respaldo.
- **Restauración manual incompleta:** conserva el respaldo e informa de los archivos pendientes para poder reintentar.

Ctrl+C solicita cancelar. Un corte eléctrico o un cierre forzado pueden impedir la recuperación automática.

### Datos que conserva y límites

El reparador excluye `conf`, `minimap`, `characterdata`, `screenshots`, `log` y `cache`. Conserva las configuraciones, mapas, datos de personajes y capturas almacenados allí. También omite archivos auxiliares oficiales dentro de esas carpetas, como `conf/gpublacklist.json`.

No solicita tu cuenta o contraseña, no automatiza el juego ni incorpora cambios propios al código de los archivos oficiales. El repositorio y sus descargas no incluyen archivos del juego ni DLL de instalaciones ajenas; se obtienen del servidor oficial durante la reparación.

**Herramienta independiente, sin afiliación ni aprobación de CipSoft o BattlEye.** Trabaja con Tibia cerrado, no modifica la memoria del juego ni desactiva BattlEye. No se garantiza ausencia de bloqueos, incompatibilidades o falsos positivos. La [FAQ de BattlEye](https://www.battleye.com/support/faq/) contempla verificar o reinstalar archivos para resolver errores de integridad; esto no constituye una aprobación de esta herramienta. Consulta también la [regla 3b de Tibia](https://www.tibia.com/support/?rule=3b&subtopic=tibiarules).

**El ejecutable no tiene firma digital Authenticode.** S. Tensen es el crédito de autor en la interfaz y los metadatos, no un certificado digital. Si un antivirus muestra una detección, verifica el archivo y solicita revisión al fabricante; Microsoft dispone de un [portal para falsos positivos](https://www.microsoft.com/en-us/wdsi/filesubmission). No necesitas desactivar el antivirus para el funcionamiento previsto del programa.

### Compatibilidad y comandos

Windows 11 x64 es el sistema recomendado, con pruebas locales en un equipo. Windows 10 x64 tiene compatibilidad prevista, pendiente de pruebas. Esta compilación no admite Windows 7, 8, 8.1 ni sistemas de 32 bits. Windows ARM, Linux y macOS no están validados ni cubiertos por esta versión. Requiere Tibia instalado y acceso HTTPS al servidor oficial; utiliza Windows PowerShell y CIM para comprobar si el juego sigue abierto.

Ejemplos en PowerShell usando el nombre del archivo descargado:

```powershell
# Diagnóstico sin cambios
& '.\S-Repair.for.Tibia.exe' --idioma es --diagnostico
# Descargar y verificar en una carpeta temporal, sin instalar
& '.\S-Repair.for.Tibia.exe' --idioma es --verificar-descargas
# Reparar una instalación en otra ubicación, con confirmación
& '.\S-Repair.for.Tibia.exe' --idioma es --ruta 'D:\Juegos\Tibia' --reparar
# Mostrar los respaldos disponibles
& '.\S-Repair.for.Tibia.exe' --idioma es --restaurar
# Restaurar un respaldo concreto, con confirmación
& '.\S-Repair.for.Tibia.exe' --idioma es --ruta 'D:\Juegos\Tibia' --restaurar 'D:\Juegos\Tibia-respaldo-AAAAMMDD-HHMMSS-identificador'
# Ver todos los comandos
& '.\S-Repair.for.Tibia.exe' --idioma es --ayuda
```

### Código fuente, compilación y pruebas

La ejecución desde código fuente requiere Windows y Python 3.11 o posterior, sin bibliotecas de terceros. Para abrir los menús:

```powershell
python .\src\srepair.py --menu
```

Para compilar en Windows x64, ejecuta ` .\build.ps1` desde la raíz del repositorio. Crea `.venv`, instala `requirements-build.txt` y genera un único archivo `dist\S-Repair for Tibia.exe` sin UPX. No firma digitalmente el resultado. La versión publicada se compila con Python **3.14.3 x64** y PyInstaller **6.22.3**; no se garantiza una compilación idéntica byte por byte. Python 3.14 admite [Windows 10 o posterior](https://docs.python.org/3.14/using/windows.html#supported-windows-versions).

Ejecuta `python .\tests\test_repair.py` para comprobar idiomas, menús, confirmaciones, rutas, espera del cierre, progreso, hashes, descompresión, selección y validación de respaldos, restauración y recuperación ante fallos simulados. Las pruebas usan carpetas temporales, sin descargas reales ni cambios en tu instalación de Tibia.

<a id="english"></a>
## English

An independent assistant for Tibia installations that do not update correctly. It may help with **“Your client version is too old. Restart Tibia to update your client”** when update information is served from a stale cache or local files are damaged or outdated. It does not fix every possible update issue or replace CipSoft support.

### Download and start

Download **`S-Repair.for.Tibia.exe`** from [the latest release](https://github.com/davidag29/repair-tibia/releases/latest). Python and its dependencies are included; you do not need to install Python to use it.

**Is Windows blocking the app?** Read the [illustrated Smart App Control guide](docs/windows-app-control.md#english). It explains how to review the setting and the implications of changing it; disabling protection is not a requirement.

1. Open the executable: the full process description and notices appear immediately, initially in Spanish.
2. On that same screen, press **L — Language: English / Español**, then **2 — English**. The description is displayed again in English. Use **R — Backups / Restore**, **Y — Confirm and start**, or **N — Exit**. Pressing Enter at the welcome screen exits without changes. In the language selector, Enter keeps the current language and 0 returns without changing it.
3. If the default installation cannot be found, enter the folder containing `Tibia.exe`. Quoted paths, spaces and a path to the executable itself are accepted. **An empty response closes the tool without changes.** Invalid paths can be retried.

### Repair Tibia

Read the explanation and confirm with **Y + Enter**. **N or Enter** cancels before repair starts.

If Tibia or its launcher is running, close it normally. The tool keeps its window open and restarts checks automatically once they close. It does not forcibly close the game.

Progress bars cover checks, downloads, backup and installation, with download speed and estimated remaining time:

1. Fetch official manifests from `https://static.tibia.com/launcher/` using a unique query URL to bypass stale cache.
2. Compare local files and download only those requiring replacement.
3. Verify download sizes and SHA-256 hashes, including Tibia's LZMA wrapper format.
4. Check that the server manifest has not changed during the download.
5. Back up files before replacement, install official copies and verify the result.

When complete, close the tool and launch Tibia from its usual shortcut.

### Where are backups stored?

Backups are stored **beside the Tibia installation folder**, not in the temporary download folder. For the default installation:

```text
%LOCALAPPDATA%\Tibia-respaldo-YYYYMMDD-HHMMSS-identifier
```

For `D:\Games\Tibia`, backups are created under `D:\Games\Tibia-respaldo-*`. The program displays **the exact path** when a backup is created and after completion, along with a PowerShell restore command you can copy and paste.

Each backup contains files that were about to be replaced and `restore.json`. **It is not a full copy of the installation.** The backup remains after restoration. Backups from version 1.0.0 are supported.

### Restore with R

1. Open the tool, optionally change the language using L, then press **R — Backups / Restore** on the description screen.
2. The latest 20 backups for that installation are listed, newest first, with their full paths.
3. Enter a listed number or paste another backup folder path. An empty response exits without changes.
4. Check the installation and backup paths. Confirm with **Y + Enter**; **N or Enter** cancels.
5. Close Tibia if it is running. The tool verifies **all** backup files before the first write. If any file is missing or its hash does not match, restoration does not start.
6. Previous files are restored, and files created by that repair are removed. Restored files are verified and the backup is kept.

Restoration may revert the client to an older version. It recovers the state before that repair; it does not guarantee that the old version can connect to the current server. Use only backups created by this tool for that installation.

### If repair or restoration fails

- **Download, decompression or verification failure:** installation files are not replaced.
- **Failure before backup completion:** installation does not begin.
- **Installation failure:** the tool attempts to restore modified files in reverse order, verifies recovered copies, and displays the backup path and manual restore instructions.
- **Locked files or incomplete automatic recovery:** remaining files are listed. Close Tibia, check permissions and retry using **Restore a backup**. Keep the backup folder.
- **Incomplete manual restoration:** the backup is kept, and remaining files are reported so you can retry.

Ctrl+C requests cancellation. Power loss or forced termination can prevent automatic recovery.

### Preserved data and limitations

The repair excludes `conf`, `minimap`, `characterdata`, `screenshots`, `log` and `cache`, preserving settings, maps, character data and screenshots stored there. Official helper files within those folders, such as `conf/gpublacklist.json`, are also skipped.

The tool does not request your account or password, automate gameplay or add custom code to official game files. This repository and its downloads do not include game files or DLLs from other installations; files are fetched from the official server during repair.

**Independent tool, not affiliated with or approved by CipSoft or BattlEye.** It works with Tibia closed, does not modify game memory and does not disable BattlEye. Freedom from blocks, compatibility issues or false positives is not guaranteed. The [BattlEye FAQ](https://www.battleye.com/support/faq/) discusses verifying or reinstalling game files to fix integrity issues; this is not approval of this tool. See also [Tibia rule 3b](https://www.tibia.com/support/?rule=3b&subtopic=tibiarules).

**The executable is not Authenticode-signed.** S. Tensen is the author credit in the interface and file metadata, not a digital certificate. If antivirus software reports a detection, verify the file and request a vendor review. Microsoft provides a [false-positive submission portal](https://www.microsoft.com/en-us/wdsi/filesubmission). Disabling antivirus is not required for the tool's intended operation.

### Compatibility and commands

Windows 11 x64 is recommended and has been tested locally on one machine. Windows 10 x64 is expected to work but has not been tested. This build does not support Windows 7, 8, 8.1 or 32-bit systems. Windows ARM, Linux and macOS are not validated or covered by this release. A Tibia installation and HTTPS access to the official server are required. Windows PowerShell and CIM are used to check whether the game is running.

PowerShell examples using the downloaded filename:

```powershell
# Diagnose without changes
& '.\S-Repair.for.Tibia.exe' --language en --diagnose
# Download and verify in a temporary folder without installing
& '.\S-Repair.for.Tibia.exe' --language en --verify-downloads
# Repair another installation, with confirmation
& '.\S-Repair.for.Tibia.exe' --language en --root 'D:\Games\Tibia' --repair
# List available backups
& '.\S-Repair.for.Tibia.exe' --language en --restore
# Restore a specific backup, with confirmation
& '.\S-Repair.for.Tibia.exe' --language en --root 'D:\Games\Tibia' --restore 'D:\Games\Tibia-respaldo-YYYYMMDD-HHMMSS-identifier'
# List all commands
& '.\S-Repair.for.Tibia.exe' --language en --help
```

### Source code, build and tests

Running from source requires Windows and Python 3.11 or newer, with no third-party runtime libraries. To open the menus:

```powershell
python .\src\srepair.py --menu
```

To build on Windows x64, run `.\build.ps1` from the repository root. It creates `.venv`, installs `requirements-build.txt`, and produces a single `dist\S-Repair for Tibia.exe` without UPX. It does not digitally sign the result. The release uses Python **3.14.3 x64** and PyInstaller **6.22.3**; bit-for-bit reproducibility is not guaranteed. Python 3.14 supports [Windows 10 and newer](https://docs.python.org/3.14/using/windows.html#supported-windows-versions).

Run `python .\tests\test_repair.py` to check languages, menus, confirmation, paths, waiting for game closure, progress, hashes, decompression, backup selection and validation, restoration, and recovery from simulated failures. Tests use temporary folders, without real downloads or changes to your Tibia installation.

## Estructura / Structure

```text
src/srepair.py                 Reparador y terminal / Repair logic and terminal UI
tests/test_repair.py           Pruebas / Tests
packaging/windows-version.txt  Metadatos de Windows / Windows metadata
requirements-build.txt         Dependencias de compilación / Build dependencies
build.ps1                      Compilar el ejecutable / Build the executable
```

## Autor y derechos / Author and rights

**S. Tensen**. Copyright (c) 2026 S. Tensen.

Licencia del proyecto pendiente de definir. Tibia y BattlEye pertenecen a sus respectivos titulares.

Project license has not been selected. Tibia and BattlEye belong to their respective owners.
