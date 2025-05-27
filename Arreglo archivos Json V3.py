import json
import re
from datetime import datetime, timedelta
import unicodedata
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import sys

# --- Funciones de Utilidad ---
def clean_field_name(name):
    """
    Limpia el nombre de un campo: quita tildes y convierte a minúsculas.
    """
    name = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode('utf-8')
    return name.lower()

def extract_bible_ref(versiculo_text):
    """
    Extrae la referencia bíblica (ej. 'Juan 3:16') de un texto de versículo.
    Ahora busca el patrón incluso dentro de paréntesis al final.
    """
    # Regex para encontrar "Libro Capítulo:Versículo(s)"
    # Captura 1: Libro (incluyendo números y espacios para "1 Corintios")
    # Captura 2: Capítulo
    # Captura 3: Versículo(s) (permite rangos como 16-18)
    # Ajustada para buscar el patrón en cualquier parte de la cadena, incluso dentro de paréntesis.
    # El "(?:[A-Za-z0-9\s]+)?" es para ignorar la versión (NTV, RVR, etc.) después del versículo.
    # Se usa re.IGNORECASE para hacer la búsqueda insensible a mayúsculas/minúsculas.
    match = re.search(r'([0-9]*\s*[A-Za-záéíóúÁÉÍÓÚñÑ\s]+)\s*(\d+):(\d+(?:-\d+)?)\s*(?:[A-Za-z0-9\s]+)?', versiculo_text, re.IGNORECASE)
    
    if match:
        libro = match.group(1).strip()
        capitulo = match.group(2)
        versiculo_num = match.group(3)
        return f"{libro} {capitulo}:{versiculo_num}"
    
    return None

def normalize_book_name(book_name):
    """
    Normaliza los nombres de los libros para un ordenamiento alfabético correcto.
    Ej: "1 Juan" -> "01Juan", "Juan" -> "Juan"
    """
    book_name = unicodedata.normalize('NFKD', book_name).encode('ascii', 'ignore').decode('utf-8').lower()
    
    # Manejar libros con números para que se ordenen correctamente (1 Juan, 2 Juan, 3 Juan)
    if book_name.startswith('1 '):
        return '01' + book_name[2:]
    elif book_name.startswith('2 '):
        return '02' + book_name[2:]
    elif book_name.startswith('3 '):
        return '03' + book_name[2:]
    # Manejar libros como "Cantares de los Cantares" o "Salmos" donde solo queremos el primer prefijo para ordenar
    # Esto es una simplificación, si hay nombres muy largos y similares, se podría necesitar un mapeo.
    elif book_name.startswith('cantares'):
        return 'cantares' # Solo Cantares
    elif book_name.startswith('salmos'):
        return 'salmos' # Solo Salmos
    
    return book_name

def parse_bible_ref_for_sort(ref_string):
    """
    Parsea una cadena de referencia bíblica (ej. "Juan 3:16") en una tupla comparable para ordenar.
    Retorna (libro_normalizado, capitulo_int, versiculo_inicio_int).
    """
    match = re.match(r'([0-9]*\s*[A-Za-záéíóúÁÉÍÓÚñÑ\s]+)\s*(\d+):(\d+)(?:-\d+)?', ref_string, re.IGNORECASE)
    if match:
        book = normalize_book_name(match.group(1).strip())
        chapter = int(match.group(2))
        verse_start = int(match.group(3))
        return (book, chapter, verse_start)
    return ('z_unknown', 9999, 9999) # Fallback para poner al final si no se puede parsear

