#!/bin/bash
cd /home/entropia/cerebro_cli
source venv/bin/activate
echo "👁️👂 Procesando Multimedia (Imágenes y Audio)..."
python cerebro.py --vision --audio
read -p "Procesamiento sensorial terminado. Enter para salir..."
