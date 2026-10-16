# Construir el port y meterlo en la consola

*(English: [INSTALL.md](INSTALL.md))*

## 0. Antes de empezar: dónde se escriben las órdenes

Todo lo de esta guía va en **PowerShell**, la terminal normal de Windows: pulsa la tecla
**Windows**, escribe `powershell` y pulsa **Enter** sobre *Windows PowerShell*. Ahí escribes la
orden y pulsas **Enter**. Para ir a una carpeta, `cd` con la ruta entre comillas si tiene espacios;
o abre la carpeta en el Explorador, haz clic en la barra de direcciones, escribe `powershell` encima
y pulsa **Enter**.

**No hace falta administrador** en ningún paso. Y en uno concreto, usarlo lo **estropea**: el
certificado del §5 se crea en el almacén del usuario que ejecuta la orden, así que elevado acabaría
en el del administrador y `signtool`, corriendo como tú, no lo encontraría. Lo único que pide
administrador es el instalador de Visual Studio.

**PowerShell 7 no hace falta**: con la que trae Windows basta. Los ejemplos llevan
`-ExecutionPolicy Bypass` porque un Windows de fábrica no ejecuta un `.ps1`.

---

## 1. Lo que hace falta antes

| | Para qué |
|---|---|
| **MSYS2** con CMake, ninja y GCC | Compilar la **build de escritorio** del fork, que es la entrada de todo |
| **llvm-mingw** (clang y `ld.lld`) | Compilar para la consola, con el ABI de MSVC |
| **Visual Studio 2022** con el componente de **UWP para C++** | Su entorno `store`, y el `makeappx`/`signtool` del Windows SDK |
| **El bundle de UWP** | SDL2, Mesa y `libuwp` para UWP: [`worleydl/uwp-dep`](https://github.com/worleydl/uwp-dep) |
| **Python 3** | Los parches y el traductor |
| **Tu volcado** de *Animal Crossing* de GameCube | El juego |
| **Una Xbox en modo desarrollador** y un certificado | Instalar y firmar |

### Las variables de entorno

Los scripts no llevan ninguna ruta de ninguna máquina dentro:

```powershell
$env:ACGC_TOOLKIT = "C:\ac\llvm-mingw\bin"   # clang y ld.lld
$env:ACGC_MSYS    = "C:\msys64"                # el MSYS2 (se usa su bash.exe)
```

Visual Studio **se busca** con `vswhere`, y el Windows SDK también: no hay ninguna versión fijada.
Si falta una variable, el script se detiene diciendo cuál y para qué sirve.

---

## 2. El fork, y su build de escritorio

```powershell
git clone https://github.com/birabittoh/ACGC-PC-Port.git C:\ac\ACGC-PC-Port
```

⚠ **Compílalo y pruébalo en tu PC primero**, con sus propias instrucciones. Dos razones: si no corre
ahí no va a correr en la consola, y sobre todo que **de esa build sale la receta**: el traductor le
pide sus órdenes a `ninja`, así que tiene que existir y estar al día.

---

## 3. Los parches

```powershell
python tools\acgc_parches.py C:\ac\ACGC-PC-Port
```

Trece parches, **todos idempotentes**: se pueden pasar las veces que haga falta. Once son los
archivos que clang no acepta tal cual —el árbol de PC compila con GCC y `-fpermissive`, que clang no
tiene— y el resto es el perfil de la consola, detrás de `ACGC_UWP`, de modo que el mismo árbol sigue
compilando para PC.

---

## 4. Compilar para la consola

```powershell
python tools\construir_uwp.py --raiz C:\ac\ACGC-PC-Port
```

Lo que hace, y es lo que hay que entender de este port: **no mantiene un segundo proyecto**. Le pide
a `ninja` las órdenes de la build de escritorio —3 997 objetos—, las reescribe al dialecto de la
consola (clang con ABI de MSVC, el CRT «store», `/APPCONTAINER`) y las ejecuta. Un archivo que el
proyecto de arriba añada aparece solo.

---

## 5. Un certificado, y tu identidad en el manifiesto

```powershell
$c = New-SelfSignedCertificate -Type Custom -Subject "CN=TuNombre" `
       -KeyUsage DigitalSignature -FriendlyName "Firma UWP" `
       -CertStoreLocation "Cert:\CurrentUser\My" `
       -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3", "2.5.29.19={text}")
$c.Thumbprint
```

Y en `package\Package.appxmanifest`, los `CHANGE-ME`: `Identity Name`, `Publisher` (**idéntico** al
sujeto de tu certificado), `PublisherDisplayName` y el `PhoneProductId`.

⚠ **No cambies el `Language="EN-US"` por `x-generate`.** Ese token lo sustituye Visual Studio al
compilar, y en un manifiesto hecho a mano la consola falla al registrar el paquete con
`0x80070057`.

---

## 6. Los mosaicos, empaquetar y firmar

`package\Assets\` viene **vacía a propósito**: [`ASSETS.es.md`](ASSETS.es.md) dice los nueve
nombres y medidas, y `tools/acgc_mosaicos.py` genera unos provisionales si quieres salir del paso.

```powershell
powershell -ExecutionPolicy Bypass -File tools\empaquetar_uwp.ps1 -Version 1.0.0.0 -Certificado <tu huella>
```

⚠ **La versión sube en cada paquete nuevo**: la consola no reemplaza un paquete por otro de la misma
versión, ni cambia sus mosaicos.

---

## Instalarlo en la consola

### Antes de tocar nada: cómo tiene que estar la consola

- **En modo desarrollador**, con Dev Home instalado.
- **Encendida y con tu perfil iniciado.** ⚠ Sin un usuario conectado, la consola **no abre
  aplicaciones**: el paquete se instala, aparece en la lista y al lanzarlo no pasa nada.
- **En la misma red que tu PC**, y con su dirección a mano (la dice Dev Home). El Device Portal
  escucha en el puerto **11443** por HTTPS y pide el usuario y la contraseña
  que definiste en Dev Home.

Abre `https://<ip>:11443`. ⚠ El navegador avisará de que el certificado del sitio no es de
confianza: es el de la propia consola, que se lo hace ella. Entra igual — en Edge y Chrome,
**Avanzado** → **Continuar a … (no seguro)**; en Firefox, **Avanzado** → **Aceptar el riesgo y
continuar**.

En **My games & apps → Add**: tu `.msix`, y en **Dependency** el `Microsoft.VCLibs.x64.14.00.appx`
del Windows SDK la primera vez. **Certificate** no hace falta: el modo desarrollador acepta
cualquier paquete firmado.

⚠ **El CRT de C++ va como dependencia, nunca dentro del paquete.** Con las DLL dentro, el paquete se
instala y la activación falla con `0x8027025B` sin más explicación.

Si sale `There is not enough space on the disk`, no está llena: la primera instalación de una
familia va a `D:\DevelopmentFiles`, de unos 5 GB. Se arregla instalando primero una *semilla* con la
misma identidad y una versión más baja.

## El disco

Va a la carpeta de datos de la aplicación, que crea el primer arranque:

```text
…\LocalState\rom\
```

Se sube con el **File explorer** del Device Portal. ⚠ Si el portal responde **500**, no es la
consola: sus subidas pasan por `D:\DevelopmentFiles`, que es pequeño, y hay que subir el archivo
**partido** y unirlo allí.

Las partidas quedan también en el `LocalState`, así que **se van con el paquete** si lo desinstalas:
bájalas antes por el portal si quieres conservarlas. Para actualizar sin perderlas, no desinstales:
instala encima un paquete con una **versión mayor**.

---

## Si algo no sale bien

| Síntoma | Causa |
|---|---|
| El paquete instala y al abrirlo no pasa nada | ¿Hay un **perfil iniciado**? Y mira `errores*.txt` en el `LocalState` |
| La activación falla con `0x8027025B` | Falta la dependencia de VCLibs, o las DLL del CRT se metieron dentro del paquete |
| `0x80070057` al registrar | El manifiesto tiene `Language="x-generate"` (§5) |
| Una tormenta de `address not 32Byte aligned` | Falta el parche de la macro de alineación: es el primero de la lista y el que más duele ([`HOW-IT-WORKS.es.md`](HOW-IT-WORKS.es.md)) |
| Muere hacia el fotograma 200 con `GL_OUT_OF_MEMORY` | No es memoria: es presentar durante los primeros fotogramas. El parche los salta |
| Una violación de acceso dentro de Mesa | **La versión de Mesa.** Usa la que ya funciona en la consola |
| `There is not enough space on the disk` | No está llena: es `D:\DevelopmentFiles` |
