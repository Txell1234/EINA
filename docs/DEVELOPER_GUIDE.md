# Guía de Desarrollo - EINA Platform

## Arquitectura del Sistema

### Stack Tecnológico

- **Backend**: FastAPI (Python 3.9+)
- **Frontend**: React + TypeScript + Vite
- **Base de Datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **IA**: OpenAI (GPT-4, embeddings)
- **Testing**: pytest, pytest-asyncio

### Estructura del Código

```
EINA/
├── backend/
│   ├── app/              # Configuración de FastAPI
│   ├── models/           # Modelos SQLAlchemy
│   ├── routers/          # Endpoints API
│   ├── services/         # Lógica de negocio
│   ├── integrations/     # Integraciones con APIs externas
│   ├── schemas/          # Esquemas Pydantic
│   └── tests/            # Tests
│       ├── unit/         # Tests unitarios
│       └── integration/  # Tests de integración
└── frontend/
    ├── src/
    │   ├── components/   # Componentes React
    │   ├── services/     # Servicios API
    │   └── contexts/     # Contextos React
    └── public/
```

## Cómo Agregar Nuevos Servicios

### 1. Crear el Modelo

```python
# backend/models/nuevo_modulo.py
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func
from app.database import Base

class NuevoModelo(Base):
    __tablename__ = "nuevo_modelo"
    
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
```

### 2. Registrar el Modelo

```python
# backend/models/__init__.py
from .nuevo_modulo import NuevoModelo

__all__ = [
    # ... otros modelos
    "NuevoModelo",
]
```

### 3. Crear el Servicio

```python
# backend/services/nuevo_servicio.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
from models.nuevo_modulo import NuevoModelo

class NuevoServicio:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def crear_item(self, nombre: str) -> Dict[str, Any]:
        item = NuevoModelo(nombre=nombre)
        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)
        return {"id": item.id, "nombre": item.nombre}
```

### 4. Crear el Router

```python
# backend/routers/nuevo_modulo.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from services.nuevo_servicio import NuevoServicio

router = APIRouter(prefix="/api/nuevo-modulo", tags=["Nuevo Módulo"])

@router.post("/crear")
async def crear_item(
    nombre: str,
    db: AsyncSession = Depends(get_db)
):
    service = NuevoServicio(db)
    return await service.crear_item(nombre)
```

### 5. Registrar el Router

```python
# backend/app/main.py
from routers import nuevo_modulo

app.include_router(nuevo_modulo.router)
```

## Cómo Agregar Nuevos Endpoints

### Backend

1. Agrega el método al servicio
2. Crea el endpoint en el router
3. Registra el router en `main.py`

### Frontend

1. Agrega el método al servicio API:

```typescript
// frontend/src/services/api.ts
export const nuevoServicio = {
  crearItem: async (nombre: string) => {
    const response = await api.post('/api/nuevo-modulo/crear', null, {
      params: { nombre }
    })
    return response.data
  }
}
```

2. Crea el componente (si es necesario):

```typescript
// frontend/src/components/NuevoModulo/NuevoComponente.tsx
import { useMutation } from '@tanstack/react-query'
import { nuevoServicio } from '../../services/api'

export default function NuevoComponente() {
  const mutation = useMutation({
    mutationFn: (nombre: string) => nuevoServicio.crearItem(nombre),
    onSuccess: () => {
      alert('Item creado exitosamente')
    }
  })
  
  // ... resto del componente
}
```

## Testing

### Tests Unitarios

```python
# backend/tests/unit/test_nuevo_servicio.py
import pytest
from services.nuevo_servicio import NuevoServicio

@pytest.mark.unit
class TestNuevoServicio:
    async def test_crear_item(self, db_session):
        service = NuevoServicio(db_session)
        result = await service.crear_item("Test")
        assert "id" in result
        assert result["nombre"] == "Test"
```

### Tests de Integración

```python
# backend/tests/integration/test_nuevo_endpoints.py
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
class TestNuevoEndpoints:
    def test_crear_item(self, test_client: TestClient):
        response = test_client.post(
            "/api/nuevo-modulo/crear",
            params={"nombre": "Test"}
        )
        assert response.status_code == 200
        assert "id" in response.json()
```

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Solo unitarios
pytest tests/unit/

# Solo integración
pytest tests/integration/

# Con cobertura
pytest --cov=services --cov=models
```

## Integración con APIs Externas

### Crear un Servicio de Integración

```python
# backend/integrations/nueva_api.py
import httpx
from app.config import settings

class NuevaAPIService:
    def __init__(self):
        self.api_key = settings.NUEVA_API_KEY
        self.base_url = "https://api.nueva.com"
    
    async def obtener_datos(self, query: str):
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/datos",
                params={"query": query, "api_key": self.api_key}
            )
            return response.json()
```

## Guía de Contribución

### Proceso de Desarrollo

1. Crea una rama desde `main`
2. Implementa tus cambios
3. Escribe tests
4. Asegúrate de que todos los tests pasen
5. Actualiza la documentación
6. Crea un Pull Request

### Estándares de Código

- **Python**: Sigue PEP 8
- **TypeScript**: Usa ESLint
- **Commits**: Mensajes descriptivos
- **Tests**: Cobertura mínima del 70%

### Estructura de Commits

```
tipo(scope): descripción

[descripción detallada opcional]

Fixes #issue
```

Tipos: `feat`, `fix`, `docs`, `test`, `refactor`

## Configuración del Entorno

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Variables de Entorno

Crea `.env` en `backend/`:

```env
DATABASE_URL=sqlite+aiosqlite:///./osint_platform.db
OPENAI_API_KEY=tu_api_key
NEWS_API_KEY=tu_api_key
# ... otras APIs
```

## Base de Datos

### Migraciones

```python
# Crear tablas
from app.database import engine, Base
from models import *
async with engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)
```

### Consultas

```python
from sqlalchemy import select
from models.nuevo_modulo import NuevoModelo

result = await db.execute(
    select(NuevoModelo).where(NuevoModelo.nombre == "Test")
)
items = result.scalars().all()
```

## Debugging

### Backend

```python
import logging
logger = logging.getLogger(__name__)
logger.debug("Mensaje de debug")
```

### Frontend

```typescript
console.log("Debug:", data)
// O usar React DevTools
```

## Recursos Adicionales

- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [React Docs](https://react.dev/)
- [SQLAlchemy Docs](https://docs.sqlalchemy.org/)
- [pytest Docs](https://docs.pytest.org/)
