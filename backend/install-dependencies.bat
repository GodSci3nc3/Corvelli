@echo off
REM Script de instalación automática de dependencias - Windows

echo ===========================================
echo   Corvelli - Instalacion de Dependencias
echo ===========================================
echo.

REM Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python no esta instalado
    echo Descarga desde: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python encontrado
python --version

REM Verificar Node.js
node --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js no esta instalado
    echo Descarga desde: https://nodejs.org/
    pause
    exit /b 1
)

echo [OK] Node.js encontrado
node --version
echo.

REM Instalar dependencias Python
echo Instalando paquetes Python...
pip install fastapi uvicorn pydantic paramiko pyserial python-dotenv requests

if %errorlevel% neq 0 (
    echo [ERROR] Error instalando paquetes Python
    pause
    exit /b 1
)

echo [OK] Paquetes Python instalados
echo.

REM Instalar dependencias Node.js
echo Instalando paquetes Node.js...
cd /d %~dp0
call npm install

if %errorlevel% neq 0 (
    echo [ERROR] Error instalando paquetes Node.js
    pause
    exit /b 1
)

echo [OK] Paquetes Node.js instalados
echo.
echo ===========================================
echo   [OK] Instalacion completada exitosamente
echo ===========================================
echo.
echo Ahora puedes ejecutar Corvelli
pause
