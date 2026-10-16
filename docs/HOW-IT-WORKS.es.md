# Cómo funciona, y por qué cada parche está ahí

*(English: [HOW-IT-WORKS.md](HOW-IT-WORKS.md))*

## El método: traducir la compilación, no mantener otra

La decompilación de *Animal Crossing* se compila para PC con GCC desde un `ninja` generado. Llevar
eso a una consola tiene dos caminos: escribir un segundo proyecto de CMake para `WindowsStore` —y
mantenerlo al día cada vez que el proyecto de arriba añade un archivo— o **traducir la compilación
que ya existe**.

Este port hace lo segundo, igual que el de *Diddy Kong Racing*: `construir_uwp.py` ejecuta
`ninja -t commands` sobre la build de escritorio, toma las 3 997 órdenes de compilación, las
reescribe —clang con ABI de MSVC en vez de GCC, el CRT «store», las cabeceras de la consola— y las
vuelve a ejecutar. Después enlaza con `ld.lld` y `/APPCONTAINER`.

La ventaja no es la elegancia: es que **un archivo nuevo del proyecto de arriba aparece solo**, sin
que haya que tocar nada aquí.

## El fallo gordo: la alineación que se tiraba a la basura

**El síntoma**: una tormenta de `OSPanic … address not 32Byte aligned` en la consola, que en el
escritorio **no aparece ni una sola vez**.

Se midió en vez de suponerlo. Instrumentando la comprobación, la dirección estaba alineada a 16 y el
tamaño era correcto. Con el **mapa del enlazador** se identificó la variable culpable: un buffer
declarado con la macro de alineación del juego, pidiendo 32… y no teniéndolos.

**La causa** está en cómo el árbol elige la sintaxis de esa macro:

```c
#ifdef __GNUC__
#define ATTRIBUTE_ALIGN(num) __attribute__((aligned(num)))
#elif defined(_MSC_VER)
#define ATTRIBUTE_ALIGN(num) __declspec(align(num))
```

Clang con ABI de MSVC **no define `__GNUC__`** (define `_MSC_VER` y `__clang__`), así que caía en la
rama del `__declspec`. Y en la sintaxis de MSVC, `__declspec` tiene que ir **delante** de la
declaración; donde esa macro se usa va **detrás** del declarador, y ahí se ignora **en silencio**.
Resultado: *todas* las alineaciones que pide el juego se estaban descartando.

⚠ **Y el primer arreglo fue el equivocado**, que es lo que hace esto digno de contarse: cambiar la
rama de `_MSC_VER` no movió el buffer **ni un byte**. Lo que funciona es que la rama del atributo de
GCC **reconozca también a clang**, porque clang acepta los atributos de GCC aunque esté emulando el
ABI de MSVC, y ese sí vale detrás del declarador. Además, la macro está definida **dos veces** en el
árbol y hubo que tocar las dos; cuál ganaba se comprobó con `clang -E -dM`, no a ojo.

Con eso, el buffer pasó a una dirección múltiplo de 32 y **el archivo de errores de la consola quedó
en 0 bytes**.

De regalo, un fallo latente del propio lane de PC: la ARAM emulada salía de un `malloc` normal
—16 bytes garantizados— cuando el sistema que la usa exige 32. En el escritorio caía bien de
casualidad. Ahora se pide alineada. ⚠ Y hay que **incluir `<malloc.h>`**: sin él la función se
declara implícita, el compilador asume que devuelve `int` y **el puntero de 64 bits se trunca**, sin
un solo aviso.

## El segundo gordo: `GL_OUT_OF_MEMORY` sin falta de memoria

Con todo lo anterior resuelto, el juego arrancaba limpio y moría hacia el fotograma 200 dentro de
Mesa.

Lo primero fue **descartar lo que no era**, con medidas y no con conjeturas:

| Se sospechó | Medida | Veredicto |
|---|---|---|
| Falta de memoria | `GlobalMemoryStatusEx` en cada punto | **4 982 MB libres de 5 120**, carga del 2 % |
| GPU reiniciada (TDR) | `glGetGraphicsResetStatus` | **0**, sin reinicio |
| vsync, tamaño de ventana, redimensionado, presentar deprisa | uno a uno | sigue rompiendo |

Lo que lo encontró fue **sembrar sondas** por el arranque: cada punto intenta crear la misma textura
pequeña y dice SANO o ROTO. El corte quedó entre dos líneas consecutivas: sano después de procesar
eventos, **roto justo después de presentar**. Y presentar no es más que `SDL_GL_SwapWindow`.

**La causa: presentar durante los primeros fotogramas del arranque.** Lo único que cambia el
resultado es cuántos presentados se hacen al principio, así que el arreglo es saltárselos.

Antes de llegar ahí hubo otra parada: una violación de acceso dentro de Mesa que **desapareció al
cambiar la versión de Mesa**. Es la tercera vez que Mesa decide en este catálogo, y la regla ya está
escrita: **probar primero el Mesa que ya funciona en la consola**.

## Los demás, que son el peaje de todo port UWP

| | Qué pasa |
|---|---|
| Tres cabeceras que MSVC no tiene | `dirent.h`, `strings.h` y `unistd.h`. Van en `src/compat/`, escritas para esto |
| `_m_prefetch` | No existe con el ABI de MSVC |
| `strdup` | No está en el CRT «store» |
| El ABI de MSVC **sí decora** los nombres de las variables globales | Y el juego las declara desde ensamblador esperando que no |
| `__forceinline` **no es** `always_inline` | Y el árbol asume que sí |
| Las rutas relativas y el directorio de trabajo | El driver de vídeo de WinRT cambia el directorio de trabajo al de instalación, que es de solo lectura |
| El juego tiraba su propio diagnóstico a `NUL` | Hasta que eso se arregló, los fallos de arriba eran invisibles |
| `Language="x-generate"` | No vale en un manifiesto hecho a mano: `0x80070057` al registrar |
| El CRT de C++ dentro del paquete | `0x8027025B` al activar. Va como **dependencia** |

## Lo que no está resuelto

- **La suspensión del modo desarrollador**: al volver de Home el juego empieza de nuevo.
- El paquete con los mosaicos definitivos se construyó pero no llegó a instalarse en la consola: lo
  jugado y probado fue la versión anterior, idéntica salvo las imágenes.
