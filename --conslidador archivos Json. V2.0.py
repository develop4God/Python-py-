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
            else: # Si existe el archivo base sin sufijo (primera vez que se genera ese timestamp)
                version = max(version, 0) # Asegura que al menos sea 0 para el primer sufijo (_1)
    
    if found_existing:
        version += 1 # Incrementa la versión si se encontró un archivo existente con el mismo timestamp
        final_filename = f"{current_base_name}_{version}.{extension}"
    else:
        final_filename = f"{current_base_name}.{extension}"
        
    return os.path.join(directory, final_filename)

def normalize_verse_reference(verse_str):
    """
    Normaliza una cadena de referencia de versículo para usarla como clave única.
    Extrae la referencia bíblica (ej. 'Filipenses 2:3-4 RVR1960') ignorando el texto de la cita.
    """
    if not isinstance(verse_str, str):
        return None

    # Patron para buscar el libro, capitulo y versiculo, y opcionalmente la versión.
    # Se ajusta para capturar hasta los dos puntos y luego el texto del versículo.
    # La clave está en no capturar el resto del texto después de la referencia.
    # Modificación aquí: el patrón se hace más específico para capturar solo la referencia.
    match = re.match(r"([\wáéíóúüñÁÉÍÓÚÜÑ\s]+(?: \d+:\d+(?:-\d+)?)?)\s*(RVR1960|NVI|DHH|LBLA|TLA)?", verse_str, re.IGNORECASE)
    
    if match:
        # Intenta obtener el grupo de la referencia (el primer grupo capturado)
        # Considera que la referencia puede no incluir un ":" si es solo el libro y capítulo
        # Por ejemplo, "Génesis 1"
        raw_reference = match.group(1).strip()
        
        # Eliminar cualquier comilla o texto adicional que pueda aparecer después de la referencia directa.
        # Por ejemplo, si viene 'Filipenses 2:3-4 RVR1960: "Nada hagáis..."'
        cleaned_reference = raw_reference.split(':', 1)[0].strip() # Tomar solo lo antes del primer ':'
        
        # Opcional: Estandarizar la capitalización y eliminar espacios extra.
        return re.sub(r'\s+', ' ', cleaned_reference).strip().upper()
    
    # Si el patrón no coincide, intentar una limpieza más simple o devolver None
    # Esto puede ocurrir si el formato es muy diferente o si el campo está vacío.
    # Agregamos una verificación para cadenas muy cortas o sin contenido útil.
    if len(verse_str.strip()) > 5: # Si la cadena es lo suficientemente larga para ser un versículo.
        # Intentar extraer algo si no hay un patrón claro, aunque esto puede no ser 100% único.
        # Por ejemplo, quitar solo el texto entre comillas después del primer ":".
        parts = verse_str.split(':', 1)
        if len(parts) > 1:
            return re.sub(r'["\'`].*$', '', parts[0]).strip().upper()
        else:
            return re.sub(r'["\'`].*$', '', verse_str).strip().upper()
    return None

def repair_json_string(json_str):
    """
    Intenta reparar un string JSON común problemas de formato.
    Añade corchetes si faltan, elimina comas finales, etc.
    """
    # Intentar cargar directamente
    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        pass # Intentar reparaciones

    # 1. Eliminar posible coma final en el último elemento de un objeto o array
    json_str = re.sub(r',\s*([}\]])', r'\1', json_str)
    
    # 2. Si el JSON es una secuencia de objetos sin un array contenedor, intentar envolverlo
    # Esto es una suposición y puede que no sea lo que se necesita en todos los casos
    # Aquí asumo que el JSON esperado es un objeto o un array de objetos.
    if not json_str.strip().startswith('[') and not json_str.strip().startswith('{'):
        json_str = f"[{json_str}]"
    
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"DEBUG: Error JSON después de reparación básica: {e}")
        # Intento de reparación más robusto: añadir un punto de acceso 'data' si no existe
        if not json_str.strip().startswith('{"data":'):
            json_str_with_data_wrapper = f'{{"data": {json_str}}}'
            try:
                return json.loads(json_str_with_data_wrapper)
            except json.JSONDecodeError as e_wrapped:
                print(f"DEBUG: Error JSON después de intentar envolver en 'data': {e_wrapped}")
        
        # Último intento: envolver en un array si es un objeto simple
        if json_str.strip().startswith('{') and not json_str.strip().startswith('['):
            try:
                return json.loads(f'[{json_str}]')
            except json.JSONDecodeError as e_array:
                print(f"DEBUG: Error JSON después de intentar envolver en array: {e_array}")

        # Si todo falla, devolver None o levantar el error original.
        return None


