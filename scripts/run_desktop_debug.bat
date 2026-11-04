@echo off
REM ===========================================================================
REM run_desktop_debug.bat - Igual ao run_desktop.bat, mas com console visivel e segurando a
REM janela ao final. Use quando o run_desktop.bat abrir e fechar sozinho.
REM ===========================================================================
setlocal
cd /d "%~dp0.."

set "VPY=.venv\Scripts\python.exe"

if exist "%VPY%" goto run
echo ==^> Criando .venv e instalando dependencias...
python -m venv .venv
"%VPY%" -m pip install --upgrade pip
"%VPY%" -m pip install -r requirements\desktop.txt

:run
echo ==^> Rodando com a .venv...
"%VPY%" run_desktop.py
echo.
echo ==^> O PeptMass foi encerrado. Se houve erro, a mensagem esta acima.
pause