def generate_devocional_id(versiculo_text, existing_ids_set):
    """
    Genera un ID único para un devocional basado en su referencia bíblica.
    Formato: [primeras 4 letras del libro][capitulo][versiculo] (ej. juan316)
    Añade un sufijo numérico si el ID ya existe para asegurar la unicidad.
    `existing_ids_set` debe ser el conjunto de IDs ya usados/reservados.
    """
    bible_ref = extract_bible_ref(versiculo_text)
    if not bible_ref:
        return None # No se pudo extraer la referencia bíblica

    match = re.search(r'([0-9]*\s*[A-Za-záéíóúÁÉÍÓÚñÑ\s]+)\s*(\d+):(\d+)', bible_ref)
    if not match:
        return None # Fallback si extract_bible_ref no dio el formato esperado

    libro_raw = match.group(1).strip()
    capitulo = match.group(2)
    versiculo = match.group(3) # Esto podría ser un rango como "16-18"

    # Normalizar el nombre del libro para el ID
    libro_clean_for_id = unicodedata.normalize('NFKD', libro_raw).encode('ascii', 'ignore').decode('utf-8').replace(' ', '').lower()
    
    # Asegurarse de que el prefijo del libro sea de al menos 1 caracter, y máximo 4
    if len(libro_clean_for_id) >= 4:
        id_libro = libro_clean_for_id[0:4]
    elif len(libro_clean_for_id) > 0:
        id_libro = libro_clean_for_id # Si es "Job", que sea "job"
    else:
        return None # No se pudo derivar un prefijo de libro válido

    # Usar solo el primer número del versículo para el ID base si es un rango
    potential_id = f"{id_libro}{capitulo}{versiculo.split('-')[0]}"
    
    # Verificar unicidad del ID generado
    counter = 1
    original_potential_id = potential_id
    while potential_id in existing_ids_set:
        potential_id = f"{original_potential_id}_{counter}"
        counter += 1
    
    return potential_id

def generate_versioned_filename(base_filepath, ext_to_use=".json", suffix_prefix=""):
    """
    Genera un nombre de archivo versionado (ej. myfile_v1.json, Versiculos_myfile_v2.txt).
    Busca la última versión existente en el mismo directorio.
    suffix_prefix se usa para añadir un prefijo como "Versiculos_" al nombre base.
    ext_to_use permite especificar la extensión deseada para el archivo final (.json o .txt).
    """
    directory, filename = os.path.split(base_filepath)
    name, original_ext = os.path.splitext(filename)
    
    root_name_match = re.match(r'(.+?)(_v\d+)?$', name)
    root_name = root_name_match.group(1) if root_name_match else name

    search_name_prefix = f"{suffix_prefix}{root_name}"

    version_regex = re.compile(r'(_v)(\d+)$')

    max_version = 0
    if os.path.exists(directory) and os.path.isdir(directory):
        for existing_file in os.listdir(directory):
            if existing_file.startswith(search_name_prefix) and existing_file.endswith(ext_to_use):
                file_name_without_ext = os.path.splitext(existing_file)[0]
                match = version_regex.search(file_name_without_ext)
                if match:
                    try:
                        version = int(match.group(2))
                        if version > max_version:
                            max_version = version
                    except ValueError:
                        continue

    next_version = max_version + 1
    new_filename = f"{search_name_prefix}_v{next_version}{ext_to_use}"
    return os.path.join(directory, new_filename)

