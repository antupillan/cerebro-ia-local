#!/bin/bash

# Configuración
VENV_PATH="/home/entropia/cerebro_cli/venv"
CEREBRO_PATH="/home/entropia/cerebro_cli"
TEMP_AUDIO="/tmp/franki_voz.wav"

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Limpiar restos anteriores
rm -f "$TEMP_AUDIO"

echo -e "${BLUE}🎙️  FRANKI ESCUCHANDO... (Presiona ENTER para detener)${NC}"

# Iniciar grabación en segundo plano (silencioso)
parecord --format=s16le --channels=1 --rate=16000 "$TEMP_AUDIO" > /dev/null 2>&1 &
PID_REC=$!

# Esperar a que el usuario presione ENTER
read -p ""

# Detener grabación limpiamente
kill -SIGINT "$PID_REC" 2>/dev/null
wait "$PID_REC" 2>/dev/null

echo -e "${GREEN}🛑 Procesando audio...${NC}"

# Transcripción
echo -e "${BLUE}🧠 Transcribiendo...${NC}"
source "$VENV_PATH/bin/activate"
cd "$CEREBRO_PATH"

# Usamos python directamente para capturar la salida limpia
TEXTO_TRANSCRITO=$(python oido.py "$TEMP_AUDIO" --model small 2>/dev/null)

if [ -z "$TEXTO_TRANSCRITO" ]; then
    echo "❌ No se escuchó nada o hubo un error."
    exit 1
fi

echo -e "${GREEN}🗣️  Tú dijiste: $TEXTO_TRANSCRITO${NC}"

# Enviar a Franki (usando el módulo KRunner para notificación)
python franki_krunner.py fast "$TEXTO_TRANSCRITO"

# Limpieza
rm "$TEMP_AUDIO"
