# -*- coding: utf-8 -*-
"""Parches del arbol de Animal Crossing para compilarlo con clang (ABI de MSVC).

POR QUE HACEN FALTA. El lane de PC compila con GCC y con -fpermissive. Clang no
tiene -fpermissive y ademas convirtio en error varios avisos que GCC deja pasar.
De los 3997 archivos del arbol, clang acepta 3986 tal cual; estos parches cubren
los 11 que no, y ninguno cambia el comportamiento del juego: son conversiones
explicitas que el compilador antes se inventaba.

Medido el 2026-09-17, no supuesto: la lista sale de compilar el arbol entero con
-fsyntax-only y agrupar los errores.

TODOS SON IDEMPOTENTES: se pueden correr las veces que haga falta.
"""
import io
import os
import re
import sys

# La raiz del arbol del fork, por argumento:
#     python tools/acgc_parches.py <ruta del clon de ACGC-PC-Port>
_libres = [a for a in sys.argv[1:] if not a.startswith("-")]
if not _libres:
    sys.exit("uso: acgc_parches.py <ruta del clon de birabittoh/ACGC-PC-Port>")
RAIZ = os.path.abspath(_libres[0])
for _sena in ("pc", os.path.join("src", "static")):
    if not os.path.exists(os.path.join(RAIZ, _sena)):
        sys.exit("no es la raiz del fork (falta %s): %s\n"
                 "Clonalo de https://github.com/birabittoh/ACGC-PC-Port (docs/INSTALL.es.md §2)."
                 % (_sena, RAIZ))


def leer(rel):
    with io.open(os.path.join(RAIZ, rel), encoding="utf-8", errors="surrogateescape") as f:
        return f.read()


def escribir(rel, texto):
    with io.open(os.path.join(RAIZ, rel), "w", encoding="utf-8", errors="surrogateescape", newline="") as f:
        f.write(texto)


def parche(rel, fn):
    antes = leer(rel)
    despues = fn(antes)
    if antes == despues:
        print("  = %s (ya estaba)" % rel)
        return 0
    escribir(rel, despues)
    print("  + %s" % rel)
    return 1


# ---------------------------------------------------------------- 1. vu32
def p_padclamp(s):
    """`vu32` no se resuelve en dsp.h.

    dsp.h vive en include/dolphin/ y hace #include "types.h", que por la regla de
    la comilla resuelve al types.h de SU carpeta —include/dolphin/types.h—, y ese
    no define vu32; el bueno es include/types.h. Se incluye el bueno desde
    Padclamp.c, donde la comilla si resuelve por -I include porque en su carpeta
    no hay ningun types.h.
    """
    if '#include "types.h"' in s:
        return s
    return '#include "types.h"\n' + s


# ---------------------------------------------------------------- 2. operator new
def p_jkrheap(s):
    """El .cpp define operator new(u32) y la cabecera lo declara con size_t.

    En 32 bits coincidian; en 64 bits size_t son 8 bytes y clang lo rechaza con
    «'operator new' takes type size_t as 1st parameter», que ademas es lo que
    manda el estandar.
    """
    return re.sub(r"(operator new(?:\[\])?\()u32(\s+byteCount)", r"\1size_t\2", s)


# ---------------------------------------------------------------- 3 y 4. enums
def p_setstate(s):
    """setState(EOF) y seek(x, SEEK_SET): int donde se espera un enum.

    EOF y SEEK_SET son macros de la libc que valen int. GCC con -fpermissive lo
    convierte solo; clang no, y tiene razon. Se hace explicito.
    """
    # setState y clrState toman EIoState; seek y seekPos toman JSUStreamSeekFrom
    s = re.sub(r"\b(setState|clrState)\(EOF\)", r"\1((EIoState)EOF)", s)
    s = re.sub(r"\b(seek|seekPos)\(([^,()]+),\s*(SEEK_SET|SEEK_CUR|SEEK_END)\)",
               r"\1(\2, (JSUStreamSeekFrom)\3)", s)
    # no duplicar el cast si ya estaba
    s = s.replace("(EIoState)(EIoState)", "(EIoState)")
    s = s.replace("(JSUStreamSeekFrom)(JSUStreamSeekFrom)", "(JSUStreamSeekFrom)")
    return s


# ---------------------------------------------------------------- 5. strtol
def p_jutexception(s):
    """strtol sin declarar: falta <stdlib.h>.

    Con MinGW llegaba de rebote por otra cabecera; con las cabeceras de MSVC no.
    """
    if "#include <stdlib.h>" in s:
        return s
    ancla = '#include "MSL_C/MSL_Common/float.h"'
    return s.replace(ancla, ancla + "\n\n#include <stdlib.h>", 1)


