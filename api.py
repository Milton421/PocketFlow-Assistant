from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import os
import uuid
import time
import json
from contextlib import asynccontextmanager
from datetime import datetime
import shutil

from nodes.document_processor_node import DocumentProcessorNode
from nodes.retriever_node import Retriever
from nodes.prompt_constructor_node import PromptConstructor
from nodes.response_generator_node import ResponseGenerator
from nodes.query_preprocessor_node import QueryPreprocessor
from nodes.response_formatter_node import ResponseFormatter

# --- Modelos Pydantic ---
class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    filters: Optional[Dict[str, Any]] = None
    namespace: Optional[str] = None
    stream: Optional[bool] = False

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime

class ChatSession(BaseModel):
    session_id: str
    messages: List[ChatMessage] = []
    created_at: datetime

# --- Variables globales ---
formatter = ResponseFormatter()
chat_sessions: Dict[str, ChatSession] = {}
query_metrics: List[Dict] = []

# --- Carpeta de documentos ---
DOCUMENTS_FOLDER = "documents"

# --- Lifespan event handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    if os.path.exists(DOCUMENTS_FOLDER):
        docs = [
            f for f in os.listdir(DOCUMENTS_FOLDER)
            if f.lower().endswith((".pdf", ".docx", ".txt"))
        ]
        if docs:
            print("📂 Procesando documentos al inicio...")
            for file in docs:
                path = os.path.join(DOCUMENTS_FOLDER, file)
                print(f"  ➜ Indexando {file}")
                doc_processor.process(path, {"source": file})
        else:
            print("⚠️ La carpeta 'documents/' está vacía. Agrega archivos para indexarlos.")
    else:
        print("⚠️ No existe la carpeta 'documents/'. Crea la carpeta y coloca tus archivos.")
    
    yield
    # Shutdown (si necesitas cleanup)
    print("🔄 Cerrando aplicación...")

# --- Inicialización de FastAPI ---
app = FastAPI(
    title="PocketFlow Assistant (FAISS)",
    description="RAG System with FAISS vector database",
    version="2.0.0",
    lifespan=lifespan
)

# --- Nodos principales ---
doc_processor = DocumentProcessorNode()
retriever = Retriever()
prompt_builder = PromptConstructor()
generator = ResponseGenerator()
preprocessor = QueryPreprocessor()

@app.get("/")
async def root():
    return {
        "message": "PocketFlow Assistant (FAISS) está activo. Usa /ask para consultas o /upload para subir documentos."
    }


# --- Funciones auxiliares ---
def calculate_confidence_score(chunks: List[Dict], answer: str) -> str:
    """Calcula el nivel de confianza basado en relevancia y longitud de respuesta"""
    if not chunks:
        return "low"
    
    avg_score = sum(c.get("relevance_score", 0) for c in chunks) / len(chunks)
    answer_length = len(answer.split())
    
    if avg_score >= 0.7 and answer_length >= 20:
        return "high"
    elif avg_score >= 0.4 and answer_length >= 10:
        return "medium"
    else:
        return "low"

def log_query_metrics(query: str, response_time: float, confidence: str, chunks_count: int):
    """Registra métricas de consulta para monitoreo"""
    metric = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "response_time": response_time,
        "confidence": confidence,
        "chunks_retrieved": chunks_count,
        "query_id": str(uuid.uuid4())
    }
    query_metrics.append(metric)
    
    # Mantener solo las últimas 1000 métricas
    if len(query_metrics) > 1000:
        query_metrics.pop(0)

