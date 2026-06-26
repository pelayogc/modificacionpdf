from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import fitz


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _hex_color(color: int | None) -> str | None:
    if color is None:
        return None
    return f"#{color:06x}"


def _dominant_span_style(spans: list[dict[str, Any]]) -> dict[str, Any]:
    weighted: dict[tuple[str, float, int | None], int] = {}
    for span in spans:
        text = span.get("text", "")
        if not text:
            continue
        key = (
            str(span.get("font") or "Helvetica"),
            round(float(span.get("size") or 11), 2),
            span.get("color"),
        )
        weighted[key] = weighted.get(key, 0) + len(text)
    if not weighted:
        return {"font_name": "Helvetica", "font_size": 11, "color": "#000000"}
    font_name, font_size, color = max(weighted.items(), key=lambda item: item[1])[0]
    return {"font_name": font_name, "font_size": font_size, "color": _hex_color(color) or "#000000"}


def extract_pdf_context(input_pdf: Path, *, max_chars: int = 14000) -> dict[str, Any]:
    doc = fitz.open(input_pdf)
    pages: list[dict[str, Any]] = []
    used_chars = 0
    truncated = False

    try:
        for page_index, page in enumerate(doc, start=1):
            page_blocks: list[dict[str, Any]] = []
            page_dict = page.get_text("dict")
            for block_index, block in enumerate(page_dict.get("blocks", []), start=1):
                if block.get("type") != 0:
                    continue
                lines = []
                spans = []
                for line in block.get("lines", []):
                    line_spans = line.get("spans", [])
                    spans.extend(line_spans)
                    line_text = "".join(span.get("text", "") for span in line_spans)
                    if cleaned := _clean_text(line_text):
                        lines.append(cleaned)
                text = _clean_text(" ".join(lines))
                if not text:
                    continue
                next_used = used_chars + len(text)
                if next_used > max_chars:
                    truncated = True
                    break
                used_chars = next_used
                page_blocks.append(
                    {
                        "id": f"p{page_index}_b{block_index}",
                        "page": page_index,
                        "bbox": [round(float(v), 2) for v in block["bbox"]],
                        "text": text,
                        **_dominant_span_style(spans),
                    }
                )
            pages.append(
                {
                    "page": page_index,
                    "width": round(float(page.rect.width), 2),
                    "height": round(float(page.rect.height), 2),
                    "blocks": page_blocks,
                }
            )
            if truncated:
                break
    finally:
        doc.close()

    return {"pages": pages, "truncated": truncated}


def pdf_context_for_prompt(context: dict[str, Any]) -> str:
    return json.dumps(context, ensure_ascii=False, separators=(",", ":"))
