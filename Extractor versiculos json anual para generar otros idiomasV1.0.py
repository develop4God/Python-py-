import json
import re
from typing import Dict, Set
import os
from tkinter import filedialog, Tk

class ExtractorVersiculos:
    def __init__(self):
        """Inicializa el extractor con traducciones de libros bíblicos."""
        self.traducciones_libros = {
            "Mateo": "Matthew", "Marcos": "Mark", "Lucas": "Luke", "Juan": "John", 
            "Hechos": "Acts", "Romanos": "Romans", "1 Corintios": "1 Corinthians", 
            "2 Corintios": "2 Corinthians", "Gálatas": "Galatians", "Efesios": "Ephesians", 
            "Filipenses": "Philippians", "Colosenses": "Colossians", "1 Tesalonicenses": "1 Thessalonians", 
            "2 Tesalonicenses": "2 Thessalonians", "1 Timoteo": "1 Timothy", "2 Timoteo": "2 Timothy", 
            "Tito": "Titus", "Filemón": "Philemon", "Hebreos": "Hebrews", "Santiago": "James", 
            "1 Pedro": "1 Peter", "2 Pedro": "2 Peter", "1 Juan": "1 John", "2 Juan": "2 John", 
            "3 Juan": "3 John", "Judas": "Jude", "Apocalipsis": "Revelation"
        }
        
        # Para portugués
        self.traducciones_pt = {
            "Mateo": "Mateus", "Marcos": "Marcos", "Lucas": "Lucas", "Juan": "João", 
            "Hechos": "Atos", "Romanos": "Romanos", "1 Corintios": "1 Coríntios", 
            "2 Corintios": "2 Coríntios", "Gálatas": "Gálatas", "Efesios": "Efésios", 
            "Filipenses": "Filipenses", "Colosenses": "Colossenses", "1 Tesalonicenses": "1 Tessalonicenses", 
            "2 Tesalonicenses": "2 Tessalonicenses", "1 Timoteo": "1 Timóteo", "2 Timoteo": "2 Timóteo", 
            "Tito": "Tito", "Filemón": "Filemon", "Hebreos": "Hebreus", "Santiago": "Tiago", 
            "1 Pedro": "1 Pedro", "2 Pedro": "2 Pedro", "1 Juan": "1 João", "2 Juan": "2 João", 
            "3 Juan": "3 João", "Judas": "Judas", "Apocalipsis": "Apocalipse"
        }
        
        # Para francés
        self.traducciones_fr = {
            "Mateo": "Matthieu", "Marcos": "Marc", "Lucas": "Luc", "Juan": "Jean", 
            "Hechos": "Actes", "Romanos": "Romains", "1 Corintios": "1 Corinthiens", 
            "2 Corintios": "2 Corinthiens", "Gálatas": "Galates", "Efesios": "Éphésiens", 
            "Filipenses": "Philippiens", "Colosenses": "Colossiens", "1 Tesalonicenses": "1 Thessaloniciens", 
            "2 Tesalonicenses": "2 Thessaloniciens", "1 Timoteo": "1 Timothée", "2 Timoteo": "2 Timothée", 
            "Tito": "Tite", "Filemón": "Philémon", "Hebreos": "Hébreux", "Santiago": "Jacques", 
            "1 Pedro": "1 Pierre", "2 Pedro": "2 Pierre", "1 Juan": "1 Jean", "2 Juan": "2 Jean", 
            "3 Juan": "3 Jean", "Judas": "Jude", "Apocalipsis": "Apocalypse"
        }
        
        # Para chino simplificado
        self.traducciones_zh = {
            "Mateo": "马太福音", "Marcos": "马可福音", "Lucas": "路加福音", "Juan": "约翰福音",
            "Hechos": "使徒行传", "Romanos": "罗马书", "1 Corintios": "哥林多前书",
            "2 Corintios": "哥林多后书", "Gálatas": "加拉太书", "Efesios": "以弗所书",
            "Filipenses": "腓立比书", "Colosenses": "歌罗西书", "1 Tesalonicenses": "帖撒罗尼迦前书",
            "2 Tesalonicenses": "帖撒罗尼迦后书", "1 Timoteo": "提摩太前书", "2 Timoteo": "提摩太后书",
            "Tito": "提多书", "Filemón": "腓利门书", "Hebreos": "希伯来书", "Santiago": "雅各书",
            "1 Pedro": "彼得前书", "2 Pedro": "彼得后书", "1 Juan": "约翰一书", "2 Juan": "约翰二书",
            "3 Juan": "约翰三书", "Judas": "犹大书", "Apocalipsis": "启示录"
        }
        
        # Para japonés
        self.traducciones_ja = {
            "Mateo": "マタイの福音書", "Marcos": "マルコの福音書", "Lucas": "ルカの福音書", "Juan": "ヨハネの福音書",
            "Hechos": "使徒の働き", "Romanos": "ローマ人への手紙", "1 Corintios": "コリント人への手紙第一",
            "2 Corintios": "コリント人への手紙第二", "Gálatas": "ガラテヤ人への手紙", "Efesios": "エペソ人への手紙",
            "Filipenses": "ピリピ人への手紙", "Colosenses": "コロサイ人への手紙", "1 Tesalonicenses": "テサロニケ人への手紙第一",
            "2 Tesalonicenses": "テサロニケ人への手紙第二", "1 Timoteo": "テモテへの手紙第一", "2 Timoteo": "テモテへの手紙第二",
            "Tito": "テトスへの手紙", "Filemón": "ピレモンへの手紙", "Hebreos": "ヘブル人への手紙", "Santiago": "ヤコブの手紙",
            "1 Pedro": "ペテロの手紙第一", "2 Pedro": "ペテロの手紙第二", "1 Juan": "ヨハネの手紙第一", "2 Juan": "ヨハネの手紙第二",
            "3 Juan": "ヨハネの手紙第三", "Judas": "ユダの手紙", "Apocalipsis": "ヨハネの黙示録"
        }

    def seleccionar_archivo(self) -> str:
        """Abre selector de archivos."""
        root = Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        
        archivo = filedialog.askopenfilename(
            title="Selecciona el archivo JSON",
            filetypes=[("Archivos JSON", "*.json"), ("Todos los archivos", "*.*")]
        )
        root.destroy()
        return archivo

    def extraer_versiculos_del_json(self, archivo_json: str) -> Set[str]:
        """Extrae versículos únicos del JSON."""
        versiculos = set()
        
        try:
            with open(archivo_json, 'r', encoding='utf-8') as f:
                datos = json.load(f)
            
            print(f"✅ Archivo cargado: {os.path.basename(archivo_json)}")
            
            # Navegar estructura: data -> idiomas -> fechas -> devocionales
            if 'data' in datos:
                for idioma, fechas in datos['data'].items():
                    for fecha, devocionales in fechas.items():
                        if isinstance(devocionales, list):
                            for devocional in devocionales:
                                if isinstance(devocional, dict) and 'versiculo' in devocional:
                                    texto_versiculo = devocional['versiculo']
                                    
                                    # Extraer libro, capítulo y versículo
                                    patron = r'([A-Za-záéíóúüñÁÉÍÓÚÜÑ\s\d]+?)\s+(\d+):(\d+(?:-\d+)?)'
                                    match = re.search(patron, texto_versiculo)
                                    
                                    if match:
                                        libro = match.group(1).strip()
                                        capitulo = match.group(2)
                                        versiculo = match.group(3)
                                        
                                        cita = f"{libro} {capitulo}:{versiculo}"
                                        versiculos.add(cita)
            
            print(f"📊 Extraídos {len(versiculos)} versículos únicos")
            return versiculos
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return set()

    def traducir_versiculos(self, versiculos_es: Set[str]) -> Dict[str, Set[str]]:
        """Traduce versículos a otros idiomas."""
        versiculos_traducidos = {
            'es': set(),
            'en': set(),
            'pt': set(),
            'fr': set(),
            'zh': set(),
            'ja': set()
        }
        
        for versiculo in versiculos_es:
            # Extraer partes del versículo
            match = re.match(r'(.+?)\s+(\d+:\d+(?:-\d+)?)', versiculo)
            if match:
                libro = match.group(1).strip()
                cap_vers = match.group(2)
                
                # Español (original)
                versiculos_traducidos['es'].add(f"{libro} {cap_vers}")
                
                # Inglés
                libro_en = self.traducciones_libros.get(libro, libro)
                versiculos_traducidos['en'].add(f"{libro_en} {cap_vers}")
                
                # Portugués
                libro_pt = self.traducciones_pt.get(libro, libro)
                versiculos_traducidos['pt'].add(f"{libro_pt} {cap_vers}")
                
                # Francés
                libro_fr = self.traducciones_fr.get(libro, libro)
                versiculos_traducidos['fr'].add(f"{libro_fr} {cap_vers}")
                
                # Chino simplificado
                libro_zh = self.traducciones_zh.get(libro, libro)
                versiculos_traducidos['zh'].add(f"{libro_zh} {cap_vers}")
                
                # Japonés
                libro_ja = self.traducciones_ja.get(libro, libro)
                versiculos_traducidos['ja'].add(f"{libro_ja} {cap_vers}")
        
        return versiculos_traducidos

    def formatear_para_codigo(self, versiculos: Set[str], idioma: str) -> str:
        """Formatea versículos en el estilo solicitado."""
        if not versiculos:
            return f"# No hay versículos en {idioma}"
        
        # Ordenar versículos
        versiculos_ordenados = sorted(list(versiculos))
        
        # Formatear en líneas de 10 elementos máximo
        lineas = []
        for i in range(0, len(versiculos_ordenados), 10):
            grupo = versiculos_ordenados[i:i+10]
            elementos = ', '.join(f'"{v}"' for v in grupo)
            if i + 10 >= len(versiculos_ordenados):
                lineas.append(f"    {elementos}")
            else:
                lineas.append(f"    {elementos},")
        
        return '\n'.join(lineas)

    def mostrar_resultados(self, versiculos_traducidos: Dict[str, Set[str]]):
        """Muestra los resultados formateados."""
        idiomas = {
            'es': 'ESPAÑOL',
            'en': 'INGLÉS', 
            'pt': 'PORTUGUÉS',
            'fr': 'FRANCÉS',
            'zh': 'CHINO (简体中文)',
            'ja': 'JAPONÉS (日本語)'
        }
        
        print(f"\n" + "="*80)
        print("📋 VERSÍCULOS EXTRAÍDOS Y TRADUCIDOS - LISTOS PARA COPIAR")
        print("="*80)
        
        for codigo, nombre in idiomas.items():
            versiculos = versiculos_traducidos.get(codigo, set())
            if versiculos:
                print(f"\n🌐 {nombre} ({len(versiculos)} versículos únicos):")
                print("-" * 50)
                formato_codigo = self.formatear_para_codigo(versiculos, codigo)
                print(formato_codigo)
        
        print(f"\n" + "="*80)
        print("✨ ¡Listo! Copia y pega el formato que necesites en tu código")
        print("="*80)

def main():
    """Función principal - Simple y directo."""
    print("🔍 EXTRACTOR SIMPLE DE VERSÍCULOS")
    print("="*40)
    
    extractor = ExtractorVersiculos()
    
    # Seleccionar archivo
    print("📁 Selecciona tu archivo JSON...")
    archivo = extractor.seleccionar_archivo()
    
    if not archivo:
        print("❌ No se seleccionó archivo.")
        return
    
    # Extraer versículos del JSON
    print(f"\n🔄 Procesando archivo...")
    versiculos_es = extractor.extraer_versiculos_del_json(archivo)
    
    if not versiculos_es:
        print("❌ No se encontraron versículos.")
        return
    
    # Traducir a otros idiomas
    print(f"🌐 Traduciendo a múltiples idiomas...")
    versiculos_traducidos = extractor.traducir_versiculos(versiculos_es)
    
    # Mostrar resultados formateados
    extractor.mostrar_resultados(versiculos_traducidos)
    
    input("\n⏎ Presiona Enter para salir...")

if __name__ == "__main__":
    main()
