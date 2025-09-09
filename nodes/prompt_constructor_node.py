class PromptConstructor:
    def construct(self, query: str, context_chunks: list):
        # Concatenar todos los textos relevantes
        context_texts = "\n\n".join([c["text"] for c in context_chunks])

        # Prompt mejorado y flexible
        prompt = f"""
Responde de forma clara y breve a la siguiente pregunta usando exclusivamente el contexto proporcionado.

Pregunta:
{query}

Contexto:
{context_texts}

Instrucciones:
- Usa solo información del contexto.
- Si encuentras información relacionada, inclúyela aunque sea parcial.
- Si la información es ambigua, explica qué se puede responder y qué no.
- No inventes nada que no aparezca en el contexto.
- Solo responde exactamente: "No se encontró información suficiente"
  si realmente no hay NADA en el contexto que esté relacionado.

Respuesta:
"""
        return prompt.strip()
