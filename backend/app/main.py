"""
FastAPI main application entry point
"""
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.database import engine, Base
import uvicorn
import logging

# Agregar el directorio backend al PYTHONPATH si no está
# Esto asegura que los imports de models, routers, services, etc. funcionen
backend_dir = Path(__file__).parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import all models first (so Base.metadata knows about them)
from models import *  # noqa: F401, F403

# Import routers
from routers import (
    auth,
    cases,
    osint_collection,
    ai_analysis,
    qualitative,
    predictions,
    reports,
    investments,
    kpis,
    sync,
    unified,
    visualizations,
    geographic,
    research,
    heatmap,
    admin,
    dashboard,
    posts,
    reputation,
    public_affairs,
    geopolitical_advanced,
    integration,
)
from routers import geopolitical

# Create database tables
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# FastAPI app instance
app = FastAPI(
    title="OSINT Intelligence Platform",
    description="Plataforma integral de análisis OSINT con IA",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - Must be added before routers
cors_origins = settings.cors_origins_list
logger.info(f"CORS origins configurados: {cors_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],  # Exponer headers para debugging
    max_age=3600,  # Cache preflight requests for 1 hour
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])
app.include_router(cases.router, prefix="/cases", tags=["Cases"])  # Sin /api para compatibilidad
app.include_router(osint_collection.router, prefix="/api/osint", tags=["OSINT Collection"])
app.include_router(osint_collection.router, prefix="/osint", tags=["OSINT Collection"])  # Sin /api
app.include_router(ai_analysis.router, prefix="/api/ai", tags=["AI Analysis"])
app.include_router(ai_analysis.router, prefix="/ai", tags=["AI Analysis"])  # Sin /api
app.include_router(qualitative.router, prefix="/api/qualitative", tags=["Qualitative Analysis"])
app.include_router(qualitative.router, prefix="/qualitative", tags=["Qualitative Analysis"])  # Sin /api
app.include_router(predictions.router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(investments.router, prefix="/api/investments", tags=["Investment Recommendations"])
app.include_router(investments.router, prefix="/investment", tags=["Investment Recommendations"])  # Sin /api
app.include_router(kpis.router, prefix="/kpis", tags=["KPIs"])
app.include_router(sync.router, prefix="/api/sync", tags=["Synchronization"])
app.include_router(sync.router, prefix="/sync", tags=["Synchronization"])  # Sin /api para compatibilidad
app.include_router(unified.router, prefix="/api/unified", tags=["Unified Analysis"])
app.include_router(unified.router, prefix="/unified", tags=["Unified Analysis"])  # Sin /api para compatibilidad
app.include_router(visualizations.router, prefix="/api/visualizations", tags=["Visualizations"])
app.include_router(geographic.router, prefix="/api/geographic", tags=["Geographic"])
app.include_router(geopolitical.router, tags=["Geopolitical"])
app.include_router(research.router, prefix="/api/research", tags=["Research"])
app.include_router(heatmap.router, prefix="/api/heatmap", tags=["Heatmap"])
app.include_router(admin.router, tags=["Admin"])
app.include_router(dashboard.router, tags=["Dashboard"])
app.include_router(posts.router, tags=["Posts"])
app.include_router(reputation.router, tags=["Reputation"])
app.include_router(public_affairs.router, tags=["Public Affairs"])
app.include_router(geopolitical_advanced.router, tags=["Geopolitical Advanced"])
app.include_router(integration.router, tags=["Integration"])

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    logger.info("=" * 60)
    logger.info("INICIANDO SERVIDOR BACKEND")
    logger.info("=" * 60)
    
    logger.info("Inicializando base de datos...")
    await init_db()
    logger.info("Base de datos inicializada correctamente")
    
    # Validar configuración de OpenAI
    if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.strip() == "":
        logger.warning("=" * 60)
        logger.warning("ADVERTENCIA: OPENAI_API_KEY no está configurada")
        logger.warning("Las funciones de IA usarán planes de fallback")
        logger.warning("Para habilitar análisis completo con IA, configura OPENAI_API_KEY en .env")
        logger.warning("=" * 60)
    else:
        logger.info("OpenAI configurado correctamente")
    
    logger.info("=" * 60)
    logger.info("SERVIDOR BACKEND LISTO")
    logger.info(f"Servidor corriendo en http://{settings.HOST}:{settings.PORT}")
    logger.info(f"Documentación disponible en http://{settings.HOST}:{settings.PORT}/docs")
    logger.info("=" * 60)

@app.get("/")
async def root():
    """Root endpoint"""
    return JSONResponse({
        "message": "OSINT Intelligence Platform API",
        "version": "1.0.0",
        "docs": "/docs"
    })

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    from datetime import datetime
    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    })

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

