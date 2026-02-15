#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
BIBLIOTECARIO v4.0 - Gestor de Archivos Inteligente
---------------------------------------------------
Rol: Mantenimiento del Sistema de Archivos (Deduplicación, Organización).
Uso: python bibliotecario.py [scan|dedup|organize|stats] --target "/ruta"
Optimización: Hash MD5 para precisión total.
---------------------------------------------------
"""

import os
import sys
import hashlib
import sqlite3
import argparse
import pandas as pd
from datetime import datetime

# --- CONFIGURACIÓN ---
DB_PATH = "inventario_maestro.db"
IGNORAR_CARPETAS = {'node_modules', '.git', 'venv', '__pycache__', '.vscode', 'build', 'dist', '.idea'}

def calcular_hash(ruta, block_size=65536):
    """Calcula MD5 del archivo."""
    hasher = hashlib.md5()
    try:
        with open(ruta, 'rb') as f:
            buf = f.read(block_size)
            while len(buf) > 0:
                hasher.update(buf)
                buf = f.read(block_size)
        return hasher.hexdigest()
    except: return None

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
            tamano_bytes INTEGER,
            hash_contenido TEXT,
            fecha_modificacion TEXT
        )
    ''')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash ON archivos(hash_contenido)')
    conn.commit()
    return conn

def escanear(ruta_base):
    conn = conectar_db()
    cursor = conn.cursor()
    print(f"📂 Escaneando: {ruta_base}...")
    
    count = 0
    for root, dirs, files in os.walk(ruta_base):
        dirs[:] = [d for d in dirs if d not in IGNORAR_CARPETAS]
        
        for file in files:
            ruta_abs = os.path.join(root, file)
            try:
                stats = os.stat(ruta_abs)
                ext = os.path.splitext(file)[1].lower()
                
                # Hash solo si es necesario (optimizable)
                file_hash = calcular_hash(ruta_abs)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO archivos (nombre, extension, ruta_completa, carpeta_padre, tamano_bytes, hash_contenido, fecha_modificacion)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (file, ext, ruta_abs, os.path.basename(root), stats.st_size, file_hash, datetime.now().isoformat()))
                
                count += 1
                if count % 100 == 0: print(f"   -> Procesados: {count}", end='\r')
            except: pass
            
    conn.commit()
    conn.close()
    print(f"\n✅ Escaneo completado. {count} archivos indexados.")

def buscar_duplicados():
    conn = conectar_db()
    query = '''
        SELECT hash_contenido, COUNT(*) as copias, SUM(tamano_bytes)/1024/1024 as MB_total
        FROM archivos 
        WHERE hash_contenido IS NOT NULL
        GROUP BY hash_contenido
        HAVING copias > 1
        ORDER BY MB_total DESC
    '''
    df = pd.read_sql_query(query, conn)
    
    if df.empty:
        print("✅ No hay duplicados.")
        return

    print(f"\n⚠️  Detectados {len(df)} grupos de duplicados. Generando reporte...")
    
    with open("reporte_duplicados.txt", "w") as f:
        f.write("REPORTE DE DUPLICADOS\n=====================\n\n")
        for _, row in df.iterrows():
            f.write(f"HASH: {row['hash_contenido']} | Espacio desperdiciado: {row['MB_total']:.2f} MB\n")
            rutas = pd.read_sql_query("SELECT ruta_completa FROM archivos WHERE hash_contenido = ?", conn, params=(row['hash_contenido'],))
            for r in rutas['ruta_completa']:
                f.write(f" - {r}\n")
            f.write("\n")
            
    print(f"📄 Ver detalles en 'reporte_duplicados.txt'")
    conn.close()

def estadisticas():
    conn = conectar_db()
    try:
        df = pd.read_sql_query("SELECT extension, COUNT(*) as cant, SUM(tamano_bytes)/1024/1024 as MB FROM archivos GROUP BY extension ORDER BY MB DESC LIMIT 10", conn)
        print("\nTOP 10 TIPOS DE ARCHIVO POR ESPACIO:")
        print(df.to_string(index=False))
    except: print("Base de datos vacía.")
    conn.close()

def main():
    parser = argparse.ArgumentParser(description="BIBLIOTECARIO: Gestor de Archivos")
    parser.add_argument("accion", choices=["scan", "dedup", "stats"], help="Acción a realizar")
    parser.add_argument("--target", type=str, help="Ruta objetivo (para scan)")
    
    args = parser.parse_args()
    
    if args.accion == "scan":
        if not args.target: sys.exit("Error: --target requerido para scan.")
        escanear(args.target)
    elif args.accion == "dedup":
        buscar_duplicados()
    elif args.accion == "stats":
        estadisticas()

if __name__ == "__main__":
    main()