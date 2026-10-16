# -*- coding: utf-8 -*-
"""Construye AnimalCrossing.exe para Xbox Series X (UWP, AppContainer).

EL METODO, que es el de Diddy Kong Racing y Sonic Advance: no se reimplementa la
build. Se toma la build de escritorio que YA FUNCIONA (CMake + ninja + gcc de 64
bits), se le piden sus ordenes reales y se traduce cada una a clang con ABI de
MSVC. Lo que compila en el escritorio compila aqui, con las mismas banderas y los
mismos includes; lo unico que cambia es el compilador, el CRT y el enlazador.

POR QUE CLANG Y NO MSVC: el codigo del decomp usa extensiones de GCC que el front
end de C de MSVC no tiene. Y por que no GCC: un paquete de la consola exige el ABI
de MSVC. Clang da las dos cosas a la vez.

REQUISITOS
  1. La build de escritorio configurada y compilada en acgc-64\\pc\\build
     (de ahi salen la lista de archivos y sus banderas).
  2. Los parches de herramientas\\acgc_parches.py aplicados.
  3. Visual Studio 2022 con las bibliotecas «store» (vcvarsall x64 store).

USO
    python construir_uwp.py            compila lo que falte y enlaza
    python construir_uwp.py --rehacer  recompila TODO (obligatorio si se toco
                                       una cabecera o una bandera -D)
    python construir_uwp.py --limpiar  borra los objetos y empieza de cero
"""
import io
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

XBOX = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAIZ = os.path.join(XBOX, "acgc-64")
BUILD_PC = os.path.join(RAIZ, "pc", "build")
SALIDA = os.path.join(XBOX, "build-uwp")
OBJ = os.path.join(SALIDA, "obj")
COMPAT = os.path.join(XBOX, "fuentes", "compat")
FUENTES_UWP = os.path.join(XBOX, "fuentes", "uwp")
DEP = os.path.join(XBOX, "uwp-dep")

# Las tres rutas que esto necesita vienen por variable de entorno (docs/INSTALL.es.md §2):
#
#   ACGC_TOOLKIT   el llvm-mingw con clang y ld.lld (ABI de MSVC)
#   ACGC_MSYS      el MSYS2 que compila la build de escritorio del fork (su bash.exe)
#
# Visual Studio se busca con vswhere: fijar la ruta a una version es la forma mas rapida de que
# esto deje de funcionar en la maquina de al lado.
def _entorno(nombre, que):
    import os
    v = os.environ.get(nombre)
    if not v:
        raise SystemExit('falta la variable de entorno %s (%s). docs/INSTALL.es.md §2.'
                         % (nombre, que))
    if not Path(v).exists():
        raise SystemExit('%s apunta a algo que no existe: %s' % (nombre, v))
    return v


def _vcvarsall():
    import subprocess
    vswhere = Path(r'C:\Program Files (x86)\Microsoft Visual Studio\Installer\vswhere.exe')
    if vswhere.is_file():
        r = subprocess.run([str(vswhere), '-latest', '-property', 'installationPath'],
                           capture_output=True, text=True)
        if r.stdout.strip():
            cand = Path(r.stdout.strip()) / 'VC/Auxiliary/Build/vcvarsall.bat'
            if cand.is_file():
                return str(cand)
    raise SystemExit('no encuentro vcvarsall.bat: hace falta Visual Studio con el componente de '
                     'UWP para C++ (docs/INSTALL.es.md §1)')


TOOLKIT = _entorno('ACGC_TOOLKIT', 'el llvm-mingw con clang y ld.lld')
MSYS_BASH = str(Path(_entorno('ACGC_MSYS', 'el MSYS2 que compila la build de escritorio'))
                / 'usr' / 'bin' / 'bash.exe')
VCVARSALL = _vcvarsall()

# Avisos que clang moderno subio a error y que este decomp dispara a montones.
# No se toca el codigo: GCC los deja pasar y el lane de PC lleva anos con ellos.
SUAVES = ["-Wno-implicit-int", "-Wno-implicit-function-declaration",
          "-Wno-incompatible-pointer-types", "-Wno-int-conversion",
          "-Wno-incompatible-function-pointer-types", "-fno-builtin"]
