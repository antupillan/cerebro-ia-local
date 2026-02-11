import os
import sys
import sqlite3
import datetime
import hashlib
import ollama
import pandas as pd

# --- TUS RUTAS ---
RUTAS_CARPETAS = [
    "/home/entropia/Documentos/Aetheria",
    "/home/entropia/Documentos/Calibre Library",  # Nombre real detectado
    "/home/entropia/Documentos/Literatura",       # Reemplaza a Filosofía
    "/home/entropia/Documentos/Defensa",
    "/home/entropia/Documentos/Notes",            # Probablemente contenga info útil
    "/home/entropia/Documentos/Project",          # Posible ubicación de Kia Besta?
    "/home/entropia/Documentos/Nacionalización_indigena", # Parece relevante
    "/home/entropia/Documentos/Diplomado metodos agiles"
]

# --- FILTROS DE RUIDO (CRUCIAL PARA PROYECTOS DE CÓDIGO) ---
IGNORAR_CARPETAS = {'node_modules', '.git', 'venv', '__pycache__', '.vscode', 'build', 'dist', '.idea'}
IGNORAR_EXTENSIONES = {'.map', '.lock'} 

DB_PATH = "inventario_maestro.db"

def calcular_hash(ruta, block_size=65536):
    """Calcula la huella digital única (MD5) del archivo."""
    hasher = hashlib.md5()
    try:
        with open(ruta, 'rb') as f:
            buf = f.read(block_size)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(block_size)
        return hasher.hexdigest()
    except:
        return None

