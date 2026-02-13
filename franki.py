import os
import sys
import sqlite3
import subprocess
import warnings
import shutil
import signal
import json
import time
from datetime import datetime

# --- BLINDAJE DE ENTORNO (SILENCIO TOTAL DE TRAZADO) ---
os.environ["LANGCHAIN_TRACING_V2"] = "false"
for key in ["LANGCHAIN_HANDLER", "LANGCHAIN_ENABLE_TRACING", "LANGCHAIN_API_KEY"]:
    if key in os.environ: os.environ.pop(key, None)

from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
from langchain_core.tools import tool
from duckduckgo_search import DDGS
from faster_whisper import WhisperModel

warnings.filterwarnings("ignore")

# --- CONFIGURACIÓN DE NÚCLEO ---
NOMBRE_SISTEMA = "Franki (Federated Recursive Artificial Neural Knowledge Interface)"
MODELO_ORQUESTADOR = "llama3.1:8b"
CEREBROS_ESPECIALISTAS = {
    "logica": "deepseek-r1:8b",     # Razonamiento crítico y planificación
    "codigo": "qwen2.5-coder:7b"    # Ingeniería de software y scripts
}
MODELOS_VISION = {
    "rapido": "moondream",
    "normal": "llava-phi3",
    "pro": "llama3.2-vision"
}
DB_PERSISTENTE = "franki_cortex.db"
PATH_CONOCIMIENTO = "./faiss_db"

class Color:
    VERDE = '\033[92m'; AMARILLO = '\033[93m'; AZUL = '\033[94m'
    MAGENTA = '\033[95m'; CYAN = '\033[96m'; ROJO = '\033[91m'
    RESET = '\033[0m'; BOLD = '\033[1m'

# --- GESTIÓN DE SEÑALES Y ESTADO ---
def interceptor_señal(sig, frame):
    print(f"\n\n{Color.ROJO}⚠️  INTERRUPCIÓN DE FLUJO: Franki reiniciando ciclo de espera...{Color.RESET}")
    raise KeyboardInterrupt

signal.signal(signal.SIGINT, interceptor_señal)

# --- CAPA DE MEMORIA EPISÓDICA Y APRENDIZAJE ---
class Memoria:
    @staticmethod
    def inicializar():
        with sqlite3.connect(DB_PERSISTENTE) as conn:
            conn.execute('''CREATE TABLE IF NOT EXISTS episodios 
                            (id INTEGER PRIMARY KEY, timestamp TEXT, role TEXT, content TEXT)''')
            conn.execute('''CREATE TABLE IF NOT EXISTS auditoria 
                            (id INTEGER PRIMARY KEY, ts TEXT, comando TEXT, explicacion TEXT)''')

    @staticmethod
    def registrar(role, content):
        with sqlite3.connect(DB_PERSISTENTE) as conn:
            conn.execute("INSERT INTO episodios (timestamp, role, content) VALUES (?, ?, ?)",
                         (datetime.now().isoformat(), role, content))

    @staticmethod
    def auditar(cmd, razon):
        with sqlite3.connect(DB_PERSISTENTE) as conn:
            conn.execute("INSERT INTO auditoria (ts, comando, explicacion) VALUES (?, ?, ?)",
                         (datetime.now().isoformat(), cmd, razon))

    @staticmethod
    def recuperar_contexto(n=10):
        try:
            with sqlite3.connect(DB_PERSISTENTE) as conn:
                cursor = conn.execute("SELECT role, content FROM episodios ORDER BY id DESC LIMIT ?", (n,))
                filas = cursor.fetchall()
                return [HumanMessage(content=c) if r=='user' else AIMessage(content=c) for r,c in reversed(filas)]
        except: return []

# --- ARSENAL DE HERRAMIENTAS (SISTEMA SENSORIAL Y EJECUTIVO) ---

