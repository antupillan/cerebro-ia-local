#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
CONSEJERO v2.0 - Agente de Investigación Web (One-Shot)
-------------------------------------------------------
Rol: Sub-agente de búsqueda y síntesis de información externa.
Uso: python consejero.py "query"
Salida: Informe conciso con fuentes.
------------------------------------------------------- """

import sys
import argparse
import json
import warnings
import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
import html2text

# Configuración de Logs
warnings.filterwarnings("ignore")

# --- INTEGRACIÓN CEREBRO (Aprendizaje Pasivo) ---
try:
    from cerebro import memorizar
except ImportError:
    # Si no hay cerebro, decorador dummy que no hace nada
    def memorizar(tipo_origen):
        return lambda func: func

try:
    from langchain_ollama import ChatOllama
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
except ImportError:
    # Si se importa como módulo y fallan estas, puede ser problemático, 
    # pero permitimos que el script principal maneje la excepción si es necesario.
    pass

# --- CONFIGURACIÓN ---
MODELO_SINTESIS = "llama3.1:8b"

def buscar_web(query, max_results=5):
    """Busca en DuckDuckGo y devuelve resultados crudos."""
    # print(f"   🔎 Investigando: '{query}'...", file=sys.stderr)
    try:
        results = DDGS().text(query, max_results=max_results)
        return list(results) if results else []
    except Exception as e:
        print(f"   ⚠️ Error de red: {e}", file=sys.stderr)
        return []

def leer_pagina(url):
    """
    [CONSEJERO] Lee una URL y la convierte a Markdown limpio.
    Mantiene enlaces, tablas y estructura, pero elimina el ruido.
    """
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() 
        
        # Configurar el convertidor
        h = html2text.HTML2Text()
        h.ignore_links = False      
        h.ignore_images = True      
        h.ignore_emphasis = False   
        h.body_width = 0            
        
        # Conversión
        markdown_content = h.handle(response.text)
        
        # Limpieza extra
        clean_md = "\n".join([line for line in markdown_content.splitlines() if line.strip()])
        
        return clean_md[:8000] 
    except Exception as e:
        return f"Error leyendo web: {e}"

def sintetizar_info(query, resultados):
    """Usa Llama 3.1 para generar un informe."""
    if not resultados: return "No se encontró información relevante."

    # Si hay pocos resultados o parecen pobres, intentamos leer la primera web
    contexto_parts = []
    for i, r in enumerate(resultados):
        body = r['body']
        # Si es el primer resultado y es muy corto, intentamos expandirlo
        if i == 0 and len(body) < 200:
             full_text = leer_pagina(r['href'])
             if full_text: body = full_text[:1000] # Limitamos para no saturar
        
        contexto_parts.append(f"Fuente: {r['href']}\nInfo: {body}")

    contexto = "\n\n".join(contexto_parts)
    
    template = """
    Eres un Analista de Inteligencia. Responde a la consulta basándote en:
    
    CONSULTA: {query}
    
    DATOS RECUPERADOS:
    {contexto}
    
    INSTRUCCIONES:
    1. Responde directamente a la pregunta.
    2. Si buscas datos numéricos (hora, precio), sé exacto.
    3. Cita la URL principal.
    """
    
    try:
        prompt = ChatPromptTemplate.from_template(template)
        llm = ChatOllama(model=MODELO_SINTESIS, temperature=0.1)
        chain = prompt | llm | StrOutputParser()
        return chain.invoke({"query": query, "contexto": contexto})
    except NameError:
        return "Error: Langchain no disponible."

@memorizar("investigacion_web")
def investigar(query: str) -> str:
    """Función principal para ser importada por otros módulos."""
    raw = buscar_web(query)
    return sintetizar_info(query, raw)

def main():
    if len(sys.argv) < 2:
        print("Uso: python consejero.py 'tu pregunta'")
        sys.exit(1)
    
    query = " ".join(sys.argv[1:])
    print(investigar(query))

if __name__ == "__main__":
    main()