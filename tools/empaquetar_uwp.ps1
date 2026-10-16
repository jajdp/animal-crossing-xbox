<#
.SYNOPSIS
  Empaqueta y firma AnimalCrossing.exe como .msix para la Xbox Series X.

.DESCRIPTION
  A diferencia de Banjo-Kazooie, aqui NO hay proyecto de Visual Studio: el
  ejecutable lo produce clang + lld directamente (herramientas\construir_uwp.py),
  asi que el paquete se arma a mano con makeappx y se firma con signtool. Es mas
  corto y no depende de MSBuild.

  El contenido del paquete es deliberadamente pequeno: el ejecutable, sus DLL, los
  dos shaders y los mosaicos. LA IMAGEN DEL DISCO NO VA DENTRO (1,36 GiB): se sube
  aparte a LocalState con el Device Portal, igual que el .o2r de Star Fox 64.

.PARAMETER Version
  Sube en cada ciclo: la consola no reemplaza un paquete por otro de la MISMA version.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$Version,
  # La huella SHA-1 de TU certificado de firma, en tu almacen personal (40 digitos hexadecimales):
  #   Get-ChildItem Cert:\CurrentUser\My | Format-List Subject, Thumbprint
  # Aqui no hay ninguna por omision: un certificado es de quien lo crea.
  [Parameter(Mandatory = $true)][Alias('Certificado')][string]$Huella,
  # Que Mesa entra en el paquete. El bundle original trae 24.3.0-rc2, un release
  # candidate de 2024, y es el principal sospechoso de la violacion de acceso que
  # mata al juego hacia el fotograma 200 (ver notas-port-uwp.md 4.11).
  # 'mesa-25' usa el 25.2.6 de la rama xbsx2-deps, que ademas ya no necesita
  # libglapi.dll: lo fusionaron dentro de libgallium_wgl.
  [ValidateSet('bundle', 'mesa-25', 'mesa-251', 'mesa-banjo')]
  [string]$Mesa = 'bundle'
)

$ErrorActionPreference = 'Stop'

$xbox     = Split-Path $PSScriptRoot -Parent
$build    = Join-Path $xbox "build-uwp"
$fuentes  = Join-Path $xbox "fuentes\uwp"
$dep      = Join-Path $xbox "uwp-dep"
$acgc     = Join-Path $xbox "acgc-64"
$crt      = Join-Path $dep "crt"
$layout   = Join-Path $build "layout"
$paquete  = Join-Path $xbox "paquete"

$exe = Join-Path $build "AnimalCrossing.exe"
if (-not (Test-Path $exe)) { throw "falta el ejecutable: $exe (corre construir_uwp.py)" }

# --- herramientas del SDK -------------------------------------------------
$sdkRoot = "C:\Program Files (x86)\Windows Kits\10\bin"
$sdkVer = Get-ChildItem $sdkRoot -Directory |
  Where-Object { Test-Path (Join-Path $_.FullName "x64\makeappx.exe") } |
  Sort-Object Name -Descending | Select-Object -First 1
if (-not $sdkVer) { throw "no encuentro makeappx.exe en el SDK de Windows" }
$makeappx = Join-Path $sdkVer.FullName "x64\makeappx.exe"
$signtool = Join-Path $sdkVer.FullName "x64\signtool.exe"
Write-Host "  SDK: $($sdkVer.Name)"

# --- 1. armar el layout ---------------------------------------------------
Write-Host "=== 1. layout ==="
if (Test-Path $layout) { Get-ChildItem $layout -Recurse | Remove-Item -Recurse -Force }
New-Item -ItemType Directory -Force -Path $layout | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $layout "shaders") | Out-Null

Copy-Item $exe $layout

