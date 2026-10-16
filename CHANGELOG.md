# Changelog

All notable changes to this repository. Dates are `YYYY-MM-DD`.

The versions here are **the repository's**, not the package's. The package version is whatever you
pass to `empaquetar_uwp.ps1 -Version`, and it has to go up on every package you install.

## [1.0.0] — 2026-10-13

First publication. The recipe for the UWP port, as it was applied to the build that runs — and is
played with a controller — on a real Xbox Series X.

### Added

- **`tools/acgc_parches.py`** — thirteen idempotent patches, including the one that mattered most:
  the game's alignment macro was being silently discarded, because clang targeting the MSVC ABI does
  not define `__GNUC__` and `__declspec(align())` is ignored where that macro sits.
- **`tools/construir_uwp.py`** — the translator: it reads the desktop build's own `ninja` commands
  and re-runs them in the console's dialect, so the recipe does not need a second CMake project and
  survives the upstream adding files.
- **`tools/empaquetar_uwp.ps1`** — layout, `makeappx` and `signtool`.
- **`src/uwp/main.cpp`** and **`src/compat/`** — the WinRT entry point and three headers MSVC does
  not ship.
- **Documentation in both languages**, with the eighteen stumbles and how each was measured rather
  than guessed — including the `GL_OUT_OF_MEMORY` that was not about memory at all.

### Fixed, relative to the tooling this came from

- **The packager's version regex no longer rewrites the manifest's `MinVersion`s.** The old pattern
  matched `Version="…"` anywhere, so it also replaced `TargetDeviceFamily`'s and the VCLibs
  dependency's minimum versions with the package version. It never blocked an install — the console
  has higher versions of both — but the installed manifest stopped requiring what the template
  intends.

### Not included, on purpose

- The disc, the game data, the executable, the `.msix`, the saves and the package tiles.
- The UWP libraries (Mesa, SDL2, `libuwp`): other people's binaries. The guide says where to get
  them, and **which Mesa**, which is not a detail here.