def consolidate_devotionals(file_paths, output_dir):
    """
    Consolida devocionales de múltiples archivos JSON.
    """
    total_devotionals_loaded = 0
    total_processed_files = 0
    all_devotionals = {}  # Usaremos un diccionario para almacenar devocionales por fecha y luego el objeto completo.
    all_verses_data = {}  # Para almacenar versículos únicos normalizados para la lista final

    for file_path in file_paths:
        print(f"--------------------------------------------------")
        print(f"Procesando '{os.path.basename(file_path)}'...")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            data = json.loads(content)
            
            # Si la carga falla, intentar reparar
        except json.JSONDecodeError as e:
            print(f"  ❌ Error de formato JSON en '{os.path.basename(file_path)}': {e}. Intentando reparar...")
            data = repair_json_string(content)
            if data is None:
                print(f"  ❌ No se pudo reparar '{os.path.basename(file_path)}'. Se omitirá.")
                continue # Saltar al siguiente archivo si no se pudo reparar
            else:
                print(f"  ✔ '{os.path.basename(file_path)}' reparado exitosamente.")

        total_processed_files += 1

        # Asumiendo que la estructura principal es {"data": {"es": {"YYYY-MM-DD": [...]}}}
        if "data" in data and "es" in data["data"]:
            for date_key, devotionals_list in data["data"]["es"].items():
                if date_key not in all_devotionals:
                    all_devotionals[date_key] = []

                for devocional in devotionals_list:
                    total_devotionals_loaded += 1
                    
                    # Extraer y normalizar el versículo para la unicidad
                    verse_reference = devocional.get("versiculo")
                    normalized_verse = normalize_verse_reference(verse_reference)

                    if normalized_verse:
                        # Usar una clave que combine la fecha y el versículo normalizado
                        unique_key = f"{date_key}_{normalized_verse}"
                        if unique_key not in all_verses_data:
                            all_devotionals[date_key].append(devocional)
                            all_verses_data[unique_key] = verse_reference # Guardar la versión original del versículo para la lista final
                        # else:
                            # print(f"    Advertencia: Devocional duplicado para '{normalized_verse}' en '{date_key}'. Se omitirá.")
                    else:
                        print(f"  ¡ADVERTENCIA! Devocional sin referencia de versículo válida para unicidad en '{os.path.basename(file_path)}'. Se omitirá: {verse_reference}")
            
            print(f"  '{os.path.basename(file_path)}' procesado. Devocionales agregados: {len(devotionals_list)}")
        else:
            print(f"  ❌ Estructura JSON inesperada en '{os.path.basename(file_path)}'. Se esperaba 'data' y 'es'. Se omitirá.")
            
    # Reorganizar los devocionales consolidados para la salida final
    final_consolidated_data = {"data": {"es": {}}}
    total_unique_devotionals = 0
    for date_key in sorted(all_devotionals.keys()):
        final_consolidated_data["data"]["es"][date_key] = all_devotionals[date_key]
        total_unique_devotionals += len(all_devotionals[date_key])

    total_devotionals_discarded_duplicates = total_devotionals_loaded - total_unique_devotionals

    # Guardar el JSON consolidado
    consolidated_json_filename_full_path = None
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        consolidated_json_filename_full_path = get_next_versioned_filename("devocionales_consolidados", "json", output_dir)
        with open(consolidated_json_filename_full_path, 'w', encoding='utf-8') as f:
            json.dump(final_consolidated_data, f, ensure_ascii=False, indent=4)
        print(f"✔ Devocionales consolidados guardados en: '{consolidated_json_filename_full_path}'")
    except Exception as e:
        print(f"❌ ERROR al guardar el JSON consolidado: {e}")

    # Guardar la lista de versículos utilizados
    list_verses_filename = None
    try:
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        list_verses_filename = get_next_versioned_filename("lista_versiculos", "txt", output_dir)
        with open(list_verses_filename, 'w', encoding='utf-8') as f:
            f.write("==================================================\n")
            f.write("           LISTA DE VERSÍCULOS UTILIZADOS         \n")
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
                                           f"Lista de versículos: {list_verses_filename}\n"
                                           f"Total de devocionales únicos: {total_unique_devotionals}")


def select_files_and_merge():
    """
    Función para la interfaz gráfica que permite seleccionar archivos y ejecutar la consolidación.
    """
    root = tk.Tk()
    root.withdraw() # Oculta la ventana principal de Tkinter

    messagebox.showinfo("Seleccionar Archivos", "Por favor, selecciona los archivos JSON de devocionales a consolidar.")
    file_paths = filedialog.askopenfilenames(
        title="Seleccionar Archivos JSON de Devocionales",
        filetypes=[("Archivos JSON", "*.json")]
    )

    if not file_paths:
        messagebox.showwarning("Sin Selección", "No se seleccionaron archivos. El proceso ha sido cancelado.")
        return

    # Pedir al usuario la carpeta de salida
    messagebox.showinfo("Carpeta de Salida", "Por favor, selecciona la carpeta donde se guardarán los archivos consolidados.")
    output_directory = filedialog.askdirectory(
        title="Seleccionar Carpeta de Salida para Devocionales Consolidados"
    )

    if not output_directory:
        messagebox.showwarning("Sin Carpeta de Salida", "No se seleccionó una carpeta de salida. El proceso ha sido cancelado.")
        return

    print("--- Iniciando proceso de fusión de devocionales JSON ---")
    print(f"Archivos JSON seleccionados para procesar: {', '.join([os.path.basename(p) for p in file_paths])}")
    print(f"Los archivos de salida se guardarán en: '{output_directory}'")
    
    consolidate_devotionals(file_paths, output_directory)

if __name__ == "__main__":
    try:
        select_files_and_merge()
    except Exception as e:
        messagebox.showerror("Error Crítico", f"Ha ocurrido un error inesperado: {e}\nPor favor, revisa la consola para más detalles.")
        print(f"ERROR CRÍTICO INESPERADO: {e}")