# Las DLL de la consola: SDL2 (WinRT), Mesa (el OpenGL) y libuwp.
# opengl32.dll es la fachada de Mesa; sin libgallium_wgl.dll no dibuja nada.
$dlls = @("SDL2.dll", "opengl32.dll", "libgallium_wgl.dll", "libglapi.dll", "libuwp.dll", "z-1.dll", "dxil.dll")
if ($Mesa -ne 'bundle') {
  # SDL2 y libuwp SIEMPRE del bundle: el ejecutable enlaza contra sus .lib y
  # cambiarlas dejaria importaciones sin resolver. Solo se cambia Mesa.
  $dlls = @("SDL2.dll", "libuwp.dll")
}
foreach ($d in $dlls) {
  $o = Join-Path $dep "bin\$d"
  if (Test-Path $o) { Copy-Item $o $layout } else { Write-Host "  ! falta $d" }
}
if ($Mesa -eq 'mesa-banjo') {
  # El juego COMPLETO de Banjo-Kazooie, SDL2 y libuwp incluidos. Es la unica opcion
  # que toca esas dos, y a proposito: lo que se compara es la combinacion entera.
  foreach ($d in @("opengl32.dll", "libgallium_wgl.dll", "z-1.dll", "dxil.dll",
                   "libuwp.dll", "SDL2.dll", "glfw3.dll")) {
    $o = Join-Path $dep "mesa-banjo\$d"
    if (Test-Path $o) { Copy-Item $o $layout -Force } else { throw "falta $o" }
  }
  Write-Host "  DLL: las de Banjo-Kazooie (Mesa 25.1.1, su SDL2 y su libuwp)"
} elseif ($Mesa -ne 'bundle') {
  foreach ($d in @("opengl32.dll", "libgallium_wgl.dll", "z-1.dll", "dxil.dll")) {
    $o = Join-Path $dep "$Mesa\$d"
    if (Test-Path $o) { Copy-Item $o $layout } else { throw "falta $o" }
  }
  $ver = if ($Mesa -eq 'mesa-25') { '25.2.6 (rama xbsx2-deps)' } else { '25.1.1 (rama ghostship)' }
  Write-Host "  Mesa: $ver, sin libglapi"
} else {
  Write-Host "  Mesa: 24.3.0-rc2 (bundle original)"
}

# El runtime de C++ NO va dentro del paquete.
#
# El ejecutable importa msvcp140_app.dll y vcruntime140_app.dll (las variantes
# «_app», las unicas validas en un AppContainer). La tentacion es copiarlas al
# lado del .exe, y SE PROBO: el paquete se instala, se registra y luego falla al
# ACTIVARSE con 0x8027025B, un error que no explica nada. Lo que hace falta es
# declararlas como framework en el manifiesto (<PackageDependency> de
# Microsoft.VCLibs.140.00), que es lo que hacen todos los paquetes que si
# arrancan en esta consola. El framework ya esta instalado desde el port de
# Banjo-Kazooie.


# Los shaders: el juego los abre con ruta relativa y el envoltorio los copia a
# LocalState en el primer arranque.
Copy-Item (Join-Path $acgc "pc\shaders\default.vert") (Join-Path $layout "shaders")
Copy-Item (Join-Path $acgc "pc\shaders\default.frag") (Join-Path $layout "shaders")

Copy-Item (Join-Path $fuentes "Assets") $layout -Recurse

# El manifiesto va como AppxManifest.xml, con la version de esta vuelta.
$manifiesto = Get-Content (Join-Path $fuentes "Package.appxmanifest") -Raw
# Solo la version de <Identity>: el patron de antes ('Version="..."' a secas) casaba
# tambien con los dos MinVersion del manifiesto --TargetDeviceFamily y la dependencia de
# VCLibs-- y los reescribia con la version del paquete. No impedia instalar, porque la
# consola tiene versiones mayores que las dos, pero el manifiesto instalado dejaba de
# exigir lo que la plantilla pretende.
$manifiesto = [regex]::Replace($manifiesto,
    '(?<=<Identity\b[^>]*?\s)Version="\d+\.\d+\.\d+\.\d+"',
    "Version=`"$Version`"")
Set-Content (Join-Path $layout "AppxManifest.xml") $manifiesto -Encoding UTF8

$n = (Get-ChildItem $layout -Recurse -File).Count
$mb = [math]::Round(((Get-ChildItem $layout -Recurse -File | Measure-Object Length -Sum).Sum / 1MB), 1)
Write-Host "  $n archivos, $mb MB"

# --- 2. empaquetar --------------------------------------------------------
Write-Host "=== 2. makeappx ==="
New-Item -ItemType Directory -Force -Path $paquete | Out-Null
$msix = Join-Path $paquete "AnimalCrossing-$Version.msix"
if (Test-Path $msix) { Remove-Item $msix -Force }
& $makeappx pack /d $layout /p $msix /o
if ($LASTEXITCODE -ne 0) { throw "fallo makeappx" }

# --- 3. firmar ------------------------------------------------------------
Write-Host "=== 3. firma ==="
& $signtool sign /fd SHA256 /sha1 $Huella $msix
if ($LASTEXITCODE -ne 0) { throw "fallo la firma" }

$tam = [math]::Round((Get-Item $msix).Length / 1MB, 1)
Write-Host ""
Write-Host "OK: $msix  ($tam MB)"
