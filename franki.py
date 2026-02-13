#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FRANKI v6.0 - Federated Recursive Artificial Neural Knowledge Interface
-----------------------------------------------------------------------
EDICIÓN SEGURA (SECURE CORE)
- Sudo: BLOQUEADO.
- Escritura/Ejecución: REQUIERE CONFIRMACIÓN MANUAL.
- Entorno: 100% Local (Ollama + Subprocesos).
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
import re
from typing import List, Dict, Any
from datetime import datetime
from pathlib import Path

# --- DEPENDENCIAS (BÁSICAS LOCALES) ---
try:
    import pyperclip
    from odf.opendocument import OpenDocumentText
    from odf.text import P, H
    from odf.style import Style, TextProperties
    from langchain_ollama import ChatOllama, OllamaEmbeddings
    from langchain_community.vectorstores import FAISS
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
    from langchain_core.tools import tool
    from duckduckgo_search import DDGS
except ImportError:
    pass # Se asume entorno configurado

# --- INTERFAZ UI ---
class UI:
    CYAN = '\033[96m'; GREEN = '\033[92m'; YELLOW = '\033[93m'
    RED = '\033[91m'; MAGENTA = '\033[95m'; BOLD = '\033[1m'
    RESET = '\033[0m'; DIM = '\033[2m'

    @staticmethod
    def header():
        os.system('clear')
        print(f"{UI.GREEN}{UI.BOLD}╔═════════════════════════════════════════════════════════════════════════╗")
        print(f"║  FRANKI v6.0 - SECURE CORE (NO SUDO | HUMAN GATED)                      ║")
        print(f"║  {UI.DIM}System: Garuda Linux | User Control: STRICT{UI.RESET}{UI.GREEN}{UI.BOLD}                            ║")
        print(f"╚═════════════════════════════════════════════════════════════════════════╝{UI.RESET}")

# --- PROTOCOLO DE SEGURIDAD ---
class SafetyProtocol:
    FORBIDDEN_PATTERNS = [
        r"sudo\s+",          # Sudo explícito
        r"su\s+",            # Switch user
        r"rm\s+-rf\s+/",     # Borrado raíz
        r":\(\)\{ :\|:& \};:" # Fork bomb
    ]

    @staticmethod
    def validate_command(cmd: str) -> str:
        """Retorna mensaje de error si es peligroso, o None si pasa el filtro."""
        for pattern in SafetyProtocol.FORBIDDEN_PATTERNS:
            if re.search(pattern, cmd):
                return f"⛔ SEGURIDAD: El comando '{cmd}' contiene patrones prohibidos ({pattern}). ACCIÓN BLOQUEADA."
        return None

    @staticmethod
    def ask_permission(action_type: str, detail: str) -> bool:
        """Interrumpe la ejecución para pedir permiso al usuario."""
        print(f"\n{UI.YELLOW}⚠️  SOLICITUD DE {action_type}:{UI.RESET}")
        print(f"   {UI.BOLD}➤ {detail}{UI.RESET}")
        try:
            ans = input(f"   {UI.CYAN}¿Autorizar? [s/N] > {UI.RESET}").lower().strip()
            return ans in ['s', 'y', 'si', 'yes']
        except KeyboardInterrupt:
            return False

# --- MEMORIA (LOCAL) ---
class MemoryCortex:
    def __init__(self):
        self._init_sql()
        # Usamos BGE-M3 localmente
        self.embeddings = OllamaEmbeddings(model="bge-m3:latest")
        self.kg_path = Path("knowledge_graph.json")
        if not self.kg_path.exists(): self.save_kg({"user": "Entropia", "projects": []})

    def _init_sql(self):
        with sqlite3.connect("franki_memoria.db") as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS interactions (ts TEXT, role TEXT, content TEXT)")

    def log(self, role, content):
        with sqlite3.connect("franki_memoria.db") as conn:
            conn.execute("INSERT INTO interactions VALUES (?, ?, ?)", (datetime.now().isoformat(), role, content))

    def save_kg(self, data):
        json.dump(data, open(self.kg_path, 'w'), indent=2)

    def load_kg(self):
        try: return json.load(open(self.kg_path))
        except: return {}
    
    def rag_search(self, query):
        if not os.path.exists("./faiss_db"): return ""
        try:
            db = FAISS.load_local("./faiss_db", self.embeddings, allow_dangerous_deserialization=True)
            return "\n".join([d.page_content for d in db.similarity_search(query, k=2)])
        except: return ""

mem = MemoryCortex()

# --- HERRAMIENTAS CONTROLADAS ---

@tool
def sys_bash(command: str):
    """
    Ejecuta comandos Bash. 
    BLOQUEA SUDO. Requiere confirmación del usuario.
    """
    # 1. Filtro Automático
    security_warning = SafetyProtocol.validate_command(command)
    if security_warning:
        return security_warning

    # 2. Filtro Humano
    if not SafetyProtocol.ask_permission("EJECUCIÓN BASH", command):
        return "⛔ USUARIO DENEGÓ LA EJECUCIÓN."

    # 3. Ejecución
    print(f"{UI.DIM}   (Ejecutando...){UI.RESET}")
    try:
        res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=60)
        return res.stdout if res.returncode == 0 else f"ERROR:\n{res.stderr}"
    except Exception as e: return f"EXCEPTION: {e}"

