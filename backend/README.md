# OSINT Intelligence Platform - Backend

Backend FastAPI para la plataforma OSINT con integración de IA.

## Instalación

1. Crear entorno virtual:
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

2. Instalar dependencias:
```bash
pip install -r requirements.txt
```

3. Configurar variables de entorno:
```bash
cp .env.example .env
# Editar .env con tus configuraciones
```

4. Ejecutar servidor:
```bash
python -m app.main
# O con uvicorn directamente:
uvicorn app.main:app --reload
```

## Estructura

- `app/`: Aplicación principal FastAPI
- `routers/`: Endpoints de la API
- `models/`: Modelos SQLAlchemy
- `schemas/`: Schemas Pydantic
- `services/`: Lógica de negocio
- `integrations/`: Integraciones con herramientas OSINT

## Documentación

Una vez ejecutando el servidor, la documentación está disponible en:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc









