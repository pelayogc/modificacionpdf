from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from app.config import settings
from app.pdf_ops import SUPPORTED_OPERATIONS
from app.pdf_context import pdf_context_for_prompt


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
Usa el contexto del PDF para localizar el texto real antes de pedir una busqueda.
Para cambios semanticos como "cambia la direccion", "actualiza el telefono" o "modifica el CIF", elige el bloque concreto del contexto y usa replace_block_text con su bbox.
Cuando modifiques texto existente, conserva el font_name, font_size y color del bloque original siempre que aparezcan en DOCUMENT_CONTEXT_JSON.
No uses replace_text con palabras genericas como "direccion", "telefono", "email" o "cliente"; replace_text solo debe buscar texto exacto visible en el documento.
Si no puedes localizar con confianza el bloque afectado, anade una nota visible con add_text explicando que no se pudo localizar el dato exacto.
Limite antifalsificacion de facturas: rechaza cualquier peticion que intente modificar lineas de venta, conceptos de venta, cantidades, precios, descuentos, bases imponibles, impuestos, totales, importes, NIF/CIF/VAT, razon social, datos fiscales, numeracion de factura, fechas fiscales o cualquier dato que pueda alterar el valor legal o contable de una factura.
Si la peticion cruza ese limite, devuelve exactamente una operacion reject_request con un motivo claro y no incluyas ninguna operacion de modificacion.
Operaciones permitidas:
- reject_request: reason.
- add_text: page, x, y, text, font_size opcional, font_name opcional, color opcional hex.
- add_watermark: text, pages opcional 'all'/numero/lista, opacity opcional, color opcional.
- highlight_text: query, pages opcional, color opcional.
- redact_text: query, pages opcional.
- replace_text: find, replace, pages opcional, font_size opcional, font_name opcional.
- replace_block_text: page, bbox [x0,y0,x1,y1], text, font_size opcional, font_name opcional, color opcional.
- rotate_page: page, degrees 0/90/180/270.
- delete_pages: pages lista.
- reorder_pages: order lista con todas las paginas.
Devuelve solo el JSON valido del plan."""


def build_pdf_plan(
    *,
    filename: str,
    page_count: int,
    instructions: str,
    document_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
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
                    f"\nDOCUMENT_CONTEXT_JSON:\n"
                    f"{pdf_context_for_prompt(document_context or {'pages': [], 'truncated': False})}"
                ),
            },
        ],
    )
    plan = json.loads(response.output_text)
    operations = plan.get("operations")
    if not isinstance(operations, list) or not operations:
        raise ValueError("El modelo no devolvio operaciones aplicables.")
    return plan
