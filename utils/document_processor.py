from PyPDF2 import PdfReader
from docx import Document
import os
import re
from utils.embeddings import generate_embeddings
from utils.faiss_client import get_client

# Librerías adicionales para extracción robusta de PDFs
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

try:
    import pdfplumber
    HAS_PDFPLUMBER = True
except ImportError:
    HAS_PDFPLUMBER = False


class DocumentProcessor:
    def __init__(self):
        self.faiss_client = get_client()

    def process(self, file_path: str, metadata: dict):
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".pdf":
            return self._process_pdf(file_path, metadata)
        elif ext == ".docx":
            return self._process_docx(file_path, metadata)
        elif ext == ".txt":
            return self._process_txt(file_path, metadata)
        else:
            raise ValueError("Formato no soportado")

    # ---------------- PDF ----------------
    def _process_pdf(self, file_path: str, metadata: dict):
        all_chunks, all_metadatas = [], []
        
        # Intentar múltiples métodos de extracción
        page_texts = self._extract_pdf_text_robust(file_path)
        
        for page_num, page_text in enumerate(page_texts, 1):
            if not page_text.strip():
                continue

            # Dividir cada página en chunks
            page_chunks = self._chunk_text(page_text, chunk_size=150, overlap=30)

            for chunk_idx, chunk in enumerate(page_chunks):
                chunk_metadata = {
                    "text": chunk,
                    "page": page_num,
                    "chunk_index": len(all_chunks),
                    "page_chunk_index": chunk_idx,
                    **metadata
                }

                # Asegurar metadatos mínimos
                if "source" not in chunk_metadata or not chunk_metadata.get("source"):
                    chunk_metadata["source"] = os.path.basename(file_path)
                if "source_path" not in chunk_metadata or not chunk_metadata.get("source_path"):
                    chunk_metadata["source_path"] = file_path

                # Intentar detectar título/sección
                title = self._detect_story_title(chunk)
                if title and "section" not in chunk_metadata:
                    chunk_metadata["section"] = title

                all_chunks.append(chunk)
                all_metadatas.append(chunk_metadata)

        # Embeddings
        if all_chunks:
            embeddings = generate_embeddings(all_chunks)
            self.faiss_client.add_embeddings(embeddings, all_metadatas)

        return all_metadatas

    # ---------------- DOCX ----------------
    def _process_docx(self, file_path: str, metadata: dict):
        doc = Document(file_path)
        text = "\n".join([para.text for para in doc.paragraphs if para.text.strip()])

        chunks = self._chunk_text(text, chunk_size=150, overlap=30)
        embeddings = generate_embeddings(chunks)

        metadatas = []
        for idx, chunk in enumerate(chunks):
            meta = {
                "text": chunk,
                "page": None,
                "chunk_index": idx,
                "page_chunk_index": idx,
                **metadata
            }

            if "source" not in meta or not meta.get("source"):
                meta["source"] = os.path.basename(file_path)
            if "source_path" not in meta or not meta.get("source_path"):
                meta["source_path"] = file_path

            title = self._detect_story_title(chunk)
            if title and "section" not in meta:
                meta["section"] = title

            metadatas.append(meta)

        if chunks:
            self.faiss_client.add_embeddings(embeddings, metadatas)
        return metadatas

    # ---------------- TXT ----------------
    def _process_txt(self, file_path: str, metadata: dict):
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = self._chunk_text(text, chunk_size=150, overlap=30)
        embeddings = generate_embeddings(chunks)

        metadatas = []
        for idx, chunk in enumerate(chunks):
            meta = {
                "text": chunk,
                "page": None,
                "chunk_index": idx,
                "page_chunk_index": idx,
                **metadata
            }

            if "source" not in meta or not meta.get("source"):
                meta["source"] = os.path.basename(file_path)
            if "source_path" not in meta or not meta.get("source_path"):
                meta["source_path"] = file_path

            title = self._detect_story_title(chunk)
            if title and "section" not in meta:
                meta["section"] = title

            metadatas.append(meta)

        if chunks:
            self.faiss_client.add_embeddings(embeddings, metadatas)
        return metadatas

    # ---------------- Detectar títulos ----------------
    def _detect_story_title(self, text: str) -> str:
        """Detecta posibles títulos al inicio de un texto"""
        lines = text.strip().split('\n')

        for i, line in enumerate(lines[:5]):  # primeras 5 líneas
            line = line.strip()
            if not line:
                continue

            if (5 <= len(line) <= 80 and
                not line.endswith('.') and
                not line.endswith(',') and
                not re.search(r'\d{2,}', line) and
                len([c for c in line if c.isalpha()]) > len(line) * 0.5):

                metadata_patterns = [
                    r'esc\.\s*sec\.',
                    r'página\s*\d+',
                    r'capítulo\s*\d+',
                    r'\d{4}',  # años
                    r'autor:|fuente:|fecha:'
                ]

                is_metadata = any(re.search(pattern, line, re.IGNORECASE) for pattern in metadata_patterns)
                if not is_metadata:
                    return line

        return None

    # ---------------- Chunking ----------------
    def _chunk_text(self, text, chunk_size=150, overlap=30):
        """
        Divide el texto en fragmentos de ~150 palabras con un solapamiento de 30.
        Preserva mejor el contexto y evita cortar información importante.
        """
        # Limpiar texto extraído de PDF con problemas de espaciado
        text = self._clean_extracted_text(text)
        
        # Dividir por oraciones primero para preservar contexto
        sentences = re.split(r'[.!?]+\s+', text)
        if not sentences:
            return []
        
        chunks = []
        current_chunk = []
        current_word_count = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            sentence_words = sentence.split()
            sentence_word_count = len(sentence_words)
            
            # Si agregar esta oración excede el tamaño del chunk
            if current_word_count + sentence_word_count > chunk_size and current_chunk:
                # Crear chunk actual
                chunk_text = ' '.join(current_chunk).strip()
                if chunk_text:
                    chunks.append(chunk_text)
                
                # Comenzar nuevo chunk con overlap
                if overlap > 0 and len(current_chunk) > overlap:
                    # Mantener las últimas palabras como overlap
                    overlap_words = ' '.join(current_chunk).split()[-overlap:]
                    current_chunk = overlap_words + sentence_words
                    current_word_count = len(overlap_words) + sentence_word_count
                else:
                    current_chunk = sentence_words
                    current_word_count = sentence_word_count
            else:
                # Agregar oración al chunk actual
                current_chunk.extend(sentence_words)
                current_word_count += sentence_word_count
        
        # Agregar el último chunk si tiene contenido
        if current_chunk:
            chunk_text = ' '.join(current_chunk).strip()
            if chunk_text:
                chunks.append(chunk_text)
        
        # Fallback al método original si no se generaron chunks
        if not chunks:
            words = text.split()
            if not words:
                return []

            if len(words) <= chunk_size:
                return [" ".join(words)]

            start = 0
            while start < len(words):
                end = min(start + chunk_size, len(words))
                chunk_words = words[start:end]
                chunk_text = " ".join(chunk_words).strip()
                if chunk_text:
                    chunks.append(chunk_text)
                start += chunk_size - overlap

        return chunks
    
    # ---------------- Limpieza de texto extraído ----------------
    def _clean_extracted_text(self, text):
        """Limpia problemas comunes de extracción de PDFs"""
        if not text:
            return ""
        
        # Normalizar saltos de línea y caracteres especiales
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\u00a0", " ")  # Non-breaking space
        text = text.replace("\u2019", "'")  # Right single quotation mark
        text = text.replace("\u201c", '"').replace("\u201d", '"')  # Smart quotes
        text = text.replace("\u2013", "-").replace("\u2014", "-")  # En/em dashes
        
        # Corregir nombres propios comunes que se separan mal
        name_fixes = {
            r'Francisco\s+Rabal': 'Francisco Rabal',
            r'Agust[íi]n\s+Gonz[áa]lez': 'Agustín González',
            r'Max\s+Estrella': 'Max Estrella',
            r'Don\s+Latino': 'Don Latino',
            r'Valle\s+Incl[áa]n': 'Valle Inclán',
            r'Luces\s+de\s+Bohemia': 'Luces de Bohemia'
        }
        
        for pattern, replacement in name_fixes.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Corregir espacios innecesarios entre caracteres
        # Ejemplo: "ent ierr o" -> "entierro"
        text = re.sub(r'(\w)\s+(\w)(?=\w)', r'\1\2', text)
        
        # Corregir palabras cortadas por espacios (más agresivo)
        # Ejemplo: "Max Est rella" -> "Max Estrella"
        text = re.sub(r'(\w{2,})\s+(\w{1,3})\s+(\w{2,})', r'\1\2\3', text)
        
        # Corregir separaciones en palabras con acentos
        text = re.sub(r'([aeiouáéíóú])\s+([bcdfghjklmnpqrstvwxyz]{1,2})\s+([aeiouáéíóú])', r'\1\2\3', text, flags=re.IGNORECASE)
        
        # Limpiar múltiples espacios
        text = re.sub(r'\s+', ' ', text)
        
        # Corregir espacios antes de puntuación
        text = re.sub(r'\s+([.,;:!?])', r'\1', text)
        
        # Corregir espacios después de puntuación
        text = re.sub(r'([.,;:!?])\s*', r'\1 ', text)
        
        # Limpiar líneas que solo contienen caracteres especiales o números
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if line and not re.match(r'^[\d\s\-_=.]+$', line) and len(line) > 2:
                cleaned_lines.append(line)
        
        return ' '.join(cleaned_lines).strip()

    # ---------------- Extracción robusta de PDF ----------------
    def _extract_pdf_text_robust(self, file_path: str):
        """Extrae texto usando múltiples métodos como fallback"""
        page_texts = []
        
        # Método 1: PyMuPDF (más robusto)
        if HAS_PYMUPDF:
            try:
                print(f"[PDF] Intentando extracción con PyMuPDF: {os.path.basename(file_path)}")
                doc = fitz.open(file_path)
                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    # Intentar múltiples métodos de extracción de PyMuPDF
                    text = page.get_text()
                    
                    # Si el texto está vacío o muy corto, intentar con layout preservado
                    if len(text.strip()) < 50:
                        text = page.get_text("text", flags=fitz.TEXT_PRESERVE_LIGATURES | fitz.TEXT_PRESERVE_WHITESPACE)
                    
                    # Si aún está vacío, intentar extraer de bloques de texto
                    if len(text.strip()) < 50:
                        blocks = page.get_text("dict")["blocks"]
                        text_blocks = []
                        for block in blocks:
                            if "lines" in block:
                                for line in block["lines"]:
                                    for span in line["spans"]:
                                        if "text" in span:
                                            text_blocks.append(span["text"])
                        text = " ".join(text_blocks)
                    
                    page_texts.append(text)
                doc.close()
                
                # Verificar si se extrajo contenido útil
                total_chars = sum(len(text.strip()) for text in page_texts)
                if total_chars > 100:  # Si hay contenido sustancial
                    print(f"[PDF] PyMuPDF exitoso: {total_chars} caracteres extraídos")
                    return page_texts
                else:
                    print(f"[PDF] PyMuPDF extrajo poco contenido, probando siguiente método")
                    page_texts = []
            except Exception as e:
                print(f"[PDF] Error con PyMuPDF: {e}")
                page_texts = []
        
        # Método 2: pdfplumber (bueno para tablas)
        if HAS_PDFPLUMBER and not page_texts:
            try:
                print(f"[PDF] Intentando extracción con pdfplumber: {os.path.basename(file_path)}")
                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        text = page.extract_text() or ""
                        page_texts.append(text)
                
                total_chars = sum(len(text.strip()) for text in page_texts)
                if total_chars > 100:
                    print(f"[PDF] pdfplumber exitoso: {total_chars} caracteres extraídos")
                    return page_texts
                else:
                    print(f"[PDF] pdfplumber extrajo poco contenido, probando siguiente método")
                    page_texts = []
            except Exception as e:
                print(f"[PDF] Error con pdfplumber: {e}")
                page_texts = []
        
        # Método 3: PyPDF2 (fallback)
        if not page_texts:
            try:
                print(f"[PDF] Intentando extracción con PyPDF2: {os.path.basename(file_path)}")
                reader = PdfReader(file_path)
                for page in reader.pages:
                    text = page.extract_text() or ""
                    page_texts.append(text)
                
                total_chars = sum(len(text.strip()) for text in page_texts)
                print(f"[PDF] PyPDF2 completado: {total_chars} caracteres extraídos")
                return page_texts
            except Exception as e:
                print(f"[PDF] Error con PyPDF2: {e}")
                return []
        
        return page_texts