# --- Endpoint de consulta mejorado ---
@app.post("/ask")
async def ask_advanced(request: QueryRequest):
    start_time = time.time()
    
    try:
        # Preprocesar query
        clean_query = preprocessor.preprocess(request.query)

        # Recuperar contexto relevante con filtros
        context = retriever.retrieve(
            clean_query, 
            top_k=request.top_k,
            filters=request.filters,
            namespace=request.namespace
        )

        # Construir el prompt
        prompt = prompt_builder.construct(clean_query, context)

        # Generar respuesta
        response = generator.generate(clean_query, context)

        # Calcular confianza mejorada
        confidence = calculate_confidence_score(context, response["answer"])
        response["confidence"] = confidence

        # Formatear respuesta con lógica inteligente
        query_lower = request.query.lower()
        explicit_list_keywords = [
            "lista", "listar", "enumera", "cuáles son", "qué tipos", 
            "menciona los", "incluye los", "cuáles fueron", "recursos",
            "qué recursos", "recursos didácticos", "mencionan"
        ]
        narrative_keywords = [
            "qué visión", "cómo", "por qué", "explica", "describe", 
            "cuál es", "de qué manera", "transmite", "presenta",
            "muestra", "refleja", "expresa", "significa"
        ]
        
        is_explicit_list = any(keyword in query_lower for keyword in explicit_list_keywords)
        is_narrative = any(keyword in query_lower for keyword in narrative_keywords)
        force_bullets = is_explicit_list and not is_narrative
        
        print(f"[DEBUG] Query: '{query_lower}'")
        print(f"[DEBUG] is_explicit_list: {is_explicit_list}")
        print(f"[DEBUG] is_narrative: {is_narrative}")
        print(f"[DEBUG] force_bullets: {force_bullets}")
        print(f"[DEBUG] Answer before format: '{response['answer'][:100]}...'")
        
        response["answer"] = formatter.format(
            response["answer"],
            force_bullets=force_bullets,
            is_unified_request=not is_narrative
        )
        
        print(f"[DEBUG] Answer after format: '{response['answer'][:100]}...'")
        print("="*50)

        # Registrar métricas
        response_time = time.time() - start_time
        log_query_metrics(request.query, response_time, confidence, len(context))

        return {
            **response,
            "response_time": round(response_time, 3),
            "query_processed": clean_query
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

# --- Endpoint de consulta simple (backward compatibility) ---
@app.get("/ask")
async def ask_simple(query: str):
    request = QueryRequest(query=query)
    return await ask_advanced(request)


# --- Subida de documentos ---
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not os.path.exists(DOCUMENTS_FOLDER):
        os.makedirs(DOCUMENTS_FOLDER)
    file_path = os.path.join(DOCUMENTS_FOLDER, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Procesar el documento subido
    doc_processor.process(file_path, {"source": file.filename})

    return {"message": f"Archivo '{file.filename}' subido y procesado correctamente."}

@app.post("/reindex/{filename}")
async def reindex_document(filename: str):
    """Reindexar un documento específico con métodos de extracción mejorados"""
    file_path = os.path.join(DOCUMENTS_FOLDER, filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Archivo '{filename}' no encontrado")
    
    try:
        # Limpiar índices existentes para este documento (si fuera necesario)
        # Por ahora, simplemente reprocesar y agregar
        print(f"🔄 Reindexando documento: {filename}")
        doc_processor.process(file_path, {"source": filename})
        
        return {
            "message": f"Documento '{filename}' reindexado exitosamente",
            "file_path": file_path
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reindexando documento: {str(e)}")

@app.get("/documents")
async def list_documents():
    """Listar documentos disponibles en la carpeta"""
    if not os.path.exists(DOCUMENTS_FOLDER):
        return {"documents": [], "message": "Carpeta de documentos no existe"}
    
    docs = [
        f for f in os.listdir(DOCUMENTS_FOLDER) 
        if f.lower().endswith((".pdf", ".docx", ".txt"))
    ]
    
    return {
        "documents": docs,
        "total": len(docs),
        "folder": DOCUMENTS_FOLDER
    }


# --- Chat Sessions ---
@app.post("/chat/new")
async def create_chat_session():
    """Crear nueva sesión de chat"""
    session_id = str(uuid.uuid4())
    session = ChatSession(
        session_id=session_id,
        created_at=datetime.now()
    )
    chat_sessions[session_id] = session
    return {"session_id": session_id}

@app.post("/chat/{session_id}/message")
async def send_chat_message(session_id: str, request: QueryRequest):
    """Enviar mensaje en una sesión de chat"""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    session = chat_sessions[session_id]
    
    # Agregar mensaje del usuario
    user_message = ChatMessage(
        role="user",
        content=request.query,
        timestamp=datetime.now()
    )
    session.messages.append(user_message)
    
    # Construir contexto con historial
    context_history = ""
    if len(session.messages) > 1:
        recent_messages = session.messages[-6:]  # Últimos 3 intercambios
        context_history = "\n".join([
            f"{msg.role}: {msg.content}" for msg in recent_messages[:-1]
        ])
    
    # Procesar consulta con contexto de historial
    response = await ask_advanced(request)
    
    # Agregar respuesta del asistente
    assistant_message = ChatMessage(
        role="assistant",
        content=response["answer"],
        timestamp=datetime.now()
    )
    session.messages.append(assistant_message)
    
    return {
        **response,
        "session_id": session_id,
        "message_count": len(session.messages)
    }

@app.get("/chat/{session_id}/history")
async def get_chat_history(session_id: str):
    """Obtener historial de chat"""
    if session_id not in chat_sessions:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    return chat_sessions[session_id]

# --- Streaming Responses ---
@app.post("/ask/stream")
async def ask_stream(request: QueryRequest):
    """Endpoint para respuestas streaming"""
    async def generate_response():
        start_time = time.time()
        qid = str(uuid.uuid4())
        
        # Preprocesar query
        clean_query = preprocessor.preprocess(request.query)
        yield f"data: {json.dumps({'type': 'status', 'message': 'Procesando consulta...'})}\n\n"
        
        # Recuperar contexto
        context = retriever.retrieve(
            clean_query,
            top_k=request.top_k,
            filters=request.filters,
            namespace=request.namespace
        )
        yield f"data: {json.dumps({'type': 'status', 'message': f'Encontrados {len(context)} fragmentos relevantes'})}\n\n"
        
        # Generar respuesta
        response = generator.generate(clean_query, context)
        
        # Formatear respuesta
        query_lower = request.query.lower()
        explicit_list_keywords = ["lista", "listar", "enumera", "cuáles son", "qué tipos"]
        narrative_keywords = ["qué visión", "cómo", "por qué", "explica", "describe"]
        
        is_explicit_list = any(keyword in query_lower for keyword in explicit_list_keywords)
        is_narrative = any(keyword in query_lower for keyword in narrative_keywords)
        force_bullets = is_explicit_list and not is_narrative
        
        formatted_answer = formatter.format(
            response["answer"],
            force_bullets=force_bullets,
            is_unified_request=not is_narrative
        )
        
        # Simular streaming de la respuesta
        # Preservar espacios y saltos de línea durante el streaming
        import re
        tokens = re.split(r'(\s+)', formatted_answer)
        total = max(1, len([t for t in tokens if t is not None]))
        for i, token in enumerate(tokens):
            if token is None:
                continue
            chunk = {
                'type': 'content',
                'content': token,
                'progress': (i + 1) / total
            }
            yield f"data: {json.dumps(chunk)}\n\n"
            time.sleep(0.02)  # Simular delay más fluido y conservar nuevos renglones
        
        # Enviar fuentes y métricas finales
        final_data = {
            'type': 'complete',
            'sources': response.get('sources', []),
            'confidence': calculate_confidence_score(context, response["answer"]),
            'response_time': round(time.time() - start_time, 3),
            'query_id': qid
        }
        yield f"data: {json.dumps(final_data)}\n\n"
    
    return StreamingResponse(generate_response(), media_type="text/event-stream")

# --- Monitoring y Analytics ---
@app.get("/metrics")
async def get_metrics():
    """Obtener métricas del sistema"""
    if not query_metrics:
        return {"message": "No hay métricas disponibles"}
    
    # Calcular estadísticas
    total_queries = len(query_metrics)
    avg_response_time = sum(m["response_time"] for m in query_metrics) / total_queries
    confidence_distribution = {}
    
    for metric in query_metrics:
        conf = metric["confidence"]
        confidence_distribution[conf] = confidence_distribution.get(conf, 0) + 1
    
    recent_queries = query_metrics[-10:] if len(query_metrics) >= 10 else query_metrics
    
    return {
        "total_queries": total_queries,
        "average_response_time": round(avg_response_time, 3),
        "confidence_distribution": confidence_distribution,
        "recent_queries": recent_queries,
        "active_chat_sessions": len(chat_sessions)
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "documents_folder_exists": os.path.exists(DOCUMENTS_FOLDER),
        "indexed_documents": len([f for f in os.listdir(DOCUMENTS_FOLDER) 
                                 if f.lower().endswith((".pdf", ".docx", ".txt"))]) if os.path.exists(DOCUMENTS_FOLDER) else 0
    }

# --- Ejecutar servidor ---
if __name__ == "__main__":
    import uvicorn
    print(" Iniciando PocketFlow Assistant API...")
    print(" Servidor disponible en: http://127.0.0.1:8000")
    print(" Documentación en: http://127.0.0.1:8000/docs")
    uvicorn.run(app, host="127.0.0.1", port=8000)
