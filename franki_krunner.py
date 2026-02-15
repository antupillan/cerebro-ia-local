#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
FRANKI KRUNNER BRIDGE v1.0
--------------------------
Permite invocar a la IA desde Alt+Space (KRunner/Rofi).
Uso: python franki_krunner.py [fast|deep|code|vision] "query"
Salida: Notificación de sistema (notify-send) o Portapapeles.
--------------------------
"""

import sys
import os
import subprocess
import time
import warnings
import logging

# Configuración de logs para depuración
logging.basicConfig(filename="/tmp/franki_krunner.log", level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Supress Pydantic V1 warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")

try:
    import pyperclip
    from langchain_ollama import ChatOllama
except ImportError as e:
    logging.error(f"Import Error: {e}")
    sys.exit(f"Error: Faltan dependencias. {e}")

# --- CONFIGURACIÓN ---
MODELS = {
    "fast": "llama3.2:3b",     # Respuesta inmediata (< 2s)
    "normal": "llama3.1:8b",   # Razonamiento estándar
    "deep": "deepseek-r1:8b",  # Pensamiento profundo
    "code": "qwen2.5-coder:7b" # Generación de código
}

def notificar(titulo, mensaje, urgencia="normal"):
    """Envía notificación al escritorio KDE de forma segura."""
    try:
        subprocess.run(
            ["notify-send", "-u", urgencia, "-t", "10000", titulo, mensaje],
            check=False
        )
    except Exception as e:
        logging.error(f"Error enviando notificación: {e}")

def copiar_portapapeles(texto):
    try:
        pyperclip.copy(texto)
        notificar("Franki", "Respuesta copiada al portapapeles.")
    except Exception as e:
        logging.error(f"Error copiando al portapapeles: {e}")
        notificar("Franki Error", "Fallo al copiar al portapapeles.", "critical")

def ejecutar_ia(modo, query):
    model = MODELS.get(modo, MODELS["normal"])
    logging.info(f"Ejecutando IA. Modo: {modo}, Query: {query}")
    
    # Feedback inmediato
    notificar("Franki", f"Pensando ({modo})...", "low")
    
    try:
        llm = ChatOllama(model=model, temperature=0.1)
        res = llm.invoke(query).content
        logging.info("Respuesta recibida correctamente.")
        
        # Si es código o muy largo, mejor al portapapeles
        if modo == "code" or len(res) > 200:
            copiar_portapapeles(res)
            # Mostramos solo el inicio en la notificación
            notificar("Franki (Copiado)", res[:150] + "...")
        else:
            notificar("Franki", res)
            
    except Exception as e:
        error_msg = str(e)
        logging.error(f"Error en ejecución IA: {error_msg}")
        notificar("Franki Error", error_msg, "critical")

def main():
    if len(sys.argv) < 3:
        print("Uso: franki_krunner.py [fast|deep|code] 'query'")
        sys.exit(1)
        
    modo = sys.argv[1]
    query = sys.argv[2]
    
    ejecutar_ia(modo, query)

if __name__ == "__main__":
    main()
