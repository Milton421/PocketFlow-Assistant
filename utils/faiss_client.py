import faiss
import numpy as np
import os
import pickle
from typing import Optional

INDEX_FILE = "faiss_index.bin"
META_FILE = "metadata.pkl"

# --- Singleton compartido con autoreload por mtime ---
_shared_client: Optional["FAISSClient"] = None
_last_index_mtime: Optional[float] = None
_last_meta_mtime: Optional[float] = None


def get_client(dim: int = 1536) -> "FAISSClient":
    global _shared_client
    if _shared_client is None:
        _shared_client = FAISSClient(dim)
    return _shared_client


class FAISSClient:
    def __init__(self, dim: int = 1536):
        self.dim = dim
        self.index = faiss.IndexFlatL2(dim)
        self.metadata = []
        self._load_if_available()

    def _load_if_available(self):
        global _last_index_mtime, _last_meta_mtime
        if os.path.exists(INDEX_FILE) and os.path.exists(META_FILE):
            self.index = faiss.read_index(INDEX_FILE)
            with open(META_FILE, "rb") as f:
                self.metadata = pickle.load(f)
            _last_index_mtime = os.path.getmtime(INDEX_FILE)
            _last_meta_mtime = os.path.getmtime(META_FILE)

    def _reload_if_changed(self):
        global _last_index_mtime, _last_meta_mtime
        try:
            idx_mtime = os.path.getmtime(INDEX_FILE) if os.path.exists(INDEX_FILE) else None
            meta_mtime = os.path.getmtime(META_FILE) if os.path.exists(META_FILE) else None
        except Exception:
            idx_mtime = meta_mtime = None

        if idx_mtime and meta_mtime and (idx_mtime != _last_index_mtime or meta_mtime != _last_meta_mtime):
            # Recargar desde disco
            self.index = faiss.read_index(INDEX_FILE)
            with open(META_FILE, "rb") as f:
                self.metadata = pickle.load(f)
            _last_index_mtime = idx_mtime
            _last_meta_mtime = meta_mtime

    def add_embeddings(self, embeddings, metadatas):
        vectors = np.array(embeddings).astype("float32")
        self.index.add(vectors)
        self.metadata.extend(metadatas)
        self._save()

    def query(self, query_vector, top_k=5, force_min_chunk=True):
        """Busca en FAISS y devuelve chunks con metadata normalizada"""
        # Asegurar que estamos leyendo la última versión del índice
        self._reload_if_changed()

        if self.index.ntotal == 0:
            return []

        query = np.array([query_vector]).astype("float32")
        distances, indices = self.index.search(query, top_k)

        results = []
        seen_keys = set()

        for idx, dist in zip(indices[0], distances[0]):
            if idx < len(self.metadata):
                meta = self.metadata[idx].copy()

                # --- Score normalizado ---
                score = 1.0 / (1.0 + float(dist))   # 0 < score <= 1
                meta["relevance_score"] = round(score, 4)

                # --- Garantizar campos mínimos ---
                meta.setdefault("text", "")
                meta.setdefault("source", "")
                meta.setdefault("page", None)
                meta.setdefault("chunk_index", None)
                meta.setdefault("section", None)
                meta.setdefault("source_path", None)

                # --- Evitar duplicados (mismo texto/página) ---
                key = f"{meta['source']}_{meta['page']}_{meta['chunk_index']}"
                if key in seen_keys:
                    continue
                seen_keys.add(key)

                results.append(meta)

        # --- Si no pasa ningún chunk y hay metadata disponible, forzar el mejor ---
        if force_min_chunk and not results and len(self.metadata) > 0:
            best = self.metadata[0].copy()
            best["relevance_score"] = 0.1  # mínimo para que pase el filtro
            results.append(best)

        return results

    def _save(self):
        global _last_index_mtime, _last_meta_mtime
        faiss.write_index(self.index, INDEX_FILE)
        with open(META_FILE, "wb") as f:
            pickle.dump(self.metadata, f)
