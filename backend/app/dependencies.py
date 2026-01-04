"""
Shared dependencies for FastAPI routes
AUTENTICACIÓ ELIMINADA - Tots els endpoints són públics
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

# Autenticació completament eliminada
# Tots els endpoints són públics i no requereixen autenticació