# ---------------------------------------------------------------- 6. void*
def p_jsyswrapper(s):
    """Devolver void* como CSDIFileEntry* sin conversion: C++ no lo permite."""
    viejo = "    return JKRGetResourceEntry_byName(root_name, res_name, reinterpret_cast<JKRArchive*>(archive));"
    nuevo = "    return (CSDIFileEntry*)JKRGetResourceEntry_byName(root_name, res_name, reinterpret_cast<JKRArchive*>(archive));"
    if nuevo in s:
        return s
    return s.replace(viejo, nuevo, 1)


# ---------------------------------------------------------------- 7. emu64
def p_emu64(s):
    """Dos asignaciones de int a enum de GX, en codigo anadido por el port."""
    viejo1 = "    this->projection_type = saved_proj_type;"
    nuevo1 = "    this->projection_type = (GXProjectionType)saved_proj_type;"
    if nuevo1 not in s:
        s = s.replace(viejo1, nuevo1, 1)

    viejo2 = "            int mat_src = (this->geometry_mode & G_SHADE) ? GX_SRC_VTX : GX_SRC_REG;"
    nuevo2 = "            GXColorSrc mat_src = (this->geometry_mode & G_SHADE) ? GX_SRC_VTX : GX_SRC_REG;"
    if nuevo2 not in s:
        s = s.replace(viejo2, nuevo2, 1)
    return s


# ---------------------------------------------------------------- 8. fixnes
def p_fixnes_inline(s):
    """`__forceinline` no significa lo mismo que `always_inline`, y eso rompe el enlace.

    fixnes elige entre las dos por `#ifdef _MSC_VER`, y clang con ABI de MSVC
    define _MSC_VER aunque no sea MSVC. La diferencia no es cosmetica:

      - GCC: `__attribute__((always_inline))` sobre una declaracion normal deja la
        funcion con enlace EXTERNO. apu.c la define y quien la llama enlaza.
      - MSVC: `__forceinline` implica `inline`, asi que la definicion de apu.c no
        emite simbolo, y pc_nes_fixnes.c —que solo ve la declaracion— se queda
        llamando a un simbolo que no existe.

    Se arregla dejando la rama de MSVC para MSVC de verdad.
    """
    viejo = "#ifdef _MSC_VER\n#define FIXNES_NOINLINE __declspec(noinline)"
    nuevo = "#if defined(_MSC_VER) && !defined(__clang__)\n#define FIXNES_NOINLINE __declspec(noinline)"
    if nuevo in s:
        return s
    return s.replace(viejo, nuevo, 1)


# ---------------------------------------------------------------- 9. extern "C"
def p_extern_c_arena(s):
    """`arena_memory` se declara en C++ sin extern "C", y en el ABI de MSVC eso importa.

    Diferencia REAL entre los dos ABI, no una manía del compilador: el ABI de
    Itanium (GCC) no decora los nombres de las variables globales, asi que el
    `extern u8* arena_memory;` de un .cpp buscaba «arena_memory» y lo encontraba
    en pc_os.c, que es C. El ABI de MSVC SI las decora, asi que el .cpp pasa a
    buscar «?arena_memory@@3PEAEEA» y no lo encuentra jamas.
    """
    viejo = "extern u8* arena_memory;"
    nuevo = ('#ifdef __cplusplus\nextern "C" u8* arena_memory;\n#else\n'
             "extern u8* arena_memory;\n#endif")
    if 'extern "C" u8* arena_memory;' in s:
        return s
    return s.replace(viejo, nuevo, 1)


# ---------------------------------------------------------------- 10. salida
def p_no_nul(s):
    """El juego tira su propia salida a NUL, y en la consola eso deja ciego.

    `pc_main.c` hace freopen("NUL") sobre stdout y stderr salvo que se arranque
    con --verbose, porque escribir en la terminal de Windows sin buffer hunde los
    fotogramas. En la Xbox no hay terminal: el envoltorio ya ha apuntado stdout a
    LocalState\\salida.txt, que es el UNICO diagnostico disponible, y este freopen
    lo anulaba. Sintoma: salida.txt de 0 bytes y ni una pista de por que muere.
    """
    viejo = """    if (!g_pc_verbose) {
#ifdef _WIN32
        freopen("NUL", "w", stdout);
        freopen("NUL", "w", stderr);"""
    nuevo = """    if (!g_pc_verbose) {
#if defined(ACGC_UWP)
        /* En la consola no hay terminal que frenar, y stdout ya apunta a un
           archivo de LocalState: tirarlo a NUL dejaria el arranque sin
           diagnostico. Ver xbox\\notas-port-uwp.md. */
#elif defined(_WIN32)
        freopen("NUL", "w", stdout);
        freopen("NUL", "w", stderr);"""
    if "defined(ACGC_UWP)" in s:
        return s
    return s.replace(viejo, nuevo, 1)


