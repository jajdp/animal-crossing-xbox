# Animal Crossing on Xbox — the UWP port

How to take the PC port of *Animal Crossing* (GameCube, 2001) — the 64-bit fork
[`birabittoh/ACGC-PC-Port`](https://github.com/birabittoh/ACGC-PC-Port), on top of
[ACreTeam](https://github.com/ACreTeam/ac-decomp)'s decompilation — and run it **on an Xbox Series
in Developer Mode**, as a UWP package you build and sign yourself.

*(Español: [README.es.md](README.es.md))*

It is not a theory: the game boots, reaches the town at 1920×1080 and **plays with a controller**,
with its saves in the package's `LocalState`.

## What this repository is

**A recipe and the tools that apply it.** The method is the same one used for the *Diddy Kong
Racing* port, and it is what makes this maintainable: instead of writing a second CMake project for
the console, **the desktop build is translated**. `construir_uwp.py` asks `ninja` for the desktop
tree's commands — 3 997 objects — rewrites them into the console's dialect (clang with the MSVC ABI,
the "store" CRT, `/APPCONTAINER`) and runs them again. A file upstream adds shows up on its own.

| Piece | What it is |
|---|---|
| `tools/acgc_parches.py` | Thirteen idempotent patches. Eleven are files clang will not take as they are — the PC tree builds with GCC and `-fpermissive` — and the rest is the console profile |
| `tools/construir_uwp.py` | The translator: reads the desktop `ninja`'s commands and compiles and links for UWP |
| `tools/empaquetar_uwp.ps1` | The layout, `makeappx` and `signtool` |
| `src/uwp/main.cpp` | The WinRT entry point, which hands the thread to SDL |
| `src/compat/` | Three headers MSVC does not have (`dirent.h`, `strings.h`, `unistd.h`) |
| `package/` | The manifest, with `CHANGE-ME` where your identity goes |

## What it is not

There is no **disc, no game data, no executable, no `.msix`, no tiles and none of the UWP
libraries** (Mesa, SDL2, `libuwp`) here — those are other people's binaries. You need your own dump
and the fork building on your PC first. See [`NOTICE.md`](NOTICE.md).

## What you need first

| | |
|---|---|
| The 64-bit fork | [`birabittoh/ACGC-PC-Port`](https://github.com/birabittoh/ACGC-PC-Port), **building on your PC first** (its desktop build is the input to everything) |
| Your own dump | Of your copy of *Animal Crossing* for GameCube |
| MSYS2 | For the fork's desktop build (CMake, ninja and GCC) |
| llvm-mingw | clang and `ld.lld` with the MSVC ABI: that is what builds for the console |
| Visual Studio 2022 | With the **C++ UWP component**: its `store` environment is needed, plus `makeappx`/`signtool` from the Windows SDK |
| The UWP bundle | SDL2, Mesa and `libuwp` built for UWP: [`worleydl/uwp-dep`](https://github.com/worleydl/uwp-dep). ⚠ **Mesa's version matters** (see below) |
| Python 3, an Xbox in Developer Mode and a certificate | The scripts, the console, and signing |

## How it goes

```powershell
# 1. patch your clone of the fork (idempotent)
python tools\acgc_parches.py C:\ac\ACGC-PC-Port

# 2. build the fork's desktop build (with MSYS2), then translate it to UWP
python tools\construir_uwp.py --raiz C:\ac\ACGC-PC-Port

# 3. package and sign
powershell -ExecutionPolicy Bypass -File tools\empaquetar_uwp.ps1 -Version 1.0.0.0 -Certificado <thumbprint>
```

Step by step, including the console side: **[`docs/INSTALL.md`](docs/INSTALL.md)**.

## What it had to solve

Eighteen stumbles, and the last three are the ones that carry over to any other game brought down
this road. The detail is in **[`docs/HOW-IT-WORKS.md`](docs/HOW-IT-WORKS.md)**.

| | Symptom | Cause |
|---|---|---|
| 1 | A storm of `address not 32Byte aligned` that on the PC **never appears once** | **The big one.** The game's alignment macro picks its branch on `__GNUC__`, which clang targeting the MSVC ABI does not define, so it fell into the `__declspec` branch — which in that syntax goes **before** the declaration, and there it sat after the declarator, silently ignored. **Every** alignment the game asks for was being thrown away |
| 2 | The first fix for that **did not move the buffer one byte** | Putting `__declspec(align())` where it already was changes nothing: what works is making the GCC-attribute branch recognise clang too, which accepts GCC attributes even while emulating the MSVC ABI. And the macro is defined **twice** in the tree |
| 3 | Dies around frame 200 inside Mesa, with `GL_OUT_OF_MEMORY` | **It was not memory**: 4 982 MB of 5 120 were free. It is presenting during the first frames of startup. Found by bisection, seeding probes: `SANO` all the way to `pc_platform_swap_buffers`, `ROTO` right after. Skipping the first presents fixes it |
| 4 | Before that, an access violation inside Mesa | **It was Mesa's version.** With 25.2.6 it goes away. That is this catalogue's rule: try the Mesa that already works on the console first |
| 5 | Installs, and activation fails with `0x8027025B` | The C++ CRT goes as a package **dependency**, never inside the package |
| 6 | `0x80070057` registering the package | `Language="x-generate"` is not valid in a hand-written manifest: that token is substituted by Visual Studio |
| 7 | Nine more, while compiling | Three headers MSVC does not have, `_m_prefetch`, `strdup` outside the "store" CRT, global variable names the MSVC ABI **does** decorate, `__forceinline` not being `always_inline`, relative paths and the working directory, and the game's own diagnostics going to `NUL` |

## Credits and license

Port and tooling by **Recompilaciones**. Released under the [MIT](LICENSE), which is the license of
the fork's port layer (© 2026 FlyingMeta); ACreTeam's decompilation that all of this comes from is
**CC0** (public domain).

*Animal Crossing* is © Nintendo. This project is not affiliated with Nintendo, with Microsoft, or
with the authors of the decompilation or the PC port, and distributes nothing that belongs to them.
The detail is in [`NOTICE.md`](NOTICE.md). Rights holders: **jajdpmail@gmail.com**.
