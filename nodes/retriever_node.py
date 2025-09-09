# nodes/retriever_node.py
from utils.embeddings import generate_embeddings
from utils.faiss_client import FAISSClient
from typing import List, Dict

class Retriever:
    def __init__(self, dim: int = 1536):
        self.client = FAISSClient(dim)

    def retrieve(self, query: str, top_k: int = 5, filters: Dict = None, namespace: str = None) -> List[Dict]:
        qv = generate_embeddings([query])[0]
        raw = self.client.query(qv, top_k * 3)  # pedimos varios

        # Aplicar filtros de metadata si se proporcionan
        if filters:
            filtered_raw = []
            for r in raw:
                metadata = r.get("metadata", {})
                match = True
                
                for filter_key, filter_value in filters.items():
                    if filter_key not in metadata:
                        match = False
                        break
                    
                    # Soporte para filtros de lista (ej: section: ["engine", "retry"])
                    if isinstance(filter_value, list):
                        if metadata[filter_key] not in filter_value:
                            match = False
                            break
                    else:
                        if metadata[filter_key] != filter_value:
                            match = False
                            break
                
                if match:
                    filtered_raw.append(r)
            raw = filtered_raw

        # Aplicar filtro de namespace si se proporciona
        if namespace:
            raw = [r for r in raw if r.get("namespace") == namespace]

        # dedup por (archivo, página, fragmento)
        seen = {}
        for r in raw:
            key = (r.get("source"), r.get("page"), r.get("chunk_index"))
            if key not in seen or r.get("relevance_score",0.0) > seen[key].get("relevance_score",0.0):
                seen[key] = r

        # híbrido: primero mejor score, luego orden natural
        results = sorted(
            seen.values(),
            key=lambda x: (
                -x.get("relevance_score", 0.0),
                str(x.get("source","")),
                x.get("page") or 0,
                x.get("chunk_index") or 0
            )
        )[:top_k]

        # debug rápido
        print(f"\n[Retriever] Entrego {len(results)} chunks (filtros aplicados: {bool(filters or namespace)}):")
        for r in results:
            print(f"  - {r.get('source')} p.{r.get('page')} c.{r.get('chunk_index')} score={r.get('relevance_score')}")
        return results
