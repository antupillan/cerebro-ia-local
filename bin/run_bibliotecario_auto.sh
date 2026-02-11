#!/bin/bash
cd /home/entropia/cerebro_cli
source venv/bin/activate
echo "🕵️ Escaneo rápido de archivos en curso..."
python bibliotecario.py --auto
read -p "Inventario actualizado. Enter para salir..."
