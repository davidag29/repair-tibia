# S-Repair for Tibia

**Autor: S. Tensen · Windows x64 · Interfaz de terminal**

Asistente independiente para reparar instalaciones de Tibia cuyo cliente no se actualiza correctamente. Puede ayudar con el aviso **“Your client version is too old. Restart Tibia to update your client”** cuando la información de actualización recibida está almacenada en una caché antigua o hay archivos desactualizados o dañados.

No soluciona todas las causas posibles de errores de actualización ni sustituye el soporte técnico de CipSoft.

## Descargar

Descarga **`S-Repair for Tibia.exe`** desde [Releases](https://github.com/davidag29/repair-tibia/releases). El ejecutable incluye Python y sus dependencias: **no necesitas instalar Python para usarlo**.

## Cómo usarlo

1. Abre el ejecutable con tu usuario habitual de Windows.
2. Si no encuentra Tibia en `%LOCALAPPDATA%\Tibia`, indica la carpeta que contiene `Tibia.exe`. Acepta rutas con espacios o entre comillas, y también la ruta al propio `Tibia.exe`.
3. Si dejas la ruta vacía y presionas **Enter**, el programa se cierra sin hacer cambios. Si la ruta es incorrecta, puedes volver a intentarlo.
4. Lee la explicación inicial y escribe **Y + Enter** para confirmar. **N o Enter** cancelan antes de iniciar la reparación.
5. Si Tibia o su launcher están abiertos, ciérralos normalmente. El reparador mantiene su ventana abierta y reinicia la comprobación cuando detecta que se cerraron. No fuerza el cierre del juego.
6. Espera a que termine la revisión, descarga, respaldo e instalación. Las barras muestran el progreso; durante la descarga también indican velocidad y tiempo estimado.
7. Al finalizar, cierra el reparador y abre Tibia desde su acceso directo habitual.

Puedes cancelar con **Ctrl+C**. Durante la instalación, el reparador intenta restaurar los archivos que haya modificado si ocurre un error o una interrupción controlada. Un corte de energía o un cierre forzado pueden impedir esa recuperación automática.

## Qué hace

- Consulta los manifiestos oficiales de `https://static.tibia.com/launcher/` usando una URL de consulta única para evitar información almacenada en caché.
- Compara los archivos locales del launcher, el cliente y los recursos con los hashes de los manifiestos.
- Descarga únicamente los archivos que requieren reemplazo y verifica su tamaño y SHA-256, antes y después de descomprimirlos.
- Reconoce la envoltura LZMA utilizada por los paquetes de Tibia.
- Comprueba que la versión del servidor no haya cambiado durante la descarga.
- Crea un respaldo antes de escribir en la instalación y verifica los archivos reemplazados.

Los archivos se obtienen directamente del servidor oficial. **Este repositorio y sus Releases no distribuyen archivos del juego, DLL de Tibia ni copias de instalaciones ajenas.**

## Datos que se conservan

El reparador excluye de la reparación las carpetas `conf`, `minimap`, `characterdata`, `screenshots`, `log` y `cache`. Esto conserva las configuraciones, mapas, datos de personajes y capturas almacenados allí. También omite archivos auxiliares oficiales dentro de esas carpetas, como `conf/gpublacklist.json`.

No solicita tu cuenta o contraseña. No automatiza acciones dentro del juego ni incorpora cambios propios al código de los archivos oficiales.

## Respaldos y restauración

El respaldo se guarda **junto a la carpeta de instalación**, con un nombre como:

```text
Tibia-respaldo-AAAAMMDD-HHMMSS-identificador
```

Incluye los archivos que van a reemplazarse y un registro `restore.json`. La ruta exacta aparece en la terminal. Consérvalo hasta comprobar que Tibia funciona correctamente.

Para restaurar, cierra Tibia y ejecuta desde PowerShell, sustituyendo la ruta por la del respaldo:

```powershell
& '.\S-Repair for Tibia.exe' --restore 'C:\ruta\Tibia-respaldo-AAAAMMDD-HHMMSS-identificador'
```

Si la instalación está en otra ubicación, puedes indicarla con `--root`:

```powershell
& '.\S-Repair for Tibia.exe' --root 'D:\Juegos\Tibia' --restore 'D:\Juegos\Tibia-respaldo-AAAAMMDD-HHMMSS-identificador'
```

## Compatibilidad

| Sistema | Estado de esta versión |
| --- | --- |
| Windows 11 x64 | Recomendado; pruebas locales en un equipo. |
| Windows 10 x64 | Compatibilidad prevista, pendiente de pruebas en ese sistema. |
| Windows 7, 8 y 8.1 | No compatibles con esta compilación. |
| Windows de 32 bits | No compatible con el ejecutable x64. |
| Windows ARM, Linux y macOS | No validados ni cubiertos por esta versión. |

La compilación publicada incluye Python 3.14, que admite [Windows 10 o posterior](https://docs.python.org/3.14/using/windows.html#supported-windows-versions). Se requiere una instalación de Tibia y conexión HTTPS al servidor oficial. El programa utiliza Windows PowerShell y CIM para consultar los nombres y rutas de los procesos y detectar si Tibia sigue abierto.

## BattlEye, firma y antivirus

**Esta herramienta es independiente y no cuenta con aprobación ni afiliación de CipSoft o BattlEye.** Restaura copias oficiales verificadas por hash con el juego cerrado; no modifica la memoria del juego ni desactiva BattlEye. No se garantiza la ausencia de bloqueos, incompatibilidades o falsos positivos.

BattlEye contempla verificar o reinstalar archivos del juego para solucionar errores de integridad en su [FAQ oficial](https://www.battleye.com/support/faq/). Esto no constituye una aprobación de este reparador. Consulta también la [regla 3b de Tibia](https://www.tibia.com/support/?rule=3b&subtopic=tibiarules).

**El ejecutable de esta versión no tiene firma digital Authenticode.** “S. Tensen” es el crédito de autor en la interfaz y los metadatos; no es un certificado digital. Windows o un antivirus pueden mostrar avisos. No es necesario desactivar el antivirus para el funcionamiento previsto del programa. Si aparece una detección, verifica el archivo y solicita su revisión al fabricante; Microsoft dispone de un [portal para reportar falsos positivos](https://www.microsoft.com/en-us/wdsi/filesubmission).

## Ejecutar desde el código fuente

Requiere Windows y Python **3.11 o posterior**, sin bibliotecas de terceros para la ejecución del reparador.

```powershell
python .\src\srepair.py --repair
```

El código fuente sin argumentos realiza un diagnóstico; el `.exe` abierto con doble clic muestra la bienvenida y solicita confirmación para reparar.

Opciones disponibles:

```powershell
# Diagnóstico local, sin modificar la instalación
& '.\S-Repair for Tibia.exe' --diagnose

# Descargar, descomprimir y verificar en una carpeta temporal, sin instalar
& '.\S-Repair for Tibia.exe' --verify-downloads

# Elegir la instalación y solicitar confirmación para reparar
& '.\S-Repair for Tibia.exe' --root 'D:\Juegos\Tibia' --repair
```

## Compilar el ejecutable

Usa Windows x64 con Python 3.11 o posterior. Para reproducir la combinación de herramientas utilizada en esta versión, usa Python **3.14.3 x64** y PyInstaller **6.22.3**. No se garantiza una compilación idéntica byte por byte.

Desde la raíz del repositorio:

```powershell
.\build.ps1
```

El script crea `.venv`, instala las dependencias de `requirements-build.txt` y genera un único ejecutable en `dist\S-Repair for Tibia.exe`, sin UPX. No firma digitalmente el resultado. Si PowerShell restringe los scripts en tu equipo, sigue la política de ejecución aprobada para ese entorno.

## Pruebas

```powershell
python .\tests\test_repair.py
```

Las pruebas usan archivos temporales y descargas simuladas; no necesitan una instalación real de Tibia, no descargan archivos del juego y no modifican tu instalación. Cubren rutas alternativas, confirmación y cancelación, espera del cierre del juego, progreso, hashes, descompresión, respaldo, restauración y rechazo de rutas protegidas o descargas corruptas.

## Estructura

```text
src/srepair.py                 Reparador e interfaz de terminal
tests/test_repair.py           Pruebas con archivos temporales
packaging/windows-version.txt  Nombre, autor y versión de Windows
requirements-build.txt         Herramientas de compilación
build.ps1                      Compilación del ejecutable
```

## Autor y derechos

Autor: **S. Tensen**. Copyright (c) 2026 S. Tensen.

Licencia del proyecto: pendiente de definir. Tibia y BattlEye pertenecen a sus respectivos titulares.
