#!/bin/bash
cd /home/entropia/cerebro_cli
source venv/bin/activate
echo "👁️ Analizando Imágenes y PDFs escaneados..."
python cerebro.py --vision
read -p "Análisis visual completado. Enter para salir..."
