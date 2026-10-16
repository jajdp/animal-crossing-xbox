# Notice

*(Español: [NOTICE.es.md](NOTICE.es.md))*

## Not affiliated

This is an unofficial, noncommercial fan project. It is **not affiliated with, endorsed by or
connected to Nintendo or Microsoft**, nor to [ACreTeam](https://github.com/ACreTeam/ac-decomp), nor
to the authors of the PC port or of its
[64-bit fork](https://github.com/birabittoh/ACGC-PC-Port). *Animal Crossing*, *Xbox* and all
related names and marks are the property of their respective owners, and are used here only to say
what this works with.

Nothing here is for sale, and nothing here is monetized.

## What this repository does not distribute

No disc image. No game data or assets. No built executable. No `.msix`. No save data. No package
tiles (`package/Assets/` is empty, and [`docs/ASSETS.md`](docs/ASSETS.md) asks for your own).

**And none of the UWP libraries**: Mesa, SDL2 and `libuwp` are other people's binaries. The guide
says where they come from.

## What it does contain of other people's work

**Patches against the 64-bit fork.** The thirteen patch scripts quote the lines of the fork's source
that each one checks before writing, so that they fail safely instead of corrupting a tree they do
not recognise. That fork is **dual-licensed**: the decompilation it carries, from ACreTeam, is
**CC0 1.0** (public domain), and the port layer is **MIT**, © 2026 FlyingMeta. Both permit this, and
this repository is released under [the MIT](LICENSE), with the fork's notice carried along.

**`src/uwp/main.cpp` and `src/compat/`** are first-party: the WinRT entry point, and three small
headers that stand in for ones MSVC does not ship (`dirent.h`, `strings.h`, `unistd.h`).

**There are no screenshots here.** A screenshot of this running would be mostly Nintendo's artwork.

## Takedown and contact

If you hold rights in this material and want something here removed or changed, write to
**jajdpmail@gmail.com**, saying what you object to and in what capacity you are writing.

Requests from rights holders are honoured: the disputed part is removed, or the repository is taken
down, without argument, and you will get a reply confirming it.
