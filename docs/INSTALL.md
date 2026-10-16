# Building the port and getting it onto the console

*(Español: [INSTALL.es.md](INSTALL.es.md))*

## 0. Before you start: where the commands go

Everything here goes in **PowerShell**, the ordinary Windows terminal: press the **Windows** key,
type `powershell` and press **Enter** on *Windows PowerShell*. That is where you type the command
and press **Enter**. To move to a folder use `cd` with the path, in quotes if it has spaces; or open
the folder in File Explorer, click the address bar, type `powershell` over whatever is there and
press **Enter**.

**No administrator is needed** anywhere. And in one step it **breaks** things: the certificate in §5
is created in the store of whoever runs the command, so elevated it would land in the
administrator's store and `signtool`, running as you, would not find it. The only thing that asks
for administrator is the Visual Studio installer.

**PowerShell 7 is not needed**: the one Windows ships is enough. The examples carry
`-ExecutionPolicy Bypass` because a stock Windows will not run a `.ps1`.

---

## 1. What you need first

| | What for |
|---|---|
| **MSYS2** with CMake, ninja and GCC | Building the fork's **desktop build**, which is the input to everything |
| **llvm-mingw** (clang and `ld.lld`) | Building for the console, with the MSVC ABI |
| **Visual Studio 2022** with the **C++ UWP component** | Its `store` environment, and `makeappx`/`signtool` from the Windows SDK |
| **The UWP bundle** | SDL2, Mesa and `libuwp` for UWP: [`worleydl/uwp-dep`](https://github.com/worleydl/uwp-dep) |
| **Python 3** | The patches and the translator |
| **Your dump** of *Animal Crossing* for GameCube | The game |
| **An Xbox in Developer Mode** and a certificate | Installing, and signing |

### The environment variables

The scripts carry no machine's paths inside them:

```powershell
$env:ACGC_TOOLKIT = "C:\ac\llvm-mingw\bin"   # clang and ld.lld
$env:ACGC_MSYS    = "C:\msys64"                # MSYS2 (its bash.exe is used)
```

Visual Studio **is found** with `vswhere`, and so is the Windows SDK: no version is pinned. If a
variable is missing, the script stops saying which one and what it is for.

---

## 2. The fork, and its desktop build

```powershell
git clone https://github.com/birabittoh/ACGC-PC-Port.git C:\ac\ACGC-PC-Port
```

⚠ **Build it and test it on your PC first**, with its own instructions. Two reasons: if it does not
run there it will not run on the console, and above all **the recipe comes out of that build** — the
translator asks `ninja` for its commands, so it has to exist and be current.

---

## 3. The patches

```powershell
python tools\acgc_parches.py C:\ac\ACGC-PC-Port
```

Thirteen patches, **all idempotent**: run them as many times as you like. Eleven are the files clang
will not take as they are — the PC tree builds with GCC and `-fpermissive`, which clang does not
have — and the rest is the console profile, behind `ACGC_UWP`, so the same tree still builds for the
PC.

---

## 4. Building for the console

```powershell
python tools\construir_uwp.py --raiz C:\ac\ACGC-PC-Port
```

What it does, and this is the thing to understand about this port: **it does not maintain a second
project**. It asks `ninja` for the desktop build's commands — 3 997 objects — rewrites them into the
console's dialect (clang with the MSVC ABI, the "store" CRT, `/APPCONTAINER`) and runs them. A file
upstream adds shows up on its own.

---

## 5. A certificate, and your identity in the manifest

```powershell
$c = New-SelfSignedCertificate -Type Custom -Subject "CN=YourName" `
       -KeyUsage DigitalSignature -FriendlyName "UWP signing" `
       -CertStoreLocation "Cert:\CurrentUser\My" `
       -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
$c.Thumbprint
```

And in `package\Package.appxmanifest`, the `CHANGE-ME`s: `Identity Name`, `Publisher` (**identical**
to your certificate's subject), `PublisherDisplayName` and `PhoneProductId`.

⚠ **Do not change `Language="EN-US"` to `x-generate`.** That token is substituted by Visual Studio at
build time, and in a hand-written manifest the console fails to register the package with
`0x80070057`.

---

## 6. Tiles, packaging and signing

`package\Assets\` ships **empty on purpose**: [`ASSETS.md`](ASSETS.md) lists the nine names and
sizes, and `tools/acgc_mosaicos.py` generates placeholder ones if you want to get going.

```powershell
powershell -ExecutionPolicy Bypass -File tools\empaquetar_uwp.ps1 -Version 1.0.0.0 -Certificado <your thumbprint>
```

⚠ **Bump the version for every new package**: the console will not replace a package whose version
matches the installed one, nor change its tiles.

---

## Installing it on the console

### Before touching anything: how the console has to be

- **In Developer Mode**, with Dev Home installed.
- **On, and with your profile signed in.** ⚠ With no user signed in the console **will not launch
  apps**: the package installs, shows up in the list, and launching it does nothing.
- **On the same network as your PC**, with its address at hand (Dev Home shows it). The Device
  Portal listens on port **11443** over HTTPS and asks for the username and
  password you set in Dev Home.

Open `https://<ip>:11443`. ⚠ The browser will warn that the site's certificate is not trusted: it is
the console's own. Go in anyway — in Edge and Chrome, **Advanced** → **Continue to … (unsafe)**; in
Firefox, **Advanced** → **Accept the Risk and Continue**.

In **My games & apps → Add**: your `.msix`, and under **Dependency** the Windows SDK's
`Microsoft.VCLibs.x64.14.00.appx` the first time. **Certificate** is not needed: Developer Mode
accepts any signed package.

⚠ **The C++ CRT goes as a dependency, never inside the package.** With the DLLs inside, the package
installs and activation fails with `0x8027025B` and no further explanation.

If it says `There is not enough space on the disk`, it is not full: the first install of a family
goes to `D:\DevelopmentFiles`, about 5 GB. Install a *seed* first — same identity, lower version.

## The disc

It goes into the app's data folder, which the first launch creates:

```text
…\LocalState\rom\
```

Upload it with the Device Portal's **File explorer**. ⚠ If the portal answers **500**, it is not the
console: its uploads pass through `D:\DevelopmentFiles`, which is small, and the file has to go up
**split** and be joined there.

The saves also live in `LocalState`, so they **go with the package** if you uninstall it: download
them through the portal first if you want to keep them. To update without losing them, do not
uninstall: install a package with a **higher version** on top.

---

## If something goes wrong

| Symptom | Cause |
|---|---|
| The package installs and launching does nothing | Is a **profile signed in**? And read `errores*.txt` in `LocalState` |
| Activation fails with `0x8027025B` | The VCLibs dependency is missing, or the CRT DLLs were put inside the package |
| `0x80070057` on registration | The manifest has `Language="x-generate"` (§5) |
| A storm of `address not 32Byte aligned` | The alignment-macro patch is missing: it is the first on the list and the one that hurts most ([`HOW-IT-WORKS.md`](HOW-IT-WORKS.md)) |
| Dies around frame 200 with `GL_OUT_OF_MEMORY` | It is not memory: it is presenting during the first frames. The patch skips them |
| An access violation inside Mesa | **Mesa's version.** Use the one that already works on the console |
| `There is not enough space on the disk` | It is not full: it is `D:\DevelopmentFiles` |