SUAVES_CXX = ["-Wno-register", "-Wno-c++11-narrowing", "-Wno-writable-strings"]

# __PRFCHWINTRIN_H: SDL2 declara _m_prefetch «hasta que arreglen clang 11» y en
# clang 22 ya es un builtin, asi que choca. Se define la guarda de la cabecera de
# clang para que gane la de SDL. Misma trampa que en Diddy Kong Racing; ahi se
# probo incluir <intrin.h> entero y fue PEOR (rompio seis archivos mas).
# strdup: el CRT «store» no lo exporta (la cabecera lo declara dllimport y la
# biblioteca no lo tiene). El nombre con guion bajo, que es el oficial de MSVC, si
# esta. Ningun archivo del arbol DEFINE una funcion llamada strdup, asi que
# renombrarla en el preprocesador es seguro.
# PC_GL_DEBUG lo trae el propio port: hace que PC_GL_CHECK informe de cada error
# de OpenGL con archivo y linea. Es el mejor instrumento disponible y no hay que
# escribir nada. Se deja puesto mientras dure el diagnostico del lane Xbox.
DEFINES_UWP = ["-DACGC_UWP", "-D__PRFCHWINTRIN_H", "-D_MT", "-D_DLL", "-Dstrdup=_strdup",
               "-DPC_GL_DEBUG"]

LIBS_SISTEMA = ["WindowsApp.lib", "OneCore.lib", "ntdll.lib", "ws2_32.lib",
                "msvcrt.lib", "msvcprt.lib", "vcruntime.lib", "ucrt.lib"]


def entorno_store():
    bat = os.path.join(SALIDA, "_env.bat")
    os.makedirs(SALIDA, exist_ok=True)
    io.open(bat, "w", encoding="utf-8").write(
        '@echo off\r\ncall "%s" x64 store >nul 2>&1\r\nset\r\n' % VCVARSALL)
    out = subprocess.run(["cmd", "/c", bat], capture_output=True, text=True,
                         errors="replace").stdout
    env = dict(os.environ)
    for linea in out.splitlines():
        if "=" in linea:
            k, v = linea.split("=", 1)
            env[k] = v
    if "INCLUDE" not in env or "store" not in env.get("LIB", ""):
        raise SystemExit("ERROR: no se cargo el entorno «store» de Visual Studio")
    return env


def win_split(s):
    """Tokeniza respetando comillas en cualquier posicion (shlex no lo hace)."""
    out, cur, dentro, vivo = [], [], False, False
    for ch in s:
        if ch == '"':
            dentro = not dentro
            vivo = True
        elif ch.isspace() and not dentro:
            if cur or vivo:
                out.append("".join(cur))
            cur, vivo = [], False
        else:
            cur.append(ch)
            vivo = True
    if cur or vivo:
        out.append("".join(cur))
    return out


def ordenes_de_la_build_pc():
    posix = BUILD_PC.replace("\\", "/").replace("H:/", "/h/")
    r = subprocess.run(
        [MSYS_BASH, "-lc",
         "export MSYSTEM=UCRT64; source /etc/profile; cd '%s' && ninja -t commands" % posix],
        capture_output=True, text=True, errors="replace")
    if r.returncode != 0:
        raise SystemExit("ERROR: no pude leer las ordenes de la build de escritorio.\n" + r.stderr[:500])
    return [l for l in r.stdout.splitlines() if ".obj" in l and " -c " in l]


