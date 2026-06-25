from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from app import main


def _sample_pdf(path: Path) -> None:
    doc = fitz.open()
    doc.new_page().insert_text((72, 72), "Documento de prueba")
    doc.save(path)
    doc.close()


def test_upload_process_and_download(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(main.settings, "data_dir", tmp_path)
    monkeypatch.setattr(main.settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(main.settings, "output_dir", tmp_path / "outputs")
    monkeypatch.setattr(main.settings, "db_path", tmp_path / "app.db")
    monkeypatch.setattr(main.settings, "local_dev_user_email", "pelayo@think-tank.es")
    monkeypatch.setattr(
        main,
        "build_pdf_plan",
        lambda **_: {
            "summary": "Anadir marca de agua",
            "operations": [{"type": "add_watermark", "text": "BORRADOR", "pages": "all"}],
        },
    )

    main.init_db()
    source = tmp_path / "source.pdf"
    _sample_pdf(source)

    client = TestClient(main.app)
    with source.open("rb") as fh:
        response = client.post(
            "/process",
            data={"instructions": "anade marca de agua BORRADOR"},
            files={"pdf": ("source.pdf", fh, "application/pdf")},
        )

    assert response.status_code == 200
    assert "PDF generado" in response.text

    job_id = next((tmp_path / "outputs").glob("*.pdf")).stem
    download = client.get(f"/download/{job_id}")
    assert download.status_code == 200
    assert download.headers["content-type"] == "application/pdf"
