Programas de Utilidad de Devocionales
🌐 Selecciona tu Idioma / Select your Language
Español (ES)

English (EN)

Español (ES)
Este proyecto incluye un conjunto de programas de utilidad diseñados para manipular, consolidar y procesar archivos JSON que contienen datos de devocionales bíblicos. Son herramientas complementarias a los programas principales de generación de devocionales.

🛠️ Especificaciones Técnicas
1. Ajuste de json para cumplir con formato providers.py
Propósito: Este script ajusta la estructura de un archivo JSON de devocionales existente para que sea compatible con un formato que puede soportar múltiples versiones de devocionales por fecha, anidando por idioma. Es útil para preparar datos antiguos o generados con un formato diferente para sistemas que esperan una estructura más anidada y detallada.

Librerías Clave: json, datetime, re (expresiones regulares).

Funcionalidad Clave:

adjust_json_for_multi_version(input_filepath, output_filepath): Función principal que lee un archivo JSON de entrada, itera sobre los devocionales, asegura que cada uno tenga un campo "version" (intentando extraerlo del versículo si es necesario, o asignando 'RVR1960' por defecto), y los agrupa por fecha.

Formato de Entrada Esperado: Una lista de objetos devocionales (ej. [{...}, {...}]).

Formato de Salida Generado:

{
    "data": {
        "es": {
            "YYYY-MM-DD": [
                { /* devocional RVR1960 */ },
                { /* devocional NTV */ }
            ]
        }
    }
}

Manejo de Errores: Incluye bloques try-except para FileNotFoundError, json.JSONDecodeError y otros errores generales durante el procesamiento de archivos.

2. --conslidador archivos Json. V2.0.py (Consolidador de Archivos JSON)
Propósito: Este script proporciona una interfaz gráfica de usuario (GUI) simple (usando Tkinter) que permite al usuario seleccionar múltiples archivos JSON de devocionales. Luego, los consolida en un único archivo JSON, eliminando devocionales duplicados basados en el versículo normalizado, y generando una lista de todos los versículos únicos utilizados.

Librerías Clave: json, os, re, datetime, tkinter (para la GUI), collections.Counter.

Funcionalidad Clave:

get_next_versioned_filename(): Determina el siguiente nombre de archivo versionado incluyendo la fecha y hora de ejecución para evitar sobrescribir archivos existentes.

normalize_verse_reference(verse_str): Normaliza una cadena de referencia de versículo para usarla como clave única, extrayendo la referencia bíblica sin el texto de la cita ni la versión (ej. "Filipenses 2:3-4" de "Filipenses 2:3-4 RVR1960: "Nada hagáis..."").

repair_json_string(json_str): Intenta reparar problemas comunes de formato en un string JSON para permitir su carga, como comas finales o falta de un array contenedor.

consolidate_devotionals(file_paths, output_dir): Función central que itera sobre los archivos seleccionados, los lee (intentando reparar JSONs inválidos), extrae devocionales, los agrupa por fecha y versículo normalizado para evitar duplicados, y guarda el resultado consolidado y una lista de versículos utilizados.

select_files_and_merge(): Configura la GUI (Tkinter) para la selección de archivos de entrada y la carpeta de salida, y luego llama a consolidate_devotionals.

Interfaz Gráfica (GUI): Utiliza tkinter para una interfaz de usuario básica que permite la selección interactiva de archivos y directorios mediante cuadros de diálogo. Muestra mensajes de estado y un resumen final.

Output: Genera un archivo JSON consolidado y un archivo .txt con la lista de versículos utilizados, ambos con nombres versionados que incluyen un timestamp.

3. --Excludes verses cargando archivo.py (Extractor de Versículos Excluidos)
Propósito: Este script, con su propia interfaz gráfica (GUI) de Tkinter, permite al usuario seleccionar archivos JSON de devocionales. Su función principal es extraer todas las referencias de versículos encontradas en el campo "versiculo" de los devocionales. Luego, genera un archivo excluded_verses.json que contiene una lista ordenada de estos versículos, útil para mantener un registro de versículos ya empleados en la generación o para identificar patrones. También detecta y reporta cualquier versículo duplicado en la lista extraída.

Librerías Clave: tkinter (para la GUI), filedialog, messagebox, scrolledtext, json, re, os, ttk, collections.Counter.

