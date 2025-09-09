from openai import OpenAI
import os

# Inicializar cliente con la API key desde la variable de entorno
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def call_llm(prompt: str):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Eres un asistente experto en documentación técnica."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content
