# Cerebro: Local AI OS Integration for Garuda Linux 🧠💻

Cerebro es un ecosistema de Inteligencia Artificial local diseñado para integrarse profundamente con el flujo de trabajo de un usuario avanzado de Linux (KDE/Garuda). A diferencia de los asistentes de chat convencionales, este sistema opera bajo una arquitectura de **Modernidad Líquida**, adaptando su identidad y funciones dinámicamente según el contexto de los datos del usuario.

## 🚀 Características Principales

### 1. Cerebro IA (Multimodalidad Local)
Motor de RAG (Retrieval-Augmented Generation) que procesa y memoriza el contexto local del usuario utilizando modelos de última generación ejecutados localmente vía **Ollama**.
* **Lectura:** Indexación semántica de PDFs y archivos de texto.
* **Vista:** Análisis de imágenes y planos mediante **LLaVA**.
* **Oído:** Transcripción y análisis de audio con **OpenAI Whisper**.

### 2. Bibliotecario IA (Gestión de Datos)
Automatización del mantenimiento del sistema de archivos.
* Escaneo silencioso y actualización de la base de datos SQL del inventario.
* Detección proactiva de archivos duplicados y gestión de limpieza.

### 3. Consejo Líquido (Estratega Reactivo)
Un agente de auditoría proactiva que analiza el estado de proyectos específicos (como la restauración de la Kia Besta o el desarrollo de Aetheria) para ofrecer sugerencias estratégicas basadas en la síntesis de toda la memoria local.

## 🛠️ Arquitectura Técnica

El sistema se apoya en una pila tecnológica robusta y desacoplada del sistema operativo principal para garantizar la estabilidad:

* **Core:** Python 3.14+.
* **Vector DB:** FAISS para almacenamiento de embeddings semánticos.
* **Modelos:** Llama 3.1 (Texto), LLaVA (Visión), Whisper (Audio).
* **Integración:** Lanzadores `.desktop` integrados en **KRunner** para acceso inmediato mediante atajos de teclado.

## 📦 Instalación

1.  **Dependencias del Sistema:**
    ```bash
    sudo pacman -S ollama poppler github-cli
    ```
2.  **Clonar y Configurar:**
    ```bash
    git clone [https://github.com/antupillan/cerebro-ia-local.git](https://github.com/antupillan/cerebro-ia-local.git)
    cd cerebro-ia-local
    ./setup.sh
    ```
3.  **Entorno Virtual:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

## ⌨️ Atajos de KRunner (Alt + Space)

| Comando | Acción |
| :--- | :--- |
| `Cerebro IA` | Inicia chat con memoria persistente. |
| `Cerebro: Vista` | Procesa imágenes y documentos visuales. |
| `Consejo Líquido` | Auditoría estratégica de proyectos. |
| `Comandos IA` | Abre la hoja de referencia técnica. |

## ⚖️ Licencia
Este proyecto es una implementación personal de código abierto enfocada en la soberanía de datos y la automatización avanzada.
