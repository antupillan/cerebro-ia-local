#!/bin/bash
cd /home/entropia/cerebro_cli
source venv/bin/activate
echo "📚 Actualizando lecturas (Texto, PDF, Docs)..."
python cerebro.py --texto
read -p "Lectura completada. Enter para salir..."
