# 🤖 PocketFlow Assistant  

PocketFlow Assistant es un sistema avanzado de **recuperación y generación de respuestas (RAG)** que te permite interactuar con documentos de manera inteligente.  
Combina **búsqueda semántica** con **modelos de lenguaje** para ofrecer respuestas precisas basadas en tu información.  

---

## 📌 Tabla de Contenidos  
1. [Introducción](#-introducción)  
2. [Arquitectura del Sistema](#-arquitectura-del-sistema)  
3. [Requisitos del Sistema](#-requisitos-del-sistema)  
4. [Instalación y Configuración](#-instalación-y-configuración)  


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

## 📊 **Diagrama del flujo del sistema:**  

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
```



## 💻 Requisitos del Sistema
-Python 3.10 o superior

-Windows, macOS o Linux

-4 GB RAM mínimo (8 GB recomendados)

-Conexión a internet para descargar modelos y usar API

## 🛠️ Instalación y Configuración

Clona el repositorio:

```bash
git clone https://github.com/tu_usuario/pocketflow-assistant.git
cd pocketflow-assistant
```
Crear entorno virtual

```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```
Instalar dependencias

```bash
pip install -r requirements.txt
```
Configurar variables de entorno
Crea un archivo .env con:

```env
OPENAI_API_KEY=tu_clave_aquí
EMBEDDING_MODEL=text-embedding-3-small
```

Iniciar el sistema

```bash
# Backend
python api.py
# Interfaz
streamlit run ui.py
```


## ⚙️ 10. Diseño Técnico

### 🔄 Flujo de Datos
1. **Procesamiento de Documentos** → Generación de **Embeddings** → Almacenamiento en **FAISS**  
2. **Consulta del Usuario** → Conversión a **Embedding** → **Recuperación** de fragmentos → Generación de **Respuesta**

### 🎛️ Personalización
- Modelo de *embeddings* configurable  
- Tamaño de fragmentos (*chunk size*) ajustable  
- Umbral de relevancia modificable  
```mermaid
flowchart LR
    %% ===== FLUJO DE DATOS =====
    subgraph Indexación[Procesamiento de Documentos]
        A[Documentos] --> B[Generar Embeddings]
        B --> C[Almacenar en FAISS]
    end

    subgraph Consulta[Consulta del Usuario]
        D[Pregunta del Usuario] --> E[Generar Embedding de Consulta]
        E --> F[Buscar en FAISS]
        F --> G[Recuperar Fragmentos Relevantes]
        G --> H[Generar Respuesta con LLM]
    end

    %% CONEXIÓN ENTRE FLUJOS
    C --> F
```
 




