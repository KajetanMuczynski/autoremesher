# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (C) 2026 Quadami contributors
#
# Install or update the Quadami Blender add-on on Windows and remove old copies.
# The Windows twin of quadami-update.sh; see README.md next to it.
#
#   powershell -ExecutionPolicy Bypass -File quadami-update.ps1 <zip> <blender.exe>                # dry run
#   powershell -ExecutionPolicy Bypass -File quadami-update.ps1 -Apply <zip> <blender.exe>         # asks, then acts
#   powershell -ExecutionPolicy Bypass -File quadami-update.ps1 -Apply -AllVersions <zip> <blender.exe>
#
# <zip> is the inner quadami-<version>-windows-x64.zip, not GitHub's addon-windows-x64.zip
# wrapper around it. The Blender you name decides where it installs: the script asks that
# Blender for its own extensions folder, installs with Blender's own command (as CI does) and
# then asks Blender whether the add-on is enabled:
#   blender.exe --command extension install-file -r user_default -e <zip>
#
# What it may delete (nothing else):
#   - <that Blender's extensions folder>\<repo>\quadami        (replaced by the install anyway)
#   - with -AllVersions: %APPDATA%\Blender Foundation\Blender\<X.Y>\extensions\<repo>\quadami and
#     ...\<X.Y>\scripts\addons\{quadami,autoremesher_blender} of every Blender version
#   - %TEMP%\quadami-* and %TEMP%\autoremesher-*   worker temp folders left by a crash
#   - %USERPROFILE%\Downloads\quadami-*.zip and addon-windows-x64*.zip, except <zip>
#
# Written for Windows PowerShell 5.1 (built into Windows 10 and 11) and PowerShell 7.

param(
    [Parameter(Position = 0)][string]$Zip,
    [Parameter(Position = 1)][string]$Blender,
    [switch]$Apply,
    [switch]$AllVersions
)

# Native programs write to stderr; under 'Stop' Windows PowerShell 5.1 turns that into an error.
$ErrorActionPreference = 'Continue'
Set-StrictMode -Version 2.0

function Fail([string]$Message) {
    Write-Host $Message -ForegroundColor Red
    exit 1
}

if (-not $Zip -or -not $Blender) {
    Fail 'usage: quadami-update.ps1 [-Apply] [-AllVersions] <quadami-...-windows-x64.zip> <blender.exe>'
}
if (-not (Test-Path -LiteralPath $Zip -PathType Leaf)) { Fail "Zip not found: $Zip" }
$Zip = (Resolve-Path -LiteralPath $Zip).ProviderPath

# A folder works too (the Blender install folder): use the blender.exe inside it.
if (Test-Path -LiteralPath $Blender -PathType Container) { $Blender = Join-Path $Blender 'blender.exe' }
$cmd = Get-Command $Blender -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1
if (-not $cmd) { Fail "Blender executable not found: $Blender" }
$exe = $cmd.Source

$running = Get-Process -Name 'blender', 'blender-launcher', 'autoremesher-cli' -ErrorAction SilentlyContinue
if ($running) { Fail 'Blender or the remesher is running. Quit Blender first.' }

# Runs Blender, returns its output lines (stdout and stderr) as strings.
function Invoke-Blender([string[]]$Arguments) {
    $lines = & $script:exe @Arguments 2>&1 | ForEach-Object { "$_" }
    $script:blenderExit = $LASTEXITCODE
    return @($lines)
}

function Get-Marked([string[]]$Lines, [string]$Marker) {
    foreach ($line in $Lines) {
        if ($line.StartsWith($Marker)) { return $line.Substring($Marker.Length).Trim() }
    }
    return ''
}

# Blender prints the path as UTF-8 hex: its console output is decoded with the OEM code page,
# which would garble a user name with non-ASCII letters (a Polish l-stroke, say).
# Keep this file ASCII: Windows PowerShell 5.1 reads a script without a BOM in the ANSI code page.
function ConvertFrom-Hex([string]$Hex) {
    if ($Hex -notmatch '^([0-9a-f]{2})+$') { return '' }
    $bytes = New-Object byte[] ($Hex.Length / 2)
    for ($i = 0; $i -lt $bytes.Length; $i++) { $bytes[$i] = [Convert]::ToByte($Hex.Substring(2 * $i, 2), 16) }
    return [System.Text.Encoding]::UTF8.GetString($bytes)
}

