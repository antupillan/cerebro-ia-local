import os
rutas = [
    "/home/entropia/Documentos/Kia Besta",
    "/home/entropia/Documentos/Biblioteca_Calibre",
    "/home/entropia/Documentos/Filosofia"
]
for r in rutas:
    existe = os.path.exists(r)
    contenido = len(os.listdir(r)) if existe else "N/A"
    print(f"Ruta: '{r}' | Existe: {existe} | Archivos: {contenido}")
