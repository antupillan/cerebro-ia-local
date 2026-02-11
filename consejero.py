import os
import sys
import sqlite3
import json
import re
import ollama
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
# [NUEVO] Módulo de Búsqueda Web
from duckduckgo_search import DDGS

# --- CONFIGURACIÓN ---
DB_SQL_PATH = "inventario_maestro.db"
DB_VECTOR_PATH = "./faiss_db"
MODELO_EMBEDDING = "bge-m3:latest"
MODELO_PENSANTE = "llama3.1:8b" 

def investigar_web(query):
    """[ANTENA] Busca información fresca en internet."""
    print(f" 🌐 Conectando a la red para buscar: '{query}'...")
    try:
        # Buscamos 3 resultados relevantes
        results = DDGS().text(query, max_results=3)
        if not results: return "Sin resultados en la web."
        
        informe = ""
        for r in results:
            informe += f"- [WEB] {r['title']}: {r['body']} (Link: {r['href']})\n"
        return informe
    except Exception as e:
        return f"Error de conexión: {e}"

def obtener_frentes_activos():
    """Detecta actividad reciente en tus archivos."""
    if not os.path.exists(DB_SQL_PATH): return "Base de datos no encontrada."
        
    conn = sqlite3.connect(DB_SQL_PATH)
    cursor = conn.cursor()
    
    # Buscamos carpetas con movimiento reciente
    try:
        cursor.execute("SELECT carpeta_padre, COUNT(*) FROM (SELECT carpeta_padre FROM archivos ORDER BY fecha_modificacion DESC LIMIT 100) GROUP BY carpeta_padre ORDER BY COUNT(*) DESC LIMIT 5")
        zonas = cursor.fetchall()
        conn.close()
        
        if not zonas: return "Sin actividad reciente."
            
        reporte = "ZONAS CALIENTES (Archivos modificados):\n"
        for zona, intensidad in zonas:
            reporte += f"- {zona} (Actividad: {intensidad}%)\n"
        return reporte
    except: return "Error SQL."

def generar_roles_dinamicos(contexto_actividad):
    print(" 🔮 La IA está definiendo el Consejo basado en tu realidad...")
    
    prompt = f"""
    Analiza mis archivos activos:
    {contexto_actividad}

    Define 3 roles de expertos que necesito HOY.
    Para cada rol, incluye una 'busqueda_web' sugerida (ej: "manual taller kia besta pdf" o "bell hooks pdf").
    
    Responde SOLO con un JSON puro:
    [
        {{"id": "1", "titulo": "...", "descripcion": "...", "query_db": "...", "busqueda_web": "..."}},
        ...
    ]
    """
    
    res = ollama.chat(model=MODELO_PENSANTE, messages=[{'role': 'user', 'content': prompt}])
    try:
        match = re.search(r'\[.*\]', res['message']['content'], re.DOTALL)
        return json.loads(match.group(0)) if match else []
    except: 
        return [{"id": "1", "titulo": "Consultor General", "descripcion": "Fallback", "query_db": "general", "busqueda_web": "novedades tecnología"}]

def consultar_memoria(keywords):
    """Busca en tu disco duro (FAISS)."""
    try:
        embedding_func = OllamaEmbeddings(model=MODELO_EMBEDDING)
        if not os.path.exists(DB_VECTOR_PATH): return "Memoria vacía."
        vectorstore = FAISS.load_local(DB_VECTOR_PATH, embedding_func, allow_dangerous_deserialization=True)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
        docs = retriever.invoke(keywords)
        return "\n".join([f"[MEMORIA LOCAL]: {d.page_content[:300]}..." for d in docs])
    except: return "No se pudo acceder a la memoria vectorial."

def ejecutar_consejo(rol, actividad_reciente):
    print(f"\n🧠 Invocando a: {rol['titulo']}...")
    
    # 1. Memoria Interna (Lo que ya tienes)
    contexto_interno = consultar_memoria(rol['query_db'])
    
    # 2. Memoria Externa (Lo que busca en Google/DDG)
    # Aquí es donde ocurre la magia: El rol busca lo que le falta
    contexto_externo = investigar_web(rol['busqueda_web'])
    
    print(" 🤔 Sintetizando estrategia (Interna + Externa)...")
    
    prompt_final = f"""
    ACTÚA COMO: {rol['titulo']}
    CONTEXTO: {rol['descripcion']}
    
    MIS ARCHIVOS ACTIVOS:
    {actividad_reciente}
    
    LO QUE SÉ (Memoria Local):
    {contexto_interno}
    
    LO QUE ENCONTRÉ EN INTERNET (Novedades/Recursos):
    {contexto_externo}
    
    Tu tarea:
    Dame un consejo estratégico. 
    Si encontraste recursos útiles en la web (PDFs, manuales), sugiéreme descargarlos o revisarlos (incluye los links).
    Cruza la información local con la de internet.
    """
    
    stream = ollama.chat(model=MODELO_PENSANTE, messages=[{'role': 'user', 'content': prompt_final}], stream=True)
    
    print("\n" + "═"*60)
    print(f" 📋 INFORME DEL CONSEJERO")
    print("═"*60)
    for chunk in stream:
        print(chunk['message']['content'], end='', flush=True)
    print("\n" + "═"*60)

def main():
    print("\n🏛️  CONSEJO LÍQUIDO CONECTADO (v2.0)")
    actividad = obtener_frentes_activos()
    roles = generar_roles_dinamicos(actividad)
    
    print("\nConsejeros disponibles hoy:")
    print("-" * 50)
    for r in roles:
        print(f" {r['id']}. {r['titulo']}")
        print(f"    └─ Busca en web: '{r.get('busqueda_web', 'General')}'")
    print("-" * 50)
    print(" 4. Salir")
    
    op = input("\n¿A quién escuchamos? ")
    seleccion = next((r for r in roles if r['id'] == op), None)
    
    if seleccion:
        ejecutar_consejo(seleccion, actividad)
    elif op == '4': pass

if __name__ == "__main__":
    main()
