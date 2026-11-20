@echo off
REM ============================================
REM ULTRA RECIBOS - GERAR EXECUTAVEL E INSTALADOR
REM Execute no Windows, na pasta do projeto.
REM ============================================
setlocal
cd /d "%~dp0"

echo [1/4] Instalando dependencias...
python -m pip install -r requirements.txt || goto :erro

echo [2/4] Executando testes automatizados...
python tests\executar_testes.py || goto :erro

echo [3/4] Gerando executavel (PyInstaller)...
python -m PyInstaller --noconfirm --clean --distpath dist --workpath build UltraRecibos.spec || goto :erro

echo [4/4] Gerando instalador (Inno Setup)...
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (
    echo Inno Setup 6 nao encontrado. O executavel esta em dist\UltraRecibos.
    goto :fim
)
"%ISCC%" UltraRecibos_Instalador.iss || goto :erro

echo.
echo Concluido. Instalador gerado na pasta "instalador".
goto :fim

:erro
echo.
echo ERRO: o processo foi interrompido. Verifique as mensagens acima.
exit /b 1

:fim
endlocal
