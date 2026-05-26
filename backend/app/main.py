"""
FastAPI main application entry point
"""
import sys
from contextlib import asynccontextmanager
from pathlib import Path
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.database import engine, Base
from app.limiter import limiter
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
    investment_advanced,
    intelligence,
    tavily as tavily_router,
)
from routers import geopolitical
from routers import extract as extract_router
from routers import prospective as prospective_router
from routers import analysis as analysis_router

# Create database tables
def _run_alembic_upgrade() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", settings.database_url_sync)
    command.upgrade(cfg, "head")


async def init_db():
    if settings.USE_ALEMBIC:
        await asyncio.to_thread(_run_alembic_upgrade)
        logger.info("Migracions Alembic aplicades (head)")
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    async with engine.begin() as conn:
        from app.schema_patches import run_schema_patches_sync

        await conn.run_sync(run_schema_patches_sync)

async def _check_critical_apis():
    """Check critical APIs and generate alerts if not configured"""
    alerts = []
    
    # Check OpenAI (critical)
    openai_key = settings.OPENAI_API_KEY.strip() if settings.OPENAI_API_KEY else ""
    if not openai_key or openai_key == "sk-proj-TU_CLAVE_API_AQUI":
        alerts.append({
            "level": "critical",
            "api": "openai",
            "message": "OpenAI API key is not configured",
            "impact": "All AI-powered features will use fallback mode"
        })
    
    # Log alerts
    if alerts:
        logger.warning("=" * 60)
        logger.warning("ALERTAS DE CONFIGURACIÓN - APIs CRÍTICAS")
        logger.warning("=" * 60)
        for alert in alerts:
            logger.warning(f"[{alert['level'].upper()}] {alert['api']}: {alert['message']}")
            logger.warning(f"  Impacto: {alert['impact']}")
        logger.warning("=" * 60)
        logger.warning(f"Total de alertas críticas: {len(alerts)}")
        logger.warning("Consulta /api/integration/status para más detalles")
        logger.warning("=" * 60)
    else:
        logger.info("✓ Todas las APIs críticas están configuradas correctamente")


def _log_startup_status() -> None:
    """Log OpenAI and LLM provider configuration on startup."""
    openai_key = settings.OPENAI_API_KEY.strip() if settings.OPENAI_API_KEY else ""
    if not openai_key or openai_key == "sk-proj-TU_CLAVE_API_AQUI":
        logger.warning("=" * 60)
        logger.warning("ADVERTENCIA: OPENAI_API_KEY no está configurada correctamente")
        logger.warning("Estado: OPENAI_API_KEY está vacía o contiene valor placeholder")
        logger.warning("Consecuencias:")
        logger.warning("  - Las funciones de IA usarán planes de fallback (sin análisis real)")
        logger.warning("  - La clasificación OSINT retornará sentiment neutral y categorías vacías")
        logger.warning("  - Los análisis Taranis/OSINTGPT/Ominis retornarán resultados de fallback")
        logger.warning("  - La creación de casos por prompt usará plan básico en lugar de IA")
        logger.warning("Solución:")
        logger.warning("  - Configura OPENAI_API_KEY en el archivo .env con tu clave real")
        logger.warning("  - Obtén una clave en https://platform.openai.com/api-keys")
        logger.warning("  - Reinicia el servidor después de configurar la clave")
        logger.warning("=" * 60)
    else:
        logger.info("✓ OpenAI configurado correctamente")
        logger.info(f"  Modelo: {settings.OPENAI_MODEL}")
        logger.info(f"  Modelo de embeddings: {settings.OPENAI_EMBEDDING_MODEL}")

    from services.llm_service import llm_config_error_message, resolve_provider

    llm_provider = resolve_provider()
    if llm_provider:
        logger.info(f"✓ LLM prospectiu/extracció: {llm_provider} (LLM_PROVIDER={settings.LLM_PROVIDER})")
    else:
        logger.warning("ADVERTENCIA: extracció i escenaris prospectius desactivats")
        logger.warning(f"  {llm_config_error_message()}")


MONITOR_INTERVAL_SECONDS = settings.ALERT_MONITOR_INTERVAL_HOURS * 3600
_monitor_batch_running = False


async def _run_monitor_batch() -> None:
    """Run OSINT monitor checks without blocking the HTTP event loop."""
    global _monitor_batch_running
    if _monitor_batch_running:
        logger.info("Monitor scheduler: lot anterior encara actiu, s'omet")
        return

    _monitor_batch_running = True
    try:
        from services.alert_monitor_service import run_all_active_monitors

        summary = await run_all_active_monitors()
        if summary.get("checked"):
            logger.info(
                "Monitor scheduler: %d monitors comprovats, %d coincidències noves",
                summary["checked"],
                summary.get("new_matches", 0),
            )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("Monitor scheduler error: %s", exc)
    finally:
        _monitor_batch_running = False


