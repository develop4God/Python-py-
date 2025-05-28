import json
import os
import re
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

def get_next_versioned_filename(base_name, extension, directory="."):
    """
    Determina el siguiente nombre de archivo versionado incluyendo la fecha y hora de ejecución.
    Formato: base_YYYYMMDD_HHMMSS.ext
    Si ya existe un archivo con el mismo timestamp, añade un sufijo de conteo: base_YYYYMMDD_HHMMSS_1.ext
    """
    now = datetime.now()
    timestamp_str = now.strftime("%Y%m%d_%H%M%S")
    
    # Nombre base con timestamp
    current_base_name = f"{base_name}_{timestamp_str}"
    
    version = 0
    # Patrón para encontrar archivos con el mismo timestamp para añadir un sufijo incremental
    pattern = re.compile(rf"^{re.escape(current_base_name)}(?:_(\d+))?\.{re.escape(extension)}$")
    
    if not os.path.isdir(directory):
        os.makedirs(directory, exist_ok=True) 
        
    found_existing = False
    for filename in os.listdir(directory):
        match = pattern.match(filename)
        if match:
            found_existing = True
            if match.group(1): # Si existe un sufijo numérico (ej. _1, _2)
                current_version = int(match.group(1))
                if current_version > version:
                    version = current_version
            else: # Si existe el archivo base sin sufijo (primera colisión del mismo segundo)
                # Si el archivo sin sufijo existe, se considera la versión 0 o 1
                if version == 0: # Para asegurar que si el archivo sin sufijo ya existe, el siguiente sea _1
                    version = 1 

    if found_existing:
        return os.path.join(directory, f"{current_base_name}_{version + 1}.{extension}")
    else:
        return os.path.join(directory, f"{current_base_name}.{extension}")


def validate_and_load_json(filepath):
    """
    Valida y carga un archivo JSON.
    Intenta una reparación simple si falta el corchete de cierre ']' al final.
    Retorna la lista de devocionales y un mensaje de éxito/error/reparación.
    """
    content = ""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip() 
    except Exception as e:
        return None, f"¡ERROR! No se pudo leer el archivo '{filepath}': {e}"

    fixed_bracket_message = ""
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        if not content.endswith(']'):
            try:
                data = json.loads(content + ']')
                fixed_bracket_message = f"Se corrigió automáticamente el corchete de cierre faltante en '{filepath}'."
            except json.JSONDecodeError as e_fixed:
                return None, (
                    f"¡ADVERTENCIA! El archivo '{filepath}' fue descartado. No es un JSON válido y no pudo ser reparado.\n"
                    f"Error de parsing: {e_fixed.msg}\n"
                    f"Ubicación del fallo: Línea {e_fixed.lineno}, Columna {e_fixed.colno} (Carácter {e_fixed.pos})"
                )
        else:
            return None, (
                f"¡ADVERTENCIA! El archivo '{filepath}' fue descartado. No es un JSON válido.\n"
                f"Error de parsing: {e.msg}\n"
                f"Ubicación del fallo: Línea {e.lineno}, Columna {e.colno} (Carácter {e.pos})"
            )
    
    if not isinstance(data, list):
        if isinstance(data, dict):
            data = [data]
        else:
            return None, (
                f"¡ADVERTENCIA! El archivo '{filepath}' fue descartado. El contenido no es una lista de devocionales esperada (es de tipo '{type(data).__name__}')."
            )

    return data, fixed_bracket_message if fixed_bracket_message else "OK"

def normalize_verse_for_uniqueness(verse_text):
    """
    Normaliza el texto del versículo para usarlo como clave única de detección de duplicados.
    Quita espacios, dos puntos, y contenido entre paréntesis, y convierte a minúsculas.
    Ej: "Juan 3:16 (NTV): Porque..." -> "juan316"
    Ej: "Juan 3 : 16" -> "juan316"
    """
    if not verse_text:
        return None
    
    cleaned_text = re.sub(r'\s*\(.*?\)', '', verse_text)
    
    if ':' in cleaned_text:
        cleaned_text = cleaned_text.split(':', 1)[0]
    
    normalized_text = cleaned_text.replace(" ", "").replace(":", "").lower()
    
    return normalized_text

def get_display_verse_reference(devocional):
    """
    Extrae la referencia legible del versículo (Libro Capítulo:Versículo) para la lista final.
    Remueve cualquier texto de versión (ej. NTV, RV1960) y el texto posterior al versículo.
    
    Ej: "Efesios 2:8 (NTV): Dios los salvó..." -> "Efesios 2:8"
    Ej: "Juan 3:16: De tal manera..." -> "Juan 3:16"
    Ej: "1 Juan 2:1 NTV - \"Mis queridos hijos...\"" -> "1 Juan 2:1"
    """
    versiculo_completo = devocional.get('versiculo', '').strip()
    if not versiculo_completo:
        return None

    # Paso 1: Eliminar cualquier texto entre paréntesis (versión, ej. "(NTV)"),
    # y cualquier texto después de un guion. Esto nos deja solo la referencia principal.
    temp_reference = re.sub(r'\s*\(.*?\)', '', versiculo_completo)
    temp_reference = temp_reference.split('-', 1)[0].strip() # Quita texto después de un guion

    # Paso 2: Usar una regex para capturar "Libro Capítulo:Versículo" si está presente.
    # Prioriza formatos como "1 Juan 2:1"
    match_reference = re.match(r"^(.*?(\d+:\d+))", temp_reference) 
    if match_reference:
        cleaned_reference = match_reference.group(1).strip()
    else:
        # Fallback: Si no tiene "Capítulo:Versículo", busca "Libro Capítulo" (con al menos un número)
        # y quita todo lo que venga después de un posible primer dos puntos (si es el texto del versículo).
        cleaned_reference = temp_reference.split(':', 1)[0].strip()
        
        # Asegurarse de que al menos contenga un dígito para ser una referencia válida
        if not any(char.isdigit() for char in cleaned_reference):
            return None # No es una referencia válida si no tiene números
            
    return cleaned_reference.strip()