# --- Función Principal de Procesamiento ---
def process_and_merge_devocionales_interactive():
    root = tk.Tk()
    root.withdraw() # Oculta la ventana principal de Tkinter

    print("--- Proceso de Fusión y Actualización de Devocionales ---")
    print("Paso 1: Mostrando diálogo de selección única/múltiple de archivos.")

    # 1. Única selección de archivos: base + nuevos
    messagebox.showinfo(
        "Seleccionar Archivos",
        "Por favor, selecciona **primero el archivo JSON base (maestro)**.\n\n"
        "Luego, manteniendo 'Ctrl' (o la opción de selección múltiple de tu sistema), "
        "selecciona **todos los archivos JSON nuevos** que desees añadir.\n\n"
        "Haz clic en 'Abrir' (o equivalente) cuando hayas terminado."
    )
    selected_files = filedialog.askopenfilenames(
        title="Seleccionar Archivo Base Y Nuevos Archivos JSON",
        filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")]
    )

    if not selected_files:
        print("Error: No se seleccionó ningún archivo. El proceso no puede continuar.")
        root.destroy()
        sys.exit(1)

    # El primer archivo seleccionado es el base, el resto son los nuevos
    base_file = selected_files[0]
    new_file_paths = list(selected_files[1:])
    
    print(f"Paso 1 Completado: Archivo base detectado: '{base_file}'")
    if new_file_paths:
        print(f"  Nuevos archivos detectados ({len(new_file_paths)}): {new_file_paths}")
    else:
        print("  No se detectaron nuevos archivos JSON para añadir.")
    
    all_devocionales_raw = [] # Lista para recopilar todos los devocionales antes de procesar IDs y fechas
    
    # Set para controlar la duplicidad de referencias de versículos para el TXT/consola
    seen_refs_for_txt = set()
    all_versiculos_for_txt = [] # Almacena solo la referencia bíblica para el TXT y la consola

    # 2. Cargar devocionales existentes del archivo base
    print("\nPaso 2: Cargando devocionales del archivo base.")
    if os.path.exists(base_file) and os.path.getsize(base_file) > 0:
        try:
            with open(base_file, 'r', encoding='utf-8') as f:
                existing_devocionales_from_file = json.load(f)
            
            for devocional_item in existing_devocionales_from_file:
                # Limpiar nombres de campos y añadir a la lista raw
                cleaned_devocional = {}
                for key, value in devocional_item.items():
                    cleaned_devocional[clean_field_name(key)] = value
                all_devocionales_raw.append(cleaned_devocional)

                # Recopilar referencia bíblica para el TXT/consola, evitando duplicados
                ref = extract_bible_ref(cleaned_devocional.get('versiculo', ''))
                if ref and ref not in seen_refs_for_txt:
                    all_versiculos_for_txt.append(ref)
                    seen_refs_for_txt.add(ref)
            
            print(f"  Cargados {len(existing_devocionales_from_file)} devocionales del archivo base.")

        except json.JSONDecodeError as e:
            print(f"  Error: El archivo base '{base_file}' no es un JSON válido o está vacío. {e}")
        except Exception as e:
            print(f"  Error al cargar el archivo base '{base_file}': {e}")
    else:
        print(f"  Archivo base '{base_file}' no existe o está vacío. Se procesarán solo los nuevos devocionales si los hay.")
    print("Paso 2 Completado.")

    # 3. Cargar nuevos devocionales y añadirlos a la lista raw
    if new_file_paths:
        print("\nPaso 3: Cargando nuevos archivos JSON.")
        new_files_loaded_count = 0
        for filepath in new_file_paths:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        new_files_loaded_count += 1
                        print(f"  - Cargado '{os.path.basename(filepath)}' ({len(data)} entradas).")
                        
                        for devocional_item in data:
                            cleaned_devocional = {}
                            for key, value in devocional_item.items():
                                cleaned_devocional[clean_field_name(key)] = value
                            all_devocionales_raw.append(cleaned_devocional)

                            # Recopilar referencia bíblica para el TXT/consola, evitando duplicados
                            ref = extract_bible_ref(cleaned_devocional.get('versiculo', ''))
                            if ref and ref not in seen_refs_for_txt:
                                all_versiculos_for_txt.append(ref)
                                seen_refs_for_txt.add(ref)
                    else:
                        print(f"  - Advertencia: '{os.path.basename(filepath)}' no contiene una lista de devocionales. Omitido.")
            except json.JSONDecodeError:
                print(f"  - Error: '{os.path.basename(filepath)}' no es un JSON válido. Omitido.")
            except Exception as e:
                print(f"  - Error al cargar '{os.path.basename(filepath)}': {e}. Omitido.")
        
        if not all_devocionales_raw: # Si después de cargar base y nuevos, no hay nada
            print("Error: No se pudieron cargar devocionales de ningún archivo (base o nuevos). Proceso cancelado.")
            root.destroy()
            sys.exit(1)
        print(f"Paso 3 Completado: {new_files_loaded_count} nuevos archivos cargados.")
    else:
        print("Paso 3 Completado: No hay nuevos archivos JSON para procesar.")

    # 4. Asignar IDs y Fechas a todos los devocionales y organizar la lista final.
    print("\nPaso 4: Asignando IDs y fechas a todos los devocionales.")
    
    # Conjunto para rastrear todos los IDs que se asignan, sean del tipo que sean
    # Esto es crucial para la unicidad de los IDs.
    assigned_ids = set() 
    
    # Primero, iterar para generar los IDs tipo juan316 y reservar sus espacios
    # No asignamos los IDs de respaldo aún, solo los juan316.
    for devocional in all_devocionales_raw:
        # Si el devocional ya trae un ID, lo usamos si es único
        if 'id' in devocional and devocional['id'] and devocional['id'] not in assigned_ids:
            assigned_ids.add(devocional['id'])
            # No hacemos nada más, ya tiene un ID válido y único
        else:
            # Intentar generar un ID juan316. Si ya existe, generate_devocional_id le dará un sufijo.
            generated_id = generate_devocional_id(devocional.get('versiculo', ''), assigned_ids)
            if generated_id:
                devocional['id'] = generated_id
                assigned_ids.add(generated_id)
            # Si no se pudo generar (ej. no hay versículo), o si el ID del devocional era duplicado,
            # 'id' se quedará sin asignar temporalmente o con su valor original si no era válido.
            # Se manejará con un fallback en la siguiente fase si es necesario.

    # Ahora, re-iterar para asignar IDs de respaldo a los que no tienen uno válido/único
    id_fallback_counter = 1
    for devocional in all_devocionales_raw:
        if 'id' not in devocional or not devocional['id'] or devocional['id'] not in assigned_ids:
            # Si el ID no existe o no se asignó en la fase anterior, darle un fallback
            while f"devocional_fallback_{id_fallback_counter}" in assigned_ids:
                id_fallback_counter += 1
            devocional['id'] = f"devocional_fallback_{id_fallback_counter}"
            assigned_ids.add(devocional['id'])
            print(f"  Advertencia: ID no generado para devocional. Usando ID de respaldo: {devocional['id']}")
        
    # --- Manejo de Fechas ---
    last_valid_date_from_existing = None
    for devocional in all_devocionales_raw:
        if 'date' in devocional and devocional['date']:
            try:
                current_dev_date = datetime.strptime(devocional['date'], '%Y-%m-%d')
                devocional['_temp_date_obj'] = current_dev_date # Guardar el objeto datetime temporalmente
                if last_valid_date_from_existing is None or current_dev_date > last_valid_date_from_existing:
                    last_valid_date_from_existing = current_dev_date
            except ValueError:
                devocional['_temp_date_obj'] = None 
                print(f"  Advertencia: Formato de fecha inválido en devocional con ID '{devocional['id']}'. Se le asignará una nueva fecha.")
        else:
            devocional['_temp_date_obj'] = None
    
    # Asignar fechas consecutivas a los que no tienen una fecha válida
    # Determinar la fecha de inicio para los devocionales sin fecha
    start_date_for_new_devs = last_valid_date_from_existing + timedelta(days=1) if last_valid_date_from_existing else datetime.now()
    current_assigned_date = start_date_for_new_devs

    # Recorrer todos los devocionales y asignar fechas
    for devocional in all_devocionales_raw:
        if devocional['_temp_date_obj'] is None: # Solo asignar si no tiene fecha válida ya
            devocional['date'] = current_assigned_date.strftime('%Y-%m-%d')
            devocional['_temp_date_obj'] = current_assigned_date 
            current_assigned_date += timedelta(days=1)
    
    # Ordenar la lista final por la fecha asignada (usando el objeto datetime temporal)
    # Esto garantiza que los devocionales con fechas originales se mantengan en orden,
    # y los nuevos/sin fecha se inserten cronológicamente después de ellos.
    final_devocionales_list = sorted(all_devocionales_raw, key=lambda x: x['_temp_date_obj'])

    # Eliminar la clave temporal '_temp_date_obj'
    for devocional in final_devocionales_list:
        if '_temp_date_obj' in devocional:
            del devocional['_temp_date_obj']

    print("Paso 4 Completado: IDs y fechas asignadas a todos los devocionales.")

    # 5. Guardar archivo JSON final versionado (automático)
    print("\nPaso 5: Guardando el archivo JSON final versionado.")
    json_output_file = generate_versioned_filename(base_file, ext_to_use=".json")

    try:
        with open(json_output_file, 'w', encoding='utf-8') as f:
            json.dump(final_devocionales_list, f, ensure_ascii=False, indent=2)
        total_devocionales = len(final_devocionales_list)
        print(f"Paso 5 Completado: Archivo JSON guardado como '{json_output_file}'.")
        print(f"Total de devocionales en el archivo maestro: {total_devocionales}.")
    except Exception as e:
        print(f"Error al guardar el archivo JSON: {e}")
        print(f"Asegúrate de que Pydroid tenga permisos de almacenamiento y que la ruta '{json_output_file}' sea escribible.")
        root.destroy()
        sys.exit(1)

    # 6. Generar y guardar el archivo TXT de versículos versionado (automático)
    print("\nPaso 6: Generando y guardando el archivo TXT de versículos.")
    versiculos_txt_output_file = "" 
    if all_versiculos_for_txt:
        # Ordenar la lista de referencias de versículos alfabéticamente
        all_versiculos_for_txt.sort(key=parse_bible_ref_for_sort)

        versiculos_txt_output_file = generate_versioned_filename(
            json_output_file, 
            ext_to_use=".txt", 
            suffix_prefix="Versiculos_"
        )
        
        try:
            with open(versiculos_txt_output_file, 'w', encoding='utf-8') as f:
                f.write("--- Versículos Contenidos en el Archivo Final ---\n")
                for idx, versiculo_ref in enumerate(all_versiculos_for_txt):
                    f.write(f"{idx+1}. {versiculo_ref}\n")
                f.write("--------------------------------------------------\n")
            print(f"Paso 6 Completado: Archivo de versículos guardado como: '{versiculos_txt_output_file}'.")
        except Exception as e:
            print(f"Error al guardar el archivo de versículos TXT: {e}")
            print(f"Asegúrate de que Pydroid tenga permisos de almacenamiento y que la ruta '{versiculos_txt_output_file}' sea escribible.")
    else:
        print("Paso 6 Completado: No se encontraron versículos para generar el archivo TXT.")

    # 7. Mensaje de Confirmación Final en Consola (Punto 1 y 2)
    print("\n--- Proceso Finalizado con Éxito ---")
    print(f"Archivos de salida generados:")
    print(f"  - JSON Maestro: '{json_output_file}'")
    print(f"  - TXT de Versículos: '{versiculos_txt_output_file}'")
    print(f"Total de devocionales procesados: {total_devocionales}")
    
    if all_versiculos_for_txt:
        print("\n--- Versículos Registrados en el Archivo Final (Ordenado) ---")
        for idx, versiculo_ref in enumerate(all_versiculos_for_txt):
            print(f"{idx+1}. {versiculo_ref}")
        print("--------------------------------------------------")
    else:
        print("No se registraron versículos en la lista final.")

    root.destroy() # Cierra la ventana de Tkinter al finalizar

    # PAUSA PARA MANTENER LA CONSOLA ABIERTA
    input("\nProceso completado. Presiona Enter para salir...") 
    sys.exit(0) # Salida exitosa

# --- Ejecutar el script ---
if __name__ == "__main__":
    process_and_merge_devocionales_interactive()
