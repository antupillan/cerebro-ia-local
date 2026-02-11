#!/bin/bash
cd /home/entropia/cerebro_cli
source venv/bin/activate
python cerebro.py
# Pausa al final por si hay error, para poder leerlo
read -p "Presiona Enter para cerrar..."
