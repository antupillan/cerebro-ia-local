#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FRANKI v8.0 - Federated Recursive Artificial Neural Knowledge Interface
-----------------------------------------------------------------------
EDICIÓN FEDERACIÓN NEURAL (NEURAL FEDERATION CORE)
- Orquestador: Llama 3.1
- Especialistas: DeepSeek-R1 (Lógica), Qwen2.5 (Código).
- Capacidades: Arquitectura, Sistema, Ofimática, Delegación Automática.
-----------------------------------------------------------------------
"""

import os
import sys
import subprocess
import shutil
import json
import sqlite3
import re
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

# --- CONFIGURACIÓN ---
OBSIDIAN_VAULT_PATH = os.path.expanduser("~/Documentos/ObsidianVault") 
OUTPUT_DIR = "franki_output"

if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)
if not os.path.exists(OBSIDIAN_VAULT_PATH): os.makedirs(OBSIDIAN_VAULT_PATH)

# --- DEFINICIÓN DE LA FEDERACIÓN (MODELOS) ---
FEDERATION = {
    "orchestrator": "llama3.1:8b",     # El Jefe (Maneja herramientas y seguridad)
    "thinker": "deepseek-r1:8b",       # El Filósofo (Planificación, Razonamiento)
    "coder": "qwen2.5-coder:7b",       # El Ingeniero (Scripts complejos, OpenSCAD)
    "vision_fast": "moondream:latest", # El Ojo Rápido
    "vision_detail": "llama3.2-vision:latest" # El Ojo Detallado
}

# --- IMPORTS ---
try:
    import pyperclip
    from odf.opendocument import OpenDocumentText
    from odf.text import P, H
    from langchain_ollama import ChatOllama, OllamaEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
    from langchain_core.tools import tool
    
    # Módulos locales (Modulariadad restaurada)
    import consejero
    import vision
    import cerebro # Motor CEREBRO v4.0 integrado
    import vigia   # Ojo Efímero (Contextual)
    import centinela # Monitor de Salud
    import cronos    # Gestor de Calendario
except ImportError as e:
    print(f"Error importando dependencias: {e}")
    pass

# --- UI ---
class UI:
    CYAN = '\033[96m'; GREEN = '\033[92m'; YELLOW = '\033[93m'
    RED = '\033[91m'; MAGENTA = '\033[95m'; BOLD = '\033[1m'; BLUE = '\033[94m'
    RESET = '\033[0m'; DIM = '\033[2m'

    @staticmethod
    def header():
        os.system('clear')
        print(f"{UI.BLUE}{UI.BOLD}╔══════════════════════════════════════════════════════════════════════════════════════╗")
        print(f"║  FRANKI v8.2 (Federated Recursive Artificial Neural Knowledge Interface)             ║")
        print(f"║  {UI.DIM}System: Garuda Linux | Security: SECURE CORE | Vault: ~/Documentos/ObsidianVault{UI.RESET}{UI.BLUE}{UI.BOLD}    ║")
        print(f"╚══════════════════════════════════════════════════════════════════════════════════════╝{UI.RESET}")
        
        print(f"\n{UI.CYAN}{UI.BOLD}🎛️  PANEL DE COMANDO & CHULETA:{UI.RESET}")
        
        # Columna 1: Inteligencia
        print(f"  {UI.BOLD}[1] NÚCLEOS NEURONALES (Delegación Automática){UI.RESET}")
        print(f"      • {UI.GREEN}Orquestador (Llama 3.1){UI.RESET} : Gestión general, Archivos, Bash.")
        print(f"      • {UI.MAGENTA}Thinker (DeepSeek R1){UI.RESET}   : Estrategia, Lógica, Matemáticas.")
        print(f"      • {UI.YELLOW}Coder (Qwen 2.5){UI.RESET}        : Python, OpenSCAD, Scripts complejos.")
        print(f"      • {UI.BLUE}Vision (Llama 3.2/Moondream){UI.RESET}: Análisis de imágenes y diagramas.")

        # Columna 2: Integración KRunner
        print(f"\n  {UI.BOLD}[2] INTEGRACIÓN DE ESCRITORIO (Alt+Space / Super+S){UI.RESET}")
        print(f"      • {UI.YELLOW}ia 'pregunta'{UI.RESET}     → Respuesta rápida (Notificación).")
        print(f"      • {UI.YELLOW}deep 'lógica'{UI.RESET}     → Razonamiento profundo (Portapapeles).")
        print(f"      • {UI.YELLOW}code 'script'{UI.RESET}     → Generación de código (Portapapeles).")

        # Columna 3: Herramientas
        print(f"\n  {UI.BOLD}[3] HERRAMIENTAS ACTIVAS{UI.RESET}")
        print(f"      • {UI.BOLD}3D/CAD:{UI.RESET}       'Diseña pieza...'    → Código .scad + Render .png")
        print(f"      • {UI.BOLD}Web:{UI.RESET}          'Investiga sobre...' → Búsqueda DuckDuckGo + Informe.")
        print(f"      • {UI.BOLD}Visión:{UI.RESET}       'Qué ves en ./img.png' → Análisis visual.")
        print(f"      • {UI.BOLD}Notas:{UI.RESET}        'Guarda nota...'     → Archivo Markdown en Obsidian.")
        
        # Columna 4: Atajos
        print(f"\n  {UI.BOLD}[4] ATAJOS DE TERMINAL{UI.RESET}")
        print(f"      • {UI.YELLOW}/clip{UI.RESET} : Analiza portapapeles. | {UI.YELLOW}exit{UI.RESET} : Salir.")
        print(f"{UI.DIM}────────────────────────────────────────────────────────────────────────────────────────{UI.RESET}")

# --- PROTOCOLO DE SEGURIDAD ---
class SafetyProtocol:
    FORBIDDEN = [r"sudo\s+", r"rm\s+-rf\s+/", r":\(\)\{ :\|:& \};:"]

    @staticmethod
    def ask(action: str, detail: str) -> bool:
        print(f"\n{UI.YELLOW}⚠️  SOLICITUD DE {action}:{UI.RESET}")
        print(f"   {UI.BOLD}➤ {detail}{UI.RESET}")
        try:
            return input(f"   {UI.CYAN}¿Autorizar? [s/N] > {UI.RESET}").lower().strip() in ['s', 'y', 'si']
        except: return False

# --- MEMORIA ---
class MemoryCortex:
    def __init__(self):
        self._init_sql()
        self.embeddings = OllamaEmbeddings(model="bge-m3:latest")
        self.kg_path = Path("knowledge_graph.json")
        if not self.kg_path.exists(): self.save_kg({"user": "Entropia", "projects": ["Penal", "Aetheria"]})

    def _init_sql(self):
        with sqlite3.connect("franki_memoria.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS interactions (ts TEXT, role TEXT, content TEXT)")

    def log(self, role, content):
        with sqlite3.connect("franki_memoria.db") as conn:
            conn.execute("INSERT INTO interactions VALUES (?, ?, ?)", (datetime.now().isoformat(), role, content))

    def save_kg(self, data): json.dump(data, open(self.kg_path, 'w'), indent=2)
    def rag(self, query):
        if not os.path.exists("./faiss_db"): return ""
        try:
            db = FAISS.load_local("./faiss_db", self.embeddings, allow_dangerous_deserialization=True)
            return "\n".join([d.page_content for d in db.similarity_search(query, k=2)])
        except: return ""

mem = MemoryCortex()

# --- HERRAMIENTA DE FEDERACIÓN (NUEVA) ---

@tool
def tool_consult_specialist(specialty: str, task: str):
    """
    [FEDERACIÓN] Delega tareas complejas a modelos especializados.
    Args:
        specialty (str): 'thinker' (Planificación/Lógica) o 'coder' (Código/Scripts).
        task (str): Descripción detallada de la tarea a realizar.
    """
    model_name = FEDERATION.get(specialty)
    if not model_name: return f"Error: Especialidad '{specialty}' desconocida. Usa 'thinker' o 'coder'."
    
    print(f"{UI.MAGENTA}   📡 [NEXO] Conectando con nodo especialista: {specialty.upper()} ({model_name})...{UI.RESET}")
    
    try:
        specialist = ChatOllama(model=model_name, temperature=0.1)
        response = specialist.invoke(task)
        return f"RESPUESTA DE {specialty.upper()}:\n{response.content}"
    except Exception as e:
        return f"Error conectando con especialista: {e}"

# --- HERRAMIENTAS DE ARQUITECTO & SISTEMA ---

@tool
def tool_openscad_compile(filename: str, scad_code: str):
    """[ARQUITECTURA] Compila código OpenSCAD a PNG."""
    base_path = os.path.join(OUTPUT_DIR, filename)
    scad_file = f"{base_path}.scad"
    png_file = f"{base_path}.png"
    if not SafetyProtocol.ask("MODELADO 3D", f"Crear {scad_file}"): return "⛔ DENEGADO."
    with open(scad_file, 'w') as f: f.write(scad_code)
    cmd = f"openscad -o {png_file} {scad_file} --imgsize=800,600 --colorscheme=DeepOcean"
    try:
        subprocess.run(cmd, shell=True, check=True, timeout=60)
        return f"✅ Modelo 3D: {png_file}"
    except Exception as e: return f"Error OpenSCAD: {e}"

@tool
def tool_graphviz_render(filename: str, dot_code: str):
    """[LÓGICA] Genera diagramas DOT."""
    base_path = os.path.join(OUTPUT_DIR, filename)
    dot_file = f"{base_path}.dot"
    png_file = f"{base_path}.png"
    if not SafetyProtocol.ask("DIAGRAMA", f"Compilar {dot_file}"): return "⛔ DENEGADO."
    with open(dot_file, 'w') as f: f.write(dot_code)
    try:
        subprocess.run(f"dot -Tpng {dot_file} -o {png_file}", shell=True, check=True)
        return f"✅ Diagrama: {png_file}"
    except Exception as e: return f"Error Graphviz: {e}"

@tool
def tool_obsidian_note(filename: str, content: str, folder: str = ""):
    """[CONOCIMIENTO] Crea nota Obsidian."""
    full_path = os.path.join(OBSIDIAN_VAULT_PATH, folder)
    if not os.path.exists(full_path): os.makedirs(full_path)
    file_path = os.path.join(full_path, f"{filename}.md")
    if not SafetyProtocol.ask("OBSIDIAN", f"Crear nota {file_path}"): return "⛔ DENEGADO."
    try:
        with open(file_path, 'w') as f: f.write(content)
        return f"✅ Nota Obsidian: {file_path}"
    except Exception as e: return f"Error: {e}"

@tool
def tool_list_directory(path: str = "."):
    """[SISTEMA] Lista archivos. NO usar Bash para esto."""
    path = os.path.expanduser(path)
    if not os.path.exists(path): return f"Error: Ruta {path} no existe."
    if not os.path.isdir(path): return f"Error: {path} no es directorio."
    try:
        items = os.listdir(path)
        return f"CONTENIDO DE {path}:\n" + "\n".join(items[:50])
    except Exception as e: return f"Error: {e}"

@tool
def sys_bash(command: str):
    """[SISTEMA] Ejecuta Bash. Requiere confirmación."""
    if SafetyProtocol.ask("BASH", command):
        return subprocess.run(command, shell=True, capture_output=True, text=True).stdout
    return "⛔ DENEGADO"

@tool
def tool_read_file(filepath: str):
    """[SISTEMA] Lee archivos de texto. Si es carpeta, la lista."""
    path = os.path.expanduser(filepath)
    if os.path.isdir(path): return tool_list_directory.invoke(path)
    try: return open(path).read()[:3000]
    except: return "Error lectura."

@tool
def tool_web_search(query: str):
    """
    [CONSEJERO] Busca información en Internet (DuckDuckGo) y sintetiza una respuesta.
    Úsalo cuando necesites datos actuales, precios, noticias o documentación.
    """
    print(f"{UI.YELLOW}   🌏 [WEB] Llamando a módulo Consejero: '{query}'...{UI.RESET}")
    try:
        return consejero.investigar(query)
    except Exception as e:
        return f"Error en módulo Consejero: {e}"

@tool
def tool_visit_webpage(url: str):
    """
    [WEB] Lee el contenido completo de una URL específica.
    """
    print(f"{UI.YELLOW}   🌐 [NAV] Llamando a módulo Consejero (Lector): {url}...{UI.RESET}")
    try:
        content = consejero.leer_pagina(url)
        return f"CONTENIDO DE {url}:\n{content[:4000]}..."
    except Exception as e:
        return f"Error leyendo web: {e}"

@tool
def tool_vision_analysis(image_path: str, prompt: str = "Describe esta imagen detalladamente."):
    """
    [VISIÓN] Analiza una imagen local usando el módulo de visión.
    Args:
        image_path: Ruta del archivo de imagen (jpg, png).
        prompt: Pregunta sobre la imagen.
    """
    print(f"{UI.BLUE}   👁️ [VISIÓN] Llamando a módulo Visión: {image_path}...{UI.RESET}")
    try:
        return vision.analyze_image(image_path, prompt)
    except Exception as e:
        return f"Error en módulo Visión: {e}"

@tool
def tool_read_clipboard(dummy: str = ""):
    """[SISTEMA] Lee el contenido actual del portapapeles."""
    try:
        content = pyperclip.paste()
        if not content.strip(): return "AVISO: El portapapeles está vacío."
        return f"CONTENIDO DEL PORTAPAPELES:\n{content}"
    except Exception as e: return f"Error leyendo portapapeles: {e}"

@tool
def tool_smart_knowledge(query: str):
    """
    [CEREBRO] Motor de búsqueda híbrido.
    Úsalo cuando el usuario pida información sobre proyectos, facturas, manuales 
    o archivos específicos (ej: 'Busca el PDF de la Kia Besta').
    
    Automáticamente:
    1. Revisa si ya lo sabe (FAISS).
    2. Si no, usa KDE Baloo para buscar el archivo en el disco.
    3. Si lo encuentra, lo lee y lo aprende en segundo plano.
    """
    print(f"{UI.MAGENTA}   🧠 [CEREBRO] Procesando consulta inteligente: '{query}'...{UI.RESET}")
    try:
        return cerebro.motor.consultar(query)
    except Exception as e:
        return f"Error en motor cerebral: {e}"

@tool
def tool_system_health(dummy: str = ""):
    """
    [CENTINELA] Reporte de salud del sistema (CPU, RAM, Disco, Batería).
    Úsalo cuando el usuario pregunte 'cómo está la pc', 'recursos', 'espacio en disco'.
    """
    print(f"{UI.GREEN}   🛡️ [CENTINELA] Auditando sistema...{UI.RESET}")
    try:
        return centinela.reporte_general()
    except Exception as e:
        return f"Error en Centinela: {e}"

@tool
def tool_calendar_check(dummy: str = ""):
    """
    [CRONOS] Consulta la agenda local en Obsidian.
    Úsalo para ver tareas pendientes y compromisos anotados.
    """
    print(f"{UI.YELLOW}   📅 [CRONOS] Consultando agenda local...{UI.RESET}")
    return cronos.reloj.listar_eventos()

@tool
def tool_calendar_add(summary: str, date_time: str = ""):
    """
    [CRONOS] Anota una tarea o recordatorio en la agenda de Obsidian.
    date_time: Opcional, formato 'YYYY-MM-DD HH:MM'.
    """
    print(f"{UI.YELLOW}   📅 [CRONOS] Anotando tarea: {summary}...{UI.RESET}")
    return cronos.reloj.crear_evento(summary, date_time)

@tool
def tool_see_screen(question: str):
    """
    [VIGÍA] Mira la pantalla del usuario (Screenshot temporal).
    Úsalo cuando el usuario diga 'mira esto', 'lee este error', 'qué opinas de este diseño'.
    El usuario deberá seleccionar el área con el mouse.
    """
    return vigia.capturar_y_analizar(question)

# --- CEREBRO ---
class FrankiBrain:
    def __init__(self):
        self.tools = [
            tool_consult_specialist, # <--- LA JOYA DE LA CORONA
            tool_web_search, tool_visit_webpage, tool_vision_analysis, tool_read_clipboard, # <--- NUEVOS SENTIDOS
            tool_smart_knowledge, tool_see_screen, tool_system_health, # <--- HERRAMIENTAS EJECUTIVAS
            tool_calendar_check, tool_calendar_add, # <--- CRONOS
            tool_list_directory, tool_read_file, sys_bash,
            tool_openscad_compile, tool_graphviz_render, tool_obsidian_note
        ]
        self.tool_map = {t.name: t for t in self.tools}
        self.llm = ChatOllama(model=FEDERATION["orchestrator"], temperature=0.1)
        self.agent = self.llm.bind_tools(self.tools)

    def react_loop(self, user_input: str):
        # Manejo especial para comando /clip
        if user_input.strip() == "/clip":
             user_input = "Lee el portapapeles y explícame o resume qué hay ahí."

        # rag = mem.rag(user_input)  <-- DEPRECATED: Usamos el nuevo CEREBRO
        rag = cerebro.motor.consultar(user_input)

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        prompt = SystemMessage(content=f"""
        Eres FRANKI v8.2 (Orquestador de Federación Neural).
        
        UBICACIÓN USUARIO: Santiago, Chile.
        FECHA Y HORA ACTUAL: {now_str} (Zona Horaria: America/Santiago)
        
        PROTOCOLO DE DELEGACIÓN (IMPORTANTE):
        1. CÓDIGO complejo (Python, OpenSCAD) -> USA `tool_consult_specialist('coder', ...)`
        2. PLANIFICACIÓN/RAZONAMIENTO -> USA `tool_consult_specialist('thinker', ...)`
        3. PANTALLA/CONTEXTO VISUAL ("Mira esto") -> USA `tool_see_screen`. Esto es efímero (RAM).
        4. AGENDA/TIEMPO -> USA `tool_calendar_check` o `tool_calendar_add`. (Local en Obsidian).
        5. ESTADO DEL SISTEMA -> USA `tool_system_health`.
        6. DATOS ACTUALES/WEB -> USA `tool_web_search`. Si el resumen es insuficiente, USA `tool_visit_webpage`.
        7. IMÁGENES (Archivos) -> USA `tool_vision_analysis`.
        8. ARCHIVOS/PROYECTOS -> USA `tool_smart_knowledge`. Es tu mejor herramienta para buscar en el disco y en tu memoria técnica (FAISS).
        
        CONTEXTO DINÁMICO (MEMORIA VIVA):
        Tus módulos sensoriales (Oído, Visión, Consejero) trabajan autónomamente.
        Siempre consulta tu memoria (FAISS) antes de decir "no sé", porque es muy posible 
        que el usuario haya ejecutado 'oido.py' o 'vision.py' de forma independiente 
        hace un momento y la información ya esté disponible en tu contexto.
        
        INSTRUCCIONES CLAVE:
        - Si buscas horarios, conviértelos a la hora local del usuario (Santiago).
        - NO uses `tool_read_clipboard` para saludos. Úsalo SOLO si se pide explícitamente.
        
        HERRAMIENTAS: tool_smart_knowledge, tool_see_screen, tool_system_health, tool_calendar_check, tool_calendar_add, tool_web_search, tool_vision_analysis, tool_read_file, sys_bash.
        
        CONTEXTO ACTUAL: {rag}
        """)
        
        messages = [prompt, HumanMessage(content=user_input)]
        
        steps = 0
        while steps < 10:
            try:
                res = self.agent.invoke(messages)
                messages.append(res)
                if not res.tool_calls:
                    print(f"\n{UI.GREEN}FRANKI >{UI.RESET} {res.content}")
                    mem.log("ai", res.content)
                    break
                
                for call in res.tool_calls:
                    t_name = call['name']
                    print(f"{UI.CYAN}   🔧 HERRAMIENTA: {t_name}{UI.RESET}")
                    func = self.tool_map.get(t_name)
                    if func:
                        try:
                            # Ejecución protegida para evitar crashes por argumentos inválidos
                            out = func.invoke(call['args'])
                        except Exception as e:
                            # Capturamos el error y se lo devolvemos al modelo como observación
                            out = f"Error de validación o ejecución ({t_name}): {str(e)}. Por favor corrige los argumentos."
                            print(f"{UI.RED}   [!] Error recuperable: {e}{UI.RESET}")
                        
                        messages.append(ToolMessage(content=str(out), tool_call_id=call['id']))
                steps += 1
            except KeyboardInterrupt:
                print(f"\n{UI.RED}⚠️ Cancelado.{UI.RESET}"); return

def main():
    UI.header()
    brain = FrankiBrain()
    while True:
        try:
            u_input = input(f"\n{UI.BOLD}{UI.BLUE}╭─[Entropia@Franki] \n╰─➤ {UI.RESET}")
            if not u_input.strip(): continue
            if u_input.lower() in ["exit", "salir"]:
                break
            mem.log("user", u_input)
            brain.react_loop(u_input)
        except KeyboardInterrupt: print("Pausado.")

if __name__ == "__main__": main()