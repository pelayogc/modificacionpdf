from pathlib import Path

import fitz

from app.pdf_context import extract_pdf_context


def test_extract_pdf_context_includes_typography(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Direccion: Calle Antigua 1", fontsize=12, fontname="helv")
    doc.save(source)
    doc.close()

    context = extract_pdf_context(source)
    block = context["pages"][0]["blocks"][0]

    assert block["text"] == "Direccion: Calle Antigua 1"
    assert block["font_name"] == "Helvetica"
    assert block["font_size"] == 12
    assert block["color"] == "#000000"
