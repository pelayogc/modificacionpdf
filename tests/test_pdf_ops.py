from pathlib import Path

import fitz

from app.pdf_ops import apply_operations


def _sample_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Contrato de prueba", fontsize=12)
    doc.save(path)
    doc.close()


def test_add_watermark_and_highlight(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    _sample_pdf(source)

    result = apply_operations(
        source,
        output,
        [
            {"type": "add_watermark", "text": "BORRADOR", "pages": "all"},
            {"type": "highlight_text", "query": "Contrato", "pages": "all"},
        ],
    )

    assert result == {"input_pages": 1, "output_pages": 1}
    assert output.exists()
    with fitz.open(output) as doc:
        assert doc.page_count == 1
        assert "BORRADOR" in doc[0].get_text()


def test_delete_page(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Uno")
    doc.new_page().insert_text((72, 72), "Dos")
    doc.save(source)
    doc.close()

    result = apply_operations(source, output, [{"type": "delete_pages", "pages": [2]}])

    assert result == {"input_pages": 2, "output_pages": 1}


def test_replace_block_text(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    output = tmp_path / "output.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Direccion: Calle Antigua 1", fontsize=12)
    doc.save(source)
    doc.close()

    with fitz.open(source) as source_doc:
        rect = source_doc[0].search_for("Direccion: Calle Antigua 1")[0]

    result = apply_operations(
        source,
        output,
        [
            {
                "type": "replace_block_text",
                "page": 1,
                "bbox": [rect.x0, rect.y0, rect.x1, rect.y1],
                "text": "Direccion: Calle Nueva 2",
                "font_name": "Helvetica",
                "font_size": 12,
            }
        ],
    )

    assert result == {"input_pages": 1, "output_pages": 1}
    with fitz.open(output) as doc:
        text = doc[0].get_text()
        assert "Calle Nueva 2" in text
        assert "Calle Antigua 1" not in text
        spans = doc[0].get_text("dict")["blocks"][0]["lines"][0]["spans"]
        assert round(spans[0]["size"]) == 12
