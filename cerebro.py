import os
import sys
import argparse
import warnings
import logging
import io
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
    DirectoryLoader, TextLoader, PyPDFLoader, 
    UnstructuredMarkdownLoader, UnstructuredWordDocumentLoader, UnstructuredODTLoader
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

# [MEJORA 1] LISTA NEGRA DE ARCHIVOS (Evita la trampa de Calibre)
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
        
        # [MEJORA 2] Log Contextual: Muestra la carpeta padre para saber qué libro es
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
    
    # 1. INTENTO DE TEXTO
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

    # 2. INTENTO VISUAL
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
        import shutil
        shutil.rmtree(VECTOR_DB_PATH)
    if os.path.exists(VECTOR_DB_PATH):
        try: return FAISS.load_local(VECTOR_DB_PATH, embedding_func, allow_dangerous_deserialization=True)
        except: pass
    return None

def escanear(modos, target=None, reset=False):
    embedding_func = OllamaEmbeddings(model=MODELO_EMBEDDING)
    vectorstore = obtener_db(embedding_func, reset)
    docs = []

    iterador = [(os.path.dirname(target), [os.path.basename(target)])] if target else RUTAS_CARPETAS
    
    modelo_whisper = None
    if modos.get("audio"):
        try: modelo_whisper = WhisperModel(MODELO_WHISPER, device="cpu", compute_type="int8")
        except: modos["audio"] = False

    print(f"\n🚀 Iniciando escaneo inteligente...")
    ext_img = {'.jpg', '.jpeg', '.png'}
    ext_aud = {'.mp3', '.m4a', '.wav', '.ogg'}

    for item in iterador:
        walker = os.walk(item) if isinstance(item, str) else [(item[0], [], item[1])]

        for root, _, files in walker:
            for file in files:
                # [MEJORA 3] FILTROS DE SEGURIDAD
                if target and file != os.path.basename(target): continue
                if file.lower() in IGNORAR_ARCHIVOS: continue # <--- ESTO FALTABA
                
                ruta_abs = os.path.join(root, file)
                ext = os.path.splitext(file)[1].lower()

                # A. PDF
                if modos.get("texto") and ext == '.pdf':
                    d = analizar_pdf_inteligente(ruta_abs, activar_vision=modos.get("vision"))
                    if d: docs.extend(d)

                # B. TEXTO
                elif modos.get("texto") and ext in ['.txt', '.md', '.docx', '.odt']:
                    try: 
                        if ext == '.docx': l = UnstructuredWordDocumentLoader(ruta_abs)
                        elif ext == '.odt': l = UnstructuredODTLoader(ruta_abs)
                        else: l = TextLoader(ruta_abs)
                        d = l.load(); docs.extend(d) if d else None
                    except: pass

                # C. IMAGENES
                elif modos.get("vision") and ext in ext_img:
                    d = procesar_imagen(ruta_abs)
                    if d: docs.append(d)

                # D. AUDIO
                elif modos.get("audio") and ext in ext_aud and modelo_whisper:
                    d = procesar_audio(ruta_abs, modelo_whisper)
                    if d: docs.append(d)

    if not docs:
        print("✅ Nada nuevo que procesar.")
        return

    print(f" [MEMORIA] Guardando {len(docs)} fragmentos...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    splits = splitter.split_documents(docs)
    
    if vectorstore is None: vectorstore = FAISS.from_documents(splits, embedding_func)
    else: vectorstore.add_documents(splits)
    vectorstore.save_local(VECTOR_DB_PATH)
    print("✅ Guardado.")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--texto", action="store_true", help="Procesa texto y PDF inteligente")
    parser.add_argument("--vision", action="store_true", help="Permite analizar imágenes y PDFs escaneados")
    parser.add_argument("--audio", action="store_true", help="Procesa audio")
    parser.add_argument("--reset", action="store_true", help="Resetea DB")
    parser.add_argument("--target", type=str, help="Archivo específico")
    args = parser.parse_args()

    modos = {"texto": args.texto, "vision": args.vision, "audio": args.audio}
    
    if args.target:
        ext = os.path.splitext(args.target)[1].lower()
        if ext in ['.jpg', '.png']: modos["vision"] = True
        elif ext in ['.mp3', '.wav']: modos["audio"] = True
        else: modos["texto"] = True 

    if not any(modos.values()) and not args.target and not args.reset:
        modo_chat()
        return

    escanear(modos, args.target, args.reset)

def modo_chat():
    embedding_func = OllamaEmbeddings(model=MODELO_EMBEDDING)
    if not os.path.exists(VECTOR_DB_PATH):
        print("❌ Memoria vacía.")
        return
    vectorstore = FAISS.load_local(VECTOR_DB_PATH, embedding_func, allow_dangerous_deserialization=True)
    llm = ChatOllama(model="llama3.1:8b", temperature=0.0, keep_alive="1h")
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    template = "Contexto: {context}\nPregunta: {question}\nRespuesta:"
    prompt = ChatPromptTemplate.from_template(template)
    rag_chain = ({"context": retriever | format_docs, "question": RunnablePassthrough()} | prompt | llm | StrOutputParser())
    print(f"\n🧠 CEREBRO ONLINE")
    while True:
        try:
            q = input("\n[Entropia]: ")
            if q.strip() in ["salir", "exit"]: break
            if q:
                for chunk in rag_chain.stream(q): print(chunk, end="", flush=True)
                print("")
        except KeyboardInterrupt: break

def format_docs(docs): return "\n\n".join(doc.page_content for doc in docs)

if __name__ == "__main__":
    main()