@tool
def herramienta_vision(ruta: str, pregunta: str, precision: str = "normal"):
    """
    [SENTIDO: VISTA] Analiza imágenes o diagramas.
    Niveles: 'rapido' (identificación), 'normal' (contexto), 'pro' (OCR/Ingeniería).
    """
    modelo = MODELOS_VISION.get(precision, "llava-phi3")
    try:
        import ollama
        print(f"{Color.CYAN}   👁️  Activando sensor visual ({modelo})...{Color.RESET}")
        res = ollama.chat(model=modelo, messages=[{'role': 'user', 'content': pregunta, 'images': [ruta]}])
        return f"RESULTADO VISUAL: {res['message']['content']}"
    except Exception as e: return f"ERROR_VISUAL: {str(e)}"

@tool
def herramienta_especialista(rama: str, consulta: str):
    """
    [SENTIDO: COGNICIÓN] Invoca expertos: 'logica' (DeepSeek) o 'codigo' (Qwen).
    Usa 'logica' para estrategias de proyectos y 'codigo' para desarrollo.
    """
    modelo = CEREBROS_ESPECIALISTAS.get(rama, MODELO_ORQUESTADOR)
    try:
        print(f"{Color.AZUL}   🧠 Delegando a especialista {rama} ({modelo})...{Color.RESET}")
        llm = ChatOllama(model=modelo, temperature=0)
        return llm.invoke(consulta).content
    except Exception as e: return f"ERROR_ESPECIALISTA: {str(e)}"

@tool
def herramienta_capataz(comando: str, razon_tecnica: str):
    """
    [SENTIDO: ACCIÓN] Ejecuta comandos Bash en Garuda Linux.
    Requiere una justificación técnica sólida para su aprobación.
    """
    return "APPROVAL_REQUIRED"

@tool
def herramienta_cerebro_local(query: str):
    """
    [SENTIDO: MEMORIA] Consulta la base de datos de conocimiento FAISS (Manuales, notas, proyectos).
    """
    if not os.path.exists(PATH_CONOCIMIENTO): return "Memoria FAISS no inicializada."
    try:
        embeddings = OllamaEmbeddings(model="bge-m3:latest")
        db = FAISS.load_local(PATH_CONOCIMIENTO, embeddings, allow_dangerous_deserialization=True)
        docs = db.similarity_search(query, k=3)
        return "\n".join([f"Fragmento: {d.page_content}" for d in docs])
    except Exception as e: return f"ERROR_MEMORIA_LOCAL: {str(e)}"

@tool
def herramienta_consejero_web(busqueda: str):
    """
    [SENTIDO: PERCEPCIÓN EXTERNA] Busca en la web información actualizada.
    """
    try:
        results = DDGS().text(busqueda, max_results=3)
        return "\n".join([f"[{r['title']}] {r['body']}" for r in results])
    except: return "ERROR_WEB: No se pudo acceder a internet."

@tool
def herramienta_oido(archivo_audio: str):
    """
    [SENTIDO: AUDICIÓN] Transcribe archivos de voz a texto usando Whisper.
    """
    try:
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, _ = model.transcribe(archivo_audio)
        return " ".join([s.text for s in segments])
    except Exception as e: return f"ERROR_AUDIO: {str(e)}"

# --- LÓGICA DE CONTROL Y DASHBOARD ---

def mostrar_interfaz():
    os.system('clear')
    print(f"{Color.BOLD}{Color.MAGENTA}╔══════════════════════════════════════════════════════════════════════╗{Color.RESET}")
    print(f"{Color.BOLD}{Color.MAGENTA}║  {NOMBRE_SISTEMA} v6.0         ║{Color.RESET}")
    print(f"{Color.BOLD}{Color.MAGENTA}║  ESTADO: OPERATIVO | AUDITORÍA: ACTIVA | APRENDIZAJE: ON             ║{Color.RESET}")
    print(f"{Color.BOLD}{Color.MAGENTA}╚══════════════════════════════════════════════════════════════════════╝{Color.RESET}")
    print(f"   [SENSÓRICA]  1: Visión  4: Cerebro  5: Consejero  6: Oído")
    print(f"   [EJECUCIÓN]  2: Especialista (Lógica/Código)  3: Capataz (Bash)")
    print(f"   {Color.AMARILLO}INFO:{Color.RESET} Presiona {Color.BOLD}Ctrl+C{Color.RESET} para interrumpir una tarea lenta.")
    print("-" * 72)

