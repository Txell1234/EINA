# OSINT Intelligence Platform

Plataforma integral de análisis OSINT con IA que combina recopilación de datos, análisis cualitativo/cuantitativo y predicciones.

## Características

- **Recopilación OSINT**: Integración con Sherlock, Recon-ng, Google News, Reddit, GitHub
- **Análisis con IA**: Taranis AI, OSINTGPT, Ominis-OSINT
- **Análisis Cualitativo/Cuantitativo**: Basado en premisas, frameworks de razonamiento y KPIs
- **Predicciones**: Sistema de predicciones con porcentajes de confianza
- **Recomendaciones de Inversión**: Análisis de riesgos geopolíticos, políticos y sociales
- **Creación de Casos con IA**: El usuario puede crear casos mediante prompts y la IA genera el plan de acción

## Stack Tecnológico

- **Backend**: FastAPI (async) con SQLAlchemy
- **Frontend**: React + TypeScript + Vite
- **Base de datos**: SQLite (desarrollo) / PostgreSQL (producción)
- **IA**: OpenAI (GPT-4, embeddings)

## Instalación

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configurar variables de entorno
# En Windows PowerShell:
# $env:OPENAI_API_KEY = 'tu-clave-api-aqui'
# python -m app.main

# O crear archivo .env (copiar desde env.example y editar)
# cp env.example .env
# Editar .env con tus configuraciones, especialmente OPENAI_API_KEY
python -m app.main
```

**Nota de Seguridad**: La clave API de OpenAI ya está configurada en el entorno. Si necesitas cambiarla, edita el archivo `.env` o establece la variable de entorno `OPENAI_API_KEY`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Uso

1. Accede a http://localhost:3000
2. Inicia sesión o regístrate
3. Crea un caso mediante prompt (ej: "Análisis de comercio India-UAE")
4. La IA analiza el prompt y genera un plan automático
5. El sistema ejecuta búsquedas OSINT y análisis
6. Visualiza resultados en el dashboard

## Documentación API

Una vez ejecutando el backend, la documentación está disponible en:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

