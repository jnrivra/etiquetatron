@echo off
echo ========================================
echo   Construyendo EtiquetaSeparador.exe
echo ========================================
echo.

REM Instalar dependencias
echo Instalando dependencias...
pip install -r requirements.txt pyinstaller

echo.
echo Creando ejecutable...
pyinstaller --onefile --windowed --name "EtiquetaSeparador" --icon=NONE main.py

echo.
echo ========================================
echo   Build completado!
echo   El ejecutable esta en: dist\EtiquetaSeparador.exe
echo ========================================
pause
