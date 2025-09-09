import re
import unicodedata

class QueryPreprocessor:
    def preprocess(self, query: str) -> str:
        """
        Limpia y normaliza la query del usuario antes de pasarla al retriever.
        - Elimina espacios extra
        - Normaliza tildes
        - Convierte a minúsculas
        - Limpia caracteres raros
        """
        if not query or not isinstance(query, str):
            return ""

        # Normalizar unicode (ejemplo: acentos)
        query = unicodedata.normalize("NFKC", query)

        # Pasar a minúsculas
        query = query.lower()

        # Eliminar caracteres no alfanuméricos básicos (excepto ? y .)
        query = re.sub(r"[^a-záéíóúüñ0-9\s\?\.\-]", " ", query)

        # Reemplazar múltiples espacios por uno
        query = re.sub(r"\s+", " ", query).strip()

        return query
