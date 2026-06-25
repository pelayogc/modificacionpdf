from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import settings
from app.pdf_ops import SUPPORTED_OPERATIONS


PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "summary": {"type": "string"},
        "operations": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "additionalProperties": True,
                "required": ["type"],
                "properties": {
                    "type": {"type": "string", "enum": sorted(SUPPORTED_OPERATIONS)},
                },
            },
        },
    },
    "required": ["summary", "operations"],
}


SYSTEM_PROMPT = """Eres un planificador de modificaciones de PDF.
Convierte la peticion del usuario en operaciones JSON ejecutables.
No prometas cambios que no esten en las operaciones permitidas.
Usa paginas 1-based. Si faltan coordenadas para anadir texto, usa posiciones razonables.
Si la peticion es ambigua, genera una operacion conservadora o devuelve una marca de agua/nota visible.
Operaciones permitidas:
- add_text: page, x, y, text, font_size opcional, color opcional hex.
- add_watermark: text, pages opcional 'all'/numero/lista, opacity opcional, color opcional.
- highlight_text: query, pages opcional, color opcional.
- redact_text: query, pages opcional.
- replace_text: find, replace, pages opcional, font_size opcional.
- rotate_page: page, degrees 0/90/180/270.
- delete_pages: pages lista.
- reorder_pages: order lista con todas las paginas.
Devuelve solo el JSON valido del plan."""


def build_pdf_plan(*, filename: str, page_count: int, instructions: str) -> dict[str, Any]:
    client = OpenAI()
    response = client.responses.create(
        model=settings.model,
        reasoning={"effort": "low"},
        text={
            "format": {
                "type": "json_schema",
                "name": "pdf_modification_plan",
                "schema": PLAN_SCHEMA,
                "strict": False,
            },
            "verbosity": "low",
        },
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Archivo: {filename}\n"
                    f"Numero de paginas: {page_count}\n"
                    f"Instrucciones: {instructions}"
                ),
            },
        ],
    )
    plan = json.loads(response.output_text)
    operations = plan.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("El modelo no devolvio operaciones aplicables.")
    return plan
