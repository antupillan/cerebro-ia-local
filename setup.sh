#!/bin/bash

echo "🚀 Iniciando instalación de Cerebro IA Local..."

# 1. Detectar usuario y rutas actuales
USER_HOME=$HOME
INSTALL_DIR="$USER_HOME/cerebro_cli"
DESKTOP_DIR="$USER_HOME/.local/share/applications"

echo "📂 Directorio detectado: $INSTALL_DIR"

# 2. Crear carpetas si no existen
mkdir -p "$DESKTOP_DIR"

# 3. Copiar y configurar lanzadores
echo "⚙️  Configurando lanzadores para el usuario: $USER..."

for file in install/*.desktop; do
    filename=$(basename "$file")
    target="$DESKTOP_DIR/$filename"
    
    # Copiamos el archivo
    cp "$file" "$target"
    
    # Reemplazamos TU_USUARIO por el usuario real del sistema
    sed -i "s|/home/TU_USUARIO|$USER_HOME|g" "$target"
    
    echo "   ✅ Instalado: $filename"
done

# 4. Permisos de ejecución a los scripts binarios
chmod +x "$INSTALL_DIR/bin/"*.sh

# 5. Actualizar base de datos de escritorio
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || kbuildsycoca6 2>/dev/null

echo "🎉 Instalación completada. Presiona Alt+Space y busca 'Cerebro'."
