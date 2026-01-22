"""
EtiquetaSeparador - Separa etiquetas de envío de PDFs en imágenes individuales
https://github.com/jnrivra/etiquetatron
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
from PIL import Image, ImageOps
import numpy as np
import io
import os
import re
import sys
import subprocess
import threading

# Dimensiones finales de etiqueta (62mm x 150mm a 300 DPI)
LABEL_WIDTH_MM = 62
LABEL_HEIGHT_MM = 150
DPI = 300
MARGIN_MM = 4  # Margen interno en mm

# Convertir a píxeles
LABEL_WIDTH_PX = int(LABEL_WIDTH_MM / 25.4 * DPI)   # ~732 px
LABEL_HEIGHT_PX = int(LABEL_HEIGHT_MM / 25.4 * DPI)  # ~1772 px
MARGIN_PX = int(MARGIN_MM / 25.4 * DPI)              # ~47 px


def detect_content_bounds(img, threshold=250):
    """
    Detecta el bounding box del contenido real en una imagen.
    Busca píxeles que no sean blancos (< threshold).
    Retorna (left, top, right, bottom) o None si no hay contenido.
    """
    # Convertir a escala de grises
    gray = img.convert('L')
    pixels = np.array(gray)

    # Encontrar píxeles con contenido (no blancos)
    content_mask = pixels < threshold

    if not content_mask.any():
        return None

    # Encontrar los límites del contenido
    rows = np.any(content_mask, axis=1)
    cols = np.any(content_mask, axis=0)

    top = np.argmax(rows)
    bottom = len(rows) - np.argmax(rows[::-1])
    left = np.argmax(cols)
    right = len(cols) - np.argmax(cols[::-1])

    return (left, top, right, bottom)


def center_on_canvas(content_img, canvas_width, canvas_height, margin):
    """
    Centra una imagen de contenido en un canvas blanco con margen.
    Escala el contenido si es necesario para que quepa con el margen.
    """
    content_width, content_height = content_img.size

    # Área disponible para el contenido (canvas - márgenes)
    available_width = canvas_width - (2 * margin)
    available_height = canvas_height - (2 * margin)

    # Calcular factor de escala para que quepa
    scale_w = available_width / content_width
    scale_h = available_height / content_height
    scale = min(scale_w, scale_h, 1.0)  # No agrandar, solo reducir si es necesario

    # Escalar contenido si es necesario
    if scale < 1.0:
        new_width = int(content_width * scale)
        new_height = int(content_height * scale)
        content_img = content_img.resize((new_width, new_height), Image.LANCZOS)
        content_width, content_height = content_img.size

    # Crear canvas blanco
    canvas = Image.new('RGB', (canvas_width, canvas_height), (255, 255, 255))

    # Calcular posición centrada
    x = (canvas_width - content_width) // 2
    y = (canvas_height - content_height) // 2

    # Pegar contenido centrado
    if content_img.mode == 'RGBA':
        canvas.paste(content_img, (x, y), content_img)
    else:
        canvas.paste(content_img, (x, y))

    return canvas


def find_labels_in_page(img, ventas_count):
    """
    Detecta y extrae etiquetas individuales de una página.
    Divide la página en secciones y detecta el contenido en cada una.
    """
    img_width, img_height = img.size

    # Estimar altura de cada sección basándose en cantidad de etiquetas
    if ventas_count == 0:
        return []

    section_height = img_height // max(ventas_count, 1)

    labels = []
    for i in range(ventas_count):
        # Definir región aproximada de esta etiqueta
        y_start = i * section_height
        y_end = min((i + 1) * section_height + 20, img_height)  # +20 para overlap

        # Recortar sección
        section = img.crop((0, y_start, img_width, y_end))

        # Detectar contenido real dentro de la sección
        bounds = detect_content_bounds(section)

        if bounds:
            left, top, right, bottom = bounds
            # Agregar pequeño padding al recorte
            padding = 5
            left = max(0, left - padding)
            top = max(0, top - padding)
            right = min(section.width, right + padding)
            bottom = min(section.height, bottom + padding)

            # Recortar el contenido detectado
            content = section.crop((left, top, right, bottom))
            labels.append(content)
        else:
            # Si no detecta contenido, usar la sección completa
            labels.append(section)

    return labels


class EtiquetaSeparador(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configuración de la ventana
        self.title("Etiqueta Separador")
        self.geometry("600x500")
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

    def create_widgets(self):
        # Frame principal con padding
        self.main_frame = ctk.CTkFrame(self, corner_radius=0)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Logo/Título
        self.title_label = ctk.CTkLabel(
            self.main_frame,
            text="📦 Etiqueta Separador",
            font=ctk.CTkFont(size=28, weight="bold")
        )
        self.title_label.pack(pady=(20, 5))

        self.subtitle_label = ctk.CTkLabel(
            self.main_frame,
            text="Convierte PDFs de etiquetas en imágenes individuales",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        self.subtitle_label.pack(pady=(0, 30))

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
            text="github.com/jnrivra/etiquetatron",
            font=ctk.CTkFont(size=10),
            text_color="gray40"
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