def traduce(cmd):
    partes = win_split(cmd)
    if not partes:
        return None, None, None
    es_cxx = partes[0].endswith("c++.exe")
    argv = [CLANGXX if es_cxx else CLANG, "--target=x86_64-pc-windows-msvc"]
    argv += SUAVES + (SUAVES_CXX if es_cxx else []) + DEFINES_UWP
    # compat\ primero: aporta dirent.h, strings.h y unistd.h, que MSVC no trae
    argv += ["-I", COMPAT, "-isystem", os.path.join(DEP, "include"),
             "-isystem", os.path.join(DEP, "include", "SDL2")]
    src = obj = None
    i = 1
    while i < len(partes):
        p = partes[i]
        if p in ("-MT", "-MF"):
            i += 2
            continue
        if p == "-o":
            obj = partes[i + 1]
            i += 2
            continue
        if p == "-c":
            src = partes[i + 1]
            i += 2
            continue
        if p in ("-MD", "-fpermissive"):
            i += 1
            continue
        if p == "-isystem":
            # el SDL2 de MSYS2 se sustituye por el de la consola (ya anadido arriba)
            if "SDL2" not in partes[i + 1]:
                argv += ["-isystem", partes[i + 1]]
            i += 2
            continue
        argv.append(p)
        i += 1
    if src is None:
        return None, None, None
    # El main() del juego pasa a llamarse acgc_game_main: en UWP el main de verdad
    # lo pone SDL_WinRTRunApp desde fuentes\uwp\main.cpp.
    if src.replace("\\", "/").endswith("pc/src/pc_main.c"):
        argv.append("-Dmain=acgc_game_main")
    destino = os.path.join(OBJ, obj.replace("/", os.sep).replace("CMakeFiles" + os.sep, ""))
    argv += ["-c", src, "-o", destino]
    return argv, src, destino


def compila(trabajos, env, rehacer=False):
    """Compila lo que falte.

    ⚠ El salto por fecha mira SOLO el .c, no sus cabeceras ni las banderas: aqui
    no hay seguimiento de dependencias (la build de escritorio si lo tiene, con
    -MD). Si se parchea una cabecera o cambian los -D, hay que pasar --rehacer, o
    el enlace fallara con simbolos viejos y se pierde media hora buscando por que.
    """
    fallos = []
    hechos = [0]
    t0 = time.time()

    def uno(t):
        argv, src, destino = t
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        if (not rehacer and os.path.exists(destino)
                and os.path.getmtime(destino) > os.path.getmtime(src)):
            return None
        r = subprocess.run(argv, capture_output=True, text=True, errors="replace", env=env)
        if r.returncode != 0:
            return (src, r.stderr)
        return None

    with ThreadPoolExecutor(max_workers=16) as ex:
        for res in ex.map(uno, trabajos):
            hechos[0] += 1
            if hechos[0] % 400 == 0:
                print("  ...%d/%d (%.0f s), fallos: %d" % (hechos[0], len(trabajos), time.time() - t0, len(fallos)))
                sys.stdout.flush()
            if res:
                fallos.append(res)
    return fallos


def compila_envoltorio(env):
    """fuentes\\uwp\\main.cpp: el punto de entrada WinRT.

    Dos banderas que solo lleva ESTE archivo, y ninguna es opcional:

    - `-DWINAPI_FAMILY=WINAPI_FAMILY_APP` (2). SDL declara SDL_WinRTRunApp dentro
      de `#ifdef __WINRT__`, y ese simbolo lo pone SDL_platform.h solo si la
      familia de API es de aplicacion. Sin esto el enlace se queda sin punto de
      entrada. NO se le pone al juego: cambiaria las cabeceras de Windows bajo
      sus 3997 archivos, que compilan tal cual.
    - `-std=c++20`. C++/WinRT incluye <experimental/coroutine>, que con clang
      corta la compilacion con un #error y remite al <coroutine> de C++20.
    """
    destino = os.path.join(OBJ, "uwp_main.obj")
    argv = [CLANGXX, "--target=x86_64-pc-windows-msvc", "-std=c++20",
            "-DWINAPI_FAMILY=WINAPI_FAMILY_APP",
            "-fno-strict-aliasing", "-w"] + DEFINES_UWP
    argv += ["-isystem", os.path.join(DEP, "include"),
             "-isystem", os.path.join(DEP, "include", "SDL2"),
             "-c", os.path.join(FUENTES_UWP, "main.cpp"), "-o", destino]
    r = subprocess.run(argv, capture_output=True, text=True, errors="replace", env=env)
    if r.returncode != 0:
        print(r.stderr[:4000])
        raise SystemExit("ERROR: no compila el envoltorio WinRT")
    return destino


