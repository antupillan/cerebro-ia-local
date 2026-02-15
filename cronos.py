#!/usr/bin/env python3
# -*- coding: utf-8 -*-"""
CRONOS v1.2 - GESTOR TEMPORAL LOCAL (Obsidian + Parsing)
--------------------------------------------------------
Rol: Ejecutivo de Agenda Privada.
Capacidades: Leer, escribir y PARSEAR Agenda.md de Obsidian.
"""

import os
import datetime
import re

# Ruta a tu carpeta de Obsidian
OBSIDIAN_VAULT_PATH = os.path.expanduser("~/Documentos/ObsidianVault")
AGENDA_PATH = os.path.join(OBSIDIAN_VAULT_PATH, "Agenda.md")

class CronosLocal:
    def __init__(self):
        if not os.path.exists(OBSIDIAN_VAULT_PATH):
            os.makedirs(OBSIDIAN_VAULT_PATH, exist_ok=True)
        
        if not os.path.exists(AGENDA_PATH):
            with open(AGENDA_PATH, "w", encoding='utf-8') as f:
                f.write("# 📅 MI AGENDA EJECUTIVA\n")
                f.write(f"Creada el: {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n")
                f.write("## Pendientes\n")

    def listar_eventos(self, max_results=10):
        try:
            if not os.path.exists(AGENDA_PATH): return "No se encuentra el archivo de agenda."
            with open(AGENDA_PATH, "r", encoding='utf-8') as f:
                lineas = f.readlines()
            pendientes = [l.strip() for l in lineas if "- [ ]" in l]
            if not pendientes: return "No tienes tareas pendientes."
            return "📅 AGENDA LOCAL (Obsidian):\n" + "\n".join(pendientes[:max_results])
        except Exception as e: return f"Error: {e}"

    def crear_evento(self, resumen, fecha_hora_iso):
        """Añade una tarea. Formato esperado fecha: YYYY-MM-DD HH:MM"""
        try:
            timestamp = fecha_hora_iso if fecha_hora_iso else "Pronto"
            # Formato estándar para facilitar el parsing posterior
            # Ejemplo: - [ ] 2026-02-14 15:30 | Revisar aceite
            nueva_tarea = f"- [ ] {timestamp} | {resumen}\n"
            with open(AGENDA_PATH, "a", encoding='utf-8') as f:
                f.write(nueva_tarea)
            return f"✅ Tarea anotada: {resumen}"
        except Exception as e: return f"Error: {e}"

    def obtener_eventos_raw(self):
        """
        Devuelve una lista de diccionarios para que el Daemon haga cálculos.
        Retorna: [{'dt': datetime_obj, 'summary': str}, ...] 
        """
        eventos_procesables = []
        if not os.path.exists(AGENDA_PATH): return []
        
        try:
            with open(AGENDA_PATH, "r", encoding='utf-8') as f:
                lineas = f.readlines()
            
            # Regex para buscar fechas tipo YYYY-MM-DD HH:MM o YYYY-MM-DDTHH:MM:SS
            # Formato esperado en Obsidian: "- [ ] 2026-02-14 18:00 | Titulo"
            patron_fecha = r"(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2})"
            
            for linea in lineas:
                if "- [ ]" in linea and "|" in linea:
                    match = re.search(patron_fecha, linea)
                    if match:
                        fecha_str = match.group(1).replace("T", " ")
                        try:
                            # Intentamos parsear la fecha
                            dt = datetime.datetime.strptime(fecha_str, "%Y-%m-%d %H:%M")
                            # Extraemos el título (lo que va después del |)
                            resumen = linea.split("|", 1)[1].strip()
                            eventos_procesables.append({'dt': dt, 'summary': resumen})
                        except ValueError:
                            continue # Si la fecha está mal escrita, la saltamos
        except Exception:
            pass
            
        return eventos_procesables

reloj = CronosLocal()
