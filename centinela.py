#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CENTINELA v1.0 - Monitor de Salud del Sistema
---------------------------------------------
Rol: Auditoría rápida de hardware y uso de recursos.
Uso: python centinela.py [report]
"""

import sys
import psutil
import subprocess
import shutil

def get_cpu_info():
    """Devuelve carga y temperatura promedio (si sensors está disponible)."""
    load = psutil.cpu_percent(interval=1)
    
    # Intento de lectura de temperatura (puede variar según hardware)
    temp_msg = "N/A"
    try:
        temps = psutil.sensors_temperatures()
        if 'coretemp' in temps:
            avg_temp = sum(t.current for t in temps['coretemp']) / len(temps['coretemp'])
            temp_msg = f"{avg_temp:.1f}°C"
        elif 'k10temp' in temps: # AMD
            avg_temp = temps['k10temp'][0].current
            temp_msg = f"{avg_temp:.1f}°C"
    except: pass
    
    return f"CPU: {load}% | Temp: {temp_msg}"

def get_ram_info():
    mem = psutil.virtual_memory()
    return f"RAM: {mem.percent}% ({mem.used // (1024**3)}GB / {mem.total // (1024**3)}GB)"

def get_disk_info(path="/"):
    usage = shutil.disk_usage(path)
    percent = (usage.used / usage.total) * 100
    free_gb = usage.free // (1024**3)
    return f"Disco ('{path}'): {percent:.1f}% ocupado | Libres: {free_gb}GB"

def reporte_general():
    """Genera un resumen ejecutivo para Franki."""
    uptime = subprocess.getoutput("uptime -p").replace("up ", "")
    
    reporte = [
        f"--- INFORME CENTINELA (Uptime: {uptime}) ---",
        get_cpu_info(),
        get_ram_info(),
        get_disk_info("/"), # Root
        get_disk_info("/home") # Home (importante para usuario)
    ]
    
    # Comprobar batería si existe
    if hasattr(psutil, "sensors_battery") and psutil.sensors_battery():
        bat = psutil.sensors_battery()
        plugged = "🔌 Conectado" if bat.power_plugged else "🔋 Batería"
        reporte.append(f"Energía: {bat.percent}% ({plugged})")

    return "\n".join(reporte)

if __name__ == "__main__":
    print(reporte_general())
