from utils.llm_client import call_llm 
import re, uuid
from collections import defaultdict

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None


class ResponseGenerator:
    def __init__(self):
        self.page_offsets = {}

    # ---------------- Detección de referencias legales ----------------
    def _is_legal_reference_query(self, query: str) -> bool:
        q = query.lower()
        legal_terms = [
            "constitución", "constitucion", "ley", "decreto", "código", "codigo",
            "estatuto", "norma", "reglamento", "marco jurídico", "artículo",
            "tratado", "acuerdo", "compromiso", "ratificado", "internacional"
        ]
        return any(term in q for term in legal_terms)

    # ---------------- Detección de queries de lista ----------------
    def _is_list_query(self, query: str) -> bool:
        q = query.lower()
        keywords = [
            "tipograf", "fuente", "color", "colores",
            "artículo", "articulos", "leyes", "documentos",
            "servicios", "elementos", "componentes", "puntos",
            "enumer", "lista", "datos", "estadísticas", "estadisticos",
            "funciones", "responsabilidades", "atribuciones", "papel", "rol",
            # Consultas tipo lista sobre compromisos/obligaciones
            "compromisos", "obligaciones", "tratados", "convenios", "acuerdos"
        ]
        return any(kw in q for kw in keywords)

    # ---------------- Calcular offset de páginas ----------------
    def _calculate_page_offset(self, filepath: str) -> int:
        if not filepath or not filepath.lower().endswith(".pdf"):
            return 0
        if filepath in self.page_offsets:
            return self.page_offsets[filepath]
        if fitz is None:
            self.page_offsets[filepath] = 0
            return 0

        try:
            doc = fitz.open(filepath)
            # Solo buscar en las primeras 10 páginas para evitar falsos positivos
            max_scan = min(10, doc.page_count)
            
            for i in range(max_scan):
                page = doc.load_page(i)
                text = page.get_text()
                
                if text:
                    # Buscar solo patrones claros de numeración de página
                    page_patterns = [
                        r'página\s+(\d+)',
                        r'page\s+(\d+)',
                        r'^\s*(\d+)\s*$'  # número solo al inicio de línea
                    ]
                    
                    for pattern in page_patterns:
                        matches = re.findall(pattern, text.lower())
                        if matches:
                            try:
                                page_num = int(matches[0])
                                # Solo aceptar números razonables (1-100)
                                if 1 <= page_num <= 100:
                                    off = page_num - (i + 1)
                                    self.page_offsets[filepath] = off
                                    return off
                            except ValueError:
                                continue
        except Exception:
            pass

        # Si no encuentra numeración clara, asumir que empieza en 1
        self.page_offsets[filepath] = 0
        return 0

    # ---------------- Filtrado de índices ----------------
    def _is_index_content(self, text: str) -> bool:
        text = text.strip()
        
        # Patrones típicos de índices/tablas de contenido
        index_patterns = [
            r"\.{3,}\s*\d+\s*$",  # "...........124"
            r"^\d+\s+[A-ZÁÉÍÓÚÑ\s]+\s*\.{3,}\s*\d+",  # "101 NOTICIAS...........124"
            r"^\d+\s+[A-ZÁÉÍÓÚÑ\s]+\s*\.{2,}",  # "101 NOTICIAS........"
            r"^\d+\.\s*[A-ZÁÉÍÓÚÑ\s]+\s*\.{2,}",  # "101. NOTICIAS........"
            r"^\d+\s+[A-ZÁÉÍÓÚÑ\s]+$",  # Solo números y títulos en mayúsculas
            r"\d+\s+[A-ZÁÉÍÓÚÑ\s]+\s*\.{2,}\s*\d+",  # Patrón en cualquier parte del texto
            r"[A-ZÁÉÍÓÚÑ\s]+\s*\.{3,}\s*\d+",  # Títulos con puntos y números
        ]
        
        for pattern in index_patterns:
            if re.search(pattern, text, re.MULTILINE):
                return True
        
        # Contenido muy estructurado como índice
        lines = text.split('\n')
        if len(lines) >= 2:
            index_like_lines = 0
            for line in lines:
                line = line.strip()
                if (re.match(r'^\d+\s+[A-ZÁÉÍÓÚÑ\s]+', line) or 
                    re.match(r'^\d+\.\s+[A-ZÁÉÍÓÚÑ\s]+', line) or
                    re.search(r'\.{3,}\s*\d+\s*$', line) or
                    re.search(r'\d+\s+[A-ZÁÉÍÓÚÑ\s]+\s*\.{2,}\s*\d+', line)):
                    index_like_lines += 1
            
            # Si más del 50% de las líneas parecen de índice
            if index_like_lines / len(lines) > 0.5:
                return True
        
        # Detectar si el texto contiene múltiples patrones de índice
        index_pattern_count = 0
        for pattern in index_patterns:
            matches = re.findall(pattern, text, re.MULTILINE)
            index_pattern_count += len(matches)
        
        # Si hay más de 2 patrones de índice en el texto, probablemente es un índice
        if index_pattern_count >= 2:
            return True
        
        # texto muy ruidoso: poca proporción alfabética
        alpha = len(re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]", text))
        if len(text) >= 30 and alpha / len(text) < 0.35:
            return True
            
        return False

    # ---------------- Detectar contenido irrelevante ----------------
    def _is_irrelevant_content(self, text: str) -> bool:
        text = text.strip()
        
        # Patrones de contenido irrelevante
        irrelevant_patterns = [
            r"^[A-ZÁÉÍÓÚÑ\s]+$",  # Solo mayúsculas (títulos/encabezados)
            r"^\d+\s*$",  # Solo números
            r"^[^\w\s]*$",  # Solo símbolos/puntuación
            r"^(ISSN|ISBN|DOI|URL|http)",  # Metadatos técnicos
            r"^(Editorial|Edita|Publicado|Año|Número|Volumen)",  # Info editorial
            r"^(Página|Page)\s*\d+",  # Numeración de páginas
            r"^[A-ZÁÉÍÓÚÑ\s]{3,}\s*\.{3,}",  # Títulos con puntos
        ]
        
        for pattern in irrelevant_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        # Contenido muy corto o muy repetitivo
        if len(text) < 20:
            return True
            
        # Muchos símbolos repetidos
        symbol_count = len(re.findall(r'[^\w\s]', text))
        if len(text) > 0 and symbol_count / len(text) > 0.4:
            return True
            
        return False

    # ---------------- Limpiar contenido de índices ----------------
    def _clean_index_content(self, text: str) -> str:
        """Extrae solo el contenido relevante de líneas de índice"""
        # Primero limpiar todo el texto de patrones de índice
        cleaned_text = text
        
        # Remover patrones como "101 NOTICIAS...........124" y dejar solo "NOTICIAS"
        cleaned_text = re.sub(r'\d+\s+([A-ZÁÉÍÓÚÑ\s]+)\s*\.{2,}\s*\d+', r'\1', cleaned_text)
        
        # Remover patrones como "124 COLOFÓN............128" y dejar solo "COLOFÓN"
        cleaned_text = re.sub(r'\d+\s+([A-ZÁÉÍÓÚÑ\s]+)\s*\.{2,}', r'\1', cleaned_text)
        
        # Remover números al inicio de líneas: "101 NOTICIAS" -> "NOTICIAS"
        cleaned_text = re.sub(r'^\d+\s+([A-ZÁÉÍÓÚÑ\s]+)', r'\1', cleaned_text, flags=re.MULTILINE)
        
        # Remover líneas que son solo números o símbolos
        lines = cleaned_text.split('\n')
        clean_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Solo mantener líneas con contenido sustantivo (más de 2 palabras)
            if len(line.split()) >= 2 and not re.match(r'^[\d\s\.\-]+$', line):
                clean_lines.append(line)
        
        return " ".join(clean_lines).strip()

    # ---------------- Filtrar y limpiar chunks ----------------
    def _clean_and_filter_chunks(self, context_chunks, threshold: float, query: str = ""):
        if not context_chunks:
            return []

        filtered_chunks = []
        seen_keys = set()

        sorted_chunks = sorted(
            context_chunks, key=lambda c: c.get("relevance_score", 0), reverse=True
        )

        max_sources = 3
        if self._is_list_query(query):
            max_sources = 8

        for chunk in sorted_chunks:
            score = chunk.get("relevance_score", 0)
            text = chunk.get("text", "").strip()

            if self._is_legal_reference_query(query):
                filtered_chunks.append(chunk)
                continue

            if score < threshold:
                continue
            if not text:
                continue
            
            # Solo filtrar índices si el score es muy bajo (ser menos estricto)
            if score < 0.25 and self._is_index_content(text):
                continue

            # Solo filtrar contenido irrelevante si el score es muy bajo
            if score < 0.2 and self._is_irrelevant_content(text):
                continue

            key = f"{chunk.get('source', '')}_{chunk.get('page', '')}"
            if key in seen_keys:
                continue

            seen_keys.add(key)
            filtered_chunks.append(chunk)

            if len(filtered_chunks) >= max_sources:
                break

        return filtered_chunks

    # ---------------- Detectar preguntas de documentos ----------------
    def _should_answer_with_docs(self, query: str) -> bool:
        q = query.lower()
        return "qué documento" in q or "cual documento" in q or "qué archivos" in q

    # ---------------- Generar respuesta ----------------
    def generate(self, query: str, context_chunks=None, threshold: float = 0.05):
        context_chunks = context_chunks or []
        
        # Debug: mostrar chunks recibidos
        print(f"\n[ResponseGenerator] Recibidos {len(context_chunks)} chunks:")
        for i, chunk in enumerate(context_chunks[:3]):
            score = chunk.get("relevance_score", 0)
            text_preview = chunk.get("text", "")[:100]
            print(f"  Chunk {i}: score={score:.3f}, text='{text_preview}...'")
        
        filtered_chunks = self._clean_and_filter_chunks(context_chunks, threshold, query)
        print(f"[ResponseGenerator] Después del filtrado: {len(filtered_chunks)} chunks")

        if not filtered_chunks and context_chunks:
            # Si no hay chunks filtrados, tomar los mejores sin importar el threshold
            print("[ResponseGenerator] No hay chunks filtrados, tomando los mejores disponibles")
            sorted_chunks = sorted(context_chunks, key=lambda c: c.get("relevance_score", 0), reverse=True)
            filtered_chunks = sorted_chunks[:3]  # Tomar más chunks para más contexto

        if not filtered_chunks:
            print("[ResponseGenerator] No hay chunks disponibles, devolviendo respuesta vacía")
            return {
                "query_id": str(uuid.uuid4()),
                "answer": "No se encontró información suficiente",
                "sources": [],
                "confidence": "low",
            }

        # ✅ Caso especial: Query legal solo cuando piden documentos explícitamente
        if (
            self._is_legal_reference_query(query)
            and self._should_answer_with_docs(query)
            and filtered_chunks
        ):
            docs = {c.get("source", "desconocido") for c in filtered_chunks}
            answer = (
                f"Se encontró que los siguientes documentos mencionan información relevante: "
                + ", ".join(docs)
                + "."
            )
            sources = [self._format_source(c) for c in filtered_chunks]
            avg_score = sum(c.get("relevance_score", 0) for c in filtered_chunks) / len(filtered_chunks)
            confidence = "medium" if avg_score < 0.4 else "high"

            return {
                "query_id": str(uuid.uuid4()),
                "answer": answer,
                "sources": sources,
                "confidence": confidence,
            }

        # ✅ Caso: "qué documento..."
        if self._should_answer_with_docs(query):
            score_by_doc = defaultdict(float)
            for c in filtered_chunks:
                src = c.get("source", "").strip()
                if src:
                    score_by_doc[src] += float(c.get("relevance_score", 0.0))

            if score_by_doc:
                ranked_docs = sorted(
                    score_by_doc.items(), key=lambda x: x[1], reverse=True
                )
                top_docs = [d for d, _ in ranked_docs[:1]]
                if len(top_docs) == 1:
                    answer = f"El documento es: {top_docs[0]}."
                else:
                    answer = "Los documentos son: " + ", ".join(top_docs) + "."
                sources = [
                    self._format_source(c)
                    for c in filtered_chunks
                    if c.get("source") in top_docs
                ]
                avg_score = sum(c.get("relevance_score", 0) for c in filtered_chunks) / len(filtered_chunks)
                confidence = "high" if avg_score >= 0.7 else ("medium" if avg_score >= 0.4 else "low")
                return {
                    "query_id": str(uuid.uuid4()),
                    "answer": answer,
                    "sources": sources,
                    "confidence": confidence,
                }

        # ---- Flujo normal con LLM ----
        context_texts = [c.get("text", "") for c in filtered_chunks]
        
        prompt = f"""
Responde a la siguiente pregunta basándote ÚNICAMENTE en el contexto proporcionado.

Pregunta:
{query}

Contexto disponible:
{' '.join(context_texts)}

Instrucciones CRÍTICAS:
- DEBES usar TODA la información disponible en el contexto, incluso si parece parcial.
- Si el contexto menciona nombres, fechas, lugares o cualquier detalle relacionado con la pregunta, ÚSALO.
- Busca conexiones directas e indirectas entre la pregunta y el contexto.
- Responde con la información que SÍ tienes, no con lo que falta.
- NUNCA respondas "No se encontró información suficiente" si hay CUALQUIER información relacionada en el contexto.
- Si solo tienes información parcial, preséntala claramente indicando que es lo que se encontró.

Respuesta:"""

        answer = call_llm(prompt).strip()
        answer = re.sub(
            r"^(respuesta.*?:|la respuesta.*?:|respuesta con citas.*?:)\s*",
            "",
            answer,
            flags=re.IGNORECASE,
        ).strip()

        # NO aplicar postprocesado automático de listas - solo mantener el texto como viene del LLM
        # El formateo se manejará únicamente en el ResponseFormatter con control explícito

        # Selección de fuentes relevantes según solapamiento con la respuesta
        def _select_relevant_sources(ans: str, chunks):
            def tokenize(s: str):
                words = re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñÑ]{3,}", s.lower())
                stop = {"los","las","una","uno","unos","unas","del","con","por","para","como","que","segun","entre","sobre","este","esta","estos","estas","de","en","al","el","la","y","o"}
                return {w for w in words if w not in stop}

            ans_tokens = tokenize(ans)
            scored = []
            for c in chunks:
                text = c.get("text", "")
                chunk_tokens = tokenize(text)
                if not chunk_tokens or not ans_tokens:
                    score = 0.0
                else:
                    inter = len(ans_tokens & chunk_tokens)
                    union = len(ans_tokens | chunk_tokens)
                    score = inter / max(1, union)
                scored.append((score, c))

            # ordenar por score y score de relevancia base
            scored.sort(key=lambda t: (t[0], t[1].get("relevance_score", 0.0)), reverse=True)

            # Mantener top 3 o los que superen umbral mínimo
            selected = []
            for score, c in scored[:5]:
                if score >= 0.02 or len(selected) < 3:
                    selected.append(c)
            return [self._format_source(c) for c in selected]

        sources = _select_relevant_sources(answer, filtered_chunks)
        avg_score = sum(c.get("relevance_score", 0.0) for c in filtered_chunks) / len(filtered_chunks)
        confidence = "high" if avg_score >= 0.7 else ("medium" if avg_score >= 0.4 else "low")

        return {
            "query_id": str(uuid.uuid4()),
            "answer": answer,
            "sources": sources,
            "confidence": confidence,
        }

    # ---------------- Limpieza de texto ----------------
    def _clean_text(self, text: str) -> str:
        if not text:
            return ""
            
        # Eliminar caracteres especiales no deseados
        text = re.sub(r'[\x00-\x1F\x7F-\x9F]', ' ', text)  # Caracteres de control
        text = re.sub(r'\s+', ' ', text)  # Espacios múltiples a un solo espacio
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)  # Espacios antes de puntuación
        text = re.sub(r'([.,;:!?])([^\s\d])', r'\1 \2', text)  # Espacio después de puntuación
        
        # Limitar longitud máxima
        if len(text) > 300:
            # Intentar cortar en un punto o coma cercano
            last_punct = max(
                text.rfind('. ', 0, 300),
                text.rfind(', ', 0, 300),
                text.rfind('; ', 0, 300),
                text.rfind(' ', 0, 300)
            )
            if last_punct > 150:  # Si encontramos un buen punto de corte
                text = text[:last_punct].strip() + '...'
            else:
                text = text[:297].strip() + '...'
                
        return text.strip()
        
    # ---------------- Limpieza de snippets ----------------
    def _clean_snippet(self, text: str) -> str:
        if not text:
            return ""
            
        # Limpieza básica
        text = re.sub(r'[\x00-\x1F\x7F-\x9F]', ' ', text)  # Caracteres de control
        text = re.sub(r'\s+', ' ', text)  # Espacios múltiples a un solo espacio
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)  # Espacios antes de puntuación
        text = re.sub(r'([.,;:!?])([^\s\d])', r'\1 \2', text)  # Espacio después de puntuación
        
        # Corregir comillas y guiones
        text = text.replace('"', '"')
        text = text.replace('“', '"').replace('”', '"')
        text = text.replace('‘', "'").replace('’', "'")
        text = text.replace('–', '-').replace('—', '-')
        
        # Eliminar números pegados a letras (ej: "página3" -> "página 3")
        text = re.sub(r'(\d+)([a-zA-ZáéíóúÁÉÍÓÚñÑ])', r'\1 \2', text)
        text = re.sub(r'([a-zA-ZáéíóúÁÉÍÓÚñÑ])(\d+)', r'\1 \2', text)
        
        # Asegurar espacios después de signos de puntuación
        text = re.sub(r'([.,;:])([^\s\d])', r'\1 \2', text)
        
        # Eliminar espacios al inicio/fin
        text = text.strip()
        
        return text

    # ---------------- Normalizar metadatos ----------------
    def _format_source(self, chunk: dict) -> dict:
        source_display = chunk.get("source", "desconocido")
        source_path = chunk.get("source_path") or source_display
        page = chunk.get("page")
        score = round(chunk.get("relevance_score", 0), 2)

        real_page = page
        if isinstance(page, int) and str(source_path).lower().endswith(".pdf"):
            off = self._calculate_page_offset(source_path)
            real_page = max(1, page + off)

        # Obtener y limpiar el snippet
        raw_snippet = (chunk.get("text", "") or "").strip()
        
        # Limpiar el texto del snippet
        snippet = self._clean_snippet(raw_snippet)
        
        # Asegurar que el snippet tenga una longitud razonable
        max_length = 200
        if len(snippet) > max_length:
            # Intentar cortar en un punto o coma cercano
            last_punct = max(
                snippet.rfind('. ', 0, max_length + 10),
                snippet.rfind(', ', 0, max_length + 10),
                snippet.rfind('; ', 0, max_length + 10),
                snippet.rfind(' ', 0, max_length + 10)
            )
            
            if last_punct > max_length // 2:  # Si encontramos un buen punto de corte
                snippet = snippet[:last_punct].strip() + "..."
            else:
                # Si no encontramos un buen punto de corte, cortar en la palabra más cercana
                snippet = snippet[:max_length].rsplit(' ', 1)[0] + "..."
        
        # Limpiar espacios en blanco múltiples
        snippet = ' '.join(snippet.split())
        
        # Asegurar que empiece con mayúscula y termine con punto
        if snippet:
            snippet = snippet[0].upper() + snippet[1:]
            if snippet[-1] not in '.!?':
                snippet += '.'
        snippet = re.sub(r"(\d+)([A-Za-zÁÉÍÓÚáéíóúñÑ])", r"\1. \2", snippet)
        
        # Limpiar contenido de índices en snippets: extraer solo el título
        snippet = self._clean_index_content(snippet)

        return {
            "text": snippet if snippet else "Sin fragmento disponible",
            "source": source_display,
            "page": real_page,
            "section": chunk.get("section"),
            # Mostrar el índice del fragmento dentro de la página (más útil para localizarlo)
            "chunk_index": chunk.get("page_chunk_index"),
            "relevance_score": score,
        }
