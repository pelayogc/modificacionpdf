from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _csv_env(name: str, default: str) -> list[str]:
    raw = os.environ.get(name, default)
    return [item.strip().lower() for item in raw.split(",") if item.strip()]


@dataclass
class Settings:
    data_dir: Path
    upload_dir: Path
    output_dir: Path
    db_path: Path
    allowed_domains: list[str]
    admin_emails: list[str]
    model: str
    max_upload_mb: int
    app_base_url: str
    local_dev_user_email: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        data_dir = Path(os.environ.get("DATA_DIR", "data")).resolve()
        upload_dir = data_dir / "uploads"
        output_dir = data_dir / "outputs"
        return cls(
            data_dir=data_dir,
            upload_dir=upload_dir,
            output_dir=output_dir,
            db_path=data_dir / "app.db",
            allowed_domains=_csv_env(
                "ALLOWED_EMAIL_DOMAINS",
                "edicionesnobel.com,paraninfo.es,think-tank.es",
            ),
            admin_emails=_csv_env(
                "ADMIN_EMAILS",
                "pelayo@think-tank.es,pelayo@edicionesnobel.com",
            ),
            model=os.environ.get("PDF_LLM_MODEL", "gpt-5.5"),
            max_upload_mb=int(os.environ.get("MAX_UPLOAD_MB", "30")),
            app_base_url=os.environ.get("APP_BASE_URL", "http://127.0.0.1:8000"),
            local_dev_user_email=os.environ.get("LOCAL_DEV_USER_EMAIL") or None,
        )

    def ensure_dirs(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


settings = Settings.from_env()
