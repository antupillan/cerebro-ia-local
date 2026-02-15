#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CEREBRO v10 - NEXO COGNITIVO & COLMENA DE DATOS
-----------------------------------------------
Integración: Baloo -> Sentidos -> Memoria.
Novedad: Decorador @memorizar para aprendizaje pasivo desde submódulos.
"""

import os
import sys
import threading
import subprocess
import shutil
import warnings
import functools
from concurrent.futures import ThreadPoolExecutor

# Configuración de Rutas (Absoluta para compartir memoria)
# Usamos una carpeta en el home para asegurar persistencia y acceso global
DB_PATH = os.path.expanduser("~/cerebro_datos/faiss_db")
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH, exist_ok=True)

MODELO_EMB = "bge-m3:latest"

# --- IMPORTACIÓN DE LOS SENTIDOS (MÓDULOS HERMANOS) ---
# Importamos dentro de métodos o con try/except para evitar ciclos si ellos nos importan a nosotros
try:
    import oido       
    import vision     
    import consejero  
except ImportError:
    pass # Se maneja dinámicamente

from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

warnings.filterwarnings("ignore")

class NexoCognitivo:
    def __init__(self):
        self.embeddings = OllamaEmbeddings(model=MODELO_EMB)
        self.vectorstore = self._cargar_memoria()
        self.executor = ThreadPoolExecutor(max_workers=2)

    def _cargar_memoria(self):
        if os.path.exists(os.path.join(DB_PATH, "index.faiss")):
            try: return FAISS.load_local(DB_PATH, self.embeddings, allow_dangerous_deserialization=True)
            except: pass
        return None

    def aprender(self, texto, metadatos):
        """Método público para indexar datos."""
        if not texto or len(texto) < 10: return
        
        def tarea():
            try:
                # print(f"   🧠 [NEUROPLASTICIDAD] Memorizando: {metadatos.get('source', 'dato')}...")
                doc = Document(page_content=texto, metadata=metadatos)
                splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                splits = splitter.split_documents([doc])
                
                if self.vectorstore is None:
                    self.vectorstore = FAISS.from_documents(splits, self.embeddings)
                else:
                    self.vectorstore.add_documents(splits)
                
                self.vectorstore.save_local(DB_PATH)
            except Exception as e:
                print(f"   ❌ Fallo al memorizar: {e}")
        
        self.executor.submit(tarea)

    def _buscar_baloo(self, query, limit=1):
        cmd = "balooctl6" if shutil.which("balooctl6") else "balooctl"
        try:
            res = subprocess.run([cmd, "search", f"limit:{limit}", query], capture_output=True, text=True)
            rutas = [line.strip() for line in res.stdout.splitlines() if os.path.isfile(line.strip())]
            return rutas
        except: return []

    def procesar_consulta(self, query):
        # 1. MEMORIA
        if self.vectorstore:
            try:
                docs = self.vectorstore.similarity_search_with_score(query, k=1)
                if docs and len(docs[0][0].page_content) > 50: 
                    return f"💡 [MEMORIA]:\n{docs[0][0].page_content}"
            except: pass

        print(f"   🔍 [CEREBRO] Buscando en sistema (Baloo)...")
        
        # 2. BALOO + SENTIDOS
        archivos = self._buscar_baloo(query)
        if archivos:
            archivo = archivos[0]
            ext = os.path.splitext(archivo)[1].lower()
            contenido = ""
            tipo = "ARCHIVO"

            if ext in ['.mp3', '.wav', '.m4a', '.ogg']:
                print(f"   👂 Audio detectado. Invocando OÍDO...")
                # Importación dinámica para evitar conflictos circulares
                import oido
                contenido = oido.transcribir_audio(archivo, modelo="small")
                tipo = "AUDIO"
            elif ext in ['.jpg', '.png', '.jpeg', '.webp']:
                print(f"   👁️ Imagen detectada. Invocando VISIÓN...")
                import vision
                contenido = vision.analyze_image(archivo, "Describe esta imagen técnica.", fast_mode=False)
                tipo = "IMAGEN"
            elif ext in ['.pdf', '.txt', '.md', '.py', '.json']:
                try: contenido = open(archivo, 'r', errors='ignore').read()[:5000]
                except: contenido = "Error lectura"

            if contenido and "Error" not in contenido:
                # El aprendizaje ya ocurre dentro de oido/vision gracias al decorador,
                # pero si es archivo de texto plano, lo aprendemos aquí.
                if tipo == "ARCHIVO":
                    self.aprender(contenido, {"source": archivo, "type": tipo})
                return f"📂 [SISTEMA - {tipo}]:\nArchivo: {archivo}\n\n{contenido}"

        # 3. WEB
        print(f"   🌐 Buscando en WEB...")
        import consejero
        info = consejero.investigar(query)
        if "No se encontró" not in info:
            # Consejero también tendrá decorador, así que ya habrá aprendido
            return f"🌍 [WEB]:\n{info}"
            
        return "❌ Sin resultados."

# Instancia global
mind = NexoCognitivo()
motor = mind # Alias

# --- DECORADOR EXPORTABLE ---
def memorizar(tipo_origen="sistema"):
    """
    Decorador para que funciones externas guarden sus resultados en Cerebro.
    Uso: @cerebro.memorizar(tipo_origen="oido")
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Ejecutar función original
            resultado = func(*args, **kwargs)
            
            # Si hay resultado útil, Cerebro lo aprende
            if resultado and isinstance(resultado, str) and len(resultado) > 10 and "Error" not in resultado:
                # Extraer metadatos del primer argumento (usualmente la ruta o query)
                source = str(args[0]) if args else "desconocido"
                meta = {"source": source, "type": tipo_origen, "tool": func.__name__}
                
                # Aprender (La instancia 'mind' maneja el hilo)
                mind.aprender(resultado, meta)
            
            return resultado
        return wrapper
    return decorator

if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Kia Besta"
    print(mind.procesar_consulta(q))