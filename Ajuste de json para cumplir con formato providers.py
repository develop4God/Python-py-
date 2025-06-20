import json
from datetime import datetime
import re # Importar la librería de expresiones regulares

def adjust_json_for_multi_version(input_filepath, output_filepath):
    """
    Ajusta la estructura de un archivo JSON para soportar múltiples versiones
    de devocionales por fecha. La estructura de salida será:
    {'data': {'es': {'YYYY-MM-DD': [{...devocional RVR1960...}, {...devocional NTV...}]}}}
    Cada devocional en la lista debe tener su propio campo "version".

    Args:
        input_filepath (str): La ruta del archivo JSON de entrada (tu archivo actual).
        output_filepath (str): La ruta donde se guardará el nuevo archivo JSON ajustado.
    """
    try:
        with open(input_filepath, 'r', encoding='utf-8') as f:
            original_devocionales_list = json.load(f)

        # Crear un diccionario para agrupar devocionales por fecha
        devocionales_por_fecha = {}

        for devocional in original_devocionales_list:
            # Asegurarse de que el devocional tenga una fecha válida
            date_str = devocional.get('date')
            if not date_str:
                print(f"Advertencia: Devocional con ID '{devocional.get('id', 'N/A')}' no tiene campo 'date'. Se omite.")
                continue

            # Añadir el campo 'version' si no existe o asegurar que sea el correcto
            if 'version' not in devocional or not devocional['version']:
                versiculo = devocional.get('versiculo', '')
                # Intenta extraer la versión del paréntesis si existe (ej. "(RVR1960)")
                match = re.search(r'\((.*?)\)', versiculo)
                if match:
                    # Usar el texto dentro del paréntesis como la versión
                    devocional['version'] = match.group(1).strip()
                else:
                    # Asignar 'RVR1960' como valor por defecto si no se puede extraer
                    devocional['version'] = 'RVR1960' # Asignación por defecto correcta

            if date_str not in devocionales_por_fecha:
                devocionales_por_fecha[date_str] = []
            
            devocionales_por_fecha[date_str].append(devocional)

        # Crear la nueva estructura anidada
        adjusted_data = {
            'data': {
                'es': devocionales_por_fecha
            }
        }

        with open(output_filepath, 'w', encoding='utf-8') as f:
            json.dump(adjusted_data, f, indent=4, ensure_ascii=False)

        print(f"Archivo ajustado para múltiples versiones (con 'RVR1960' como default) guardado exitosamente en: {output_filepath}")
        print("Este archivo está listo para ser consumido por un DevocionalProvider flexible.")

    except FileNotFoundError:
        print(f"Error: El archivo de entrada no se encontró en '{input_filepath}'.")
    except json.JSONDecodeError:
        print(f"Error: No se pudo decodificar el JSON del archivo '{input_filepath}'.")
    except Exception as e:
        print(f"Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    # Define las rutas de tus archivos
    input_file = 'devocionales_consolidados_20250602_104839.json' # Tu archivo original
    output_file = 'devocionales_multi_version_structure_rvr1960.json' # Nuevo nombre para el archivo ajustado

    adjust_json_for_multi_version(input_file, output_file)