Funcionalidad Clave:

VerseExtractorApp: Clase principal que encapsula la GUI y la lógica de la aplicación.

select_files(): Permite seleccionar múltiples archivos JSON de entrada.

select_output_directory(): Permite seleccionar la carpeta donde se guardará el archivo excluded_verses.json.

process_files(): Inicia el proceso de extracción, actualiza una barra de progreso y el área de log en la GUI.

_find_verses_in_json(data): Función recursiva clave que busca específicamente el campo "versiculo" dentro de la estructura JSON. Utiliza una expresión regular (re.compile) para extraer solo la referencia bíblica limpia (ej., "Juan 3:16", "Hebreos 5:8-9") del contenido del campo.

Output: Genera un archivo excluded_verses.json con una lista de versículos extraídos. La lista final puede contener duplicados, los cuales son identificados y reportados en el log.

Interfaz Gráfica (GUI): Proporciona botones para la selección de archivos y directorio, una barra de progreso visual, y un área de texto desplazable para mostrar el log detallado del procesamiento.

Validación y Reporte: Incluye validación de archivos JSON y reporta errores. Utiliza collections.Counter para detectar y notificar al usuario sobre versículos duplicados encontrados en los archivos de entrada.

⚙️ Configuración y Ejecución
Requisitos Previos
Python 3.9+

pip (gestor de paquetes de Python)

Instalación de Dependencias
Navega a la raíz del proyecto y ejecuta:

pip install -r requirements.txt

(Si no tienes un requirements.txt, puedes crearlo con las siguientes librerías):

tkinter # Para la interfaz gráfica, a menudo ya incluida con Python
json
os
re
datetime
collections

Nota: tkinter usualmente viene preinstalado con Python, pero si tienes problemas, puede que necesites instalarlo por separado dependiendo de tu sistema operativo (ej., sudo apt-get install python3-tk en Debian/Ubuntu).

Ejecución de los Programas de Utilidad
Para ejecutar cualquiera de estos programas de utilidad, simplemente navega a la raíz del proyecto en tu terminal y ejecuta el script Python deseado:

Para Ajuste de json para cumplir con formato providers.py:

python "Ajuste de json para cumplir con formato providers.py"

Nota: Este script tiene rutas de archivo de entrada y salida definidas directamente en su sección if __name__ == "__main__":. Deberás editarlas en el código antes de ejecutarlo para que apunten a tus archivos.

Para --conslidador archivos Json. V2.0.py:

python "--conslidador archivos Json. V2.0.py"

Se abrirá una ventana GUI que te guiará para seleccionar los archivos JSON a consolidar y la carpeta de salida.

Para --Excludes verses cargando archivo.py:

python "--Excludes verses cargando archivo.2.0.py"

Se abrirá una ventana GUI que te guiará para seleccionar los archivos JSON de entrada y la carpeta donde se guardará el excluded_verses.json.

English (EN)
This project includes a set of utility programs designed to manipulate, consolidate, and process JSON files containing biblical devotional data. These are supplementary tools to the main devotional generation programs.

🛠️ Technical Specifications
1. Ajuste de json para cumplir con formato providers.py (Adjust JSON to Provider Format)
Purpose: This script adjusts the structure of an existing devotional JSON file to be compatible with a format that can support multiple devotional versions per date, nested by language. It is useful for preparing old data or data generated with a different format for systems expecting a more nested and detailed structure.

Key Libraries: json, datetime, re (regular expressions).

Key Functionality:

adjust_json_for_multi_version(input_filepath, output_filepath): Main function that reads an input JSON file, iterates over the devotionals, ensures each has a "version" field (attempting to extract it from the verse if necessary, or assigning 'RVR1960' by default), and groups them by date.

Expected Input Format: A list of devotional objects (e.g., [{...}, {...}]).

Generated Output Format:

{
    "data": {
        "es": {
            "YYYY-MM-DD": [
                { /* RVR1960 devotional */ },
                { /* NTV devotional */ }
            ]
        }
    }
}

Error Handling: Includes try-except blocks for FileNotFoundError, json.JSONDecodeError, and other general errors during file processing.

