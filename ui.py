import os
import requests
import streamlit as st
import re
import json
import time

# --- Configuración inicial ---
st.set_page_config(page_title="PocketFlow Assistant", page_icon="💬", layout="wide")
st.title("💬 PocketFlow Assistant")
st.markdown("Sistema RAG avanzado con soporte para filtros, chat sessions y streaming")

# Estado de sesión para historial y configuración
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "use_advanced_mode" not in st.session_state:
    st.session_state.use_advanced_mode = False

# --- Cargar documentos automáticamente ---
st.sidebar.header("📂 Documentos cargados")
documents_folder = "documents"

# --- Subida de archivos por el usuario ---
uploaded_file = st.sidebar.file_uploader("Sube un documento (.pdf, .docx, .txt)", type=["pdf", "docx", "txt"])
if uploaded_file is not None:
    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
    resp = requests.post("http://127.0.0.1:8000/upload", files=files)
    if resp.status_code == 200:
        st.sidebar.success(f"Archivo '{uploaded_file.name}' subido y procesado correctamente.")
    else:
        st.sidebar.error(f"Error al subir el archivo: {resp.text}")

if os.path.exists(documents_folder):
    docs = [f for f in os.listdir(documents_folder) if f.lower().endswith((".pdf", ".docx", ".txt"))]
    if docs:
        for d in docs:
            st.sidebar.write(f"- {d}")
    else:
        st.sidebar.write("⚠️ No hay documentos en la carpeta.")
else:
    st.sidebar.write("⚠️ No existe la carpeta 'documents'.")

st.sidebar.info("Puedes subir archivos desde aquí")

# --- Configuración avanzada ---
st.sidebar.header("⚙️ Configuración")
use_advanced = st.sidebar.checkbox("Modo Avanzado", value=st.session_state.use_advanced_mode)
st.session_state.use_advanced_mode = use_advanced

if use_advanced:
    st.sidebar.subheader("🔍 Filtros de Búsqueda")
    top_k = st.sidebar.slider("Número de chunks", 1, 10, 5)
    
    # Filtros de metadata
    filter_source = st.sidebar.text_input("Filtrar por archivo (opcional)")
    filter_section = st.sidebar.text_input("Filtrar por sección (opcional)")
    namespace = st.sidebar.text_input("Namespace (opcional)")
    
    use_streaming = st.sidebar.checkbox("Respuestas streaming", value=False)
    use_chat_session = st.sidebar.checkbox("Usar sesión de chat", value=False)
    
    # Gestión de sesiones de chat
    if use_chat_session:
        if st.sidebar.button("Nueva sesión de chat"):
            resp = requests.post("http://127.0.0.1:8000/chat/new")
            if resp.status_code == 200:
                st.session_state.session_id = resp.json()["session_id"]
                st.sidebar.success(f"Nueva sesión: {st.session_state.session_id[:8]}...")
        
        if st.session_state.session_id:
            st.sidebar.info(f"Sesión activa: {st.session_state.session_id[:8]}...")
else:
    top_k = 5
    filter_source = None
    filter_section = None
    namespace = None
    use_streaming = False
    use_chat_session = False

# --- Métricas del sistema ---
if st.sidebar.button("📊 Ver métricas"):
    try:
        resp = requests.get("http://127.0.0.1:8000/metrics")
        if resp.status_code == 200:
            metrics = resp.json()
            st.sidebar.json(metrics)
    except:
        st.sidebar.error("No se pudieron cargar las métricas")

# --- Gestión de documentos ---
st.sidebar.header("📚 Gestión de Documentos")

if st.sidebar.button("📋 Listar documentos"):
    try:
        resp = requests.get("http://127.0.0.1:8000/documents")
        if resp.status_code == 200:
            docs_info = resp.json()
            st.sidebar.write(f"**Total documentos**: {docs_info['total']}")
            for doc in docs_info['documents']:
                st.sidebar.write(f"- {doc}")
    except:
        st.sidebar.error("No se pudieron cargar los documentos")

