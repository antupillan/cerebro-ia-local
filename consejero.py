import os
import sys
import sqlite3
import json
import re
import ollama
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
from duckduckgo_search import DDGS

# --- CONFIGURACIÓN TÉCNICA ---
DB_SQL_PATH = "inventario_maestro.db"
DB_VECTOR_PATH = "./faiss_db"
MODELO_EMBEDDING = "bge-m3:latest"
MODELO_PENSANTE = "llama3.1:8b"

# Instanciación global (sin suprimir warnings para depuración)
try:
    EMBEDDINGS = OllamaEmbeddings(model=MODELO_EMBEDDING)
except Exception as e:
    print(f"Error crítico iniciando embeddings: {e}")
    sys.exit(1)

def investigar_web(query):
    """Ejecuta búsqueda externa mediante API DuckDuckGo."""
    try:
        # Usamos backend 'lite' para mayor velocidad
        results = DDGS().text(query, max_results=3, backend="lite")
        if not results: return "DATA_NOT_FOUND"
        return "\n".join([f"SOURCE: {r['href']} | CONTENT: {r['body']}" for r in results])
    except Exception as e:
        return f"CONEXION_ERROR: {str(e)}"

def obtener_frentes_activos():
    """Analiza telemetría de archivos mediante SQL."""
    if not os.path.exists(DB_SQL_PATH): return "DB_NOT_FOUND"
    
    try:
        conn = sqlite3.connect(DB_SQL_PATH)
        cursor = conn.cursor()
        query = """
            SELECT carpeta_padre, COUNT(*) 
            FROM (SELECT carpeta_padre FROM archivos ORDER BY fecha_modificacion DESC LIMIT 100) 
            GROUP BY carpeta_padre ORDER BY COUNT(*) DESC LIMIT 5
        """
        cursor.execute(query)
        zonas = cursor.fetchall()
        conn.close()
        
        if not zonas: return "SIN_ACTIVIDAD_RECIENTE"
        return "\n".join([f"SECTOR: {z[0]} | DENSIDAD: {z[1]}" for z in zonas])
    except Exception: 
        return "SQL_QUERY_FAILED"

def generar_roles_dinamicos(contexto):
    """Genera matriz de expertos basada en análisis de actividad."""
    prompt = f"""
    ANALISIS DE ACTIVIDAD: {contexto}
    TAREA: Determinar 3 perfiles técnicos necesarios para optimizar estos sectores.
    FORMATO EXCLUSIVO: JSON puro.
    SCHEMA: [{{"id": "int", "titulo": "string", "descripcion": "string", "query_db": "string", "busqueda_web": "string"}}]
    """
    try:
        res = ollama.chat(model=MODELO_PENSANTE, messages=[{'role': 'user', 'content': prompt}])
        match = re.search(r'\[.*\]', res['message']['content'], re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("JSON no encontrado")
    except Exception:
        # Fallback si falla la inferencia
        return [
            {"id": 1, "titulo": "Analista de Proyectos", "descripcion": "Gestión general", "query_db": "proyectos", "busqueda_web": "gestión proyectos"},
            {"id": 2, "titulo": "Ingeniero de Sistemas", "descripcion": "Soporte técnico", "query_db": "linux configuración", "busqueda_web": "arch linux news"},
            {"id": 3, "titulo": "Investigador", "descripcion": "Análisis académico", "query_db": "investigación", "busqueda_web": "papers recientes"}
        ]

def consultar_memoria(keywords):
    """Recupera vectores de la base de datos FAISS."""
    if not os.path.exists(DB_VECTOR_PATH): return "VEC_DB_NOT_FOUND"
    try:
        db = FAISS.load_local(DB_VECTOR_PATH, EMBEDDINGS, allow_dangerous_deserialization=True)
        docs = db.similarity_search(keywords, k=4)
        if not docs: return "NO_RELEVANT_DATA"
        return "\n".join([f"[DATA]: {d.page_content}" for d in docs])
    except Exception as e: 
        return f"VECTOR_ERROR: {str(e)}"

def ejecutar_consejo(rol, actividad):
    """Interfaz interactiva de análisis estratégico."""
    print(f"\n[SISTEMA]: Inicializando {rol['titulo']}...")
    
    # Búsqueda inicial automática basada en el rol
    print(f" 🔎 Investigando: '{rol['busqueda_web']}'...")
    ext_data = investigar_web(rol['busqueda_web'])
    
    print(f" 🧠 Recordando: '{rol['query_db']}'...")
    loc_data = consultar_memoria(rol['query_db'])

    print(f"[ESTADO]: ACTIVO | CONTEXTO CARGADO")
    print("─"*60)
    
    while True:
        query = input(f"\nλ {rol['titulo']} > ")
        if query.lower() in ["salir", "exit", "4", "5"]: break
        if not query.strip(): continue

        prompt = f"""
        ROL: {rol['titulo']} ({rol['descripcion']})
        
        INFORME DE INTELIGENCIA:
        [INTERNO]: {loc_data[:2500]} 
        [EXTERNO]: {ext_data[:2500]}
        
        CONSULTA USUARIO: {query}
        
        DIRECTRICES DE RESPUESTA:
        1. Respuesta técnica directa. Sin saludos.
        2. Cita fuentes si usas datos [INTERNO] o [EXTERNO].
        3. Prioriza especificaciones técnicas del [INTERNO] si existen.
        4. Rigor científico y economía lingüística.
        """
        
        print("\n", end="")
        stream = ollama.chat(model=MODELO_PENSANTE, messages=[{'role': 'user', 'content': prompt}], stream=True)
        for chunk in stream:
            print(chunk['message']['content'], end='', flush=True)
        print("\n" + "─"*60)

def main():
    print("\n🏛️  CONSEJO LÍQUIDO v2.2")
    actividad = obtener_frentes_activos()
    roles = generar_roles_dinamicos(actividad)
    
    # Lógica de Menú Extendido
    print("\n--- MATRIZ DE EXPERTOS SUGERIDOS ---")
    for r in roles:
        print(f"[{r['id']}] {r['titulo']}")
    
    # Opciones fijas
    opcion_libre = len(roles) + 1
    opcion_salir = len(roles) + 2
    
    print(f"[{opcion_libre}] 🏳️  Consulta Libre (Tema a elección)")
    print(f"[{opcion_salir}] 🚪 Salir")
    
    sel = input("\nSELECCIONAR ID: ")

    # Manejo de selección
    if sel == str(opcion_salir):
        print("Cerrando sesión.")
        return

    elif sel == str(opcion_libre):
        tema = input("\n¿Sobre qué tema necesitas consejo técnico hoy? ")
        rol_ad_hoc = {
            "titulo": "Consultor Especialista",
            "descripcion": f"Experto técnico en {tema}",
            "query_db": tema,
            "busqueda_web": tema
        }
        ejecutar_consejo(rol_ad_hoc, actividad)

    else:
        # Buscar en los roles generados por IA
        rol = next((r for r in roles if str(r['id']) == sel), None)
        if rol: 
            ejecutar_consejo(rol, actividad)
        else:
            print("Selección inválida.")

if __name__ == "__main__":
    main()