def enlaza(objetos, env):
    exe = os.path.join(SALIDA, "AnimalCrossing.exe")
    rsp = os.path.join(SALIDA, "enlace.rsp")
    lineas = ['"%s"' % o for o in objetos]
    lineas += ['"%s"' % os.path.join(DEP, "lib", l) for l in ("SDL2.lib", "libuwp.lib")]
    lineas += LIBS_SISTEMA
    io.open(rsp, "w", encoding="utf-8").write("\n".join(lineas))

    # /subsystem:windows,10.0 NO es cosmetico: un AppContainer exige version de
    # subsistema >= 6.2 en la cabecera PE. lld pone 6.0 por defecto y el activador
    # de la consola responde 0x8027025B sin mas explicacion.
    cmd = [LLD, "-flavor", "link", "/nologo", "/machine:x64",
           "/subsystem:windows,10.0", "/appcontainer",
           "/dynamicbase", "/nxcompat", "/largeaddressaware", "/opt:ref", "/opt:icf",
           "/nodefaultlib:libcmt", "/nodefaultlib:libcpmt",
           "/nodefaultlib:libvcruntime", "/nodefaultlib:libucrt",
           "/libpath:%s" % os.path.join(DEP, "lib"),
           "/map:%s" % os.path.join(SALIDA, "AnimalCrossing.map"),
           "/out:%s" % exe, "@%s" % rsp]
    t0 = time.time()
    p = subprocess.run(cmd, capture_output=True, text=True, errors="replace", env=env)
    err = p.stdout + p.stderr
    io.open(os.path.join(SALIDA, "enlace.log"), "w", encoding="utf-8").write(err)
    faltan = sorted(set(l.split("undefined symbol:", 1)[-1].strip()
                        for l in err.splitlines() if "undefined symbol:" in l))
    print("lld rc=%d en %.1f s; simbolos sin resolver: %d" % (p.returncode, time.time() - t0, len(faltan)))
    for s in faltan[:40]:
        print("   ", s[:150])
    if p.returncode == 0 and os.path.exists(exe):
        print("OK: %s (%s bytes)" % (exe, format(os.path.getsize(exe), ",")))
    elif p.returncode != 0 and not faltan:
        print(err[-3000:])
    return p.returncode


def main():
    if "--limpiar" in sys.argv and os.path.isdir(OBJ):
        print("Para limpiar usa la cuarentena; aqui no se borra nada.")
        return 1
    print("Entorno «store» de Visual Studio...")
    env = entorno_store()
    print("Leyendo las ordenes de la build de escritorio...")
    cmds = ordenes_de_la_build_pc()
    trabajos = [t for t in (traduce(c) for c in cmds) if t[0]]
    print("  %d unidades de compilacion" % len(trabajos))
    print("Compilando con clang (ABI de MSVC)...")
    fallos = compila(trabajos, env, rehacer="--rehacer" in sys.argv)
    print("  fallos de compilacion: %d" % len(fallos))
    if fallos:
        for src, err in fallos[:6]:
            print("  --", src.split("/acgc-64/")[-1])
            for l in err.splitlines():
                if " error: " in l:
                    print("       ", l.split("acgc-64/")[-1][:150])
        io.open(os.path.join(SALIDA, "fallos.txt"), "w", encoding="utf-8").write(
            "\n\n".join("### %s\n%s" % (s, e) for s, e in fallos))
        return 1
    print("Compilando el envoltorio WinRT...")
    envoltorio = compila_envoltorio(env)
    objetos = [t[2] for t in trabajos] + [envoltorio]
    print("Enlazando %d objetos..." % len(objetos))
    return enlaza(objetos, env)


if __name__ == "__main__":
    sys.exit(main())
