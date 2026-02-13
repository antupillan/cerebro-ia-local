import os
import sys
import argparse
import warnings
import logging
import io
import shutil
import ollama 
from faster_whisper import WhisperModel
from pdf2image import convert_from_path

# Configuración de Logs y Alertas
warnings.filterwarnings("ignore")
logging.getLogger("langchain").setLevel(logging.ERROR)
logging.getLogger("faster_whisper").setLevel(logging.ERROR)
logging.getLogger("pypdf").setLevel(logging.ERROR)

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, UnstructuredWordDocumentLoader, UnstructuredODTLoader
)
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings, ChatOllama
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# --- CONFIGURACIÓN ---
MODELO_EMBEDDING = "bge-m3:latest"
VECTOR_DB_PATH = "./faiss_db"
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100
MODELO_WHISPER = "tiny"
MAX_PAGINAS_VISION = 2 

def sanear_texto(texto):
    """Elimina caracteres incompatibles con UTF-8/JSON (surrogates)."""
    if not texto: return ""
    return texto.encode("utf-8", "ignore").decode("utf-8")

# [MEJORA] LISTA NEGRA DE ARCHIVOS
IGNORAR_ARCHIVOS = {'cover.jpg', 'metadata.opf', 'cover.png'}

RUTAS_CARPETAS = [
    "/home/entropia/Documentos/Aetheria",
    "/home/entropia/Documentos/Calibre Library",
    "/home/entropia/Documentos/Literatura",
    "/home/entropia/Documentos/Defensa",
    "/home/entropia/Documentos/Notes",
    "/home/entropia/Documentos/Project"
]

# --- INTELIGENCIA ---
def procesar_imagen(ruta_imagen, bytes_img=None, source_name=None):
    try:
        if not source_name: source_name = os.path.basename(ruta_imagen)
        if not bytes_img:
            padre = os.path.basename(os.path.dirname(ruta_imagen))
            print(f"   👁️  Mirando: [{padre}]/{source_name}...")
        else:
            print(f"   👁️  Mirando página PDF: {source_name}...")

        target = bytes_img if bytes_img else ruta_imagen
        res = ollama.chat(
            model='llava',
            messages=[{'role': 'user', 'content': 'Describe brevemente este diagrama, foto o texto manuscrito.', 'images': [target]}]
        )
        return Document(page_content=f"[VISION: {source_name}]\n{res['message']['content']}", metadata={"source": ruta_imagen})
    except: return None

def analizar_pdf_inteligente(ruta_pdf, activar_vision=False):
    docs = []
    texto_extraido = False
    try:
        loader = PyPDFLoader(ruta_pdf)
        raw_docs = loader.load()
        total_chars = sum([len(d.page_content) for d in raw_docs])
        if total_chars > 100: 
            docs.extend(raw_docs)
            texto_extraido = True
        else:
            print(f"   ⚠️  PDF escaneado: {os.path.basename(ruta_pdf)}")
    except: pass

    if not texto_extraido and activar_vision:
        try:
            print(f"   👁️  Escaneando PDF visualmente (Máx {MAX_PAGINAS_VISION} págs)...")
            images = convert_from_path(ruta_pdf, first_page=1, last_page=MAX_PAGINAS_VISION)
            for i, img in enumerate(images):
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                doc = procesar_imagen(ruta_pdf, bytes_img=img_byte_arr.getvalue(), source_name=f"{os.path.basename(ruta_pdf)}_pg{i+1}")
                if doc: docs.append(doc)
        except Exception as e:
            print(f"   [!] Error visión PDF: {e}")
    return docs

def procesar_audio(ruta_audio, modelo_whisper):
    try:
        print(f"   👂 Escuchando: {os.path.basename(ruta_audio)}...")
        segmentos, _ = modelo_whisper.transcribe(ruta_audio, beam_size=5, language="es")
        return Document(page_content=f"[AUDIO: {os.path.basename(ruta_audio)}]\n{' '.join([s.text for s in segmentos])}", metadata={"source": ruta_audio})
    except: return None

# --- NUCLEO ---
def obtener_db(embedding_func, reset=False):
    if reset and os.path.exists(VECTOR_DB_PATH):
        shutil.rmtree(VECTOR_DB_PATH)
    if os.path.exists(VECTOR_DB_PATH):
        try: return FAISS.load_local(VECTOR_DB_PATH, embedding_func, allow_dangerous_deserialization=True)
        except: pass
    return None

