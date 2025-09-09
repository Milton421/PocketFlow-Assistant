from openai import OpenAI
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env si existe
load_dotenv()

# Crear cliente de OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Leer el modelo desde variable de entorno o usar uno por defecto
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")


def generate_embeddings(texts):
    if not client.api_key:
        raise RuntimeError(
            "OPENAI_API_KEY no está configurada. Crea un archivo .env con OPENAI_API_KEY=... o define la variable de entorno."
        )

    response = client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts
    )
    return [d.embedding for d in response.data]