# Reindexar documento específico
reindex_file = st.sidebar.selectbox(
    "Reindexar documento:",
    ["Seleccionar..."] + [f for f in os.listdir(documents_folder) if f.lower().endswith((".pdf", ".docx", ".txt"))] if os.path.exists(documents_folder) else ["No hay documentos"]
)

if st.sidebar.button("🔄 Reindexar") and reindex_file != "Seleccionar...":
    try:
        resp = requests.post(f"http://127.0.0.1:8000/reindex/{reindex_file}")
        if resp.status_code == 200:
            st.sidebar.success(f"Documento '{reindex_file}' reindexado exitosamente")
        else:
            st.sidebar.error(f"Error: {resp.text}")
    except Exception as e:
        st.sidebar.error(f"Error al reindexar: {str(e)}")

# --- Entrada del usuario ---
query = st.chat_input("Escribe tu pregunta...")

if query:
    # Construir filtros
    filters = {}
    if filter_source:
        filters["source"] = filter_source
    if filter_section:
        filters["section"] = filter_section
    
    # Preparar request
    request_data = {
        "query": query,
        "top_k": top_k,
        "filters": filters if filters else None,
        "namespace": namespace if namespace else None,
        "stream": use_streaming
    }
    
    # Llamada al backend
    if use_chat_session and st.session_state.session_id:
        # Usar sesión de chat
        resp = requests.post(
            f"http://127.0.0.1:8000/chat/{st.session_state.session_id}/message",
            json=request_data
        )
    elif use_streaming:
        # Usar streaming
        resp = requests.post("http://127.0.0.1:8000/ask/stream", json=request_data)
    else:
        # Usar endpoint normal
        resp = requests.post("http://127.0.0.1:8000/ask", json=request_data)
    
    if resp.status_code == 200:
        data = resp.json()
        
        # Guardamos en historial
        st.session_state.messages.append({"role": "user", "content": query})
        st.session_state.messages.append({
            "role": "assistant",
            "content": data["answer"],
            "sources": data.get("sources", []),
            "confidence": data.get("confidence"),
            "query_id": data.get("query_id"),
            "response_time": data.get("response_time"),
            "session_id": data.get("session_id")
        })
    else:
        st.error(f"Error: {resp.text}")

# --- Renderizar historial ---
for msg in st.session_state.messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.write(msg["content"])
    else:
        with st.chat_message("assistant"):
            # Mapear bullets '• ' a '- ' y renderizar como Markdown para listas reales
            content = msg["content"]
            content = re.sub(r"(?m)^\s*•\s+", "- ", content)
            st.markdown(content)

            # --- Mostrar información de la respuesta ---
            col1, col2, col3 = st.columns(3)
            
            with col1:
                conf = msg.get("confidence", "N/A")
                color_map = {
                    "high": "🟢 Alta",
                    "medium": "🟡 Media", 
                    "low": "🔴 Baja"
                }
                st.caption(f"Confianza: {color_map.get(conf, conf)}")
            
            with col2:
                response_time = msg.get("response_time")
                if response_time:
                    st.caption(f"⏱️ Tiempo: {response_time:.2f}s")
            
            with col3:
                query_id = msg.get("query_id", "N/A")
                st.caption(f"ID: {query_id}")
            
            # Mostrar session_id si existe
            if msg.get("session_id"):
                st.caption(f"🔗 Sesión: {msg['session_id'][:8]}...")

            # --- Mostrar fuentes ---
            if msg.get("sources"):
                with st.expander("📖 Fuentes"):
                    for src in msg["sources"]:
                        ref = f"Archivo: {src.get('source', 'desconocido')}"
                        if src.get("page"):
                            ref += f" | Página: {src['page']}"
                        if src.get("chunk_index") is not None:
                            ref += f" | Fragmento #{src['chunk_index']}"
                        st.write(ref)
                        with st.expander("🔎 Ver snippet"):
                            st.write(src.get("text", ""))