# ---------------------------------------------------------------- 11. ARAM
def p_aram_alineada(s):
    """La ARAM emulada sale de un malloc normal, y el juego la exige a 32 bytes.

    ESTE ES EL FALLO QUE MATABA EL PORT EN LA CONSOLA, y es un fallo latente del
    lane de PC, no algo que introduzca UWP: la ARAM de GameCube son 16 MB que
    aqui se emulan con `malloc(PC_ARAM_SIZE)`, y JKRAram comprueba que las
    direcciones que se le pasan esten alineadas a 32 bytes
    («:::address not 32Byte aligned»). malloc en x64 solo garantiza 16.

    Que funcione o no depende de con que direccion conteste el asignador: en el
    escritorio (UCRT de MinGW) salio multiplo de 32 y el juego pasa del frame
    1381 sin una queja; con el CRT «store» salio multiplo de 16, y el juego moria
    hacia el frame 200 entre OSPanic. Misma familia que el `ALIGNED(4)` de Sonic
    Advance: el bug estaba ahi desde siempre y solo lo delata cambiar de
    compilador.

    Se pide la alineacion de verdad en vez de confiar en la suerte. No hace falta
    tocar la liberacion: este bloque no se libera nunca.
    """
    if "_aligned_malloc" in s:
        return s
    # ⚠ <malloc.h> NO es decorativo: sin el, _aligned_malloc se declara implicito,
    # el compilador asume que devuelve int y el puntero de 64 bits SE TRUNCA a 32.
    # Con los avisos bajados a silencio eso compila sin una queja y el juego se
    # comporta igual de mal que antes, pero por otro motivo. Costo un ciclo.
    s = s.replace('#include "pc_platform.h"',
                  '#include "pc_platform.h"\n\n#include <malloc.h>  /* _aligned_malloc */', 1)
    viejo = "        aram_base = (u8*)malloc(PC_ARAM_SIZE);"
    nuevo = """#if defined(_MSC_VER)
        /* 32 bytes: lo que comprueba JKRAram. malloc solo promete 16. */
        aram_base = (u8*)_aligned_malloc(PC_ARAM_SIZE, 32);
#elif defined(__STDC_VERSION__) && __STDC_VERSION__ >= 201112L
        aram_base = (u8*)aligned_alloc(32, PC_ARAM_SIZE);
#else
        aram_base = (u8*)malloc(PC_ARAM_SIZE);
#endif"""
    return s.replace(viejo, nuevo, 1)


# ---------------------------------------------------------------- 12. ATTRIBUTE_ALIGN
def p_attribute_align(s):
    """`ATTRIBUTE_ALIGN` se evapora con el ABI de MSVC, y con ella TODAS las
    alineaciones que el juego pide.

    ESTE ERA EL FALLO GORDO DEL PORT. En include/types.h la macro esta definida
    asi:

        #if defined(__MWERKS__) || defined(__GNUC__)
        #define ATTRIBUTE_ALIGN(num) __attribute__((aligned(num)))
        #elif defined(_MSC_VER)
        #define ATTRIBUTE_ALIGN(num)            <-- VACIA

    Clang con ABI de MSVC define _MSC_VER, cae en esa rama, y cada
    `static u8 buff[80] ATTRIBUTE_ALIGN(32);` del juego se queda con la
    alineacion que le apetezca al compilador: 16. El juego lo detecta al primer
    DMA a la ARAM («:::address not 32Byte aligned») y a partir de ahi va tropezando.

    ⚠ Y NO se arregla con `__declspec(align(num))`, que es lo que pone
    dolphin/types.h: en la sintaxis de MSVC el `__declspec` tiene que ir DELANTE
    de la declaracion, y aqui las declaraciones lo llevan DETRAS del declarador
    (`static u8 buff[79] ATTRIBUTE_ALIGN(32);`). Puesto ahi se ignora en silencio
    y el buffer sigue a 16. Se probo, y el sintoma no se movio ni un byte.

    Lo que si funciona: clang acepta los atributos de GCC aunque este emulando el
    ABI de MSVC, y `__attribute__((aligned(num)))` detras del declarador es valido.
    Basta con que la primera rama lo reconozca.

    Es primo hermano del `ALIGNED(4)` de Sonic Advance: alli el atributo estaba
    puesto de menos, aqui desaparecia entero. Tercera alineacion que tumba un
    port en un mes, contando la de la ARAM de aqui al lado.
    """
    viejo = "#if defined(__MWERKS__) || defined(__GNUC__)\n#define ATTRIBUTE_ALIGN(num) __attribute__((aligned(num)))"
    nuevo = ("/* __clang__ va aqui a proposito: con ABI de MSVC, clang define _MSC_VER y\n"
             "   caia en la rama de abajo, donde la macro estaba VACIA y tiraba en\n"
             "   silencio todas las alineaciones del juego. No sirve cambiar esa rama a\n"
             "   __declspec(align(n)): eso solo vale DELANTE de la declaracion y aqui va\n"
             "   detras del declarador. El atributo de GCC si vale detras, y clang lo\n"
             "   entiende siempre. */\n"
             "#if defined(__MWERKS__) || defined(__GNUC__) || defined(__clang__)\n"
             "#define ATTRIBUTE_ALIGN(num) __attribute__((aligned(num)))")
    if "__clang__ va aqui a proposito" in s:
        return s
    # deshacer el intento anterior con __declspec, si quedo puesto
    s = re.sub(r"#elif defined\(_MSC_VER\)\n/\* OJO:.*?\n#define ATTRIBUTE_ALIGN\(num\) __declspec\(align\(num\)\)\n",
               "#elif defined(_MSC_VER)\n#define ATTRIBUTE_ALIGN(num)\n", s, flags=re.S)
    return s.replace(viejo, nuevo, 1)