def procesar_y_guardar_lote(docs, embedding_func, vectorstore):
    """Sincroniza un lote de documentos con FAISS y limpia la RAM."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    splits = splitter.split_documents(docs)
    try:
        if vectorstore is None:
            vectorstore = FAISS.from_documents(splits, embedding_func)
        else:
            vectorstore.add_documents(splits)
        vectorstore.save_local(VECTOR_DB_PATH)
        print(f"✅ Lote sincronizado. RAM liberada.")
    except Exception as e:
        print(f"❌ Error al guardar lote: {e}")
    return vectorstore

def escanear(modos, target=None, reset=False):
    embedding_func = OllamaEmbeddings(model=MODELO_EMBEDDING)
    vectorstore = obtener_db(embedding_func, reset)
    docs_batch = []
    archivos_corruptos = []
    LIMITE_ARCHIVOS_BATCH = 20
    contador_batch = 0

    iterador = [(os.path.dirname(target), [os.path.basename(target)])] if target else RUTAS_CARPETAS
    modelo_whisper = None
    if modos.get("audio"):
        try: 
            modelo_whisper = WhisperModel(MODELO_WHISPER, device="cpu", compute_type="int8")
            print("👂 Oído (Whisper) activado.")
        except: modos["audio"] = False

    print(f"\n🚀 Escaneo: [{'TEXTO' if modos.get('texto') else ''} {'VISIÓN' if modos.get('vision') else ''} {'AUDIO' if modos.get('audio') else ''}]")

    for item in iterador:
        walker = os.walk(item) if isinstance(item, str) else [(item[0], [], item[1])]
        for root, _, files in walker:
            for file in files:
                if target and file != os.path.basename(target): continue
                if file.lower() in IGNORAR_ARCHIVOS: continue
                
                ruta_abs = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()
                try:
                    d = []
                    if modos.get("texto") and ext == '.pdf':
                        d = analizar_pdf_inteligente(ruta_abs, activar_vision=modos.get("vision"))
                    elif modos.get("texto") and ext in ['.txt', '.md', '.docx', '.odt']:
                        if ext == '.docx': loader = UnstructuredWordDocumentLoader(ruta_abs)
                        elif ext == '.odt': loader = UnstructuredODTLoader(ruta_abs)
                        else: loader = TextLoader(ruta_abs, encoding='utf-8')
                        d = loader.load()
                    elif modos.get("vision") and ext in {'.jpg', '.jpeg', '.png'}:
                        res_img = procesar_imagen(ruta_abs)
                        if res_img: d = [res_img]
                    elif modos.get("audio") and ext in {'.mp3', '.m4a', '.wav', '.ogg'} and modelo_whisper:
                        res_aud = procesar_audio(ruta_abs, modelo_whisper)
                        if res_aud: d = [res_aud]
                    
                    if d:
                        for doc in d: doc.page_content = sanear_texto(doc.page_content)
                        docs_batch.extend(d)
                        contador_batch += 1

                    if contador_batch >= LIMITE_ARCHIVOS_BATCH:
                        print(f"\n💾 Sincronizando lote ({contador_batch} archivos)...")
                        vectorstore = procesar_y_guardar_lote(docs_batch, embedding_func, vectorstore)
                        docs_batch = []
                        contador_batch = 0
                except Exception as e:
                    archivos_corruptos.append(f"{ruta_abs} | Error: {str(e)}")
                    print(f"   ❌ OMITIDO: {file}")
                    continue

    if docs_batch:
        print(f"\n💾 Guardando lote final...")
        vectorstore = procesar_y_guardar_lote(docs_batch, embedding_func, vectorstore)

    if archivos_corruptos:
        with open("revision_necesaria.log", "a", encoding="utf-8") as f:
            f.write(f"\n--- SESIÓN {os.path.basename(target) if target else 'GLOBAL'} ---\n")
            for linea in archivos_corruptos: f.write(linea + "\n")
        print(f"⚠️  Se omitieron {len(archivos_corruptos)} archivos. Revisa 'revision_necesaria.log'.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--texto", action="store_true")
    parser.add_argument("--vision", action="store_true")
    parser.add_argument("--audio", action="store_true")
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--target", type=str)
    args = parser.parse_args()

    modos = {"texto": args.texto, "vision": args.vision, "audio": args.audio}
    
    if args.target:
        ext = os.path.splitext(args.target)[1].lower()
        if ext in ['.jpg', '.png', '.jpeg']: modos["vision"] = True
        elif ext in ['.mp3', '.wav', '.m4a']: modos["audio"] = True
        else: modos["texto"] = True 

    if not any(modos.values()) and not args.target and not args.reset:
        modo_chat()
    else:
        escanear(modos, args.target, args.reset)

def modo_chat():
    embedding_func = OllamaEmbeddings(model=MODELO_EMBEDDING)
    if not os.path.exists(VECTOR_DB_PATH):
        print("❌ Memoria vacía.")
        return
    vectorstore = FAISS.load_local(VECTOR_DB_PATH, embedding_func, allow_dangerous_deserialization=True)
    llm = ChatOllama(model="llama3.1:8b", temperature=0.0)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    template = "Contexto: {context}\nPregunta: {question}\nRespuesta:"
    prompt = ChatPromptTemplate.from_template(template)
    rag_chain = ({"context": retriever | (lambda docs: "\n\n".join(d.page_content for d in docs)), "question": RunnablePassthrough()} | prompt | llm | StrOutputParser())
    print(f"\n🧠 CEREBRO ONLINE")
    while True:
        try:
            q = input("\n[Entropia]: ")
            if q.strip() in ["salir", "exit"]: break
            if q:
                for chunk in rag_chain.stream(q): print(chunk, end="", flush=True)
                print("")
        except KeyboardInterrupt: break

if __name__ == "__main__":
    main()
