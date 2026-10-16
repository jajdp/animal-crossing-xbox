# Animal Crossing en la Xbox — el port UWP

Cómo coger el port de PC de *Animal Crossing* (GameCube, 2001) —el fork de 64 bits
[`birabittoh/ACGC-PC-Port`](https://github.com/birabittoh/ACGC-PC-Port), sobre la decompilación de
[ACreTeam](https://github.com/ACreTeam/ac-decomp)— y hacerlo correr **en una Xbox Series en modo
desarrollador**, como un paquete UWP que compilas y firmas tú.

*(English: [README.md](README.md))*

No es una teoría: el juego arranca, llega al pueblo a 1920×1080 y **se juega con mando**, con las
partidas en el `LocalState` del paquete.

## Qué es este repositorio

**Una receta y las herramientas que la aplican.** El método es el mismo que se usó en el port de
*Diddy Kong Racing*, y es lo que hace que esto se pueda mantener: en vez de escribir un segundo
proyecto de CMake para la consola, **se traduce la compilación de escritorio**. `construir_uwp.py`
le pide a `ninja` las órdenes del árbol de PC —3 997 objetos—, las reescribe al dialecto de la
consola (clang con ABI de MSVC, el CRT «store», `/APPCONTAINER`) y las vuelve a ejecutar. Un archivo
que el proyecto de arriba añada aparece solo.

| Pieza | Qué es |
|---|---|
| `tools/acgc_parches.py` | Trece parches idempotentes. Once son archivos que clang no acepta tal cual —el árbol de PC compila con GCC y `-fpermissive`—, y el resto es el perfil de la consola |
| `tools/construir_uwp.py` | El traductor: lee las órdenes del `ninja` de escritorio y compila y enlaza para UWP |
| `tools/empaquetar_uwp.ps1` | El layout, `makeappx` y `signtool` |
| `src/uwp/main.cpp` | El punto de entrada WinRT, que le cede el hilo a SDL |
| `src/compat/` | Tres cabeceras que MSVC no tiene (`dirent.h`, `strings.h`, `unistd.h`) |
| `package/` | El manifiesto, con `CHANGE-ME` donde va tu identidad |

## Qué **no** es

Aquí no hay **disco, ni datos del juego, ni ejecutable, ni paquete `.msix`, ni mosaicos, ni las
bibliotecas de UWP** (Mesa, SDL2, `libuwp`), que son binarios de otros. Necesitas tu propio volcado
y el fork compilando en tu PC antes de empezar. Está detallado en [`NOTICE.es.md`](NOTICE.es.md).

## Qué hace falta antes

| | |
|---|---|
| El fork de 64 bits | [`birabittoh/ACGC-PC-Port`](https://github.com/birabittoh/ACGC-PC-Port), **compilando en tu PC primero** (su build de escritorio es la entrada de todo) |
| Tu propio volcado | De tu copia de *Animal Crossing* de GameCube |
| MSYS2 | Para la build de escritorio del fork (CMake, ninja y GCC) |
| llvm-mingw | clang y `ld.lld` con el ABI de MSVC: con eso se compila para la consola |
| Visual Studio 2022 | Con el componente de **UWP para C++**: hace falta su entorno `store`, y el `makeappx`/`signtool` del Windows SDK |
| El bundle de UWP | SDL2, Mesa y `libuwp` compilados para UWP: [`worleydl/uwp-dep`](https://github.com/worleydl/uwp-dep). ⚠ **La versión de Mesa importa** (ver abajo) |
| Python 3, una Xbox en modo desarrollador y un certificado | Los scripts, la consola y la firma |

## Cómo va

```powershell
# 1. parchear tu clon del fork (idempotente)
python tools\acgc_parches.py C:\ac\ACGC-PC-Port

# 2. compilar la build de escritorio del fork (con el MSYS2), y luego traducirla a UWP
python tools\construir_uwp.py --raiz C:\ac\ACGC-PC-Port

# 3. empaquetar y firmar
powershell -ExecutionPolicy Bypass -File tools\empaquetar_uwp.ps1 -Version 1.0.0.0 -Certificado <huella>
```

Paso a paso, con el lado de la consola: **[`docs/INSTALL.es.md`](docs/INSTALL.es.md)**.

## Qué hubo que resolver

Dieciocho tropiezos, y los tres últimos son los que valen para cualquier otro juego traído por este
camino. El detalle está en **[`docs/HOW-IT-WORKS.es.md`](docs/HOW-IT-WORKS.es.md)**.

| | Síntoma | Causa |
|---|---|---|
| 1 | Una tormenta de `address not 32Byte aligned` que en el PC **no sale ni una vez** | **El fallo gordo.** La macro de alineación del juego elige rama con `__GNUC__`, que clang con ABI de MSVC no define, y caía en la del `__declspec`… que en esa sintaxis va **delante** de la declaración y ahí estaba detrás, donde se ignora en silencio. **Todas** las alineaciones del juego se tiraban a la basura |
| 2 | El primer arreglo de eso **no movió el buffer ni un byte** | Poner `__declspec(align())` donde ya estaba no sirve: lo que funciona es que la rama de GCC reconozca también a clang, que acepta los atributos de GCC aunque emule el ABI de MSVC. Y la macro está definida **dos veces** en el árbol |
| 3 | Muere hacia el fotograma 200 dentro de Mesa, con `GL_OUT_OF_MEMORY` | **No era falta de memoria**: había 4 982 MB libres de 5 120. Es presentar durante los primeros fotogramas del arranque. Se encontró por bisección, sembrando sondas: `SANO` hasta `pc_platform_swap_buffers`, y `ROTO` justo después. Saltarse los primeros presentados lo arregla |
| 4 | Antes de eso, una violación de acceso dentro de Mesa | **Era la versión de Mesa.** Con la 25.2.6 desaparece. Es la regla de este catálogo: probar primero el Mesa que ya funciona en la consola |
| 5 | Se instala y la activación falla con `0x8027025B` | El CRT de C++ va como **dependencia** del paquete, nunca dentro |
| 6 | `0x80070057` al registrar el paquete | `Language="x-generate"` no vale en un manifiesto hecho a mano: ese token lo sustituye Visual Studio |
| 7 | Nueve más, de compilar | Tres cabeceras que MSVC no tiene, `_m_prefetch`, `strdup` fuera del CRT «store», los nombres de variables globales que el ABI de MSVC **sí** decora, `__forceinline` que no es `always_inline`, las rutas relativas y el directorio de trabajo, y el diagnóstico del juego yéndose a `NUL` |

## Créditos y licencia

Port y herramientas de **Recompilaciones**. Publicado bajo la [MIT](LICENSE), que es la licencia de
la capa de port del fork (© 2026 FlyingMeta); la decompilación de ACreTeam de la que todo esto sale
está en **CC0** (dominio público).

*Animal Crossing* es © Nintendo. Este proyecto no está afiliado a Nintendo, ni a Microsoft, ni a los
autores de la decompilación o del port de PC, y no distribuye nada que les pertenezca. El detalle
está en [`NOTICE.es.md`](NOTICE.es.md). Quien tenga derechos puede escribir a
**jajdpmail@gmail.com**.
