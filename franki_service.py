#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import time
import threading
import subprocess
import logging
import sys
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

# Importamos módulos clave
try:
    from franki import FrankiBrain, mem, UI
    import cronos
except ImportError as e:
    sys.exit(f"Error importando Franki: {e}")

# Configuración Flask
app = Flask(__name__)
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

# --- MONITOR DE AGENDA (LATIDO) ---
class AgendaMonitor(threading.Thread):
    def __init__(self):
        super().__init__()
        self.daemon = True # Muere si el programa principal muere
        self.notificados = set() # Memoria para no repetir avisos

    def enviar_notificacion(self, titulo, cuerpo, urgencia="normal"):
        # Rostro oficial de Franki
        icon_path = "/home/entropia/cerebro_cli/Franki_face.png"
        # Usa el sistema nativo de KDE Plasma (notify-send)
        subprocess.run([
            "notify-send", 
            "-a", "Franki Agenda", 
            "-u", urgencia, 
            "-i", icon_path, 
            titulo, 
            cuerpo
        ])

    def run(self):
        print("⏰ [DAEMON] Monitor de Agenda iniciado. Latido activo.")
        while True:
            try:
                # 1. Obtener eventos crudos desde Cronos (Local)
                # Formato: [{'dt': datetime_obj, 'summary': str}, ...]
                eventos = cronos.reloj.obtener_eventos_raw()
                
                ahora = datetime.now()

                for evt in eventos:
                    dt_evento = evt['dt']
                    resumen = evt['summary']
                    
                    # Identificador único simple (fecha + titulo) para evitar duplicados
                    evt_id = f"{dt_evento.strftime('%Y%m%d%H%M')}-{resumen}"
                    
                    # Cálculo de tiempo restante en minutos
                    diff = dt_evento - ahora
                    minutos_restantes = diff.total_seconds() / 60
                    
                    # LÓGICA DE AVISO (Rango de 14 a 16 minutos antes)
                    if 14 < minutos_restantes < 16 and evt_id not in self.notificados:
                        self.enviar_notificacion(
                            f"Reunión en 15 min: {resumen}",
                            "Prepara tus documentos. ¿Quieres que abra las notas?",
                            urgencia="critical"
                        )
                        self.notificados.add(evt_id)
                        mem.log("sistema", f"AVISO: Reunión '{resumen}' en 15 min.")
                        
                    # LÓGICA DE AVISO (Rango de 0 a 2 minutos antes - ES AHORA)
                    elif 0 < minutos_restantes < 2 and f"{evt_id}_NOW" not in self.notificados:
                        self.enviar_notificacion(
                            f"ES AHORA: {resumen}",
                            "¡Comienza ya!",
                            urgencia="critical"
                        )
                        self.notificados.add(f"{evt_id}_NOW")

            except Exception as e:
                # print(f"Error silencioso en monitor agenda: {e}")
                pass

            time.sleep(60) # Revisar cada minuto (Latido lento para ahorrar CPU)

# --- INICIO DEL SERVIDOR ---

print("🧠 [DAEMON] Cargando Franki Brain...")
brain = FrankiBrain()

# Arrancamos el corazón de la agenda
monitor = AgendaMonitor()
monitor.start()

print("✅ [DAEMON] Franki Service + Agenda Monitor operando (Puerto 54321).")

@app.route('/krunner', methods=['POST'])
def krunner_endpoint():
    data = request.json
    query = data.get('query', '')
    mode = data.get('mode', 'general') # general, code, deep

    if not query: return jsonify({"response": "Error: Consulta vacía"})

    mem.log("user_krunner", f"[{mode}] {query}")
    
    try:
        response_text = ""
        
        # --- MODO CÓDIGO (Rápido con Qwen) ---
        if mode == 'code':
            prompt = f"Genera SOLAMENTE código para: {query}"
            res = brain.tool_map['tool_consult_specialist'].invoke({'specialty': 'coder', 'task': prompt})
            response_text = res
            
        # --- MODO PROFUNDO (Lento con DeepSeek) ---
        elif mode == 'deep':
            res = brain.tool_map['tool_consult_specialist'].invoke({'specialty': 'thinker', 'task': query})
            response_text = res
            
        # --- MODO GENERAL (El Orquestador Llama 3.1) ---
        else:
            # Contexto rápido (sin imprimir todo el RAG)
            import cerebro
            rag = cerebro.motor.consultar(query)
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            sys_prompt = SystemMessage(content=f"""
            Eres FRANKI v8.2 (Modo KRunner/Daemon).
            Responde de forma CONCISA y DIRECTA. Tienes acceso a herramientas.
            Ubicación: Santiago, Chile. Hora: {now_str}.
            Contexto RAG: {rag[:500]}...
            """)
            
            messages = [sys_prompt, HumanMessage(content=query)]
            
            steps = 0
            while steps < 5: 
                res = brain.agent.invoke(messages)
                messages.append(res)
                
                if not res.tool_calls:
                    response_text = res.content
                    break
                
                for call in res.tool_calls:
                    t_name = call['name']
                    func = brain.tool_map.get(t_name)
                    if func:
                        try:
                            out = func.invoke(call['args'])
                            messages.append(ToolMessage(content=str(out), tool_call_id=call['id']))
                        except Exception as e:
                            messages.append(ToolMessage(content=f"Error: {e}", tool_call_id=call['id']))
                steps += 1
            
            if not response_text:
                response_text = "No pude generar una respuesta final tras usar las herramientas."

        mem.log("ai_daemon", str(response_text))
        return jsonify({"response": str(response_text)})

    except Exception as e:
        return jsonify({"response": f"Error interno Franki: {e}"})

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=54321, threaded=True)