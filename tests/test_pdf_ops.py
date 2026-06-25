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
