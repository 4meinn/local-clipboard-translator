# Builds dist\LocalClipboardTranslator\ (PyInstaller) and, when Inno Setup is installed,
# dist\LocalClipboardTranslator-Setup.exe. Run from the repo root:
#   powershell -ExecutionPolicy Bypass -File packaging\build.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$py = Join-Path $root ".venv\Scripts\python.exe"
& $py -m pip install --quiet -e ".[dev]"
& $py tools\make_icon.py

& $py -m PyInstaller --noconfirm --clean --windowed `
    --name LocalClipboardTranslator `
    --icon assets\icon.ico `
    --paths src `
    --add-data "assets\characters;assets\characters" `
    --add-data "assets\icon.ico;assets" `
    --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.QtPdf `
    --exclude-module PySide6.QtOpenGL --exclude-module PySide6.QtSvg --exclude-module PySide6.QtDBus `
    packaging\run_app.py

$iscc = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
) | Where-Object { Test-Path $_ } | Select-Object -First 1

if ($iscc) {
    & $iscc packaging\installer.iss
} else {
    Write-Warning "Inno Setup not found, skipping the installer. The app folder is in dist\LocalClipboardTranslator."
}
