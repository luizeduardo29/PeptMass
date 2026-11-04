@echo off
REM ===========================================================================
REM run.bat - Abre o PeptMass usando a venv isolada .venv
REM
REM Duplo-clique no Explorer. Na 1a vez, ou se a .venv sumir, ele cria a
REM venv e instala as dependencias automaticamente; depois so abre o app.
REM ===========================================================================
setlocal
cd /d "%~dp0"

set "VPY=.venv\Scripts\python.exe"
set "VPYW=.venv\Scripts\pythonw.exe"

if exist "%VPY%" goto run

echo ==^> Criando ambiente virtual .venv na primeira execucao...
python -m venv .venv
if errorlevel 1 goto novenv
echo ==^> Instalando dependencias, pode demorar na 1a vez...
"%VPY%" -m pip install --upgrade pip
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 goto nodeps

:run
start "" "%VPYW%" main.py
goto :eof

:novenv
echo ERRO ao criar a venv. O Python esta instalado e no PATH?
pause
exit /b 1

:nodeps
echo ERRO ao instalar dependencias. Ha conexao com a internet?
pause
exit /b 1
