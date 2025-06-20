import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import json
import re
import os
from tkinter import ttk
from collections import Counter # Importar Counter para contar elementos y encontrar duplicados

class VerseExtractorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Extractor de Versículos Bíblicos")
        self.root.geometry("700x600")

        # Frame principal para organizar los elementos
        main_frame = tk.Frame(root)
        main_frame.pack(pady=10, padx=10, fill=tk.BOTH, expand=True)

        # Sección de selección de archivos
        file_selection_frame = tk.LabelFrame(main_frame, text="1. Selección de Archivos JSON")
        file_selection_frame.pack(fill=tk.X, pady=5, padx=5)

        self.select_files_button = tk.Button(file_selection_frame, text="Seleccionar Archivos JSON", command=self.select_files)
        self.select_files_button.pack(pady=5, padx=10)

        self.status_files_label = tk.Label(file_selection_frame, text="Esperando selección de archivos...")
        self.status_files_label.pack(pady=5, padx=10)

        # Sección de selección de carpeta de destino
        output_dir_frame = tk.LabelFrame(main_frame, text="2. Carpeta de Destino")
        output_dir_frame.pack(fill=tk.X, pady=5, padx=5)

        self.select_output_dir_button = tk.Button(output_dir_frame, text="Seleccionar Carpeta de Destino", command=self.select_output_directory)
        self.select_output_dir_button.pack(pady=5, padx=10)

        self.output_dir_label = tk.Label(output_dir_frame, text="Carpeta de destino: No seleccionada")
        self.output_dir_label.pack(pady=5, padx=10)

        # Sección de procesamiento
        process_frame = tk.LabelFrame(main_frame, text="3. Proceso de Extracción")
        process_frame.pack(fill=tk.X, pady=5, padx=5)

        self.process_button = tk.Button(process_frame, text="Procesar y Generar excluded_verses.json", command=self.process_files, state=tk.DISABLED)
        self.process_button.pack(pady=10, padx=10)

        # Barra de progreso
        self.progress_label = tk.Label(process_frame, text="Progreso: 0%")
        self.progress_label.pack(pady=2)
        self.progressbar = ttk.Progressbar(process_frame, orient="horizontal", length=400, mode="determinate")
        self.progressbar.pack(pady=5, padx=10)

        # Área de log
        log_frame = tk.LabelFrame(main_frame, text="Log de Procesamiento")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5)

        self.log_text = scrolledtext.ScrolledText(log_frame, wrap=tk.WORD, width=60, height=10, state='disabled')
        self.log_text.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)

        self.selected_files = []
        self.output_directory = ""
        self.all_extracted_verses = [] # Cambiado de set a list para permitir duplicados

        self._check_can_process()
        self.log_message("Aplicación iniciada. Seleccione archivos y una carpeta de destino.")

    def log_message(self, message):
        """Añade un mensaje al área de log."""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END) # Auto-scroll al final
        self.log_text.config(state='disabled')
        self.root.update_idletasks() # Actualizar la UI

    def select_files(self):
        file_paths = filedialog.askopenfilenames(
            title="Seleccionar archivos JSON",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")]
        )
        if file_paths:
            self.selected_files = list(file_paths)
            self.status_files_label.config(text=f"Archivos seleccionados: {len(self.selected_files)}")
            self.log_message(f"Archivos seleccionados: {len(self.selected_files)} archivo(s).")
            for fp in self.selected_files:
                self.log_message(f"- {os.path.basename(fp)}")
        else:
            self.selected_files = []
            self.status_files_label.config(text="Ningún archivo seleccionado.")
            self.log_message("Ningún archivo JSON seleccionado.")
        self._check_can_process()

    def select_output_directory(self):
        directory = filedialog.askdirectory(title="Seleccionar carpeta para guardar el archivo de salida")
        if directory:
            self.output_directory = directory
            self.output_dir_label.config(text=f"Carpeta de destino: {self.output_directory}")
            self.log_message(f"Carpeta de destino seleccionada: {self.output_directory}")
        else:
            self.output_directory = ""
            self.output_dir_label.config(text="Carpeta de destino: No seleccionada")
            self.log_message("Ninguna carpeta de destino seleccionada.")
        self._check_can_process()

    def _check_can_process(self):
        if self.selected_files and self.output_directory:
            self.process_button.config(state=tk.NORMAL)
        else:
            self.process_button.config(state=tk.DISABLED)

    def process_files(self):
        self.all_extracted_verses.clear() # Limpiar la lista para un nuevo procesamiento
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END) # Limpiar el log antes de un nuevo procesamiento
        self.log_text.config(state='disabled')
        self.log_message("Iniciando procesamiento de archivos...")

        total_files = len(self.selected_files)
        if total_files == 0:
            messagebox.showwarning("Advertencia", "No se han seleccionado archivos para procesar.")
            self.log_message("Error: No hay archivos seleccionados para procesar.")
            return
        if not self.output_directory:
            messagebox.showwarning("Advertencia", "No se ha seleccionado una carpeta de destino para el archivo de salida.")
            self.log_message("Error: No se ha seleccionado una carpeta de destino.")
            return

        self.progressbar['value'] = 0
        self.progress_label.config(text="Progreso: 0%")
        self.process_button.config(state=tk.DISABLED) # Deshabilitar el botón mientras se procesa

        processed_count = 0
        for i, file_path in enumerate(self.selected_files):
            file_name = os.path.basename(file_path)
            self.log_message(f"Procesando archivo ({i+1}/{total_files}): {file_name}")
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Recursivamente buscar solo en el campo 'versiculo'
                self._find_verses_in_json(data)

                processed_count += 1
                progress_percentage = int((processed_count / total_files) * 100)
                self.progressbar['value'] = progress_percentage
                self.progress_label.config(text=f"Progreso: {progress_percentage}%")
                self.root.update_idletasks()

            except json.JSONDecodeError:
                messagebox.showerror("Error de JSON", f"El archivo '{file_name}' no es un JSON válido y se omitirá.")
                self.log_message(f"Error de JSON: El archivo '{file_name}' no es válido y se ha omitido.")
                continue
            except FileNotFoundError:
                messagebox.showerror("Error de Archivo", f"El archivo '{file_name}' no se encontró y se omitirá.")
                self.log_message(f"Error de Archivo: El archivo '{file_name}' no se encontró y se ha omitido.")
                continue
            except Exception as e:
                messagebox.showerror("Error Desconocido", f"Ocurrió un error al procesar '{file_name}': {e}")
                self.log_message(f"Error Desconocido al procesar '{file_name}': {e}")
                continue

        # Ordenar la lista de versículos
        output_verses = sorted(self.all_extracted_verses)

        # Verificar duplicados
        verse_counts = Counter(output_verses)
        duplicates = [verse for verse, count in verse_counts.items() if count > 1]

        if duplicates:
            self.log_message("\n--- Versículos Duplicados Encontrados ---")
            for verse in duplicates:
                self.log_message(f"- '{verse}' (aparece {verse_counts[verse]} veces)")
            messagebox.showwarning("Versículos Duplicados", f"Se encontraron {len(duplicates)} versículos duplicados. Verifique el log para detalles.")
        else:
            self.log_message("\n--- No se encontraron versículos duplicados ---")
            messagebox.showinfo("Sin Duplicados", "No se encontraron versículos duplicados en la lista final.")

        output_file_path = os.path.join(self.output_directory, "excluded_verses.json")
        try:
            with open(output_file_path, 'w', encoding='utf-8') as outfile:
                json.dump(output_verses, outfile, indent=4, ensure_ascii=False)
            
            final_message = (
                f"Todos los versículos extraídos y guardados en '{output_file_path}'. "
                f"Cantidad total de versículos en el archivo final: {len(output_verses)} (incluyendo duplicados)."
            )
            messagebox.showinfo("Éxito", final_message)
            self.log_message(f"Proceso completado. {final_message}")
            self.progressbar['value'] = 100
            self.progress_label.config(text="Progreso: 100%")
        except Exception as e:
            messagebox.showerror("Error al guardar", f"No se pudo guardar '{output_file_path}': {e}")
            self.log_message(f"Error al guardar '{output_file_path}': {e}")
        finally:
            self._check_can_process() # Re-habilitar el botón después de procesar

    def _find_verses_in_json(self, data):
        """
        Función recursiva para buscar el campo 'versiculo' en la estructura JSON.
        Solo extrae la referencia del versículo de este campo específico,
        siempre y cuando se ajuste a un patrón de referencia bíblica.
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if key == "versiculo" and isinstance(value, str):
                    # Patrón para capturar solo la referencia del versículo (ej. "Juan 3:16", "1 Corintios 13:4-7", "Salmos 23")
                    # Este regex es más permisivo con el formato que sigue a la referencia (RVR, comillas, etc.)
                    # Se enfoca en extraer el inicio de la cadena que coincide con una referencia bíblica.
                    # Se ha mejorado para manejar acentos y la "ñ" en los nombres de libros.
                    # Ejemplo: "Hebreos 5:8-9 RVR1960: \"Texto\"" -> "Hebreos 5:8-9"
                    # Ejemplo: "Juan 3:16: \"Texto\"" -> "Juan 3:16"
                    # Ejemplo: "Salmos 23" -> "Salmos 23"
                    specific_verse_reference_pattern = re.compile(
                        r'^(?:[123]?\s?[A-Za-zñÑáéíóúÁÉÍÓÚüÜ]+\.?\s?\d+(?::\d+(?:-\d+)?)?)'
                    )
                    
                    match = specific_verse_reference_pattern.match(value.strip())
                    if match:
                        cleaned_verse = match.group(0).strip() # group(0) es el match completo del patrón
                        self.all_extracted_verses.append(cleaned_verse)
                        self.log_message(f"  - Extraído: {cleaned_verse}")
                    else:
                        self.log_message(f"  - No se pudo extraer el versículo con el patrón estricto del campo 'versiculo': '{value.strip()}'")

                elif isinstance(value, (dict, list)):
                    self._find_verses_in_json(value) # Llamada recursiva
        elif isinstance(data, list):
            for item in data:
                self._find_verses_in_json(item) # Llamada recursiva

if __name__ == "__main__":
    root = tk.Tk()
    app = VerseExtractorApp(root)
    root.mainloop()

