# How it works, and why each patch is there

*(Español: [HOW-IT-WORKS.es.md](HOW-IT-WORKS.es.md))*

## The method: translate the build, do not maintain a second one

The *Animal Crossing* decompilation builds for the PC with GCC from a generated `ninja`. Taking that
to a console has two routes: write a second CMake project for `WindowsStore` — and keep it current
every time upstream adds a file — or **translate the build that already exists**.

This port does the latter, like the *Diddy Kong Racing* one: `construir_uwp.py` runs
`ninja -t commands` on the desktop build, takes its 3 997 compile commands, rewrites them — clang
with the MSVC ABI instead of GCC, the "store" CRT, the console's headers — and runs them again. Then
it links with `ld.lld` and `/APPCONTAINER`.

The advantage is not elegance: it is that **a new file upstream shows up on its own**, with nothing
to change here.

## The big one: alignment being thrown away

**The symptom**: a storm of `OSPanic … address not 32Byte aligned` on the console, which on the
desktop **never appears once**.

It was measured, not guessed. Instrumenting the check, the address was 16-aligned and the size was
right. The **linker map** identified the culprit: a buffer declared with the game's alignment macro,
asking for 32… and not having it.

**The cause** is how the tree picks that macro's syntax:

```c
#ifdef __GNUC__
#define ATTRIBUTE_ALIGN(num) __attribute__((aligned(num)))
#elif defined(_MSC_VER)
#define ATTRIBUTE_ALIGN(num) __declspec(align(num))
```

clang with the MSVC ABI **does not define `__GNUC__`** (it defines `_MSC_VER` and `__clang__`), so it
fell into the `__declspec` branch. And in MSVC's syntax, `__declspec` has to come **before** the
declaration; where that macro is used it sits **after** the declarator, where it is ignored
**silently**. The result: *every* alignment the game asks for was being discarded.

⚠ **And the first fix was the wrong one**, which is what makes this worth telling: changing the
`_MSC_VER` branch did not move the buffer **one byte**. What works is making the GCC-attribute
branch **recognise clang too**, because clang accepts GCC attributes even while emulating the MSVC
ABI, and that form does work after the declarator. The macro is also defined **twice** in the tree
and both had to be changed; which one won was checked with `clang -E -dM`, not by eye.

With that, the buffer moved to a 32-aligned address and **the console's error file came out 0 bytes
long**.

As a bonus, a latent bug in the PC lane itself: the emulated ARAM came from a plain `malloc` —
16 bytes guaranteed — where the system using it requires 32. On the desktop it landed right by luck.
Now it is requested aligned. ⚠ And `<malloc.h>` has to be included: without it the function is
implicitly declared, the compiler assumes an `int` return and **the 64-bit pointer is truncated**,
with no warning at all.

## The second big one: `GL_OUT_OF_MEMORY` with no shortage of memory

With all of the above fixed, the game booted cleanly and died around frame 200 inside Mesa.

The first job was **ruling out what it was not**, with measurements rather than guesses:

| Suspected | Measurement | Verdict |
|---|---|---|
| Out of memory | `GlobalMemoryStatusEx` at every point | **4 982 MB free of 5 120**, 2% load |
| GPU reset (TDR) | `glGetGraphicsResetStatus` | **0**, no reset |
| vsync, window size, resizing, presenting too fast | one by one | still breaks |

What found it was **seeding probes** through startup: each point tries to create the same small
texture and reports SANO or ROTO. The cut landed between two consecutive lines: healthy after
polling events, **broken right after presenting**. And presenting is just `SDL_GL_SwapWindow`.

**The cause: presenting during the first frames of startup.** The only thing that changes the
outcome is how many presents happen at the beginning, so the fix is to skip them.

Before getting there, one more stop: an access violation inside Mesa that **went away when Mesa's
version changed**. That is the third time Mesa has decided things in this catalogue, and the rule is
already written: **try the Mesa that already works on the console first**.

## The rest, which is every UWP port's toll

| | What happens |
|---|---|
| Three headers MSVC does not have | `dirent.h`, `strings.h` and `unistd.h`. They live in `src/compat/`, written for this |
| `_m_prefetch` | Does not exist under the MSVC ABI |
| `strdup` | Not in the "store" CRT |
| The MSVC ABI **does decorate** global variable names | And the game declares some from assembly expecting it not to |
| `__forceinline` **is not** `always_inline` | And the tree assumes it is |
| Relative paths and the working directory | WinRT's video driver changes the working directory to the install folder, which is read-only |
| The game sent its own diagnostics to `NUL` | Until that was fixed, every failure above was invisible |
| `Language="x-generate"` | Not valid in a hand-written manifest: `0x80070057` on registration |
| The C++ CRT inside the package | `0x8027025B` on activation. It goes as a **dependency** |

## What is not solved

- **Developer Mode suspension**: coming back from Home, the game starts over.
- The package with the final tiles was built but never installed on the console: what was played and
  tested was the previous build, identical except for the images.
