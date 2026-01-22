"""
EtiquetaTron - Separa etiquetas de envío de PDFs en imágenes individuales
Desarrollado para Mawida Dispensario
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageOps, ImageTk
import io
import os
import re
import sys
import subprocess
import threading

# Dimensiones finales de etiqueta (150mm ancho x 62mm alto a 300 DPI)
# Etiqueta horizontal/apaisada
LABEL_WIDTH_MM = 150
LABEL_HEIGHT_MM = 62
DPI = 300
MARGIN_MM = 3  # Margen interno en mm

# Convertir a píxeles
LABEL_WIDTH_PX = int(LABEL_WIDTH_MM / 25.4 * DPI)   # ~1772 px
LABEL_HEIGHT_PX = int(LABEL_HEIGHT_MM / 25.4 * DPI)  # ~732 px
MARGIN_PX = int(MARGIN_MM / 25.4 * DPI)              # ~35 px


def detect_content_bounds(img, threshold=250):
    """
    Detecta el bounding box del contenido real en una imagen.
    Busca píxeles que no sean blancos (< threshold).
    Retorna (left, top, right, bottom) o None si no hay contenido.
    """
    # Convertir a escala de grises
    gray = img.convert('L')
    width, height = gray.size
    pixels = gray.load()

    # Encontrar límites del contenido
    left = width
    top = height
    right = 0
    bottom = 0

    for y in range(height):
        for x in range(width):
            if pixels[x, y] < threshold:
                if x < left:
                    left = x
                if x > right:
                    right = x
                if y < top:
                    top = y
                if y > bottom:
                    bottom = y

    # Verificar si se encontró contenido
    if right <= left or bottom <= top:
        return None

    return (left, top, right + 1, bottom + 1)


def center_on_canvas(content_img, canvas_width, canvas_height, margin):
    """
    Centra una imagen de contenido en un canvas blanco con margen.
    Escala el contenido para LLENAR el área disponible (manteniendo proporción).
    """
    content_width, content_height = content_img.size

    # Área disponible para el contenido (canvas - márgenes)
    available_width = canvas_width - (2 * margin)
    available_height = canvas_height - (2 * margin)

    # Calcular factor de escala para LLENAR el área (puede agrandar o reducir)
    scale_w = available_width / content_width
    scale_h = available_height / content_height
    scale = min(scale_w, scale_h)  # Mantener proporción, llenar lo máximo posible

    # Escalar contenido
    new_width = int(content_width * scale)
    new_height = int(content_height * scale)
    content_img = content_img.resize((new_width, new_height), Image.LANCZOS)

    # Crear canvas blanco
    canvas = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))

    # Calcular posición centrada
    x = (canvas_width - new_width) // 2
    y = (canvas_height - new_height) // 2

    # Pegar contenido centrado
    if content_img.mode == 'RGBA':
        canvas.paste(content_img, (x, y), content_img)
    else:
        canvas.paste(content_img, (x, y))

    return canvas


def find_horizontal_dividers(img, threshold=200):
    """
    Encuentra las líneas divisorias horizontales entre etiquetas.
    Busca filas que sean mayormente blancas/claras (divisores).
    """
    gray = img.convert('L')
    width, height = gray.size
    pixels = gray.load()

    dividers = [0]  # Empieza desde arriba

    # Buscar filas que sean mayormente claras (posibles divisores)
    y = 10
    while y < height - 10:
        # Contar píxeles claros en esta fila
        light_count = sum(1 for x in range(width) if pixels[x, y] > threshold)
        ratio = light_count / width

        # Si más del 95% es claro, es un divisor potencial
        if ratio > 0.95:
            # Buscar el centro del divisor
            start_y = y
            while y < height - 1 and sum(1 for x in range(width) if pixels[x, y] > threshold) / width > 0.95:
                y += 1
            divider_center = (start_y + y) // 2

            # Solo agregar si está suficientemente lejos del anterior
            if divider_center - dividers[-1] > 100:
                dividers.append(divider_center)
        y += 1

    dividers.append(height)  # Termina al final
    return dividers


def find_labels_in_page(img, ventas_count):
    """
    Detecta y extrae etiquetas individuales de una página.
    Busca las líneas divisorias horizontales y extrae cada sección.
    """
    img_width, img_height = img.size

    if ventas_count == 0:
        return []

    # Intentar encontrar divisores automáticamente
    dividers = find_horizontal_dividers(img)

    # Si no encontró suficientes divisores, usar división uniforme
    if len(dividers) - 1 < ventas_count:
        section_height = img_height // ventas_count
        dividers = [i * section_height for i in range(ventas_count + 1)]
        dividers[-1] = img_height

    labels = []
    for i in range(min(ventas_count, len(dividers) - 1)):
        y_start = dividers[i]
        y_end = dividers[i + 1] if i + 1 < len(dividers) else img_height

        # Recortar sección
        section = img.crop((0, y_start, img_width, y_end))

        # Detectar contenido real dentro de la sección
        bounds = detect_content_bounds(section, threshold=245)

        if bounds:
            left, top, right, bottom = bounds
            # Agregar pequeño padding
            padding = 8
            left = max(0, left - padding)
            top = max(0, top - padding)
            right = min(section.width, right + padding)
            bottom = min(section.height, bottom + padding)

            # Recortar el contenido detectado
            content = section.crop((left, top, right, bottom))
            labels.append(content)
        else:
            labels.append(section)

    return labels


class EtiquetaSeparador(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de la ventana
        self.title("EtiquetaTron - Mawida")
        self.geometry("600x580")
        self.resizable(False, False)

        # Tema oscuro moderno
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Variables
        self.pdf_path = None
        self.processing = False

        # Crear interfaz
        self.create_widgets()

        # Centrar ventana
        self.center_window()

    def center_window(self):
        self.update_idletasks()
        width = self.winfo_width()
        height = self.winfo_height()
        x = (self.winfo_screenwidth() // 2) - (width // 2)
        y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f'{width}x{height}+{x}+{y}')

    def _load_logo(self):
        """Carga el logo de Mawida desde archivo o recurso empaquetado."""
        try:
            # Buscar logo en diferentes ubicaciones
            if getattr(sys, 'frozen', False):
                # Ejecutable PyInstaller
                base_path = sys._MEIPASS
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))

            logo_path = os.path.join(base_path, 'logo.png')

            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                # Redimensionar manteniendo proporción (ancho máximo 280px)
                max_width = 280
                ratio = max_width / img.width
                new_height = int(img.height * ratio)
                img = img.resize((max_width, new_height), Image.LANCZOS)
                return ctk.CTkImage(light_image=img, dark_image=img, size=(max_width, new_height))
        except Exception:
            pass
        return None

    def create_widgets(self):
        # Frame principal con padding
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Logo de Mawida
        self.logo_image = self._load_logo()
        if self.logo_image:
            self.logo_label = ctk.CTkLabel(
                self.main_frame,
                image=self.logo_image,
                text=""
            )
            self.logo_label.pack(pady=(10, 5))

        # Título
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="EtiquetaTron",
            font=ctk.CTkFont(size=24, weight="bold")
        )
        self.title_label.pack(pady=(5, 5))

        self.subtitle_label = ctk.CTkLabel(
            self.main_frame,
            text="Convierte PDFs de etiquetas en imágenes individuales",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.subtitle_label.pack(pady=(0, 20))

        # Frame para selección de archivo
        self.file_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.file_frame.pack(fill="x", padx=20, pady=10)

        self.file_label = ctk.CTkLabel(
            self.file_frame,
            text="Ningún archivo seleccionado",
            font=ctk.CTkFont(size=12),
            text_color="gray"
        )
        self.file_label.pack(pady=(0, 10))

        self.select_button = ctk.CTkButton(
            self.file_frame,
            text="📁  Seleccionar PDF",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=45,
            width=250,
            corner_radius=10,
            command=self.select_pdf
        )
        self.select_button.pack(pady=10)

        # Separador visual
        self.separator = ctk.CTkFrame(self.main_frame, height=2, fg_color="gray30")
        self.separator.pack(fill="x", padx=40, pady=20)

        # Botón de procesar
        self.process_button = ctk.CTkButton(
            self.main_frame,
            text="⚡  Procesar Etiquetas",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            width=280,
            corner_radius=10,
            fg_color="#28a745",
            hover_color="#218838",
            command=self.process_pdf,
            state="disabled"
        )
        self.process_button.pack(pady=10)

        # Barra de progreso
        self.progress_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.progress_frame.pack(fill="x", padx=40, pady=(20, 10))

        self.progress_bar = ctk.CTkProgressBar(self.progress_frame, height=8, corner_radius=4)
        self.progress_bar.pack(fill="x")
        self.progress_bar.set(0)

        self.progress_label = ctk.CTkLabel(
            self.progress_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray"
        )
        self.progress_label.pack(pady=(5, 0))

        # Área de resultados
        self.result_frame = ctk.CTkFrame(self.main_frame, fg_color="gray20", corner_radius=10)
        self.result_frame.pack(fill="both", expand=True, padx=20, pady=(10, 20))

        # Fuente monoespaciada compatible con todos los sistemas
        if sys.platform == 'darwin':
            mono_font = "Menlo"
        elif sys.platform == 'win32':
            mono_font = "Consolas"
        else:
            mono_font = "DejaVu Sans Mono"

        self.result_text = ctk.CTkTextbox(
            self.result_frame,
            font=ctk.CTkFont(size=11, family=mono_font),
            fg_color="transparent",
            height=120
        )
        self.result_text.pack(fill="both", expand=True, padx=10, pady=10)
        self.result_text.insert("1.0", "Los resultados aparecerán aquí...")
        self.result_text.configure(state="disabled")

        # Créditos
        self.credits_label = ctk.CTkLabel(
            self.main_frame,
            text="Mawida Dispensario",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#1a5276"
        )
        self.credits_label.pack(pady=(0, 5))

    def select_pdf(self):
        file_path = filedialog.askopenfilename(
            title="Seleccionar PDF de etiquetas",
            filetypes=[("Archivos PDF", "*.pdf"), ("Todos los archivos", "*.*")]
        )

        if file_path:
            self.pdf_path = file_path
            filename = os.path.basename(file_path)
            self.file_label.configure(text=f"📄 {filename}", text_color="white")
            self.process_button.configure(state="normal")
            self.log_message(f"Archivo seleccionado: {filename}")

    def log_message(self, message):
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", message)
        self.result_text.configure(state="disabled")

    def append_log(self, message):
        self.result_text.configure(state="normal")
        self.result_text.insert("end", f"\n{message}")
        self.result_text.see("end")
        self.result_text.configure(state="disabled")

    def process_pdf(self):
        if self.processing:
            return

        # Validar que el archivo existe antes de procesar
        if not self.pdf_path or not os.path.isfile(self.pdf_path):
            messagebox.showerror("Error", "El archivo PDF no existe o fue eliminado.")
            self.pdf_path = None
            self.file_label.configure(text="Ningún archivo seleccionado", text_color="gray")
            self.process_button.configure(state="disabled")
            return

        self.processing = True
        self.process_button.configure(state="disabled", text="⏳ Procesando...")
        self.select_button.configure(state="disabled")
        self.progress_bar.set(0)  # Resetear barra de progreso

        # Procesar en hilo separado para no bloquear la UI
        thread = threading.Thread(target=self._process_pdf_thread)
        thread.daemon = True
        thread.start()

    def _process_pdf_thread(self):
        doc = None
        try:
            self.after(0, lambda: self.log_message("Iniciando procesamiento..."))

            # Abrir PDF con manejo seguro de recursos
            doc = fitz.open(self.pdf_path)
            total_pages = len(doc)

            # Validar que el PDF no esté vacío
            if total_pages == 0:
                raise ValueError("El PDF está vacío (no tiene páginas)")

            self.after(0, lambda t=total_pages: self.append_log(f"PDF abierto: {t} página(s)"))

            # Extraer fecha del primer texto encontrado
            first_page_text = doc[0].get_text()
            date_match = re.search(r'(\d{1,2}/\d{1,2}/\d{4})', first_page_text)

            if date_match:
                date_str = date_match.group(1)
                # Convertir de 21/1/2026 a 2026-01-21
                parts = date_str.split('/')
                folder_date = f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
            else:
                folder_date = "sin_fecha"

            self.after(0, lambda fd=folder_date: self.append_log(f"Fecha detectada: {fd}"))

            # Crear carpeta de salida (compatible con PyInstaller)
            if getattr(sys, 'frozen', False):
                exe_dir = os.path.dirname(sys.executable)
            else:
                exe_dir = os.path.dirname(os.path.abspath(__file__))
            output_dir = os.path.join(exe_dir, "etiquetas", folder_date)
            os.makedirs(output_dir, exist_ok=True)

            self.after(0, lambda fd=folder_date: self.append_log(f"Carpeta de salida: etiquetas/{fd}/"))

            # Procesar cada página
            all_labels = []

            for page_num in range(total_pages):
                progress = (page_num + 1) / total_pages
                self.after(0, lambda p=progress: self.progress_bar.set(p * 0.5))

                page = doc[page_num]

                # Renderizar página a alta resolución (300 DPI)
                mat = fitz.Matrix(DPI/72, DPI/72)
                pix = page.get_pixmap(matrix=mat)

                # Convertir a PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))

                # Extraer números de venta del texto
                page_text = page.get_text()
                ventas = re.findall(r'Venta:\s*(S\d+)', page_text)

                if not ventas:
                    self.after(0, lambda p=page_num+1:
                        self.append_log(f"Página {p}: sin etiquetas detectadas"))
                    continue

                # Detectar y extraer etiquetas de la página
                detected_labels = find_labels_in_page(img, len(ventas))

                # Emparejar etiquetas detectadas con números de venta
                for i, (venta, label_content) in enumerate(zip(ventas, detected_labels)):
                    # Centrar contenido en canvas final con margen
                    final_img = center_on_canvas(
                        label_content,
                        LABEL_WIDTH_PX,
                        LABEL_HEIGHT_PX,
                        MARGIN_PX
                    )

                    all_labels.append({
                        'image': final_img,
                        'venta': venta,
                        'page': page_num + 1
                    })

                self.after(0, lambda p=page_num+1, t=total_pages, v=len(ventas):
                    self.append_log(f"Página {p}/{t} procesada - {v} etiquetas"))

            # Cerrar documento PDF
            doc.close()
            doc = None

            # Verificar si se encontraron etiquetas
            if not all_labels:
                self.after(0, lambda: self.append_log("⚠️ No se encontraron etiquetas con formato 'Venta: SXXXXX'"))
                self.after(0, lambda: self._finish_processing(0, output_dir))
                return

            # Guardar etiquetas
            saved_count = 0
            used_names = {}
            total_labels = len(all_labels)

            for i, label in enumerate(all_labels):
                progress = 0.5 + (i + 1) / total_labels * 0.5
                self.after(0, lambda p=progress: self.progress_bar.set(p))

                venta = label['venta']

                # Manejar duplicados con contador incremental
                if venta in used_names:
                    used_names[venta] += 1
                    filename = f"{venta}_{used_names[venta]}.jpg"
                else:
                    used_names[venta] = 1
                    filename = f"{venta}.jpg"

                filepath = os.path.join(output_dir, filename)

                # Guardar como JPG con buena calidad
                label['image'].convert('RGB').save(filepath, 'JPEG', quality=95)
                saved_count += 1

            self.after(0, lambda: self.progress_bar.set(1.0))

            # Mensaje final
            self.after(0, lambda: self._finish_processing(saved_count, output_dir))

        except Exception as e:
            self.after(0, lambda err=str(e): self._handle_error(err))
        finally:
            # Asegurar que el documento PDF se cierre siempre
            if doc is not None:
                try:
                    doc.close()
                except:
                    pass

    def _finish_processing(self, count, output_dir):
        self.processing = False
        self.process_button.configure(state="normal", text="⚡  Procesar Etiquetas")
        self.select_button.configure(state="normal")

        self.append_log(f"\n{'='*40}")
        self.append_log(f"✅ ¡COMPLETADO!")
        self.append_log(f"   {count} etiquetas guardadas")
        self.append_log(f"   📁 {output_dir}")

        # Abrir carpeta de salida (con manejo de errores)
        try:
            if os.name == 'nt':  # Windows
                os.startfile(output_dir)
            elif sys.platform == 'darwin':  # macOS
                subprocess.run(['open', output_dir], check=False)
            else:  # Linux
                subprocess.run(['xdg-open', output_dir], check=False)
        except Exception:
            # Si falla al abrir la carpeta, no es crítico
            pass

        messagebox.showinfo(
            "Proceso completado",
            f"Se han guardado {count} etiquetas en:\n{output_dir}"
        )

    def _handle_error(self, error_message):
        self.processing = False
        self.process_button.configure(state="normal", text="⚡  Procesar Etiquetas")
        self.select_button.configure(state="normal")
        self.progress_bar.set(0)

        self.append_log(f"\n❌ ERROR: {error_message}")
        messagebox.showerror("Error", f"Ocurrió un error:\n{error_message}")


def main():
    app = EtiquetaSeparador()
    app.mainloop()


if __name__ == "__main__":
    main()
