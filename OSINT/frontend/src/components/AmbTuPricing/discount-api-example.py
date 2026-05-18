"""
Exemple d'endpoint per validar codis de descompte al backend d'AmbTu.
Afegeix això al teu backend (FastAPI, Flask, etc.) perquè els codis
mai es revelin al client.

IMPORTANT: Els codis vàlids han d'estar NOMÉS al servidor (BD, variables d'entorn, etc.)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api", tags=["pricing"])


class ValidateDiscountRequest(BaseModel):
    code: str


# Els codis vàlids NOMÉS al servidor - mai al client
# En producció: usa BD, Redis, o variables d'entorn (os.getenv, etc.)
VALID_CODES = {
    # Format: "CODI": percentatge (1-100)
    # Afegeix els teus codis reals aquí. Exemple per proves:
    # "TEST": 5,
}


@router.post("/validate-discount")
def validate_discount(data: ValidateDiscountRequest):
    """Valida un codi de descompte. Retorna valid i percentatge."""
    code = (data.code or "").strip().upper()
    if not code:
        return {"valid": False, "percent": 0}

    percent = VALID_CODES.get(code)
    if percent is not None:
        return {"valid": True, "percent": percent}
    return {"valid": False, "percent": 0}
