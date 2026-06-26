from app.llm import SYSTEM_PROMPT
from app.pdf_ops import SUPPORTED_OPERATIONS


def test_invoice_falsification_limits_are_explicit() -> None:
    assert "Limite antifalsificacion de facturas" in SYSTEM_PROMPT
    assert "lineas de venta" in SYSTEM_PROMPT
    assert "datos fiscales" in SYSTEM_PROMPT
    assert "reject_request" in SUPPORTED_OPERATIONS
