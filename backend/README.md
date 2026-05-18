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

### Dependencias principales

- fastapi (API)
- uvicorn[standard] (servidor ASGI)
- sqlalchemy + aiosqlite (ORM + SQLite async)
- httpx (clientes HTTP async para integraciones)
- pydantic-settings (configuración)
- openai (cliente IA)
- python-jose[cryptography] + passlib[bcrypt] (auth/JWT y hashing)
- python-multipart (formularios OAuth2)
- dnspython (resolución DNS/WHOIS, opcional para integraciones DNS)

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

## Configuración de APIs

### APIs Críticas

**OpenAI (OBLIGATORIO para análisis de IA):**
- Obtén tu clave API en: https://platform.openai.com/api-keys
- Configura `OPENAI_API_KEY` en `.env`
- Sin esta clave, el sistema usará planes de fallback (sin análisis real de IA)

### APIs Opcionales

Consulta `env.example` para ver todas las APIs opcionales disponibles:
- **OSINT APIs**: NewsAPI, GitHub, Shodan, IPStack, EnsembleData
- **Financial APIs**: AlphaVantage, Finnhub, Financial Modeling Prep
- **Geopolitical APIs**: Permutable AI
- **Currency APIs**: ExchangeRate-API, Fixer.io
- **Crypto APIs**: CoinGecko

**Nota:** La mayoría de APIs retornarán errores si no están configuradas. Consulta `/api/integration/status` para ver el estado de todas las integraciones.

### Herramientas Externas (Opcional)

Algunas integraciones OSINT requieren herramientas externas instaladas en PATH:
- `sherlock`: Búsqueda de usernames en redes sociales
- `recon-ng`: Framework de reconocimiento web
- `theHarvester`: Búsqueda de información de dominios

## Diagnóstico

### Endpoint de Estado de Integraciones

Consulta el estado de todas las APIs configuradas:
```
GET /api/integration/status
```

Este endpoint muestra:
- Estado de configuración de cada API
- APIs críticas (OpenAI)
- APIs opcionales (OSINT, Financial, etc.)
- Resumen de configuración

### Health Check

Endpoint básico de salud con información de servicios:
```
GET /health
```

## Solución de Problemas

### "OPENAI_API_KEY no está configurada"

**Síntomas:**
- Las funciones de IA usan planes de fallback
- La clasificación OSINT retorna sentiment neutral
- Los análisis Taranis/OSINTGPT/Ominis retornan errores

**Solución:**
1. Configura `OPENAI_API_KEY` en `.env`
2. Reinicia el servidor
3. Verifica en `/health` o `/api/integration/status`

### "EnsembleData API endpoint not yet implemented"

**Síntomas:**
- Las consultas EnsembleData retornan errores aunque la API key esté configurada

**Solución:**
- La integración EnsembleData está implementada pero los endpoints específicos están pendientes
- La clase `EnsembleDataAPIService` existe pero requiere implementación completa de endpoints
- Por ahora retorna errores informativos

### APIs retornan "API key no configurada"

**Solución:**
- Configura las claves correspondientes en `.env`
- Consulta `env.example` para ver qué claves están disponibles
- La mayoría de APIs son opcionales y solo se necesitan para funcionalidades específicas

## Documentación

Una vez ejecutando el servidor, la documentación está disponible en:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc








