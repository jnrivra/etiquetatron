"""
EtiquetaSeparador - Separa etiquetas de envío de PDFs en imágenes individuales
https://github.com/jnrivra/etiquetatron
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
from PIL import Image
import io
import os
import re
import sys
import subprocess
import threading


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
                self.after(0, lambda p=progress: self.progress_bar.set(p * 0.5))  # Primera mitad para lectura

                page = doc[page_num]

                # Renderizar página a 200 DPI
                mat = fitz.Matrix(200/72, 200/72)  # 72 es el DPI base de PDF
                pix = page.get_pixmap(matrix=mat)

                # Convertir a PIL Image
                img_data = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_data))

                # Extraer texto de la página para obtener números de venta
                page_text = page.get_text()
                ventas = re.findall(r'Venta:\s*(S\d+)', page_text)

                # Dimensiones de la imagen
                img_width, img_height = img.size

                # Layout: 1 columna x 6 filas por página
                margin_x = 29
                label_width = img_width - (margin_x * 2)

                # Espaciado calibrado para 200 DPI
                first_y = 12
                spacing = 376  # Espaciado entre inicios de etiquetas
                label_height = 355  # Altura de cada etiqueta

                # Recortar etiquetas que tengan contenido
                for i, venta in enumerate(ventas):
                    if i >= 6:  # Máximo 6 etiquetas por página
                        break

                    y_start = first_y + int(i * spacing)
                    y_end = y_start + label_height

                    # Asegurar que no exceda los límites
                    if y_end > img_height:
                        y_end = img_height - 5

                    pos = (margin_x, y_start, margin_x + label_width, y_end)
                    label_img = img.crop(pos)

                    all_labels.append({
                        'image': label_img,
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
