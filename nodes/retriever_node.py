# nodes/retriever_node.py
from utils.embeddings import generate_embeddings
from utils.faiss_client import FAISSClient
from typing import List, Dict

class Retriever:
    def __init__(self, dim: int = 1536):
        self.client = FAISSClient(dim)

    def retrieve(self, query: str, top_k: int = 5, filters: Dict = None, namespace: str = None) -> List[Dict]:
        """
        Recupera chunks relevantes y aplica filtros de forma tolerante:
        - Los metadatos vienen en el propio dict del chunk (no en "metadata")
        - 'source' y 'section' aceptan coincidencia parcial y case-insensitive
        - 'source' permite escribir sin extensión o con prefijo del nombre
        - 'namespace' solo filtra si los chunks lo incluyen; si no existe, no descarta resultados
        """
        qv = generate_embeddings([query])[0]
        raw = self.client.query(qv, top_k * 3)  # pedimos varios

        def _basename_no_ext(path: str) -> str:
            if not path:
                return ""
            # obtener basename sin usar os (válido para / y \)
            name = path.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
            return name.rsplit(".", 1)[0].lower()

        def _str(s) -> str:
            return str(s or "").strip().lower()

        def _match_value(meta_val, filter_val, key: str) -> bool:
            """Coincidencia flexible para strings (source/section)."""
            if isinstance(filter_val, list):
                return any(_match_value(meta_val, fv, key) for fv in filter_val)

            fv = _str(filter_val)
            if fv == "":
                return True  # filtro vacío no restringe

            # Normalizar meta_val
            mv = _str(meta_val)

            # Reglas específicas
            if key in ("source", "source_path"):
                # comparar por basename y por el valor directo
                mv_base = _basename_no_ext(meta_val)
                return fv in mv or fv in mv_base
            if key in ("section",):
                return fv in mv

            # Comparación por igualdad como fallback
            return mv == fv

        # Aplicar filtros de metadata si se proporcionan (sobre el dict 'r' completo)
        if filters:
            filtered_raw = []
            for r in raw:
                record = r  # metadatos vienen al nivel superior
                match = True
                for filter_key, filter_value in filters.items():
                    meta_value = record.get(filter_key)  # p. ej., 'source', 'section'
                    if not _match_value(meta_value, filter_value, filter_key):
                        match = False
                        break
                if match:
                    filtered_raw.append(r)
            raw = filtered_raw

        # Aplicar filtro de namespace solo si los chunks contienen ese metadato
        if namespace:
            ns = _str(namespace)
            if any("namespace" in r for r in raw):
                raw = [r for r in raw if _str(r.get("namespace")) == ns]

        # Si los filtros eliminaron todo, relajar: volver a los mejores sin filtro
        if not raw:
            raw = self.client.query(qv, top_k * 3)

        # dedup por (archivo, página, fragmento)
        seen = {}
        for r in raw:
            key = (r.get("source"), r.get("page"), r.get("chunk_index"))
            if key not in seen or r.get("relevance_score", 0.0) > seen[key].get("relevance_score", 0.0):
                seen[key] = r

        # híbrido: primero mejor score, luego orden natural
        results = sorted(
            seen.values(),
            key=lambda x: (
                -x.get("relevance_score", 0.0),
                str(x.get("source", "")),
                x.get("page") or 0,
                x.get("chunk_index") or 0
            )
        )[:top_k]

        # debug rápido
        print(f"\n[Retriever] Entrego {len(results)} chunks (filtros aplicados: {bool(filters or namespace)}):")
        for r in results:
            print(f"  - {r.get('source')} p.{r.get('page')} c.{r.get('chunk_index')} score={r.get('relevance_score')}")
        return results
