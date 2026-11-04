<#
build.ps1
=========
Empacota o PeptMass num executável Windows com PyInstaller.

Uso:
    ./build.ps1                # build onedir em dist/PeptMass/
    ./build.ps1 -OneFile       # build onefile  em dist/PeptMass.exe
    ./build.ps1 -NoVenv        # usa o Python atual sem criar venv

Saída:
    dist/PeptMass/PeptMass.exe   (onedir)  ou  dist/PeptMass.exe (onefile)
#>
param(
    [switch]$OneFile,
    [switch]$NoVenv
)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

$python = "python"

if (-not $NoVenv) {
    if (-not (Test-Path ".venv-build")) {
        Write-Host "==> Criando venv de build (.venv-build)..." -ForegroundColor Cyan
        python -m venv .venv-build
    }
    $python = Join-Path $PSScriptRoot ".venv-build\Scripts\python.exe"
}

Write-Host "==> Instalando dependencias..." -ForegroundColor Cyan
& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt -r requirements-build.txt

Write-Host "==> Rodando a suite cientifica (rede de seguranca)..." -ForegroundColor Cyan
& $python test_suite.py
if ($LASTEXITCODE -ne 0) { throw "test_suite.py falhou - build abortado." }

if ($OneFile) { $env:PEPTMASS_ONEFILE = "1" } else { Remove-Item Env:\PEPTMASS_ONEFILE -ErrorAction SilentlyContinue }

Write-Host "==> Empacotando com PyInstaller..." -ForegroundColor Cyan
& $python -m PyInstaller peptmass.spec --noconfirm --clean
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou." }

Write-Host ""
Write-Host "==> Pronto. Artefatos em .\dist\" -ForegroundColor Green
Get-ChildItem dist
