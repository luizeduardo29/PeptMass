@echo off
REM ===========================================================================
REM build.bat - Empacota o PeptMass num executavel Windows com PyInstaller.
REM
REM Uso (prompt de comando) ou duplo-clique no Explorer:
REM     packaging\build.bat              build onedir em dist\PeptMass\PeptMass.exe
REM     packaging\build.bat onefile      build onefile  em dist\PeptMass.exe
REM     packaging\build.bat novenv       usa o Python atual sem criar venv
REM     packaging\build.bat onefile novenv   combina as duas opcoes
REM ===========================================================================
setlocal EnableExtensions

REM Trabalha sempre na raiz do projeto
cd /d "%~dp0.."

set "ONEFILE=0"
set "USEVENV=1"

:parse_args
if "%~1"=="" goto args_done
if /I "%~1"=="onefile" set "ONEFILE=1"
if /I "%~1"=="novenv"  set "USEVENV=0"
shift
goto parse_args
:args_done

set "PYTHON=python"

if "%USEVENV%"=="1" (
    if not exist ".venv-build\Scripts\python.exe" (
        echo ==^> Criando venv de build ^(.venv-build^)...
        python -m venv .venv-build
        if errorlevel 1 goto fail
    )
    set "PYTHON=%CD%\.venv-build\Scripts\python.exe"
)

echo ==^> Instalando dependencias...
"%PYTHON%" -m pip install --upgrade pip
if errorlevel 1 goto fail
"%PYTHON%" -m pip install -r requirements\build.txt
if errorlevel 1 goto fail

REM Suite cientifica (tests\): o build para se algum valor sair da referencia.
if not exist tests\test_science.py goto semtestes
echo ==^> Rodando a suite cientifica ^(rede de seguranca^)...
"%PYTHON%" tests\test_science.py
if errorlevel 1 (
    echo ERRO: test_science.py falhou - build abortado.
    goto fail
)
:semtestes

if "%ONEFILE%"=="1" (
    set "PEPTMASS_ONEFILE=1"
) else (
    set "PEPTMASS_ONEFILE="
)

echo ==^> Empacotando com PyInstaller...
"%PYTHON%" -m PyInstaller packaging\peptmass.spec --noconfirm --clean
if errorlevel 1 goto fail

echo.
echo ==^> Pronto. Artefatos em .\dist\
dir /b dist
echo.
pause
exit /b 0

:fail
echo.
echo ==^> BUILD FALHOU. Verifique as mensagens acima.
echo.
pause
exit /b 1
