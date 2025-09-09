# PocketFlowa-Assistant
Es un sistema avanzado de recuperación y generación de respuestas (RAG)


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
