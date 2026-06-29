<div align="center">

<img src="logo.png" alt="Mawida Dispensario" width="320">

# EtiquetaTron

**Extrae etiquetas de envío desde PDFs y guárdalas como imágenes individuales listas para imprimir.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Plataforma-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#)
[![License](https://img.shields.io/badge/Licencia-MIT-green.svg)](LICENSE)
[![Build Windows EXE](https://github.com/jnrivra/etiquetatron/actions/workflows/build-windows.yml/badge.svg)](https://github.com/jnrivra/etiquetatron/actions/workflows/build-windows.yml)

</div>

---

## Descripción

**EtiquetaTron** es una aplicación de escritorio con interfaz gráfica que automatiza un trabajo repetitivo de logística: tomar un PDF que contiene varias etiquetas de envío por página y recortar cada etiqueta en una imagen individual de alta resolución, lista para imprimir.

Desarrollada para **Mawida Dispensario** para agilizar la preparación diaria de despachos.

### ¿Qué hace?

- 🔍 Detecta automáticamente los números de venta dentro del PDF (formato `Venta: SXXXXX`).
- ✂️ Recorta cada etiqueta y la renderiza a **300 DPI** para impresión nítida.
- 📐 Normaliza cada etiqueta a un tamaño exacto de **135 mm × 59 mm** (centrada sobre fondo blanco).
- 📅 Detecta la fecha del PDF y organiza la salida en carpetas por día (`etiquetas/AAAA-MM-DD/`).
- 🖼️ Guarda cada etiqueta como **PNG** a 300 DPI (mejor compatibilidad de DPI con impresoras).
- 🧵 Procesa en un hilo separado, con barra de progreso y registro en vivo, sin congelar la interfaz.
- 📂 Abre automáticamente la carpeta de resultados al terminar.

## Captura de pantalla

```
┌─────────────────────────────────────────┐
│           [ Mawida Dispensario ]         │
│                                         │
│             EtiquetaTron                 │
│   Convierte PDFs de etiquetas en        │
│   imágenes individuales                 │
│                                         │
│   📄 despacho_2024-01-15.pdf            │
│                                         │
│   [📁 Seleccionar PDF]                  │
│                                         │
│   [⚡ Procesar Etiquetas]               │
│                                         │
│   ████████████████░░░░ 75%              │
│                                         │
│   > Página 3/4 - 6 etiquetas            │
└─────────────────────────────────────────┘
```

## Requisitos del PDF

La aplicación espera PDFs con el siguiente formato:

- **Layout:** hasta 6 etiquetas por página, dispuestas en una columna.
- **Identificador:** cada etiqueta debe contener el texto `Venta: SXXXXX` (donde `X` son dígitos).
- **Fecha:** el PDF debe contener una fecha en formato `DD/MM/AAAA` para nombrar la carpeta de salida. Si no se encuentra, se usa la carpeta `sin_fecha`.

### Estructura esperada

```
┌─────────────────────┐
│  Etiqueta 1         │
│  Venta: S12345      │
├─────────────────────┤
│  Etiqueta 2         │
│  Venta: S12346      │
├─────────────────────┤
│  ...                │
├─────────────────────┤
│  Etiqueta 6         │
│  Venta: S12350      │
└─────────────────────┘
```

## Instalación

### Opción 1: Ejecutable (recomendado para usuarios finales)

Descarga el ejecutable más reciente desde la pestaña [Releases](../../releases) o, en el caso de Windows, desde los [artefactos de GitHub Actions](https://github.com/jnrivra/etiquetatron/actions/workflows/build-windows.yml). No requiere instalación: solo ejecutar.

### Opción 2: Desde el código fuente

```bash
# Clonar el repositorio
git clone https://github.com/jnrivra/etiquetatron.git
cd etiquetatron

# Crear un entorno virtual (opcional pero recomendado)
python -m venv venv
source venv/bin/activate        # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python main.py
```

## Uso

1. **Abre** la aplicación.
2. **Selecciona** un archivo PDF con etiquetas.
3. **Procesa** haciendo clic en el botón verde *Procesar Etiquetas*.
4. **Resultado:** las imágenes se guardan en `etiquetas/AAAA-MM-DD/` y la carpeta se abre automáticamente.

### Estructura de salida

```
etiquetas/
└── 2024-01-15/
    ├── S12345.png
    ├── S12346.png
    ├── S12347.png
    └── ...
```

Si aparecen números de venta duplicados, se nombran de forma incremental:

```
S12345.png
S12345_2.png
S12345_3.png
```

## Compilar ejecutables

El proyecto incluye scripts de compilación con [PyInstaller](https://pyinstaller.org/) que empaquetan también el logo.

### macOS

```bash
./build_mac.sh
```

El ejecutable se genera en `dist/EtiquetaTron`.

### Windows

```batch
build_windows.bat
```

El ejecutable se genera en `dist\EtiquetaTron.exe`.

### Compilación automática (CI)

Cada *push* a `main` dispara el workflow [`build-windows.yml`](.github/workflows/build-windows.yml), que compila el `.exe` de Windows en GitHub Actions y lo publica como artefacto descargable.

### Comando manual equivalente

```bash
pyinstaller --onefile --windowed --name "EtiquetaTron" --add-data "logo.png:." main.py
# En Windows usa ; en lugar de : -> --add-data "logo.png;."
```

## Stack tecnológico

| Paquete | Versión | Rol |
|---------|---------|-----|
| [customtkinter](https://github.com/TomSchimansky/CustomTkinter) | 5.2.1 | Interfaz gráfica moderna (tema oscuro) |
| [PyMuPDF](https://pymupdf.readthedocs.io/) (fitz) | 1.23.8 | Lectura y renderizado de PDFs |
| [Pillow](https://python-pillow.org/) | 10.2.0 | Manipulación y guardado de imágenes |
| [PyInstaller](https://pyinstaller.org/) | 6.3.0 | Empaquetado de ejecutables |

## Personalización

Los parámetros de recorte están calibrados para el layout de Mawida. Si tu PDF tiene un formato distinto, ajusta estos valores en `main.py` (método `_process_pdf_thread`):

```python
label_height_pts = 120  # Altura de cada etiqueta (en puntos PDF)
label_spacing    = 130  # Espaciado vertical entre etiquetas
margin_top       = 5    # Posición Y de la primera etiqueta
margin_sides     = 20   # Margen lateral
```

Y el tamaño final de salida en las constantes superiores:

```python
FINAL_WIDTH_PX  = 1594  # 135 mm a 300 DPI
FINAL_HEIGHT_PX = 697   # 59 mm a 300 DPI
```

## Licencia

Distribuido bajo licencia **MIT**. Consulta el archivo [LICENSE](LICENSE) para más detalles.

## Autor

Desarrollado por **Juan Enrique Rivera Olivares** ([@jnrivra](https://github.com/jnrivra)) para automatizar procesos de logística y despacho.
