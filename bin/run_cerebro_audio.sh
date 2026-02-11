#!/bin/bash
cd /home/entropia/cerebro_cli
source venv/bin/activate
echo "👂 Transcribiendo Audio (Whisper)..."
python cerebro.py --audio
read -p "Transcripción auditiva completada. Enter para salir..."
