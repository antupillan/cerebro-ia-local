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
from datetime import datetime

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
from langchain_text_splitters import RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter
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

    def _normalizar_a_markdown(self, texto, metadatos):
        """Si el texto no tiene estructura, se la damos basada en su origen."""
        tipo = metadatos.get("type", "GENERAL").upper()
        origen = metadatos.get("source", "Desconocido")
        fecha = datetime.now().strftime("%Y-%m-%d")

        # Si ya parece markdown con headers, lo dejamos (búsqueda simple de '# ')
        if "\n# " in texto or texto.startswith("# "):
            return texto

        # Plantillas de Normalización
        if tipo == "AUDIO":
            return f"# 🎙️ Transcripción de Audio\n**Fuente:** {origen}\n**Fecha:** {fecha}\n\n## Contenido\n{texto}"
        elif tipo == "IMAGEN" or tipo == "VISION":
            return f"# 👁️ Análisis Visual\n**Archivo:** {origen}\n**Fecha:** {fecha}\n\n## Descripción\n{texto}"
        elif tipo == "ARCHIVO":
            return f"# 📄 Documento: {os.path.basename(origen)}\n**Ruta:** {origen}\n\n## Texto Extraído\n{texto}"
        elif "WEB" in tipo or "INVESTIGACION" in tipo:
            return f"# 🌍 Investigación Web\n**Query:** {origen}\n**Fecha:** {fecha}\n\n## Hallazgos\n{texto}"
        elif tipo == "AGENDA" or tipo == "CRONOS":
            return f"# 📅 Evento de Agenda\n**Contexto:** {origen}\n**Fecha Registro:** {fecha}\n\n## Detalle\n{texto}"
        else:
            return f"# 🧠 Memoria del Sistema\n**Origen:** {origen}\n**Tipo:** {tipo}\n\n## Datos\n{texto}"

    def aprender(self, texto, metadatos):
        """Método público para indexar datos con Estrategia de Markdown Inteligente."""
        if not texto or len(texto) < 10: return
        
        # Copia de metadatos para no mutar el original
        meta_safe = metadatos.copy()
        
        def tarea():
            try:
                # 1. Normalización: Asegurar que entra como Markdown estructurado
                texto_md = self._normalizar_a_markdown(texto, meta_safe)
                
                # 2. Split por Estructura Lógica (Headers)
                # Esto asegura que el contexto (Título/Sección) viaje con el fragmento
                headers_to_split_on = [
                    ("#", "Titulo"),
                    ("##", "Seccion"),
                    ("###", "Subseccion"),
                ]
                markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
                md_header_splits = markdown_splitter.split_text(texto_md)

                # 3. Split por Tamaño (Para secciones muy largas que pasen el límite de tokens)
                # chunk_size=1000 es un buen balance para Llama 3/DeepSeek
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000, 
                    chunk_overlap=200
                )
                
                final_splits = text_splitter.split_documents(md_header_splits)
                
                # 4. Re-inyectar metadatos base y guardar
                for split in final_splits:
                    split.metadata.update(meta_safe) # Agregamos fuente, tipo, etc.
                
                if self.vectorstore is None:
                    self.vectorstore = FAISS.from_documents(final_splits, self.embeddings)
                else:
                    self.vectorstore.add_documents(final_splits)
                
                self.vectorstore.save_local(DB_PATH)
                # print(f"   🧠 [NEUROPLASTICIDAD] Asimilado: {meta_safe.get('source')} ({len(final_splits)} fragmentos)")
                
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