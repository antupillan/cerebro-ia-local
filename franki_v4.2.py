#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FRANKI v4.2 (Stable Core) - Federated Recursive Artificial Neural Knowledge Interface
-----------------------------------------------------------------------
Sistema: Agente Autónomo con Acceso a Escritorio (ODT, Clipboard) y Enjambre de Scripts.
OS: Garuda Linux | Autor: Entropia | Corrección: Bugfixes & Type Safety
-----------------------------------------------------------------------
"""

import os
import sys
import json
import time
import signal
import sqlite3
import subprocess
import warnings
import textwrap
import glob
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

# --- AUTO-INSTALACIÓN DE DEPENDENCIAS (ROBUSTA) ---
def check_dependencies():
    # Mapa: "nombre-pip" -> "nombre-import"
    required = {
        "langchain-ollama": "langchain_ollama",
        "langchain-community": "langchain_community",
        "faiss-cpu": "langchain_community.vectorstores", # Check indirecto
        "duckduckgo-search": "duckduckgo_search",
        "pyperclip": "pyperclip",
        "odfpy": "odf"
    }
    
    missing = []
    for pkg, import_name in required.items():
        try:
            __import__(import_name.split('.')[0])
        except ImportError:
            missing.append(pkg)
    
    if missing:
        print(f"\033[93m[SISTEMA] Faltan dependencias: {', '.join(missing)}. Instalando...\033[0m")
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing)
        print(f"\033[92m[SISTEMA] Dependencias instaladas. Reiniciando Franki...\033[0m")
        os.execv(sys.executable, ['python'] + sys.argv)

check_dependencies()

# --- IMPORTS SEGUROS ---
try:
    import pyperclip
    from odf.opendocument import OpenDocumentText
    from odf.text import P, H
    from odf.style import Style, TextProperties
    from langchain_ollama import ChatOllama, OllamaEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage, AIMessage
    from langchain_core.tools import tool
    from duckduckgo_search import DDGS
except ImportError as e:
    sys.exit(f"Error crítico en imports tras instalación: {e}")

# --- CONFIGURACIÓN & ESTÉTICA ---
class UI:
    CYAN = '\033[96m'; GREEN = '\033[92m'; YELLOW = '\033[93m'
    RED = '\033[91m'; MAGENTA = '\033[95m'; BOLD = '\033[1m'
    RESET = '\033[0m'; DIM = '\033[2m'; BLUE = '\033[94m'

    @staticmethod
    def header():
        os.system('clear')
        print(f"{UI.MAGENTA}{UI.BOLD}╔═════════════════════════════════════════════════════════════════════════╗")
        print(f"║  FRANKI v4.2 - ARCH LINUX SYSTEM ARCHITECT (STABLE)                     ║")
        print(f"║  {UI.DIM}Federated Recursive Artificial Neural Knowledge Interface{UI.RESET}{UI.MAGENTA}{UI.BOLD}              ║")
        print(f"╚═════════════════════════════════════════════════════════════════════════╝{UI.RESET}")
        print(f"{UI.CYAN}  COMANDOS RÁPIDOS (CHULETA):{UI.RESET}")
        print(f"  {UI.YELLOW}• /clipboard{UI.RESET} : Analiza contenido actual del portapapeles.")
        print(f"  {UI.YELLOW}• /rapido{UI.RESET}    : Fuerza respuesta inmediata (sin DeepSeek).")
        print(f"  {UI.YELLOW}• /enjambre{UI.RESET}  : Lista scripts Python disponibles en la carpeta.")
        print(f"  {UI.YELLOW}• Ctrl+C{UI.RESET}     : Interrumpe el pensamiento actual sin salir.")
        print(f"  {UI.YELLOW}• salir{UI.RESET}      : Apaga el sistema.")
        print(f"{UI.DIM}───────────────────────────────────────────────────────────────────────────{UI.RESET}")

MODELS = {
    "orchestrator": "llama3.1:8b",     # Workhorse para tools
    "thinker": "deepseek-r1:8b",       # Razonamiento puro
    "embeddings": "bge-m3:latest"      # RAG
}

PATHS = {
    "vector_db": "./faiss_db",
    "sql_db": "franki_memoria.db",
    "kg": "knowledge_graph.json"
}

# --- CLASE 1: MEMORIA Y CONOCIMIENTO ---
class MemoryCortex:
    def __init__(self):
        self._init_sql()
        self.embeddings = OllamaEmbeddings(model=MODELS["embeddings"])
        self.kg_path = Path(PATHS["kg"])
        if not self.kg_path.exists():
            self.save_kg({"user": "Entropia", "projects": [], "learned_facts": []})

    def _init_sql(self):
        with sqlite3.connect(PATHS["sql_db"]) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS interactions (id INTEGER PRIMARY KEY, ts TEXT, role TEXT, content TEXT)")

    def log(self, role, content):
        with sqlite3.connect(PATHS["sql_db"]) as conn:
            conn.execute("INSERT INTO interactions (ts, role, content) VALUES (?, ?, ?)", (datetime.now().isoformat(), role, content))

    def load_kg(self):
        try: return json.load(open(self.kg_path))
        except: return {}

    def save_kg(self, data):
        json.dump(data, open(self.kg_path, 'w'), indent=2)

    def rag_search(self, query):
        if not os.path.exists(PATHS["vector_db"]): return ""
        try:
            db = FAISS.load_local(PATHS["vector_db"], self.embeddings, allow_dangerous_deserialization=True)
            return "\n".join([d.page_content for d in db.similarity_search(query, k=2)])
        except: return ""

mem = MemoryCortex()

# --- CLASE 2: HERRAMIENTAS AVANZADAS ---

@tool
def sys_bash(command: str):
    """[SISTEMA] Ejecuta comandos Bash. Peligroso. Úsalo para listar archivos o ejecutar scripts."""
    print(f"{UI.YELLOW}   ⚡ [BASH]: {command}{UI.RESET}")
    try:
        res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        return res.stdout if res.returncode == 0 else f"ERROR:\n{res.stderr}"
    except Exception as e: return f"EXCEPTION: {e}"

@tool
def tool_clipboard_read(dummy_arg: str = ""):
    """[ESCRITORIO] Lee el contenido de texto actual del portapapeles del sistema."""
    try:
        content = pyperclip.paste()
        if not content: return "Portapapeles vacío."
        return f"CONTENIDO PORTAPAPELES:\n{content[:2000]}..." 
    except Exception as e:
        return f"Error leyendo portapapeles (¿Falta xclip/xsel?): {str(e)}"

@tool
def tool_odt_writer(filename: str, title: str, content: str):
    """
    [OFIMÁTICA] Crea un archivo .odt. 
    'content' debe ser un SOLO string largo con saltos de línea para los párrafos.
    """
    if not filename.endswith(".odt"): filename += ".odt"
    
    try:
        doc = OpenDocumentText()
        # Estilos
        s_header = Style(name="MyHeader", family="paragraph")
        s_header.addElement(TextProperties(fontweight="bold", fontsize="14pt"))
        doc.automaticstyles.addElement(s_header)
        
        doc.text.addElement(H(outlinelevel=1, stylename=s_header, text=title))
        
        # Procesamos el contenido por líneas para crear párrafos
        for line in content.split('\n'):
            if line.strip():
                doc.text.addElement(P(text=line.strip()))
            
        doc.save(filename, True)
        return f"Documento creado: {os.path.abspath(filename)}"
    except Exception as e:
        return f"Error creando ODT: {e}"

@tool
def tool_swarm_invoke(script_name: str, args: str = ""):
    """[ENJAMBRE] Invoca scripts Python vecinos (ej: 'cerebro.py')."""
    if not os.path.exists(script_name):
        return f"Error: {script_name} no existe."
    
    print(f"{UI.BLUE}   🤖 [ENJAMBRE] Invocando: {script_name}...{UI.RESET}")
    cmd = f"python {script_name} {args}"
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=120)
        return f"SALIDA:\n{res.stdout}\nERRORES:\n{res.stderr}"
    except Exception as e: return f"Error: {e}"

@tool
def tool_knowledge_update(fact: str):
    """[MEMORIA] Guarda un dato nuevo en el Grafo JSON."""
    kg = mem.load_kg()
    if "learned_facts" not in kg: kg["learned_facts"] = []
    kg["learned_facts"].append(f"{datetime.now().date()}: {fact}")
    mem.save_kg(kg)
    return "Memoria actualizada."

# --- CLASE 3: CEREBRO PROPOSITIVO ---
class FrankiBrain:
    def __init__(self):
        self.tools = [sys_bash, tool_clipboard_read, tool_odt_writer, tool_swarm_invoke, tool_knowledge_update]
        self.tool_map = {t.name: t for t in self.tools}
        
        # Modelos
        # Llama 3.1 es el MEJOR para uso de herramientas. DeepSeek R1 es mejor para pensar.
        # Usamos Llama como conductor principal.
        self.llm = ChatOllama(model=MODELS["orchestrator"], temperature=0.1)
        self.agent = self.llm.bind_tools(self.tools)

    def scan_directory(self) -> str:
        scripts = glob.glob("*.py")
        return ", ".join([s for s in scripts if "franki" not in s])

    def react_loop(self, user_input: str, force_fast: bool = False):
        # 1. Contexto
        rag_data = mem.rag_search(user_input)
        swarm = self.scan_directory()
        kg = mem.load_kg()
        
        # 2. Prompt
        system_prompt = SystemMessage(content=f"""
        Eres FRANKI v4.2, Arquitecto de Sistemas en Garuda Linux.
        
        [HERRAMIENTAS]:
        - OFIMÁTICA: `tool_odt_writer` para informes.
        - PORTAPAPELES: `tool_clipboard_read` si el usuario dice "analiza esto" sin dar contexto.
        - ENJAMBRE: Scripts locales disponibles: [{swarm}]. ÚSALOS con `tool_swarm_invoke`.
        
        [CONTEXTO]:
        - RAG: {rag_data}
        - Hitos Recientes: {json.dumps(kg.get('learned_facts', [])[-3:])}
        
        [REGLAS]:
        1. Si piden código, ofrece guardarlo en .odt o .py.
        2. Si falla un comando, REINTENTA corrigiéndolo.
        """)

        messages = [system_prompt, HumanMessage(content=user_input)]
        
        # 3. Bucle ReAct
        steps = 0
        while steps < 10:
            try:
                response = self.agent.invoke(messages)
                messages.append(response)
                
                if not response.tool_calls:
                    print(f"\n{UI.GREEN}FRANKI >{UI.RESET} {response.content}")
                    mem.log("ai", response.content)
                    break
                
                # Ejecutar herramientas
                for call in response.tool_calls:
                    print(f"{UI.CYAN}   🔧 [TOOL] {call['name']}...{UI.RESET}")
                    tool_func = self.tool_map.get(call['name'])
                    if tool_func:
                        try:
                            # Invocación segura
                            res = tool_func.invoke(call['args'])
                            messages.append(ToolMessage(content=str(res), tool_call_id=call['id']))
                        except Exception as e:
                            err_msg = f"Error ejecutando herramienta: {str(e)}"
                            messages.append(ToolMessage(content=err_msg, tool_call_id=call['id']))
                    else:
                        messages.append(ToolMessage(content="Herramienta no encontrada", tool_call_id=call['id']))
                
                steps += 1
            except KeyboardInterrupt:
                print(f"\n{UI.RED}⚠️  Interrumpido por usuario.{UI.RESET}")
                return
            except Exception as e:
                print(f"{UI.RED}Error en bucle de pensamiento: {e}{UI.RESET}")
                break

# --- MAIN ---
def main():
    UI.header()
    brain = FrankiBrain()
    
    while True:
        try:
            print(f"\n{UI.BOLD}{UI.MAGENTA}╭─[Entropia@Franki] {UI.RESET}")
            u_input = input(f"{UI.BOLD}{UI.MAGENTA}╰─➤ {UI.RESET}")
            
            if not u_input.strip(): continue
            if u_input.lower() in ["salir", "exit"]:
                break
            
            # Comandos mágicos
            if u_input.startswith("/clipboard"):
                try:
                    content = pyperclip.paste()
                    print(f"{UI.DIM}   (Leyendo {len(content)} chars del clipboard){UI.RESET}")
                    u_input = f"Analiza este contenido del portapapeles:\n{content}\nContexto: {u_input.replace('/clipboard', '')}"
                except:
                    print(f"{UI.RED}Error leyendo clipboard.{UI.RESET}")
            
            if u_input.startswith("/enjambre"):
                print(f"{UI.BLUE}Enjambre:{UI.RESET} {brain.scan_directory()}")
                continue

            mem.log("user", u_input)
            brain.react_loop(u_input)

        except KeyboardInterrupt:
            print(f"\n{UI.YELLOW} (Sesión interrumpida. Escribe 'salir' para cerrar){UI.RESET}")
            continue

if __name__ == "__main__":
    main()
