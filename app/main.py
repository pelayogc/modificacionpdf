from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import fitz
from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import CurrentUser, get_current_user, require_admin
from app.config import settings
from app.db import admin_stats, create_job, finish_job, get_job, init_db
from app.llm import build_pdf_plan
from app.pdf_context import extract_pdf_context
from app.pdf_ops import PdfOperationError, apply_operations


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Modificacion PDF", version="1.0.0", lifespan=lifespan)
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def index(request: Request, user: CurrentUser = Depends(get_current_user)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "index.html",
        {"user": user, "max_upload_mb": settings.max_upload_mb},
    )


@app.post("/process", response_class=HTMLResponse)
async def process_pdf(
    request: Request,
    user: CurrentUser = Depends(get_current_user),
    pdf: UploadFile = File(...),
    instructions: str = Form(...),
) -> HTMLResponse:
    if not pdf.filename or not pdf.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Sube un archivo PDF.")
    if not instructions.strip():
        raise HTTPException(status_code=400, detail="Indica las modificaciones necesarias.")

    job_id = uuid4().hex
    input_path = settings.upload_dir / f"{job_id}.pdf"
    output_path = settings.output_dir / f"{job_id}.pdf"
    max_bytes = settings.max_upload_mb * 1024 * 1024

    settings.ensure_dirs()
    size = 0
    with input_path.open("wb") as fh:
        while chunk := await pdf.read(1024 * 1024):
            size += len(chunk)
            if size > max_bytes:
                input_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="El PDF supera el limite permitido.")
            fh.write(chunk)

    create_job(
        job_id=job_id,
        user_email=user.email,
        original_filename=pdf.filename,
        instructions=instructions,
        input_path=input_path,
        input_bytes=size,
        model=settings.model,
    )

    input_pages: int | None = None
    try:
        with fitz.open(input_path) as doc:
            input_pages = doc.page_count
        document_context = extract_pdf_context(input_path)
        plan = build_pdf_plan(
            filename=pdf.filename,
            page_count=input_pages,
            instructions=instructions,
            document_context=document_context,
        )
        operations = plan["operations"]
        result = apply_operations(input_path, output_path, operations)
        output_bytes = output_path.stat().st_size
        finish_job(
            job_id=job_id,
            status="completed",
            input_pages=result["input_pages"],
            output_pages=result["output_pages"],
            operations=operations,
            output_path=output_path,
            output_bytes=output_bytes,
        )
        return templates.TemplateResponse(
            request,
            "result.html",
            {
                "user": user,
                "job_id": job_id,
                "plan": plan,
                "status": "completed",
                "download_url": f"/download/{job_id}",
            },
        )
    except (PdfOperationError, ValueError, RuntimeError) as exc:
        finish_job(
            job_id=job_id,
            status="failed",
            input_pages=input_pages,
            operations=[],
            error=str(exc),
        )
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        finish_job(job_id=job_id, status="failed", input_pages=input_pages, error=str(exc))
        raise
    finally:
        await pdf.close()


@app.get("/download/{job_id}")
def download_pdf(job_id: str, user: CurrentUser = Depends(get_current_user)) -> FileResponse:
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Trabajo no encontrado.")
    if job["user_email"] != user.email and not user.is_admin:
        raise HTTPException(status_code=403, detail="No autorizado.")
    if job["status"] != "completed" or not job["output_path"]:
        raise HTTPException(status_code=404, detail="PDF no disponible.")
    path = Path(job["output_path"])
    if not path.exists():
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    filename = f"modificado-{job['original_filename']}"
    return FileResponse(path, media_type="application/pdf", filename=filename)


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request, user: CurrentUser = Depends(require_admin)) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "admin.html",
        {"user": user, "stats": admin_stats()},
    )
