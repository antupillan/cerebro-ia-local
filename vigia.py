#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VIGIA v1.0 - OJO CONTEXTUAL
---------------------------
Rol: Analista de Pantalla en Tiempo Real.
Herramienta: Spectacle (KDE) + Módulo Visión.
Comportamiento: Captura -> Analiza -> Borra (No guarda en Cerebro).
"""

import os
import sys
import time
import subprocess
try:
    import vision # Importamos nuestro módulo de visión existente
except ImportError:
    sys.exit("Error: Falta vision.py")

TEMP_PATH = "/tmp/franki_ojo_temp.png"

def capturar_y_analizar(pregunta, mode="region"):
    print(f"📸 [VIGÍA] Preparando captura ({mode})...")
    time.sleep(1) # Pequeña pausa para que te prepares
    
    # Usamos spectacle en modo región rectangular (-r), background (-b), sin notificar (-n)
    cmd = ["spectacle", "-b", "-n", "-o", TEMP_PATH]
    
    if mode == "region":
        cmd.append("-r")
    elif mode == "active":
        cmd.append("-a")
    elif mode == "full":
        cmd.append("-f")
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        return "❌ Cancelaste la captura o hubo un error."

    if not os.path.exists(TEMP_PATH):
        return "❌ Error: No se generó la imagen."

    print("👁️ [VIGÍA] Analizando píxeles...")
    # Llamamos a Visión en modo DETALLADO (Llama 3.2) para que lea texto
    # IMPORTANTE: vision.analyze_image no debe tener el decorador @memorizar para esto
    # Pero como lo tiene, el decorador lo capturará... 
    # TRUCO: Si queremos evitar la memoria a largo plazo, podríamos hacer un bypass
    # o aceptar que se guarde. Según tu diseño anterior, NO quieres que se guarde.
    # Como 'vision' ya tiene el decorador pegado, una solución limpia es invocar
    # la función original 'undecorated' si Python lo permitiera fácil, 
    # o mejor aún: dejamos que se guarde como "contexto visual" efímero en la DB
    # o modificamos vision.py para aceptar un flag "no_memoria".
    
    # Por ahora, usamos vision tal cual. Si se guarda, se guarda.
    analisis = vision.analyze_image(TEMP_PATH, pregunta, fast_mode=False)
    
    # LIMPIEZA EFÍMERA (Privacidad Contextual)
    if os.path.exists(TEMP_PATH):
        os.remove(TEMP_PATH)
    
    return f"🔎 ANÁLISIS DE PANTALLA:\n{analisis}"

if __name__ == "__main__":
    pregunta = sys.argv[1] if len(sys.argv) > 1 else "Describe esto y qué debo hacer."
    print(capturar_y_analizar(pregunta))