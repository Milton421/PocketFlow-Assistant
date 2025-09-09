import os
from pocketflow import Flow, Node
from nodes.document_processor_node import DocumentProcessorNode
from nodes.retriever_node import Retriever
from nodes.prompt_constructor_node import PromptConstructor
from nodes.response_generator_node import ResponseGenerator
from nodes.query_preprocessor_node import QueryPreprocessor
from nodes.response_formatter_node import ResponseFormatter



# --- Nodos ---
def generar_respuesta(store):
    generator = ResponseGenerator()
    formatter = ResponseFormatter()

    query = store["query"]
    context = store["context"]
    
    # CAMBIO: Pasar query Y context a generate
    response = generator.generate(query, context)  # ← Aquí estaba el error

    # Formatear respuesta final
    query_lower = query.lower()
    
    # Palabras que indican solicitud explícita de lista
    explicit_list_keywords = [
        "lista", "listar", "enumera", "cuáles son", "qué tipos", 
        "menciona los", "incluye los", "cuáles fueron", "qué recursos",
        "recursos didácticos", "se mencionan"
    ]
    
    # Palabras que indican preguntas narrativas (NO deben ser listas)
    narrative_keywords = [
        "qué visión", "cómo", "por qué", "explica", "describe", 
        "cuál es", "de qué manera", "transmite", "presenta",
        "muestra", "refleja", "expresa", "significa"
    ]
    
    # Solo forzar bullets si hay solicitud explícita Y no es narrativa
    is_explicit_list = any(keyword in query_lower for keyword in explicit_list_keywords)
    is_narrative = any(keyword in query_lower for keyword in narrative_keywords)
    
    force_bullets = is_explicit_list and not is_narrative
    
    print(f"[DEBUG] Query: '{query_lower}'")
    print(f"[DEBUG] is_explicit_list: {is_explicit_list}")
    print(f"[DEBUG] is_narrative: {is_narrative}")
    print(f"[DEBUG] force_bullets: {force_bullets}")
    
    response["answer"] = formatter.format(response["answer"], force_bullets=force_bullets)
    store["response"] = response
    return store    

def procesar_documento(store):
    doc_node = DocumentProcessorNode()
    file_path = store["file_path"]
    metadata = {"source": os.path.basename(file_path)}
    chunks = doc_node.process(file_path, metadata)
    store.setdefault("all_chunks", []).extend(chunks)
    return store

def preprocesar_query(store):
    preprocessor = QueryPreprocessor()
    raw_query = store["query"]
    clean_query = preprocessor.preprocess(raw_query)
    store["query"] = clean_query
    return store

def recuperar_contexto(store):
    retriever = Retriever()
    # ✅ Traer más chunks para tener mejor contexto
    results = retriever.retrieve(store["query"], top_k=3)
    store["context"] = results
    return store

def construir_prompt(store):
    constructor = PromptConstructor()
    query = store["query"]
    context = store["context"]
    prompt = constructor.construct(query, context)
    store["prompt"] = prompt
    return store

def generar_respuesta(store):
    generator = ResponseGenerator()
    prompt = store["prompt"]
    context = store["context"]
    response = generator.generate(prompt, context)
    store["response"] = response
    return store


if __name__ == "__main__":
    # --- Flujo de documentos ---
    flujo_docs = Flow(Node("procesar_documento", procesar_documento))

    documents_folder = "documents"
    entrada = {"all_chunks": []}

    if os.path.exists(documents_folder):
        for file in os.listdir(documents_folder):
            path = os.path.join(documents_folder, file)
            if file.lower().endswith((".pdf", ".docx", ".txt")):
                print(f"📄 Procesando: {file}")
                flujo_docs.run({"file_path": path, "all_chunks": entrada["all_chunks"]})
    else:
        print("⚠️ No se encontró la carpeta 'documents'. Crea la carpeta y coloca tus archivos allí.")
        exit()

    # --- Flujo de consulta ---
    flujo_consulta = Flow(
        Node("preprocesar_query", preprocesar_query)
        >> Node("recuperar_contexto", recuperar_contexto)
        >> Node("construir_prompt", construir_prompt)
        >> Node("generar_respuesta", generar_respuesta)
    )

    # Preguntas interactivas
    while True:
        query = input("\n❓ Ingresa tu pregunta (o escribe 'salir' para terminar): ")
        if query.lower() == "salir":
            print("👋 Saliendo del asistente.")
            break

        salida = flujo_consulta.run({"query": query})

        print("\n--- RESPUESTA FINAL ---")
        print(salida["response"]["answer"])
        print("\n--- FUENTES ---")
        for s in salida["response"]["sources"]:
            print(f"- {s['source']} (score: {s['relevance_score']:.2f})")