@tool
def tool_save_text(filename: str, content: str, mode: str = "w"):
    """
    Guarda archivos de texto/código.
    Requiere confirmación del usuario.
    """
    action = "SOBRESCRIBIR" if mode == 'w' else "AÑADIR A"
    if not SafetyProtocol.ask_permission(f"ESCRITURA ARCHIVO ({action})", f"Archivo: {filename}\n   Contenido (inicio): {content[:50]}..."):
        return "⛔ USUARIO DENEGÓ ESCRITURA."

    try:
        with open(filename, mode) as f: f.write(content + "\n")
        return f"Archivo {filename} actualizado."
    except Exception as e: return f"Error escritura: {e}"

@tool
def tool_file_delete(filepath: str):
    """Elimina archivos. REQUIERE CONFIRMACIÓN."""
    if not SafetyProtocol.ask_permission("BORRADO DE ARCHIVO", filepath):
        return "⛔ USUARIO DENEGÓ BORRADO."
    try:
        os.remove(filepath)
        return f"Archivo {filepath} eliminado."
    except Exception as e: return f"Error: {e}"

@tool
def tool_odt_report(filename: str, title: str, content: str):
    """Genera reporte ODT. Requiere confirmación."""
    if not SafetyProtocol.ask_permission("GENERAR REPORTE ODT", filename):
        return "⛔ DENEGADO."
    if not filename.endswith(".odt"):
        filename += ".odt"
    try:
        doc = OpenDocumentText()
        doc.text.addElement(H(outlinelevel=1, text=title))
        for line in content.split('\n'):
            if line.strip(): doc.text.addElement(P(text=line.strip()))
        doc.save(filename, True)
        return f"Reporte guardado en {filename}"
    except Exception as e: return f"Error ODT: {e}"

@tool
def tool_read_file(filepath: str):
    """[SAFE] Lee archivos (primeras 50 líneas). No requiere confirmación (Solo lectura)."""
    if not os.path.exists(filepath): return "Archivo no existe."
    try:
        with open(filepath, 'r') as f: return f.read(2000)
    except Exception as e: return f"Error lectura: {e}"

@tool
def tool_clipboard_read(dummy: str = ""):
    """[SAFE] Lee portapapeles. No requiere confirmación."""
    try: return pyperclip.paste()[:3000]
    except: return "Error clipboard."

# --- CEREBRO ---
class FrankiBrain:
    def __init__(self):
        # Herramientas
        self.tools = [sys_bash, tool_save_text, tool_file_delete, tool_odt_report, tool_read_file, tool_clipboard_read]
        self.tool_map = {t.name: t for t in self.tools}
        
        # Orquestador (Llama 3.1)
        self.llm = ChatOllama(model="llama3.1:8b", temperature=0.1)
        self.agent = self.llm.bind_tools(self.tools)

    def react_loop(self, user_input: str):
        # Contexto RAG Local
        rag = mem.rag_search(user_input)
        
        system_prompt = SystemMessage(content=f"""
        Eres FRANKI v6.0 (Secure Core).
        
        DIRECTRICES DE SEGURIDAD (MANDATORIAS):
        1. NO puedes usar SUDO. Si necesitas root, pide al usuario que lo haga manualmente.
        2. NO ejecutes cambios en disco sin preguntar (tus herramientas preguntarán, tú solo invócalas).
        3. Prioriza soluciones BASH simples sobre scripts complejos de Python. 
        
        CONTEXTO MEMORIA LOCAL:
        {rag}
        """ 
        )

        messages = [system_prompt, HumanMessage(content=user_input)]
        
        print(f"{UI.DIM}   (Pensando...){UI.RESET}")
        
        steps = 0
        while steps < 10:
            try:
                # 1. Pensamiento LLM
                response = self.agent.invoke(messages)
                messages.append(response)
                
                # Si no hay tools, terminamos
                if not response.tool_calls:
                    print(f"\n{UI.GREEN}FRANKI >{UI.RESET} {response.content}")
                    mem.log("ai", response.content)
                    break
                
                # 2. Ejecución de Tools (Aquí saltarán las confirmaciones)
                for call in response.tool_calls:
                    t_name = call['name']
                    print(f"{UI.CYAN}   🔧 INTENTO DE HERRAMIENTA: {t_name}{UI.RESET}")
                    
                    tool_func = self.tool_map.get(t_name)
                    if tool_func:
                        try:
                            res = tool_func.invoke(call['args'])
                            messages.append(ToolMessage(content=str(res), tool_call_id=call['id']))
                        except Exception as e:
                            messages.append(ToolMessage(content=f"Error interno: {e}", tool_call_id=call['id']))
                    else:
                        messages.append(ToolMessage(content="Herramienta no encontrada", tool_call_id=call['id']))

                steps += 1

            except KeyboardInterrupt:
                print(f"\n{UI.RED}⚠️ INTERRUPCIÓN MANUAL.{UI.RESET}")
                return

# --- MAIN ---
def main():
    UI.header()
    brain = FrankiBrain()
    
    while True:
        try:
            print(f"\n{UI.BOLD}{UI.GREEN}╭─[Entropia@Franki-Secure] {UI.RESET}")
            u_input = input(f"{UI.BOLD}{UI.GREEN}╰─➤ {UI.RESET}")
            
            if not u_input.strip(): continue
            if u_input.lower() in ["salir", "exit"]:
                break
            
            # Comandos rápidos
            if u_input.startswith("/clip"):
                u_input = f"Analiza clipboard: {pyperclip.paste()[:500]}... {u_input.replace('/clip', '')}"

            mem.log("user", u_input)
            brain.react_loop(u_input)

        except KeyboardInterrupt:
            print(f"\n{UI.YELLOW} (Sesión pausada. 'salir' para cerrar){UI.RESET}")

if __name__ == "__main__":
    main()