def conectar_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS archivos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            extension TEXT,
            ruta_completa TEXT UNIQUE,
            carpeta_padre TEXT,
            tamano_bytes INTEGER,  -- Precisión absoluta
            hash_contenido TEXT,   -- Identidad real
            fecha_modificacion TEXT
        )
    ''')
    # Índice para acelerar búsquedas de duplicados
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash ON archivos(hash_contenido)')
    conn.commit()
    return conn

def escanear_sistema():
    conn = conectar_db()
    cursor = conn.cursor()
    print(f"[BIBLIOTECARIO v2] Iniciando escaneo profundo en {len(RUTAS_CARPETAS)} zonas...")
    
    total_archivos = 0
    archivos_nuevos = 0
    omitidos = 0

    for ruta_base in RUTAS_CARPETAS:
        if not os.path.exists(ruta_base): continue
        print(f" 📂 Explorando: {ruta_base}")
        
        for root, dirs, files in os.walk(ruta_base):
            # 1. Filtrado Inteligente de Carpetas (Modifica la lista 'dirs' in-place)
            dirs[:] = [d for d in dirs if d not in IGNORAR_CARPETAS]
            
            for file in files:
                # 2. Filtrado de Extensiones
                ext = os.path.splitext(file)[1].lower()
                if ext in IGNORAR_EXTENSIONES:
                    omitidos += 1
                    continue

                ruta_abs = os.path.join(root, file)
                
                try:
                    stats = os.stat(ruta_abs)
                    tamano_bytes = stats.st_size
                    fecha = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d')
                    padre = os.path.basename(root)

                    # 3. Cálculo de Hash (Solo si es necesario para evitar lentitud extrema)
                    # Para optimizar: Podríamos hashear solo si hay colisión de nombre+tamaño,
                    # pero para 'finura' total, hasheamos todo (costoso pero seguro).
                    file_hash = calcular_hash(ruta_abs)

                    try:
                        cursor.execute('''
                            INSERT INTO archivos (nombre, extension, ruta_completa, carpeta_padre, tamano_bytes, hash_contenido, fecha_modificacion)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        ''', (file, ext, ruta_abs, padre, tamano_bytes, file_hash, fecha))
                        archivos_nuevos += 1
                    except sqlite3.IntegrityError:
                        pass 
                    
                    total_archivos += 1
                    # Barra de progreso simple
                    if total_archivos % 500 == 0:
                        print(f"    -> Procesados: {total_archivos}...", end='\r')
                    
                except Exception as e:
                    pass

    conn.commit()
    conn.close()
    print(f"\n[ESTADO] Inventario finalizado.")
    print(f"   - Total Archivos Válidos: {total_archivos}")
    print(f"   - Ruido Omitido (node_modules, etc): {omitidos}")

def consultar_duplicados():
    conn = conectar_db()
    # La consulta ahora agrupa por HASH. Si el hash es igual, el contenido es idéntico.
    query = '''
        SELECT nombre, carpeta_padre, tamano_bytes, hash_contenido, COUNT(*) as copias
        FROM archivos 
        WHERE hash_contenido IS NOT NULL
        GROUP BY hash_contenido
        HAVING copias > 1
        ORDER BY tamano_bytes DESC -- Mostrar primero los duplicados que más espacio ocupan
    '''
    df = pd.read_sql_query(query, conn)
    
    if not df.empty:
        # Convertir bytes a MB para visualización
        df['MB'] = (df['tamano_bytes'] / (1024 * 1024)).round(2)
        print(f"\n[ALERTA] Se detectaron {len(df)} grupos de archivos IDÉNTICOS (por contenido):")
        # Mostramos las columnas relevantes
        print(df[['nombre', 'MB', 'copias', 'carpeta_padre']].head(15))
        
        ver_detalles = input("\n¿Quieres ver las rutas de un archivo específico? (Escribe el nombre o Enter para salir): ")
        if ver_detalles.strip():
            detalles = pd.read_sql_query("SELECT ruta_completa FROM archivos WHERE nombre = ?", conn, params=(ver_detalles,))
            print(f"\nUbicaciones de '{ver_detalles}':")
            for r in detalles['ruta_completa']:
                print(f" - {r}")
    else:
        print("\n[OK] Limpio. No hay duplicados de contenido real.")
    
    conn.close()

def ia_sugerir_organizacion():
    conn = conectar_db()
    cursor = conn.cursor()
    # Tomamos una muestra más rica
    cursor.execute("SELECT nombre, carpeta_padre FROM archivos WHERE tamano_bytes > 10240 ORDER BY RANDOM() LIMIT 80")
    muestra = cursor.fetchall()
    conn.close()

    if not muestra:
        print("No hay suficientes datos para analizar.")
        return

    lista_archivos = "\n".join([f"- {m[0]} (Carpeta actual: {m[1]})" for m in muestra])

    prompt = f"""
    Actúa como un Bibliotecario de Sistemas Experto.
    Analiza esta lista de archivos reales de mi sistema y propón una ESTRUCTURA DE DIRECTORIOS OPTIMIZADA.
    
    Reglas:
    1. Agrupa por contexto semántico (ej. "Técnico", "Personal", "Legal").
    2. Identifica proyectos claros (Aetheria, Kia Besta, etc).
    3. Ignora archivos de sistema si se colaron.
    
    ARCHIVOS:
    {lista_archivos}

    Salida esperada: Un árbol de carpetas en Markdown.
    """

    print("\n[BIBLIOTECARIO] Consultando al Estratega (Llama 3.1)...")
    try:
        response = ollama.chat(model='llama3.1:8b', messages=[{'role': 'user', 'content': prompt}])
        print("\n" + "="*60)
        print(" 🏛️  PROPUESTA DE REORGANIZACIÓN")
        print("="*60)
        print(response['message']['content'])
    except Exception as e:
        print(f"Error conectando con Ollama: {e}")

def main():
    while True:
        print("\n--- BIBLIOTECARIO v2 (PRECISIÓN HASH) ---")
        print("1. Escanear (Ignorando node_modules)")
        print("2. Ver Estadísticas")
        print("3. Buscar Duplicados Reales (Por Contenido)")
        print("4. Sugerir Organización (IA)")
        print("5. Salir")
        
        op = input("Opción: ")
        
        if op == '1': escanear_sistema()
        elif op == '2':
            conn = conectar_db()
            try:
                df = pd.read_sql_query("SELECT extension, COUNT(*) as cant, SUM(tamano_bytes)/1024/1024 as MB FROM archivos GROUP BY extension ORDER BY MB DESC", conn)
                print(df.head(10))
            except: print("Primero debes escanear (Opción 1).")
            conn.close()
        elif op == '3': consultar_duplicados()
        elif op == '4': ia_sugerir_organizacion()
        elif op == '5': break

def generar_script_limpieza():
    conn = conectar_db()
    # Buscamos grupos de hashes repetidos
    query = '''
        SELECT hash_contenido, nombre, count(*) as c 
        FROM archivos 
        GROUP BY hash_contenido 
        HAVING c > 1
    '''
    cursor = conn.cursor()
    cursor.execute(query)
    grupos = cursor.fetchall()
    
    if not grupos:
        print("No hay duplicados para procesar.")
        return

    print(f"\n[JUEZ] Analizando {len(grupos)} conflictos de archivos...")
    
    comandos_borrado = []
    bytes_ahorrados = 0

    for hash_c, nombre, _ in grupos:
        # Traemos todas las rutas de este archivo idéntico
        q_rutas = "SELECT ruta_completa, tamano_bytes FROM archivos WHERE hash_contenido = ?"
        cursor.execute(q_rutas, (hash_c,))
        archivos = cursor.fetchall() # Lista de tuplas (ruta, bytes)
        
        # LÓGICA DE SUPERVIVENCIA
        # 1. Buscamos si alguno vive en Calibre Library (Prioridad Máxima)
        master = None
        candidatos_borrar = []
        
        rutas_calibre = [a for a in archivos if "Calibre Library" in a[0]]
        rutas_otras = [a for a in archivos if "Calibre Library" not in a[0]]
        
        if rutas_calibre:
            # Si hay uno en Calibre, ese sobrevive. 
            # (Si hay 2 en Calibre, nos quedamos con el primero que aparezca, raro caso)
            master = rutas_calibre[0]
            # El resto de Calibre + los de fuera se borran
            candidatos_borrar = rutas_calibre[1:] + rutas_otras
        else:
            # Si ninguno es de Calibre, conservamos el de la ruta más larga 
            # (asumiendo que ruta larga = mejor organizado/clasificado)
            # O podrías preferir ruta más corta. Aquí uso longitud como proxy de "ordenado".
            archivos.sort(key=lambda x: len(x[0]), reverse=True)
            master = archivos[0]
            candidatos_borrar = archivos[1:]

        # Generar comandos
        for cand in candidatos_borrar:
            ruta = cand[0]
            bytes_ahorrados += cand[1]
            # Comando rm seguro para linux
            cmd = f'rm "{ruta}" # Duplicado de: {os.path.basename(master[0])}'
            comandos_borrado.append(cmd)

    conn.close()

    # Guardar script
    nombre_script = "limpieza_duplicados.sh"
    with open(nombre_script, "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"# Script generado automáticamente. Ahorro potencial: {bytes_ahorrados/1024/1024:.2f} MB\n")
        f.write("# REVISA ESTE ARCHIVO ANTES DE EJECUTARLO\n\n")
        for cmd in comandos_borrado:
            f.write(cmd + "\n")
            
    print(f"\n[EXITO] Se ha generado '{nombre_script}'")
    print(f"   - Archivos marcados para morir: {len(comandos_borrado)}")
    print(f"   - Espacio a recuperar: {bytes_ahorrados/1024/1024:.2f} MB")
    print(f"   - INSTRUCCIÓN: Abre el archivo, revísalo y ejecútalo con 'bash {nombre_script}'")

# --- ACTUALIZAR EL MENÚ MAIN ---
def main():
    while True:
        print("\n--- BIBLIOTECARIO v3 (JUEZ) ---")
        print("1. Escanear")
        print("2. Ver Estadísticas")
        print("3. Ver Duplicados")
        print("4. Sugerir Organización (IA)")
        print("5. 💀 GENERAR SCRIPT DE LIMPIEZA (Inteligente)")
        print("6. Salir")
        
        op = input("Opción: ")
        
        if op == '1': escanear_sistema()
        elif op == '2':
            conn = conectar_db()
            try:
                df = pd.read_sql_query("SELECT extension, COUNT(*) as cant, SUM(tamano_bytes)/1024/1024 as MB FROM archivos GROUP BY extension ORDER BY MB DESC", conn)
                print(df.head(10))
            except: pass
            conn.close()
        elif op == '3': consultar_duplicados()
        elif op == '4': ia_sugerir_organizacion()
        elif op == '5': generar_script_limpieza() # <--- NUEVO
        elif op == '6': break

# --- MENÚ PRINCIPAL CON MODO AUTOMÁTICO ---
def main():
    # 1. DETECCIÓN DE MODO DESATENDIDO (Para Systemd)
    if len(sys.argv) > 1 and sys.argv[1] == "--auto":
        print("\n[MODO AUTOMÁTICO] 🌙 Protocolo nocturno iniciado...")
        try:
            escanear_sistema()
            print("[AUTO] Inventario actualizado con éxito.")
        except Exception as e:
            print(f"[AUTO] Error crítico: {e}")
        sys.exit(0)

    # 2. MODO INTERACTIVO (Para Humanos)
    while True:
        print("\n--- BIBLIOTECARIO v3 (JUEZ) ---")
        print("1. Escanear (Actualizar DB)")
        print("2. Ver Estadísticas")
        print("3. Ver Duplicados (Solo visualizar)")
        print("4. Sugerir Organización (IA)")
        print("5. 💀 GENERAR SCRIPT DE LIMPIEZA")
        print("6. Salir")
        
        op = input("Opción: ")
        
        if op == '1': escanear_sistema()
        elif op == '2':
            conn = conectar_db()
            try:
                df = pd.read_sql_query("SELECT extension, COUNT(*) as cant, ROUND(SUM(tamano_bytes)/1024.0/1024.0, 2) as MB FROM archivos GROUP BY extension ORDER BY MB DESC LIMIT 10", conn)
                print(df)
            except: pass
            conn.close()
        elif op == '3': consultar_duplicados()
        elif op == '4': ia_sugerir_organizacion()
        elif op == '5': generar_script_limpieza()
        elif op == '6': break

if __name__ == "__main__":
    main()