def main():
    Memoria.inicializar()
    mostrar_interfaz()
    
    # Orquestador con un toque de temperatura para proactividad
    llm = ChatOllama(model=MODELO_ORQUESTADOR, temperature=0.3)
    tools = [herramienta_vision, herramienta_especialista, herramienta_capataz, 
             herramienta_cerebro_local, herramienta_consejero_web, herramienta_oido]
    llm_con_tools = llm.bind_tools(tools)

    prompt_arquitecto = SystemMessage(content=f"""
    Eres {NOMBRE_SISTEMA}. No eres un script, eres el Arquitecto de este sistema.
    
    PERFIL DEL USUARIO:
    - Entorno: Garuda Linux (Arch basado). Prioriza soluciones para este sistema.
    - Proyectos: Camperización Kia Besta (Tactical/Hybrid), Software Aetheria, Modelo Penitenciario.
    
    DIRECTRICES DE AGENTE:
    1. PROACTIVIDAD: No solo respondas. Analiza si lo solicitado puede mejorarse con un script o una consulta web.
    2. RIGOR: Usa terminología de ingeniería (ISO, DIN, IEEE).
    3. TRANSPARENCIA: Explica qué herramienta numerada vas a usar.
    4. APRENDIZAJE: Si el usuario te pide organizar algo, utiliza la memoria local para ver cómo lo hiciste antes.
    5. RAPIDEZ: Si un comando Bash soluciona el problema, propónlo de inmediato con su razón técnica.
    """)

    historial = [prompt_arquitecto] + Memoria.recuperar_contexto()

    while True:
        try:
            orden = input(f"\n{Color.BOLD}👤 ORDEN > {Color.RESET}")
            if orden.lower() in ["salir", "exit", "quit"]: break
            if not orden.strip(): continue

            Memoria.registrar("user", orden)
            historial.append(HumanMessage(content=orden))
            
            # Ejecución del Orquestador
            respuesta_agente = llm_con_tools.invoke(historial)
            historial.append(respuesta_agente)

            if respuesta_agente.tool_calls:
                for call in respuesta_agente.tool_calls:
                    name = call["name"]; args = call["args"]; call_id = call["id"]
                    
                    if name == "herramienta_capataz":
                        print(f"\n{Color.AMARILLO}🛠️  PROPUESTA TÉCNICA DE CAPATAZ:{Color.RESET}")
                        print(f"   {Color.BOLD}RAZÓN:{Color.RESET} {args['razon_tecnica']}")
                        confirmacion = input(f"   ¿Ejecutar {Color.BOLD}{args['comando']}{Color.RESET}? (s/n): ").lower()
                        
                        if confirmacion == 's':
                            Memoria.auditar(args['comando'], args['razon_tecnica'])
                            resultado = subprocess.getoutput(args['comando'])
                            print(f"   {Color.VERDE}✅ Sistema modificado y auditado correctamente.{Color.RESET}")
                        else:
                            resultado = "OPERACIÓN CANCELADA POR EL USUARIO."
                    else:
                        print(f" ⚡ Ejecutando: {name}...")
                        resultado = globals()[name].invoke(args)
                    
                    historial.append(ToolMessage(content=str(resultado), tool_call_id=call_id))
                
                # Respuesta de cierre del agente tras usar herramientas
                cierre = llm_con_tools.invoke(historial)
                print(f"\n{Color.MAGENTA}Franki:{Color.RESET} {cierre.content}")
                Memoria.registrar("ai", cierre.content)
                historial.append(cierre)
            else:
                print(f"\n{Color.MAGENTA}Franki:{Color.RESET} {respuesta_agente.content}")
                Memoria.registrar("ai", respuesta_agente.content)

        except KeyboardInterrupt:
            mostrar_interfaz()
            # Limpiamos la última entrada si quedó huérfana
            if historial and isinstance(historial[-1], HumanMessage): historial.pop()
            continue
        except Exception as e:
            print(f"{Color.ROJO}⚠️ ERROR DE NÚCLEO: {str(e)}{Color.RESET}")

if __name__ == "__main__": main()