# The zip: Blender's extension zip has blender_manifest.toml at its root. GitHub's artifact
# wrapper holds only the inner zip.
Add-Type -AssemblyName System.IO.Compression.FileSystem
$buildId = 'unknown'
$manifest = $null
$archive = [System.IO.Compression.ZipFile]::OpenRead($Zip)
try {
    $names = @($archive.Entries | ForEach-Object { $_.FullName })
    foreach ($entry in $archive.Entries) {
        if ($entry.FullName -eq 'blender_manifest.toml' -or $entry.FullName -eq 'build-id.txt') {
            $reader = New-Object System.IO.StreamReader($entry.Open())
            try { $text = $reader.ReadToEnd() } finally { $reader.Close() }
            if ($entry.FullName -eq 'build-id.txt') { $buildId = $text.Trim() } else { $manifest = $text }
        }
    }
} finally {
    $archive.Dispose()
}
if (-not $manifest) {
    if ($names | Where-Object { $_ -like '*.zip' }) {
        Fail "$Zip is GitHub's wrapper. Unpack it once (right-click > Extract All) and pass the quadami-...-windows-x64.zip inside."
    }
    Fail "$Zip is not a Blender extension zip (no blender_manifest.toml)."
}
if ($manifest -notmatch '(?m)^id\s*=\s*"quadami"') { Fail "$Zip is not the Quadami add-on." }
if ($manifest -match '(?m)^platforms\s*=(.*)$' -and $Matches[1] -notmatch 'windows-x64') {
    Fail "$Zip is built for $($Matches[1].Trim()), not windows-x64."
}
if ($manifest -notmatch '(?m)^platforms\s*=') {
    Write-Host 'warning: this zip has no bundled remesher (no platforms line); the add-on will need the executable path in its preferences.' -ForegroundColor Yellow
}

$version = (Invoke-Blender @('--version') | Where-Object { $_ -like 'Blender *' } | Select-Object -First 1)
$extOut = Invoke-Blender @('-b', '--factory-startup', '--python-expr',
    "import bpy; print('QUADAMI_EXT=' + bpy.utils.user_resource('EXTENSIONS').encode('utf-8').hex())")
$extDir = ConvertFrom-Hex (Get-Marked $extOut 'QUADAMI_EXT=')
# <config>\<X.Y>\extensions, absolute: anything else and the script stops before it lists or deletes.
if (-not $extDir -or -not [System.IO.Path]::IsPathRooted($extDir) -or
    (Split-Path -Leaf $extDir) -ne 'extensions' -or
    (Split-Path -Leaf (Split-Path -Parent $extDir)) -notmatch '^\d+\.\d+$') {
    Fail "Could not get the extensions folder from $exe (got '$extDir')."
}
Write-Host "Target: $version ($exe)"
Write-Host "  extensions folder: $extDir"