async def _monitor_scheduler_loop() -> None:
    # Evita competir amb el boot i les primeres peticions de la UI
    await asyncio.sleep(120)
    while True:
        asyncio.create_task(_run_monitor_batch())
        await asyncio.sleep(MONITOR_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 60)
    logger.info("INICIANT SERVIDOR BACKEND")
    logger.info("=" * 60)

    logger.info("Inicialitzant base de dades...")
    await init_db()
    logger.info("Base de dades inicialitzada correctament")

    from app.database import AsyncSessionLocal
    from services.reasoning_framework_service import ReasoningFrameworkService

    async with AsyncSessionLocal() as db:
        seeded = await ReasoningFrameworkService(db).seed_builtin_frameworks()
        if seeded:
            logger.info("Marcs de raonament inicials: %d creats", seeded)

    from services.event_handlers import register_event_handlers

    register_event_handlers()

    await _check_critical_apis()

    openai_key = (settings.OPENAI_API_KEY or "").strip()
    if not openai_key or openai_key == "sk-proj-TU_CLAVE_API_AQUI":
        logger.warning("ADVERTÈNCIA: OPENAI_API_KEY no configurada correctament")
        logger.warning("Les funcions d'IA usaran plans de fallback")
    else:
        logger.info("✓ OpenAI configurat: model=%s", settings.OPENAI_MODEL)

    from services.llm_service import resolve_provider

    provider = resolve_provider()
    if provider:
        logger.info("✓ LLM provider actiu: %s", provider)
    else:
        logger.warning("ADVERTÈNCIA: Cap proveïdor LLM configurat (Anthropic/OpenAI/Gemini)")

    logger.info("=" * 60)
    logger.info("SERVIDOR BACKEND LISTO")
    logger.info(f"Servidor corriendo en http://{settings.HOST}:{settings.PORT}")
    logger.info(f"Documentación disponible en http://{settings.HOST}:{settings.PORT}/docs")
    logger.info("=" * 60)

    monitor_task = asyncio.create_task(_monitor_scheduler_loop())

    yield

    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass

    logger.info("Tancant servidor...")


# FastAPI app instance
app = FastAPI(
    title=settings.APP_NAME,
    description="Plataforma integral de análisis OSINT con IA",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS middleware - Must be added before routers
cors_origins = settings.cors_origins_list
logger.info(f"CORS origins configurados: {cors_origins}")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(cases.router, prefix="/api/cases", tags=["Cases"])
app.include_router(osint_collection.router, prefix="/api/osint", tags=["OSINT Collection"])
app.include_router(tavily_router.router, prefix="/api/tavily", tags=["Tavily"])
app.include_router(ai_analysis.router, prefix="/api/ai", tags=["AI Analysis"])
app.include_router(qualitative.router, prefix="/api/qualitative", tags=["Qualitative Analysis"])
app.include_router(predictions.router, prefix="/api/predictions", tags=["Predictions"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(investments.router, prefix="/api/investments", tags=["Investment Recommendations"])
app.include_router(kpis.router, prefix="/kpis", tags=["KPIs"])
app.include_router(sync.router, prefix="/api/sync", tags=["Synchronization"])
app.include_router(unified.router, prefix="/api/unified", tags=["Unified Analysis"])
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
app.include_router(investment_advanced.router, tags=["Investment Advanced"])
app.include_router(integration.router, tags=["Integration"])
app.include_router(intelligence.router, tags=["Intelligence Unit"])
app.include_router(extract_router.router, prefix="/api/extract", tags=["Extraction Pipeline"])
app.include_router(prospective_router.router, prefix="/api/prospective", tags=["Prospective Analysis"])
app.include_router(
    analysis_router.router,
    prefix="/api/analysis",
    tags=["Direct Analysis"],
)

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
    """Health check endpoint with system status"""
    from datetime import datetime
    from app.config import settings
    
    from services.llm_service import provider_status

    openai_configured = bool(
        settings.OPENAI_API_KEY and 
        settings.OPENAI_API_KEY.strip() and 
        settings.OPENAI_API_KEY != "sk-proj-TU_CLAVE_API_AQUI"
    )
    llm = provider_status()
    llm_configured = llm["configured"]
    
    from services.export_backends import probe_openpyxl, probe_weasyprint

    openpyxl_status = probe_openpyxl()
    weasyprint_status = probe_weasyprint(smoke_test=False)

    recommendations: list[str] = []
    if not llm_configured:
        recommendations.append(
            "Configura almenys una clau LLM al .env: ANTHROPIC_API_KEY, OPENAI_API_KEY o GEMINI_API_KEY "
            "(o defineix LLM_PROVIDER=anthropic|openai|gemini)"
        )
    if not openai_configured:
        recommendations.append(
            "OPENAI_API_KEY opcional per a classificació IA i embeddings (AIService)"
        )
    if not weasyprint_status.get("available"):
        recommendations.append(
            "Install WeasyPrint native libs for PDF export — see backend/Dockerfile"
        )

    return JSONResponse({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "llm": llm,
            "openai": {
                "configured": openai_configured,
                "status": "available" if openai_configured else "fallback_mode",
                "model": settings.OPENAI_MODEL if openai_configured else None
            },
            "export": {
                "weasyprint": weasyprint_status,
                "openpyxl": openpyxl_status,
            },
        },
        "recommendations": recommendations,
    })

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )

