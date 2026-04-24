# build_win.ps1 — Doc-Sorter Windows Release Build
# Erstellt: DocSorter-Setup-{version}.exe mit EINGEBAUTEM Tesseract
# → Nutzer müssen NICHTS extra installieren!
#
# Voraussetzungen:
#   pip install pyinstaller nicegui pywebview
#   Inno Setup 6: https://jrsoftware.org/isdl.php
#
# Verwendung:
#   .\build_win.ps1
#   .\build_win.ps1 -SkipTesseract   # ohne Tesseract bundeln
#   .\build_win.ps1 -SkipInstaller   # nur .exe, kein Setup

param(
    [string]$Version      = "",
    [switch]$SkipTesseract,
    [switch]$SkipInstaller
)

$ErrorActionPreference = "Stop"
$AppName  = "DocSorter"
$DistDir  = "dist\win"
$BuildDir = "build\win"

# Tesseract Download-URL (UB Mannheim – offizielle Windows-Builds)
$TesseractUrl     = "https://github.com/UB-Mannheim/tesseract/releases/download/v5.3.3.20231005/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
$TesseractInstDir = "$env:LOCALAPPDATA\Programs\Tesseract-OCR"

# Version ermitteln
if (-not $Version) {
    $Version = python -c "from src.version import __version__; print(__version__)"
}
Write-Host "🔨 Doc-Sorter Windows Build v$Version" -ForegroundColor Cyan
Write-Host ""

# ---------------------------------------------------------------------------
# 0. Pre-Build-Check: Sicherstellen dass KEINE Nutzerdaten gebundelt werden
# ---------------------------------------------------------------------------
Write-Host "🔍 Prüfe auf Nutzerdaten..." -ForegroundColor Yellow
python pre_build_check.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Build abgebrochen — Nutzerdaten-Check fehlgeschlagen!" -ForegroundColor Red
    exit 1
}
Write-Host ""

# ---------------------------------------------------------------------------
# 1. Tesseract herunterladen und still installieren (falls nicht vorhanden)
# ---------------------------------------------------------------------------
if (-not $SkipTesseract) {
    $TessExe = "$TesseractInstDir\tesseract.exe"
    if (Test-Path $TessExe) {
        Write-Host "✓ Tesseract bereits installiert: $TessExe" -ForegroundColor Green
    } else {
        Write-Host "📥 Lade Tesseract herunter (~40 MB)..." -ForegroundColor Yellow
        $TempInstaller = "$env:TEMP\tesseract-installer.exe"
        Invoke-WebRequest -Uri $TesseractUrl -OutFile $TempInstaller -UseBasicParsing

        Write-Host "📦 Installiere Tesseract still (kein Fenster)..."
        Start-Process -FilePath $TempInstaller -ArgumentList "/S /D=$TesseractInstDir" -Wait -NoNewWindow
        Remove-Item $TempInstaller -Force

        if (Test-Path $TessExe) {
            Write-Host "✓ Tesseract installiert: $TessExe" -ForegroundColor Green
        } else {
            Write-Host "⚠ Tesseract nicht gefunden nach Installation — Build ohne Tesseract" -ForegroundColor Yellow
        }
    }

    # Tesseract zu PATH hinzufügen (für diesen Build-Prozess)
    if (Test-Path $TesseractInstDir) {
        $env:PATH = "$TesseractInstDir;$env:PATH"
        $env:TESSDATA_PREFIX = "$TesseractInstDir\tessdata"
    }
}

# ---------------------------------------------------------------------------
# 2. Cleanup
# ---------------------------------------------------------------------------
if (Test-Path $DistDir)  { Remove-Item $DistDir  -Recurse -Force }
if (Test-Path $BuildDir) { Remove-Item $BuildDir -Recurse -Force }

# ---------------------------------------------------------------------------
# 3. Tesseract-Binaries für Bundling vorbereiten
# ---------------------------------------------------------------------------
$TesseractBundleArg = ""
$TessdataArg        = ""
$TessHookFile       = "hooks\hook_tesseract.py"

if (-not $SkipTesseract -and (Test-Path "$TesseractInstDir\tesseract.exe")) {
    Write-Host "📎 Bereite Tesseract-Bundle vor..." -ForegroundColor Yellow

    # Hook-Skript für PyInstaller erstellen
    New-Item -ItemType Directory -Force -Path "hooks" | Out-Null
    @"
# PyInstaller Runtime-Hook: Tesseract-Pfad setzen
import os, sys
_base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
_tess = os.path.join(_base, 'tesseract')
if os.path.isdir(_tess):
    os.environ.setdefault('PATH', '')
    os.environ['PATH'] = _tess + os.pathsep + os.environ['PATH']
    os.environ['TESSDATA_PREFIX'] = os.path.join(_tess, 'tessdata')
"@ | Out-File -FilePath $TessHookFile -Encoding utf8
    Write-Host "✓ Tesseract PyInstaller-Hook erstellt" -ForegroundColor Green
}

# ---------------------------------------------------------------------------
# 4. PyInstaller Build
# ---------------------------------------------------------------------------
Write-Host "📦 Erstelle EXE mit PyInstaller..." -ForegroundColor Yellow

# Tesseract-Binaries als --add-data übergeben
$AddDataArgs = @()
if (-not $SkipTesseract -and (Test-Path "$TesseractInstDir\tesseract.exe")) {
    $AddDataArgs += "--add-data", "$TesseractInstDir;tesseract"
}

$PyiArgs = @(
    "docsorter.spec",
    "--distpath", $DistDir,
    "--workpath", $BuildDir,
    "--noconfirm", "--clean"
) + $AddDataArgs

& pyinstaller @PyiArgs

$ExeDir = "$DistDir\$AppName"
if (-not (Test-Path $ExeDir)) {
    Write-Host "❌ $ExeDir nicht gefunden — PyInstaller fehlgeschlagen?" -ForegroundColor Red
    exit 1
}
Write-Host "✓ EXE erstellt: $ExeDir" -ForegroundColor Green

# ---------------------------------------------------------------------------
# 5. Inno Setup Installer
# ---------------------------------------------------------------------------
if (-not $SkipInstaller) {
    $InnoPath = "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
    if (-not (Test-Path $InnoPath)) { $InnoPath = "${env:ProgramFiles}\Inno Setup 6\ISCC.exe" }

    if (Test-Path $InnoPath) {
        Write-Host "📋 Erstelle Setup-Installer..." -ForegroundColor Yellow

        $IssContent = @"
[Setup]
AppName=Doc-Sorter
AppVersion=$Version
AppPublisher=DocSorter
AppPublisherURL=https://docsorter.app
AppSupportURL=https://github.com/docsorter/doc-sorter/issues
AppUpdatesURL=https://github.com/docsorter/doc-sorter/releases
DefaultDirName={autopf}\DocSorter
DefaultGroupName=DocSorter
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=${AppName}-Setup-${Version}
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\DocSorter.exe
ArchitecturesInstallIn64BitMode=x64
; Kein Terminal-Fenster beim Start
WindowResizable=no
DisableWelcomePage=no
DisableProgramGroupPage=auto

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[CustomMessages]
german.WelcomeLabel2=Doc-Sorter wird auf deinem Computer installiert.%n%nAlle Dokumente werden lokal verarbeitet — keine Cloud, keine Datenweitergabe.%n%nKlicke auf Weiter um fortzufahren.
english.WelcomeLabel2=Doc-Sorter will be installed on your computer.%n%nAll documents are processed locally — no cloud, no data sharing.%n%nClick Next to continue.

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Automatisch starten wenn Windows startet"; GroupDescription: "Autostart:"; Flags: unchecked

[Files]
; Hauptanwendung
Source: "dist\win\DocSorter\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Doc-Sorter";                  Filename: "{app}\DocSorter.exe"
Name: "{group}\Doc-Sorter deinstallieren";   Filename: "{uninstallexe}"
Name: "{commondesktop}\Doc-Sorter";          Filename: "{app}\DocSorter.exe"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "DocSorter"; ValueData: "{app}\DocSorter.exe"; Flags: uninsdeletevalue; Tasks: startupicon

[Run]
Filename: "{app}\DocSorter.exe"; Description: "Doc-Sorter jetzt starten"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill.exe"; Parameters: "/f /im DocSorter.exe"; Flags: runhidden; RunOnceId: "KillDocSorter"
"@
        $IssPath = "docsorter_setup.iss"
        $IssContent | Out-File -FilePath $IssPath -Encoding utf8
        & $InnoPath $IssPath
        Remove-Item $IssPath -Force

        Write-Host "✓ Installer: dist\${AppName}-Setup-${Version}.exe" -ForegroundColor Green
    } else {
        Write-Host "⚠ Inno Setup nicht gefunden → https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    }
}

# Cleanup Temp-Dateien
if (Test-Path "hooks\hook_tesseract.py") { Remove-Item "hooks\hook_tesseract.py" -Force }
if ((Test-Path "hooks") -and ((Get-ChildItem "hooks").Count -eq 0)) { Remove-Item "hooks" }

# ---------------------------------------------------------------------------
# Ergebnis
# ---------------------------------------------------------------------------
Write-Host ""
Write-Host "✅ Build abgeschlossen!" -ForegroundColor Green
Write-Host "   Ordner:    $ExeDir"
$Installer = "dist\${AppName}-Setup-${Version}.exe"
if (Test-Path $Installer) {
    $SizeMB = [math]::Round((Get-Item $Installer).Length / 1MB, 0)
    Write-Host "   Installer: $Installer  ($SizeMB MB)" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "   👆 Diese Datei auf der Landing Page zum Download anbieten!" -ForegroundColor White
}
