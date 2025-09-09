# 🤖 PocketFlow Assistant  

PocketFlow Assistant es un sistema avanzado de **recuperación y generación de respuestas (RAG)** que te permite interactuar con documentos de manera inteligente.  
Combina **búsqueda semántica** con **modelos de lenguaje** para ofrecer respuestas precisas basadas en tu información.  

---

## 📌 Tabla de Contenidos  
1. [Introducción](#-introducción)  
2. [Arquitectura del Sistema](#-arquitectura-del-sistema)  
3. [Requisitos del Sistema](#-requisitos-del-sistema)  
4. [Instalación y Configuración](#-instalación-y-configuración)  
5. [Interfaz de Usuario](#-interfaz-de-usuario)  
6. [Funcionalidades Principales](#-funcionalidades-principales)  
7. [Modo Avanzado](#-modo-avanzado)  
8. [Gestión de Documentos](#-gestión-de-documentos)  
9. [Sesiones de Chat](#-sesiones-de-chat)  
10. [Diseño Técnico](#-diseño-técnico)  
11. [Solución de Problemas](#-solución-de-problemas)  
12. [Preguntas Frecuentes](#-preguntas-frecuentes)  
13. [Conclusión](#-conclusión)  
14. [Soporte](#-soporte)  

---

## 🌟 Introducción  
Con PocketFlow Assistant podrás:  
- Consultar documentos en PDF, DOCX y TXT.  
- Obtener respuestas basadas en contenido real.  
- Mantener conversaciones con memoria de contexto.  
- Filtrar y personalizar parámetros de búsqueda.  

---

## 🏗️ Arquitectura del Sistema  

### 🔹 Procesamiento de Documentos (Offline)  
- Carga de documentos en múltiples formatos.  
- Fragmentación en chunks semánticos.  
- Generación de embeddings.  
- Almacenamiento en FAISS.  

### 🔹 Flujo de Consulta (Online)  
1. Normalización de la consulta.  
2. Búsqueda semántica en FAISS.  
3. Construcción de contexto.  
4. Generación de respuesta con LLM.  

📊 **Diagrama del flujo del sistema:**  

```mermaid
flowchart TD
    %% ===== OFFLINE: INDEXACIÓN =====
    subgraph Offline[Procesamiento de Documentos]
        A[Documentos en /documents] --> B[Procesar Documentos]
        B --> C[Fragmentar Texto]
        C --> D[Generar Embeddings]
        D --> E[Almacenar en FAISS]
    end

    %% ===== ONLINE: CONSULTA =====
    subgraph Online[Consulta del Usuario]
        F[Pregunta del Usuario] --> G[Preprocesar Consulta]
        G --> H[Generar Embedding de Consulta]
        H --> I[Buscar en FAISS]
        I --> J[Obtener Fragmentos Relevantes]
        J --> K[Construir Contexto]
        K --> L[Generar Respuesta con LLM]
        L --> M[Formatear Respuesta]
        M --> N[Mostrar al Usuario]
    end

    %% CONEXIONES ENTRE COMPONENTES
    E -->|Índice FAISS| I
    J -->|Fragmentos| K
    K -->|Contexto| L
💻 Requisitos del Sistema
Python 3.10 o superior

Windows, macOS o Linux

4 GB RAM mínimo (8 GB recomendados)

Conexión a internet para descargar modelos y usar API

🛠️ Instalación y Configuración
Clonar el repositorio

bash
Copy code
git clone [URL_DEL_REPOSITORIO]
cd pocket_rag
Crear entorno virtual

bash
Copy code
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
Instalar dependencias

bash
Copy code
pip install -r requirements.txt
Configurar variables de entorno
Crea un archivo .env con:

env
Copy code
OPENAI_API_KEY=tu_clave_aquí
EMBEDDING_MODEL=text-embedding-3-small
Estructura recomendada

python
Copy code
pocket_rag/
│── documents/        # documentos cargados
│── api.py            # backend
│── ui.py             # interfaz
│── faiss_index.bin   # índice vectorial
│── metadata.pkl      # metadatos
Iniciar el sistema

bash
Copy code
# Backend
uvicorn api:app --reload
# Interfaz
streamlit run ui.py
📸 Figura 1: Terminal mostrando backend e interfaz corriendo.

🖥️ Interfaz de Usuario
🔹 Barra Lateral
Documentos cargados.

Botón para subir archivos.

Configuración avanzada.

🔹 Área Principal
Historial de chat.

Entrada de texto para preguntas.

📸 Figura 2: Interfaz inicial sin documentos.
📸 Figura 3: Interfaz con documentos cargados y conversación activa.

🚀 Funcionalidades Principales
Búsqueda semántica en múltiples documentos.

Filtrado por metadatos.

Atribución de fuentes en las respuestas.

📸 Figura 4: Pregunta con respuesta citando fuentes.

🔧 Modo Avanzado
Ajustar número de chunks (1–10).

Filtrar por archivo o sección.

Configurar namespace para agrupar documentos.

Activar streaming de respuestas.

Mantener sesiones de chat.

📸 Figura 5: Pantalla de filtros y parámetros avanzados.

📚 Gestión de Documentos
Subir documentos arrastrando o seleccionando archivos.

Reindexar un documento desde el menú desplegable.

📸 Figura 6: Proceso de carga y botón Reindexar.

💬 Sesiones de Chat
Mantiene contexto entre preguntas.

Historial accesible en la interfaz.

Identificador único por sesión.

📸 Figura 7: Conversación con múltiples turnos en la misma sesión.

⚙️ Diseño Técnico
Indexación: documentos → embeddings → FAISS.

Consulta: embedding de consulta → búsqueda → respuesta.

Personalización: chunk size, modelo de embeddings, umbrales de relevancia.

📊 (Ver diagrama en la sección Arquitectura del Sistema)

🐛 Solución de Problemas
Problema	Posible Solución
Documento no carga	Verificar formato y permisos
Respuestas imprecisas	Reformular pregunta o aumentar chunks
Error en servidor	Revisar si backend está en ejecución