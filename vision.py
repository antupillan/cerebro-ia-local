#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
VISION v2.0 - Módulo de Análisis Visual Neural
----------------------------------------------
Rol: Ojos del sistema. Analiza imágenes locales.
Modelos:
- Moondream: Rápido, descripciones generales.
- Llama 3.2-Vision: Detallado, OCR, análisis técnico.

Uso: python vision.py <ruta_imagen> [prompt] [--fast]
----------------------------------------------
"""

import sys
import os
import argparse
try:
    import ollama
except ImportError:
    sys.exit("Error: Falta librería 'ollama'. pip install ollama")

# --- INTEGRACIÓN CEREBRO (Aprendizaje Pasivo) ---
try:
    from cerebro import memorizar
except ImportError:
    # Si no hay cerebro, decorador dummy que no hace nada
    def memorizar(tipo_origen):
        return lambda func: func

MODELS = {
    "fast": "moondream:latest",
    "detail": "llama3.2-vision:latest"
}

@memorizar("imagen_analizada")
def analyze_image(image_path: str, prompt: str, fast_mode: bool = False) -> str:
    if not os.path.exists(image_path):
        return f"Error: Imagen no encontrada en {image_path}"

    model = MODELS["fast"] if fast_mode else MODELS["detail"]
    
    try:
        response = ollama.chat(
            model=model,
            messages=[{
                'role': 'user',
                'content': prompt,
                'images': [image_path]
            }]
        )
        return response['message']['content']
    except Exception as e:
        return f"Error en análisis visual: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Módulo de Visión Artificial")
    parser.add_argument("path", help="Ruta de la imagen")
    parser.add_argument("prompt", nargs="?", default="Describe esta imagen.", help="Pregunta sobre la imagen")
    parser.add_argument("--fast", action="store_true", help="Usar modelo rápido (Moondream)")
    
    args = parser.parse_args()
    
    print(f"--- Viendo: {args.path} ({'Rápido' if args.fast else 'Detallado'}) ---", file=sys.stderr)
    result = analyze_image(args.path, args.prompt, args.fast)
    print(result)

if __name__ == "__main__":
    main()
