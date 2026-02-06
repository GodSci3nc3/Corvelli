#!/bin/bash
# Script de instalación automática de dependencias - Linux/macOS

echo "==========================================="
echo "  Corvelli - Instalación de Dependencias"
echo "==========================================="
echo ""

# Verificar Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 no está instalado"
    echo "Instala con: sudo apt install python3 python3-pip"
    exit 1
fi

echo "✓ Python encontrado: $(python3 --version)"

# Verificar Node.js
if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js no está instalado"
    echo "Instala con: sudo apt install nodejs npm"
    exit 1
fi

echo "✓ Node.js encontrado: $(node --version)"
echo ""

# Instalar dependencias Python
echo "Instalando paquetes Python..."
pip3 install --user fastapi uvicorn pydantic paramiko pyserial python-dotenv requests

if [ $? -eq 0 ]; then
    echo "✓ Paquetes Python instalados"
else
    echo "✗ Error instalando paquetes Python"
    exit 1
fi

# Instalar dependencias Node.js
echo ""
echo "Instalando paquetes Node.js..."
cd "$(dirname "$0")"
npm install

if [ $? -eq 0 ]; then
    echo "✓ Paquetes Node.js instalados"
else
    echo "✗ Error instalando paquetes Node.js"
    exit 1
fi

echo ""
echo "==========================================="
echo "  ✓ Instalación completada exitosamente"
echo "==========================================="
echo ""
echo "Ahora puedes ejecutar Corvelli"
