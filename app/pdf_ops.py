from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz


class PdfOperationError(ValueError):
    pass


SUPPORTED_OPERATIONS = {
    "add_text",
    "add_watermark",
    "highlight_text",
    "redact_text",
    "reject_request",
    "replace_block_text",
    "replace_text",
    "rotate_page",
    "delete_pages",
    "reorder_pages",
}


def _page_index(page_number: int, page_count: int) -> int:
    if page_number < 1 or page_number > page_count:
        raise PdfOperationError(f"La pagina {page_number} no existe.")
    return page_number - 1


def _rgb(color: str | None) -> tuple[float, float, float]:
    if not color:
        return (0, 0, 0)
    value = color.strip().lstrip("#")
    if len(value) != 6:
        raise PdfOperationError(f"Color no valido: {color}")
    try:
        return tuple(int(value[i : i + 2], 16) / 255 for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError as exc:
        raise PdfOperationError(f"Color no valido: {color}") from exc


def _pdf_font_name(font_name: Any) -> str:
    raw = str(font_name or "helv").lower()
    is_bold = "bold" in raw or raw.endswith("-bd") or "black" in raw
    is_italic = "italic" in raw or "oblique" in raw or raw.endswith("-it")
    if "cour" in raw:
        if is_bold and is_italic:
            return "cobi"
        if is_bold:
            return "cobo"
        if is_italic:
            return "coit"
        return "cour"
    if "times" in raw or "roman" in raw:
        if is_bold and is_italic:
            return "tibi"
        if is_bold:
            return "tibo"
        if is_italic:
            return "tiit"
        return "tiro"
    if "symbol" in raw:
        return "symb"
    if "zapf" in raw:
        return "zadb"
    if is_bold and is_italic:
        return "hebi"
    if is_bold:
        return "hebo"
    if is_italic:
        return "heit"
    return "helv"


def _pages_for_operation(op: dict[str, Any], page_count: int) -> list[int]:
    pages = op.get("pages")
    if pages == "all" or pages is None:
        return list(range(page_count))
    if isinstance(pages, int):
        return [_page_index(pages, page_count)]
    if isinstance(pages, list):
        return [_page_index(int(page), page_count) for page in pages]
    raise PdfOperationError("'pages' debe ser 'all', un numero o una lista de numeros.")


def _search_required(page: fitz.Page, query: str) -> list[fitz.Rect]:
    matches = page.search_for(query)
    if not matches:
        raise PdfOperationError(f"No se encontro el texto: {query}")
    return matches


def _rect_from_bbox(bbox: Any) -> fitz.Rect:
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise PdfOperationError("'bbox' debe ser una lista [x0, y0, x1, y1].")
    rect = fitz.Rect(*(float(v) for v in bbox))
    if rect.is_empty or rect.is_infinite:
        raise PdfOperationError("'bbox' no es un rectangulo valido.")
    return rect


def _insert_textbox_fit(
    page: fitz.Page,
    rect: fitz.Rect,
    text: str,
    *,
    font_size: float,
    font_name: str,
    color: tuple[float, float, float],
) -> None:
    target = fitz.Rect(rect.x0, rect.y0, rect.x1, max(rect.y1, rect.y0 + font_size + 6))
    for size in (font_size, font_size * 0.9, font_size * 0.8, font_size * 0.7, font_size * 0.6):
        overflow = page.insert_textbox(
            target,
            text,
            fontsize=max(6, size),
            fontname=font_name,
            color=color,
            align=fitz.TEXT_ALIGN_LEFT,
        )
        if overflow >= 0:
            return
    page.insert_text(
        (target.x0, target.y0 + max(6, font_size)),
        text,
        fontsize=6,
        fontname=font_name,
        color=color,
    )


def apply_operations(input_pdf: Path, output_pdf: Path, operations: list[dict[str, Any]]) -> dict[str, int]:
    if not operations:
        raise PdfOperationError("El plan no contiene operaciones aplicables.")
    rejection = next((op for op in operations if op.get("type") == "reject_request"), None)
    if rejection:
        reason = str(
            rejection.get("reason")
            or "Solicitud rechazada porque puede alterar datos fiscales o de factura."
        )
        raise PdfOperationError(reason)

    doc = fitz.open(input_pdf)
    input_pages = doc.page_count

    try:
        for op in operations:
            op_type = op.get("type")
            if op_type not in SUPPORTED_OPERATIONS:
                raise PdfOperationError(f"Operacion no soportada: {op_type}")

            if op_type == "add_text":
                page = doc[_page_index(int(op["page"]), doc.page_count)]
                font_size = float(op.get("font_size", 11))
                page.insert_text(
                    (float(op["x"]), float(op["y"])),
                    str(op["text"]),
                    fontsize=font_size,
                    fontname=_pdf_font_name(op.get("font_name")),
                    color=_rgb(op.get("color")),
                )

            elif op_type == "add_watermark":
                text = str(op["text"])
                opacity = max(0.05, min(float(op.get("opacity", 0.18)), 0.75))
                for page_index in _pages_for_operation(op, doc.page_count):
                    page = doc[page_index]
                    rect = page.rect
                    font_size = float(op.get("font_size", max(28, rect.width / 12)))
                    page.insert_textbox(
                        rect,
                        text,
                        fontsize=font_size,
                        color=_rgb(op.get("color") or "#666666"),
                        align=fitz.TEXT_ALIGN_CENTER,
                        fill_opacity=opacity,
                    )

            elif op_type == "highlight_text":
                query = str(op["query"])
                for page_index in _pages_for_operation(op, doc.page_count):
                    page = doc[page_index]
                    for rect in _search_required(page, query):
                        annot = page.add_highlight_annot(rect)
                        annot.set_colors(stroke=_rgb(op.get("color") or "#ffff00"))
                        annot.update()

            elif op_type == "redact_text":
                query = str(op["query"])
                for page_index in _pages_for_operation(op, doc.page_count):
                    page = doc[page_index]
                    for rect in _search_required(page, query):
                        page.add_redact_annot(rect, fill=_rgb(op.get("fill") or "#ffffff"))
                    page.apply_redactions()

            elif op_type == "replace_text":
                query = str(op["find"])
                replacement = str(op["replace"])
                for page_index in _pages_for_operation(op, doc.page_count):
                    page = doc[page_index]
                    rects = _search_required(page, query)
                    for rect in rects:
                        page.add_redact_annot(rect, fill=_rgb(op.get("fill") or "#ffffff"))
                    page.apply_redactions()
                    for rect in rects:
                        page.insert_text(
                            (rect.x0, rect.y1 - 2),
                            replacement,
                            fontsize=float(op.get("font_size", max(8, rect.height * 0.75))),
                            fontname=_pdf_font_name(op.get("font_name")),
                            color=_rgb(op.get("color")),
                        )

            elif op_type == "replace_block_text":
                page = doc[_page_index(int(op["page"]), doc.page_count)]
                rect = _rect_from_bbox(op["bbox"])
                text = str(op["text"])
                page.add_redact_annot(rect, fill=_rgb(op.get("fill") or "#ffffff"))
                page.apply_redactions()
                font_size = float(op.get("font_size", max(8, min(12, rect.height * 0.55))))
                _insert_textbox_fit(
                    page,
                    rect,
                    text,
                    font_size=font_size,
                    font_name=_pdf_font_name(op.get("font_name")),
                    color=_rgb(op.get("color")),
                )

            elif op_type == "rotate_page":
                page = doc[_page_index(int(op["page"]), doc.page_count)]
                degrees = int(op.get("degrees", 90))
                if degrees not in (0, 90, 180, 270):
                    raise PdfOperationError("La rotacion debe ser 0, 90, 180 o 270 grados.")
                page.set_rotation(degrees)

            elif op_type == "delete_pages":
                page_numbers = sorted(
                    {_page_index(int(page), doc.page_count) for page in op["pages"]},
                    reverse=True,
                )
                if len(page_numbers) >= doc.page_count:
                    raise PdfOperationError("No se pueden eliminar todas las paginas.")
                for page_index in page_numbers:
                    doc.delete_page(page_index)

            elif op_type == "reorder_pages":
                order = [int(page) for page in op["order"]]
                if sorted(order) != list(range(1, doc.page_count + 1)):
                    raise PdfOperationError("El nuevo orden debe incluir todas las paginas una vez.")
                doc.select([page - 1 for page in order])

        output_pdf.parent.mkdir(parents=True, exist_ok=True)
        doc.save(output_pdf, garbage=4, deflate=True)
        return {"input_pages": input_pages, "output_pages": doc.page_count}
    finally:
        doc.close()