2. --conslidador archivos Json. V2.0.py (JSON Files Consolidator V2.0)
Purpose: This script provides a simple graphical user interface (GUI) (using Tkinter) that allows the user to select multiple JSON devotional files. It then consolidates them into a single JSON file, removing duplicate devotionals based on the normalized verse, and generating a list of all unique verses used.

Key Libraries: json, os, re, datetime, tkinter (for GUI), collections.Counter.

Key Functionality:

get_next_versioned_filename(): Determines the next versioned filename including the execution date and time to prevent overwriting existing files.

normalize_verse_reference(verse_str): Normalizes a verse reference string to use as a unique key, extracting the biblical reference without the citation text or version (e.g., "Filipenses 2:3-4" from "Filipenses 2:3-4 RVR1960: "Do nothing..."").

repair_json_string(json_str): Attempts to repair common formatting issues in a JSON string to allow it to be loaded, such as trailing commas or missing enclosing arrays.

consolidate_devotionals(file_paths, output_dir): Core function that iterates over selected files, reads them (attempting to repair invalid JSONs), extracts devotionals, groups them by date and normalized verse to avoid duplicates, and saves the consolidated result and a list of used verses.

select_files_and_merge(): Configures the Tkinter GUI for selecting input files and the output folder, then calls consolidate_devotionals.

Graphical User Interface (GUI): Uses tkinter for a basic user interface that allows interactive selection of files and directories via dialog boxes. Displays status messages and a final summary.

Output: Generates a consolidated JSON file and a .txt file with the list of used verses, both with versioned names that include a timestamp.

3. --Excludes verses cargando archivo.py (Verse Excluder Loader)
Purpose: This script, with its own Tkinter GUI, allows the user to select devotional JSON files. Its main function is to extract all verse references found in the "versiculo" field of the devotionals. It then generates an excluded_verses.json file containing a sorted list of these verses, useful for keeping a record of verses already used in generation or for identifying patterns. It also detects and reports any duplicate verses in the extracted list.

Key Libraries: tkinter (for GUI), filedialog, messagebox, scrolledtext, json, re, os, ttk, collections.Counter.

Key Functionality:

VerseExtractorApp: Main class encapsulating the GUI and application logic.

select_files(): Allows selecting multiple input JSON files.

select_output_directory(): Allows selecting the folder where the excluded_verses.json file will be saved.

process_files(): Initiates the extraction process, updates a progress bar and the log area in the GUI.

_find_verses_in_json(data): Key recursive function that specifically searches for the "versiculo" field within the JSON structure. It uses a regular expression (re.compile) to extract only the clean biblical reference (e.g., "Juan 3:16", "Hebreos 5:8-9") from the field's content.

Output: Generates an excluded_verses.json file with a list of extracted verses. The final list may contain duplicates, which are identified and reported in the log.

Graphical User Interface (GUI): Provides buttons for file and directory selection, a visual progress bar, and a scrollable text area to display detailed processing logs.

Validation and Reporting: Includes JSON file validation and error reporting. Uses collections.Counter to detect and notify the user about duplicate verses found in the input files.

⚙️ Setup and Execution
Prerequisites
Python 3.9+

pip (Python package installer)

Install Dependencies
Navigate to the project root and run:

pip install -r requirements.txt

(If you don't have a requirements.txt, you can create it with the following libraries):

tkinter # For the graphical interface, often already included with Python
json
os
re
datetime
collections

Note: tkinter is usually pre-installed with Python, but if you have issues, you might need to install it separately depending on your operating system (e.g., sudo apt-get install python3-tk on Debian/Ubuntu).

Running the Utility Programs
To run any of these utility programs, simply navigate to the project root in your terminal and execute the desired Python script:

For Ajuste de json para cumplir con formato providers.py:

python "Ajuste de json para cumplir con formato providers.py"

Note: This script has input and output file paths defined directly in its if __name__ == "__main__": section. You will need to edit them in the code before running to point to your files.

For --conslidador archivos Json. V2.0.py:

python "--conslidador archivos Json. V2.0.py"

A GUI window will open, guiding you to select the JSON files to consolidate and the output folder.

For --Excludes verses cargando archivo.py:

python "--Excludes verses cargando archivo.py"

A GUI window will open, guiding you to select the input JSON files and the folder where the excluded_verses.json will be saved.