function Same-Path([string]$A, [string]$B) {
    return [string]::Equals($A.TrimEnd('\', '/'), $B.TrimEnd('\', '/'), [System.StringComparison]::OrdinalIgnoreCase)
}
function Parent([string]$Path, [int]$Levels) {
    for ($i = 0; $i -lt $Levels; $i++) { $Path = Split-Path -Parent $Path }
    return $Path
}

$tempDir = [System.IO.Path]::GetTempPath()
$profileDir = [Environment]::GetFolderPath('UserProfile')
$downloads = Join-Path $profileDir 'Downloads'
$blenderRoot = $null
if ($env:APPDATA) { $blenderRoot = Join-Path $env:APPDATA 'Blender Foundation\Blender' }

# Only paths of these exact shapes are ever deleted; checked again right before deleting.
function Test-Deletable([string]$Path) {
    $leaf = Split-Path -Leaf $Path
    $parent = Split-Path -Parent $Path
    if ($leaf -eq 'quadami' -and (Same-Path (Parent $Path 2) $script:extDir)) { return $true }
    if ($script:AllVersions -and $script:blenderRoot) {
        if ($leaf -eq 'quadami' -and (Split-Path -Leaf (Parent $Path 2)) -eq 'extensions' -and
            (Same-Path (Parent $Path 4) $script:blenderRoot)) { return $true }
        if (($leaf -eq 'quadami' -or $leaf -eq 'autoremesher_blender') -and
            (Split-Path -Leaf $parent) -eq 'addons' -and (Split-Path -Leaf (Parent $Path 2)) -eq 'scripts' -and
            (Same-Path (Parent $Path 4) $script:blenderRoot)) { return $true }
    }
    if (($leaf -like 'quadami-*' -or $leaf -like 'autoremesher-*') -and (Same-Path $parent $script:tempDir) -and
        (Test-Path -LiteralPath $Path -PathType Container)) { return $true }
    if (($leaf -like 'quadami-*.zip' -or $leaf -like 'addon-windows-x64*.zip') -and (Same-Path $parent $script:downloads) -and
        -not (Same-Path $Path $script:Zip)) { return $true }
    return $false
}

$list = New-Object System.Collections.Generic.List[string]
foreach ($repo in @(Get-ChildItem -LiteralPath $extDir -Directory -ErrorAction SilentlyContinue)) {
    $d = Join-Path $repo.FullName 'quadami'
    if (Test-Path -LiteralPath $d -PathType Container) { $list.Add($d) }
}
if ($blenderRoot -and (Test-Path -LiteralPath $blenderRoot -PathType Container)) {
    foreach ($ver in @(Get-ChildItem -LiteralPath $blenderRoot -Directory)) {
        $candidates = @()
        foreach ($repo in @(Get-ChildItem -LiteralPath (Join-Path $ver.FullName 'extensions') -Directory -ErrorAction SilentlyContinue)) {
            $candidates += Join-Path $repo.FullName 'quadami'
        }
        $addons = Join-Path $ver.FullName 'scripts\addons'
        $candidates += Join-Path $addons 'quadami'
        $candidates += Join-Path $addons 'autoremesher_blender'
        foreach ($d in $candidates) {
            if (-not (Test-Path -LiteralPath $d -PathType Container)) { continue }
            if ((Parent $d 2) -and (Same-Path (Parent $d 2) $extDir)) { continue }
            if ($AllVersions) { $list.Add($d) }
            else { Write-Host "other Blender version, kept (-AllVersions removes it): $d" }
        }
        # Other add-ons with autoremesher in the name are only reported, never removed.
        $others = @(Get-ChildItem -LiteralPath $addons -Filter '*autoremesher*' -ErrorAction SilentlyContinue)
        foreach ($repo in @(Get-ChildItem -LiteralPath (Join-Path $ver.FullName 'extensions') -Directory -ErrorAction SilentlyContinue)) {
            $others += @(Get-ChildItem -LiteralPath $repo.FullName -Filter '*autoremesher*' -ErrorAction SilentlyContinue)
        }
        foreach ($o in $others) {
            if ($o.Name -ne 'autoremesher_blender') { Write-Host "note (not touched): $($o.FullName)" }
        }
    }
}
foreach ($pattern in 'quadami-*', 'autoremesher-*') {
    foreach ($d in @(Get-ChildItem -LiteralPath $tempDir -Directory -Filter $pattern -ErrorAction SilentlyContinue)) {
        $list.Add($d.FullName)
    }
}
foreach ($pattern in 'quadami-*.zip', 'addon-windows-x64*.zip') {
    foreach ($f in @(Get-ChildItem -LiteralPath $downloads -File -Filter $pattern -ErrorAction SilentlyContinue)) {
        if (-not (Same-Path $f.FullName $Zip)) { $list.Add($f.FullName) }
    }
}

if ($list.Count -gt 0) {
    Write-Host 'Would delete:'
    foreach ($p in $list) { Write-Host "  $p" }
} else {
    Write-Host 'No old copies found.'
}
Write-Host "Would install: $Zip"
Write-Host "  build: $buildId"
Write-Host "  into: $(Join-Path $extDir 'user_default\quadami') (enabled, preferences saved)"

if (-not $Apply) {
    Write-Host 'Dry run. Run again with -Apply to do it.'
    exit 0
}
$answer = Read-Host 'Proceed? [y/N]'
if ($answer -ne 'y' -and $answer -ne 'Y') {
    Write-Host 'Nothing changed.'
    exit 0
}

foreach ($p in $list) {
    if (Test-Deletable $p) {
        Remove-Item -LiteralPath $p -Recurse -Force -ErrorAction Continue
        if (-not (Test-Path -LiteralPath $p)) { Write-Host "deleted $p" }
        else { Write-Host "could not delete $p (in use? Quit Blender and retry)" -ForegroundColor Yellow }
    } else {
        Write-Host "skipped unexpected path: $p" -ForegroundColor Yellow
    }
}

Invoke-Blender @('--command', 'extension', 'install-file', '-r', 'user_default', '-e', $Zip) |
    Where-Object { $_ -match '\S' } | ForEach-Object { Write-Host "  $_" }
$installExit = $blenderExit
$enabledOut = Invoke-Blender @('-b', '--python-expr',
    "import bpy; print('QUADAMI_ENABLED=' + str('bl_ext.user_default.quadami' in bpy.context.preferences.addons))")
$enabled = Get-Marked $enabledOut 'QUADAMI_ENABLED='
$installed = Join-Path $extDir 'user_default\quadami'
$present = Test-Path -LiteralPath $installed -PathType Container
if ($installExit -eq 0 -and $present -and $enabled -eq 'True') {
    $idFile = Join-Path $installed 'build-id.txt'
    $installedId = 'unknown'
    if (Test-Path -LiteralPath $idFile) { $installedId = (Get-Content -LiteralPath $idFile -Raw).Trim() }
    Write-Host "Installed and enabled in ${version}: $installed" -ForegroundColor Green
    Write-Host "Build: $installedId (the grey line at the bottom of the Quadami panel must show the same)"
    Write-Host "Start this same Blender ($exe), 3D Viewport, N, tab Quadami."
} else {
    Fail ("Install check failed (exit code: $installExit, folder present: $present, enabled: $enabled). " +
          'Install by hand, see README.md section 3.')
}