# ------------------------------------------------- 12b. ATTRIBUTE_ALIGN, el otro
def p_attribute_align_dolphin(s):
    """La MISMA macro, otra vez, en include/dolphin/types.h — y esta es la que gana.

    Hay dos definiciones de ATTRIBUTE_ALIGN en el arbol. La de include/types.h se
    protege con `#ifndef`, pero esta NO, asi que en cada unidad que incluya las
    dos, la ultima en procesarse manda — y es esta.

    Verificado con el preprocesador en vez de a ojo (`clang -E -dM` sobre
    m_string.c): sin tocarla, `ATTRIBUTE_ALIGN` acaba valiendo
    `__declspec(align(num))`, que detras del declarador se ignora. Ese fue el
    motivo de que el primer intento de arreglo no moviera ni un byte la direccion
    del buffer.
    """
    viejo = "#ifdef __GNUC__\n#define ATTRIBUTE_ALIGN(num) __attribute__((aligned(num)))"
    nuevo = ("/* __clang__ aqui tambien: con ABI de MSVC no hay __GNUC__, y el\n"
             "   __declspec de la rama siguiente se ignora porque en este codigo el\n"
             "   atributo va DETRAS del declarador. Comprobado con clang -E -dM. */\n"
             "#if defined(__GNUC__) || defined(__clang__)\n"
             "#define ATTRIBUTE_ALIGN(num) __attribute__((aligned(num)))")
    if "__clang__ aqui tambien" in s:
        return s
    return s.replace(viejo, nuevo, 1)


def main():
    if not os.path.isdir(RAIZ):
        print("no encuentro el arbol en", RAIZ)
        return 1
    print("Parcheando", RAIZ)
    n = 0
    n += parche("src/static/dolphin/pad/Padclamp.c", p_padclamp)
    n += parche("src/static/JSystem/JKernel/JKRHeap.cpp", p_jkrheap)
    n += parche("src/static/JSystem/JSupport/JSUInputStream.cpp", p_setstate)
    n += parche("src/static/JSystem/JKernel/JKRAramStream.cpp", p_setstate)
    n += parche("src/static/JSystem/JUtility/JUTException.cpp", p_jutexception)
    n += parche("src/static/libjsys/jsyswrapper_main.cpp", p_jsyswrapper)
    n += parche("src/static/libforest/emu64/emu64.c", p_emu64)
    n += parche("pc/lib/fixnes/common.h", p_fixnes_inline)
    n += parche("src/static/JSystem/JKernel/JKRHeap.cpp", p_extern_c_arena)
    n += parche("pc/include/pc_gbi_ptr.h", p_extern_c_arena)
    n += parche("pc/src/pc_main.c", p_no_nul)
    n += parche("pc/src/pc_aram.c", p_aram_alineada)
    n += parche("include/types.h", p_attribute_align)
    n += parche("include/dolphin/types.h", p_attribute_align_dolphin)
    print("archivos modificados en esta pasada: %d" % n)
    print()
    print("Lo que NO se parchea aqui, porque se resuelve en la linea de ordenes:")
    print("  - _m_prefetch: lo declara SDL2 «hasta que arreglen clang 11» y en")
    print("    clang 22 ya es un builtin -> se define su guarda __PRFCHWINTRIN_H")
    print("    (misma trampa que en Diddy Kong Racing).")
    print("  - dirent.h / strings.h / unistd.h: no existen en MSVC -> los aporta")
    print("    fuentes\\compat\\ por delante en el orden de busqueda.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
