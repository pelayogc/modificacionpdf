from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import fitz


def _clean_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


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
                for line in block.get("lines", []):
                    line_text = "".join(span.get("text", "") for span in line.get("spans", []))
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