def main():
    root = tk.Tk()
    root.withdraw() 

    messagebox.showinfo("Selección de Archivos", "Por favor, selecciona uno o más archivos JSON de devocionales.")
    
    file_paths = filedialog.askopenfilenames(
        title="Selecciona archivos JSON de devocionales",
        filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")]
    )

    if not file_paths:
        messagebox.showinfo("Proceso Cancelado", "No se seleccionaron archivos. El proceso ha sido cancelado.")
        return

    # Usar el directorio del primer archivo seleccionado como directorio de salida
    output_directory = os.path.dirname(file_paths[0]) 

    print("--- Iniciando proceso de fusión de devocionales JSON ---")
    print(f"Archivos JSON seleccionados para procesar: {', '.join([os.path.basename(p) for p in file_paths])}")
    print(f"Los archivos de salida se guardarán en: '{output_directory}'")
    print("-" * 50)

    consolidated_devotionals = {}  
    total_processed_files = 0
    total_devotionals_loaded = 0
    total_devotionals_discarded_duplicates = 0
    
    all_verses_data = {} 

    for file_path in file_paths:
        json_file_basename = os.path.basename(file_path) 
        print(f"Procesando '{json_file_basename}'...")
        devotionals_data, message = validate_and_load_json(file_path)

        if devotionals_data is None:
            print(message) 
            print("-" * 50)
            continue 

        if message != "OK":
            print(f"  --> {message}") 

        total_processed_files += 1
        total_devotionals_loaded += len(devotionals_data)

        devotionals_added_from_current_file = 0

        for devocional in devotionals_data:
            normalized_verse_key = normalize_verse_for_uniqueness(devocional.get('versiculo'))
            
            if not normalized_verse_key:
                print(f"  ¡ADVERTENCIA! Devocional sin referencia de versículo válida para unicidad en '{json_file_basename}'. Se omitirá: {devocional.get('versiculo', 'N/A')}")
                continue 

            verse_text_for_list = get_display_verse_reference(devocional)
            
            if not verse_text_for_list:
                print(f"  ¡ADVERTENCIA! No se pudo extraer la referencia legible del versículo de '{json_file_basename}'. Se omitirá: {devocional.get('versiculo', 'N/A')}")
                continue 

            if normalized_verse_key in consolidated_devotionals:
                print(f"  Versículo '{verse_text_for_list}' no procesado de '{json_file_basename}' por estar duplicado.")
                total_devotionals_discarded_duplicates += 1
            else:
                consolidated_devotionals[normalized_verse_key] = devocional
                devotionals_added_from_current_file += 1
                
                all_verses_data[normalized_verse_key] = verse_text_for_list
        
        print(f"  '{json_file_basename}' procesado. Devocionales agregados: {devotionals_added_from_current_file}")
        print("-" * 50)

    final_devotionals_list = list(consolidated_devotionals.values())
    total_unique_devotionals = len(final_devotionals_list)

    # --- Generar archivo JSON consolidado ---
    consolidated_json_filename_full_path = get_next_versioned_filename("devocionales_consolidados", "json", output_directory)
    consolidated_json_filename_base = os.path.basename(consolidated_json_filename_full_path) 
    
    try:
        with open(consolidated_json_filename_full_path, 'w', encoding='utf-8') as f:
            json.dump(final_devotionals_list, f, ensure_ascii=False, indent=2)
        print(f"✔ Devocionales consolidados guardados en: '{consolidated_json_filename_full_path}'")
    except Exception as e:
        print(f"❌ ERROR al guardar el archivo consolidado JSON: {e}")

    # --- Generar archivo de lista de versículos ---
    list_verses_filename = get_next_versioned_filename("lista_versiculos", "txt", output_directory)
    try:
        with open(list_verses_filename, 'w', encoding='utf-8') as f:
            # Línea de origen del consolidado final (usando el nombre con fecha/hora)
            f.write(f"Origen de versículos: {consolidated_json_filename_base}\n") 
            f.write(f"Total de versículos únicos en la lista: {len(all_verses_data)}\n")
            f.write("--------------------------------------------------\n")
            
            sorted_verses = sorted(all_verses_data.values()) 
            
            for i, display_verse in enumerate(sorted_verses):
                f.write(f"{i+1}. {display_verse}\n")
        print(f"✔ Lista de versículos utilizada guardada en: '{list_verses_filename}'")
    except Exception as e:
        print(f"❌ ERROR al guardar la lista de versículos: {e}")

    # --- Resumen Final ---
    print("\n" + "=" * 50)
    print("                RESUMEN DEL PROCESO                ")
    print("=" * 50)
    print(f"Archivos JSON seleccionados: {len(file_paths)}")
    print(f"Archivos JSON procesados exitosamente (o reparados): {total_processed_files}")
    print(f"Total de devocionales leídos de archivos: {total_devotionals_loaded}")
    print(f"Devocionales únicos consolidados: {total_unique_devotionals}")
    print(f"Devocionales descartados por duplicado (mismo versículo normalizado): {total_devotionals_discarded_duplicates}")
    print(f"Versículos únicos extraídos para la lista: {len(all_verses_data)}") 
    print("=" * 50)
    print("Proceso completado.")
    messagebox.showinfo("Proceso Completado", "El proceso de fusión de devocionales ha finalizado.\n"
                                           f"Devocionales consolidados: {consolidated_json_filename_full_path}\n"
                                           f"Lista de versículos: {list_verses_filename}")

if __name__ == "__main__":
    main()

