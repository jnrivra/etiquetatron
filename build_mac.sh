#!/bin/bash
echo "========================================"
echo "  Construyendo EtiquetaSeparador"
echo "========================================"
echo

# Instalar dependencias
echo "Instalando dependencias..."
pip3 install -r requirements.txt pyinstaller

echo
echo "Creando ejecutable..."
pyinstaller --onefile --windowed --name "EtiquetaSeparador" main.py

echo
echo "========================================"
echo "  Build completado!"
echo "  El ejecutable esta en: dist/EtiquetaSeparador"
echo "========================================"
