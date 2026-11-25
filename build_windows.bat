@echo off
chcp 65001 > nul
echo =======================================================
echo          Dead Lane - Compilação para Windows
echo =======================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [!] Ambiente virtual .venv não encontrado!
    echo Criando ambiente virtual com Python 3.14...
    py -3.14 -m venv .venv
    if errorlevel 1 (
        echo [!] Erro ao criar o ambiente virtual com 'py -3.14'. Tentando 'python'...
        python -m venv .venv
    )
)

echo [*] Instalando dependências e PyInstaller...
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt pyinstaller

echo.
echo [*] Gerando sprites e assets caso não existam...
.\.venv\Scripts\python.exe -c "from src.gerador_assets import gerar_todos_os_assets; gerar_todos_os_assets()"

echo.
echo [*] Compilando executável standalone com PyInstaller...
.\.venv\Scripts\pyinstaller.exe --clean build_windows.spec

if errorlevel 1 (
    echo.
    echo [X] Erro durante a compilação do executável!
    pause
    exit /b %errorlevel%
)

echo.
echo =======================================================
echo [V] Sucesso! Executável gerado em: dist\DeadLane.exe
echo =======================================================
echo.
pause
