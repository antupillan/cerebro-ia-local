#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OIDO v2.0 - Módulo de Transcripción Neural
------------------------------------------
Rol: Oídos del sistema. Convierte voz a texto.
Motor: Faster-Whisper (local).
Modelos recomendados: 'small' (rápido) o 'medium' (preciso).

Uso: python oido.py <archivo_audio> [--model medium]
Salida: Texto transcrito en stdout.
------------------------------------------
"""

import sys
import os
import argparse
import time
import warnings

# Silenciar advertencias de Torch/Whisper
warnings.filterwarnings("ignore")

try:
    from faster_whisper import WhisperModel
except ImportError:
    sys.exit("Error: Falta 'faster-whisper'. pip install faster-whisper")

# --- INTEGRACIÓN CEREBRO (Aprendizaje Pasivo) ---
try:
    from cerebro import memorizar
except ImportError:
    # Si no hay cerebro, decorador dummy que no hace nada
    def memorizar(tipo_origen):
        return lambda func: func

# Colores para feedback
CYAN = '\033[96m'
RESET = '\033[0m'

@memorizar("audio_transcrito")
def transcribir_audio(ruta_audio, modelo="small", idioma=None):
    if not os.path.exists(ruta_audio):
        return f"Error: Archivo {ruta_audio} no encontrado."

    print(f"{CYAN}   👂 Cargando modelo Whisper ({modelo})...{RESET}", file=sys.stderr)
    
    try:
        # device="auto" elegirá GPU si está disponible (CUDA) o CPU
        # compute_type="int8" es más rápido en CPU
        model = WhisperModel(modelo, device="auto", compute_type="int8")
        
        print(f"{CYAN}   🎙️  Transcribiendo...{RESET}", file=sys.stderr)
        segments, info = model.transcribe(ruta_audio, beam_size=5, language=idioma)
        
        texto_final = []
        for segment in segments:
            texto_final.append(segment.text)
            # Feedback de progreso en stderr para no ensuciar el pipe
            # print(f"[{segment.start:.2f}s -> {segment.end:.2f}s] {segment.text}", file=sys.stderr)
            
        return " ".join(texto_final).strip()

    except Exception as e:
        return f"Error en transcripción: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Módulo de Oído (Whisper Local)")
    parser.add_argument("file", help="Ruta del archivo de audio (mp3, wav, m4a...)")
    parser.add_argument("--model", default="small", help="Modelo Whisper (tiny, small, medium, large-v3)")
    parser.add_argument("--lang", default=None, help="Idioma (es, en...). Auto si se omite.")
    
    args = parser.parse_args()
    
    resultado = transcribir_audio(args.file, args.model, args.lang)
    print(resultado)

if __name__ == "__main__":
    main()
