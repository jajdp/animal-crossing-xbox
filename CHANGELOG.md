# Changelog

All notable changes to this repository. Dates are `YYYY-MM-DD`.

The versions here are **the repository's**, not the package's. The package version is whatever you
pass to `empaquetar_uwp.ps1 -Version`, and it has to go up on every package you install.

## [1.0.2] — 2026-11-03

### Changed

- **This repository no longer explains itself by pointing at other ports.** A dozen passages
  introduced the method, a trap or a decision as "the same as in such-and-such other port" — in
  the README, in `HOW-IT-WORKS.md`, in `src/uwp/main.cpp`, in both build tools and in the
  manifest's comments. Anyone who came here for *Animal Crossing* had no reason to know those
  ports, and the comparison was never the point: each one carried a fact that reads better stated
  outright. So the method is now described on its own terms; the `<intrin.h>` attempt that made
  things worse is reported as the measurement it is; and the note about activating the
  `CoreWindow` says **what happens when it is missing** — the app is taken for hung and closed
  within seconds, with no dump — instead of where that was learned.
- `tools/empaquetar_uwp.ps1`: the `-Mesa mesa-banjo` option **keeps its name**. It is a parameter
  value and a folder on disk, so renaming it would break the tool for anyone who already has that
  folder; what changed is that its comments now say what the set contains — Mesa 25.1.1 with the
  SDL2 and `libuwp` that shipped with it, which is why it is the only option that replaces those
  two — rather than where it came from.
- **The VCLibs note no longer assumes the framework is already on the console.** It says the
  console has to have it, and that if yours does not, the Device Portal takes dependency packages
  alongside the main one. The old wording was true of the console this was tested on and of
  nobody else's.

Nothing in the recipe or the tools changed behaviour, and that was checked: the three Python tools
and the manifest still parse, and `empaquetar_uwp.ps1` still parses under Windows PowerShell 5.1
with its BOM and its CRLF intact.

## [1.0.1] — 2026-10-20

### Changed

- **The README now says which console this was tested on, and which one it was not.** Everything here
  was built and measured on an **Xbox Series X** in Developer Mode; a **Series S has never been tried**,
  so nothing here says anything about one. The wording used to say "Xbox Series", which reads as if it
  covered both, and it does not.

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
