"""
Cases router - Gestión de casos escalables con creación mediante prompts de IA
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
# Autenticació eliminada - no es requereix
from schemas.case import CaseCreate, CaseResponse, CaseUpdate, CasePromptRequest, CaseAutoCreateRequest
from models.case import Case, CasePrompt, CaseAnalysis, CaseKPI
from models.osint import OSINTResult, OSINTQuery
from models.investments import InvestmentRecommendation
from services.case_service import CaseService
from services.ai_service import AIService
from sqlalchemy import select, func
import logging

logger = logging.getLogger(__name__)

from app.dependencies import get_current_user
from models.user import User

router = APIRouter()

@router.post("/", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    case_data: CaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create new case"""
    new_case = Case(
        name=case_data.name,
        case_type=case_data.case_type,
        description=case_data.description,
        status="pending",
        user_id=current_user.id,
    )
    db.add(new_case)
    await db.commit()
    await db.refresh(new_case)
    
    return CaseResponse.model_validate(new_case)

@router.post("/suggest-kpis", response_model=dict)
async def suggest_kpis_for_case(
    prompt: str = Body(...),
    case_type: Optional[str] = Body(None)
):
    """Suggest relevant KPIs for a case based on prompt and case type"""
    from services.ai_service import AIService
    from sqlalchemy import select
    from models.qualitative import KPI
    
    try:
        ai_service = AIService()
        
        # If case_type not provided, try to infer from prompt
        if not case_type:
            # Simple inference - can be improved
            prompt_lower = prompt.lower()
            if any(word in prompt_lower for word in ["reputación", "reputation", "sentiment", "opinión"]):
                case_type = "social"
            elif any(word in prompt_lower for word in ["comercial", "commercial", "trade", "business", "investment"]):
                case_type = "business"
            elif any(word in prompt_lower for word in ["geopolítico", "geopolitical", "bilateral", "diplomatic"]):
                case_type = "geopolitical"
            elif any(word in prompt_lower for word in ["político", "political", "election", "policy"]):
                case_type = "political"
            else:
                case_type = "general"
        
        # Get existing KPIs to avoid duplicates
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as db:
            existing_kpis_result = await db.execute(select(KPI))
            existing_kpis = existing_kpis_result.scalars().all()
            existing_kpis_list = [
                {
                    "id": k.id,
                    "name": k.name,
                    "metric_type": k.metric_type,
                    "description": k.description
                }
                for k in existing_kpis
            ]
        
        # Get AI suggestions
        suggestion_result = await ai_service.suggest_kpis_for_case(
            case_type=case_type,
            case_description=prompt,
            existing_kpis=existing_kpis_list
        )
        
        return suggestion_result
        
    except Exception as e:
        logger.error(f"Error suggesting KPIs: {e}", exc_info=True)
        return {
            "suggested_kpis": [],
            "case_type": case_type or "general",
            "error": str(e)
        }

@router.post("/from-prompt", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case_from_prompt(
    prompt_data: CasePromptRequest,
    background_tasks: BackgroundTasks
):
    """Create case from AI prompt - Respuesta inmediata sin esperar commit"""
    import time
    start_time = time.time()
    
    # LOG INMEDIATO - Si no ves esto, la petición no está llegando
    logger.info("=" * 60)
    logger.info("=== INICIO create_case_from_prompt ===")
    logger.info(f"Tiempo inicio: {start_time}")
    logger.info("Creant cas sense autenticació")
    logger.info(f"Prompt recibido: {prompt_data.prompt[:100] if prompt_data.prompt else 'None'}...")
    logger.info("=" * 60)
    
    try:
        # Autenticació eliminada - no es necessària validació
        logger.info(f"Tiempo después validación usuario: {time.time() - start_time:.3f}s")
        
        # Validar prompt ANTES de crear sesión DB
        if not prompt_data or not hasattr(prompt_data, 'prompt') or not prompt_data.prompt or not prompt_data.prompt.strip():
            logger.error("Prompt vacío o inválido")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El prompt no puede estar vacío"
            )
        
        # Preparar nombre del caso
        prompt_name = prompt_data.prompt[:50] + "..." if len(prompt_data.prompt) > 50 else prompt_data.prompt
        if not prompt_name.strip():
            prompt_name = "Caso generado"
        
        logger.info(f"Nombre del caso: {prompt_name}")
        logger.info(f"Tiempo antes de crear sesión DB: {time.time() - start_time:.3f}s")
        
        # Crear sesión independiente (no usar get_db para evitar commit automático)
        from app.database import AsyncSessionLocal
        import asyncio
        
        async with AsyncSessionLocal() as db:
            try:
                # Paso 1: Crear caso en DB
                logger.info(f"Paso 1: Creando caso en DB (tiempo: {time.time() - start_time:.3f}s)")
                new_case = Case(
                    name=prompt_name,
                    case_type="general",
                    description=prompt_data.prompt,
                    status="pending",
                    user_id=None,  # Autenticació eliminada
                )
                db.add(new_case)
                
                # Paso 2: Flush para obtener ID (rápido)
                logger.info(f"Paso 2: Haciendo flush (tiempo: {time.time() - start_time:.3f}s)")
                await db.flush()
                case_id = new_case.id
                logger.info(f"Paso 2: OK - ID obtenido: {case_id} (tiempo: {time.time() - start_time:.3f}s)")
                
                # Paso 3: Hacer commit inmediatamente (debería ser rápido)
                logger.info(f"Paso 3: Haciendo commit (tiempo: {time.time() - start_time:.3f}s)")
                commit_start = time.time()
                await db.commit()
                commit_time = time.time() - commit_start
                logger.info(f"Paso 3: OK - Caso {case_id} commiteado en {commit_time:.3f}s (tiempo total: {time.time() - start_time:.3f}s)")
                
                # Paso 4: Refresh para asegurar estado actualizado
                logger.info(f"Paso 4: Refrescando objeto (tiempo: {time.time() - start_time:.3f}s)")
                await db.refresh(new_case)
                logger.info(f"Paso 4: OK - Objeto refrescado (tiempo: {time.time() - start_time:.3f}s)")
                
                # Paso 5: Re-cargar caso desde DB para asegurar created_at
                logger.info(f"Paso 5: Re-cargando caso desde DB (tiempo: {time.time() - start_time:.3f}s)")
                from sqlalchemy import select
                case_result = await db.execute(select(Case).where(Case.id == case_id))
                loaded_case = case_result.scalar_one()
                
                # Si created_at es None, establecerlo manualmente
                if loaded_case.created_at is None:
                    from datetime import datetime
                    loaded_case.created_at = datetime.now()
                    await db.commit()
                    await db.refresh(loaded_case)
                
                logger.info(f"Paso 5: OK - Caso cargado, created_at: {loaded_case.created_at} (tiempo: {time.time() - start_time:.3f}s)")
                
                # Paso 6: Preparar respuesta
                logger.info(f"Paso 6: Preparando respuesta (tiempo: {time.time() - start_time:.3f}s)")
                response = CaseResponse.model_validate(loaded_case)
                logger.info(f"Paso 6: OK - Respuesta preparada (tiempo: {time.time() - start_time:.3f}s)")
            
                # Paso 7: Background task para análisis (commit ya hecho) - NO bloquea
                async def analyze_in_background(case_id: int, prompt_text: str, initial_name: str):
                    """Background task que hace análisis de IA"""
                    logger.info(f"Background análisis iniciado para caso {case_id}")
                    
                    # Pequeña pausa para asegurar que el commit se complete
                    await asyncio.sleep(0.1)
                    
                    # Análisis en nueva sesión
                    async with AsyncSessionLocal() as bg_db:
                        try:
                            # Cambiar status a analyzing
                            await bg_db.execute(
                                Case.__table__.update()
                                .where(Case.id == case_id)
                                .values(status="analyzing")
                            )
                            await bg_db.commit()
                            
                            # Analizar con IA
                            ai_service = AIService()
                            analysis_plan = await ai_service.analyze_case_prompt(prompt_text)
                            
                            # Actualizar caso
                            await bg_db.execute(
                                Case.__table__.update()
                                .where(Case.id == case_id)
                                .values(
                                    name=analysis_plan.get("name", initial_name),
                                    case_type=analysis_plan.get("type", "general")
                                )
                            )
                            
                            # Also suggest KPIs
                            case_type_from_plan = analysis_plan.get("type", "general")
                            kpi_suggestions = await ai_service.suggest_kpis_for_case(
                                case_type=case_type_from_plan,
                                case_description=prompt_text
                            )
                            # Add suggestions to analysis plan
                            if "suggested_kpis" in kpi_suggestions:
                                analysis_plan["suggested_kpis"] = kpi_suggestions["suggested_kpis"]
                            
                            # Guardar prompt
                            case_prompt = CasePrompt(
                                case_id=case_id,
                                prompt=prompt_text,
                                ai_analysis=analysis_plan,
                            )
                            bg_db.add(case_prompt)
                            await bg_db.commit()
                            
                            # Create suggested KPIs if analysis_plan contains kpi suggestions
                            if "suggested_kpis" in analysis_plan or "kpis" in analysis_plan:
                                from models.qualitative import KPI
                                
                                kpis_to_create = analysis_plan.get("suggested_kpis") or analysis_plan.get("kpis", [])
                                for kpi_data in kpis_to_create:
                                    if isinstance(kpi_data, dict):
                                        # Check if KPI already exists
                                        kpi_name = kpi_data.get("name", "")
                                        existing_kpi = await bg_db.execute(
                                            select(KPI).where(KPI.name == kpi_name)
                                        )
                                        kpi_obj = existing_kpi.scalar_one_or_none()
                                        
                                        if not kpi_obj:
                                            # Create new KPI template
                                            kpi_obj = KPI(
                                                name=kpi_name,
                                                kpi_type=kpi_data.get("kpi_type", "quantitative"),
                                                metric_type=kpi_data.get("metric_type"),
                                                description=kpi_data.get("description"),
                                                measurement_unit=kpi_data.get("measurement_unit"),
                                                case_type_filter=case_type_from_plan,
                                                is_template=True
                                            )
                                            bg_db.add(kpi_obj)
                                            await bg_db.flush()
                                        
                                        # Link KPI to case
                                        case_kpi = CaseKPI(
                                            case_id=case_id,
                                            kpi_id=kpi_obj.id,
                                            target_value=kpi_data.get("target_value"),
                                            measurement_unit=kpi_data.get("measurement_unit"),
                                            is_tracked=True
                                        )
                                        bg_db.add(case_kpi)
                                
                                await bg_db.commit()
                            
                            # Ejecutar análisis completo
                            case_service = CaseService(bg_db)
                            await case_service.execute_case_analysis(case_id, analysis_plan)
                            
                        except Exception as e:
                            logger.error(f"Error en background análisis: {e}", exc_info=True)
                
                # Agregar tarea en background (análisis) - NO bloquea la respuesta
                background_tasks.add_task(analyze_in_background, case_id, prompt_data.prompt, prompt_name)
                
                total_time = time.time() - start_time
                logger.info("=" * 60)
                logger.info("=== FIN create_case_from_prompt - Respondiendo ===")
                logger.info(f"Tiempo total: {total_time:.3f}s. Caso {case_id} creado y respondiendo.")
                logger.info("=" * 60)
                
                if total_time > 5.0:
                    logger.warning(f"⚠️ ADVERTENCIA: El endpoint tardó {total_time:.3f}s en responder (debería ser <1s)")
                
                return response
                
            except HTTPException as http_ex:
                logger.error(f"HTTPException en create_case_from_prompt: {http_ex.status_code} - {http_ex.detail}")
                await db.rollback()
                raise
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                total_time = time.time() - start_time if 'start_time' in locals() else 0
                logger.error(f"EXCEPCIÓN en create_case_from_prompt después de {total_time:.3f}s: {error_type}: {error_msg}", exc_info=True)
                await db.rollback()
                
                # Mensaje de error más descriptivo según el tipo
                if "database" in error_msg.lower() or "sql" in error_msg.lower():
                    detail_msg = f"Error de base de datos: {error_msg}"
                elif "connection" in error_msg.lower() or "timeout" in error_msg.lower():
                    detail_msg = f"Error de conexión: {error_msg}"
                else:
                    detail_msg = f"Error al crear caso: {error_msg}"
                
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=detail_msg
                )
    except HTTPException:
        # Re-raise HTTPExceptions sin modificar
        raise
    except Exception as e:
        # Errores fuera del contexto de DB
        error_type = type(e).__name__
        error_msg = str(e)
        total_time = time.time() - start_time if 'start_time' in locals() else 0
        logger.error(f"EXCEPCIÓN CRÍTICA en create_case_from_prompt después de {total_time:.3f}s: {error_type}: {error_msg}", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error crítico al crear caso: {error_msg}"
        )

@router.post("/auto-create", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case_auto(
    prompt_data: CaseAutoCreateRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create case from AI prompt - IA analiza el prompt y determina qué hacer"""
    try:
        logger.info("Iniciando creación de caso automático")
        
        # Validar prompt
        if not prompt_data.prompt or not prompt_data.prompt.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El prompt no puede estar vacío"
            )
        
        # Crear caso base INMEDIATAMENTE (sin esperar IA)
        # Extraer nombre básico del prompt para respuesta rápida
        prompt_name = prompt_data.prompt[:50] + "..." if len(prompt_data.prompt) > 50 else prompt_data.prompt
        if not prompt_name.strip():
            prompt_name = "Caso generado"
        
        new_case = Case(
            name=prompt_name,
            case_type="general",  # Se actualizará después del análisis IA
            description=prompt_data.prompt,
            status="analyzing",
            user_id=None,  # Autenticació eliminada
        )
        db.add(new_case)
        await db.commit()
        await db.refresh(new_case)
        logger.info(f"Caso creado con ID: {new_case.id}")
        
        # Analizar prompt con IA en background (no bloquea la respuesta)
        async def analyze_and_update_case(case_id: int, prompt_text: str, initial_name: str):
            from app.database import AsyncSessionLocal
            async with AsyncSessionLocal() as bg_db:
                try:
                    ai_service = AIService()
                    logger.info(f"Analizando prompt con IA en background para caso {case_id}...")
                    analysis_plan = await ai_service.analyze_case_prompt(prompt_text)
                    logger.info(f"Plan de análisis generado: {analysis_plan.get('name', 'Sin nombre')}")
                    
                    # Actualizar caso con información de IA
                    await bg_db.execute(
                        Case.__table__.update()
                        .where(Case.id == case_id)
                        .values(
                            name=analysis_plan.get("name", initial_name),
                            case_type=analysis_plan.get("type", "general")
                        )
                    )
                    
                    # Guardar prompt con análisis
                    case_prompt = CasePrompt(
                        case_id=case_id,
                        prompt=prompt_text,
                        ai_analysis=analysis_plan,
                    )
                    bg_db.add(case_prompt)
                    await bg_db.commit()
                    
                    # Create KPIs if provided in request or suggested by AI
                    if hasattr(prompt_data, 'selected_kpi_ids') and prompt_data.selected_kpi_ids:
                        from models.case import CaseKPI
                        for kpi_id in prompt_data.selected_kpi_ids:
                            case_kpi = CaseKPI(
                                case_id=case_id,
                                kpi_id=kpi_id,
                                is_tracked=True
                            )
                            bg_db.add(case_kpi)
                        await bg_db.commit()
                    elif "suggested_kpis" in analysis_plan or "kpis" in analysis_plan:
                        # Auto-create suggested KPIs
                        from models.qualitative import KPI
                        from models.case import CaseKPI
                        
                        kpis_to_create = analysis_plan.get("suggested_kpis") or analysis_plan.get("kpis", [])
                        for kpi_data in kpis_to_create:
                            if isinstance(kpi_data, dict):
                                kpi_name = kpi_data.get("name", "")
                                existing_kpi = await bg_db.execute(
                                    select(KPI).where(KPI.name == kpi_name)
                                )
                                kpi_obj = existing_kpi.scalar_one_or_none()
                                
                                if not kpi_obj:
                                    kpi_obj = KPI(
                                        name=kpi_name,
                                        kpi_type=kpi_data.get("kpi_type", "quantitative"),
                                        metric_type=kpi_data.get("metric_type"),
                                        description=kpi_data.get("description"),
                                        measurement_unit=kpi_data.get("measurement_unit"),
                                        case_type_filter=analysis_plan.get("type", "general"),
                                        is_template=True
                                    )
                                    bg_db.add(kpi_obj)
                                    await bg_db.flush()
                                
                                case_kpi = CaseKPI(
                                    case_id=case_id,
                                    kpi_id=kpi_obj.id,
                                    target_value=kpi_data.get("target_value"),
                                    measurement_unit=kpi_data.get("measurement_unit"),
                                    is_tracked=True
                                )
                                bg_db.add(case_kpi)
                        
                        await bg_db.commit()
                    
                    # Ejecutar análisis completo
                    case_service = CaseService(bg_db)
                    await case_service.execute_case_analysis(case_id, analysis_plan)
                    
                except Exception as e:
                    logger.error(f"Error en análisis background: {e}", exc_info=True)
                    # Usar plan de fallback
                    fallback_plan = {
                        "name": initial_name,
                        "type": "general",
                        "osint_queries": [],
                        "ai_analyses": [],
                        "kpis": [],
                        "premise": prompt_text,
                        "framework": "deductive"
                    }
                    try:
                        case_prompt = CasePrompt(
                            case_id=case_id,
                            prompt=prompt_text,
                            ai_analysis=fallback_plan,
                        )
                        bg_db.add(case_prompt)
                        await bg_db.commit()
                    except Exception as commit_error:
                        logger.error(f"Error guardando fallback plan: {commit_error}", exc_info=True)
        
        # Ejecutar análisis en background (no bloquea)
        background_tasks.add_task(analyze_and_update_case, new_case.id, prompt_data.prompt, prompt_name)
        logger.info(f"Análisis en background programado para caso {new_case.id}")
        
        return CaseResponse.model_validate(new_case)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado creando caso automático: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear caso: {str(e)}"
        )

@router.get("/", response_model=List[CaseResponse])
async def list_cases(
    skip: int = 0,
    limit: int = 100,
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List all cases - Autenticació eliminada"""
    from sqlalchemy import select
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        query = select(Case).where(Case.user_id == current_user.id)

        if status_filter:
            query = query.where(Case.status == status_filter)
        
        query = query.offset(skip).limit(limit).order_by(Case.created_at.desc())
        
        result = await db.execute(query)
        cases = result.scalars().all()
        
        logger.info(f"Query executada: {len(cases)} casos trobats a la BD")
        
        # Convertir a resposta
        case_responses = []
        for case in cases:
            try:
                # Assegurar que user_id sigui None si no està definit
                if not hasattr(case, 'user_id') or case.user_id is None:
                    case.user_id = None
                
                case_response = CaseResponse.model_validate(case)
                case_responses.append(case_response)
                logger.debug(f"Cas {case.id} ({case.name}) serialitzat correctament")
            except Exception as e:
                logger.error(f"Error convertint cas {case.id} ({case.name}): {e}", exc_info=True)
                # Continuar amb els altres casos
                continue
        
        logger.info(f"Retornant {len(case_responses)} casos vàlids de {len(cases)} trobats")
        
        # Si no hi ha casos però la query ha retornat casos, hi ha un problema de serialització
        if len(cases) > 0 and len(case_responses) == 0:
            logger.error(f"⚠️ PROBLEMA: S'han trobat {len(cases)} casos però cap s'ha pogut serialitzar!")
            # Retornar dades mínimes per debug - usar dict directe
            debug_responses = []
            for c in cases[:10]:
                try:
                    debug_responses.append({
                        "id": c.id,
                        "name": c.name or "Sense nom",
                        "case_type": str(c.case_type.value) if hasattr(c.case_type, 'value') else str(c.case_type) if c.case_type else "general",
                        "description": c.description or "",
                        "status": str(c.status.value) if hasattr(c.status, 'value') else str(c.status) if c.status else "pending",
                        "user_id": None,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                        "updated_at": c.updated_at.isoformat() if c.updated_at else None
                    })
                except Exception as e:
                    logger.error(f"Error creant resposta debug per cas {c.id}: {e}")
            return debug_responses
        
        return case_responses
    except Exception as e:
        logger.error(f"Error llistant casos: {e}", exc_info=True)
        import traceback
        logger.error(traceback.format_exc())
        return []

@router.get("/metrics")
async def get_dashboard_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard metrics - aggregated counts"""
    # Count active cases - Autenticació eliminada
    active_result = await db.execute(
        select(func.count(Case.id)).where(
            Case.status.in_(["analyzing", "pending"])
        )
    )
    active_cases = active_result.scalar() or 0
    
    # Count OSINT results (through queries)
    osint_result = await db.execute(
        select(func.count(OSINTResult.id))
        .join(OSINTQuery)
        .join(Case)
    )
    osint_data_collected = osint_result.scalar() or 0
    
    # Count completed analyses
    completed_result = await db.execute(
        select(func.count(Case.id)).where(
            Case.status == "completed"
        )
    )
    analyses_completed = completed_result.scalar() or 0
    
    # Count investment recommendations
    recommendations_result = await db.execute(
        select(func.count(InvestmentRecommendation.id))
        .join(Case)
    )
    recommendations_generated = recommendations_result.scalar() or 0
    
    return {
        "active_cases": active_cases,
        "osint_data_collected": osint_data_collected,
        "analyses_completed": analyses_completed,
        "recommendations_generated": recommendations_generated
    }

@router.get("/filtered", response_model=List[CaseResponse])
async def get_filtered_cases(
    status: Optional[str] = None,
    case_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get filtered cases - Autenticació eliminada"""
    query = Case.__table__.select()

    if status:
        query = query.where(Case.status == status)
    if case_type:
        query = query.where(Case.case_type == case_type)

    query = query.offset(skip).limit(limit).order_by(Case.created_at.desc())

    result = await db.execute(query)
    cases = result.all()

    return [CaseResponse.model_validate(case) for case in cases]

@router.get("/search", response_model=List[CaseResponse])
async def search_cases(
    q: str,
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Search cases by name or description - Autenticació eliminada"""
    from sqlalchemy import or_
    query = Case.__table__.select().where(
        or_(
            Case.name.contains(q),
            Case.description.contains(q)
        )
    )

    query = query.offset(skip).limit(limit).order_by(Case.created_at.desc())

    result = await db.execute(query)
    cases = result.all()

    return [CaseResponse.model_validate(case) for case in cases]

@router.get("/{case_id}/full", response_model=dict)
async def get_full_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get full case with all related data - Autenticació eliminada"""
    result = await db.execute(
        Case.__table__.select().where(Case.id == case_id)
    )
    case = result.first()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # TODO: Agregar datos relacionados (OSINT, AI, etc.)
    return {
        "case": CaseResponse.model_validate(case).model_dump(),
        "osint_data": [],
        "ai_analyses": [],
        "predictions": [],
    }

@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get case by ID - Autenticació eliminada"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .where(Case.user_id == current_user.id)
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    return CaseResponse.model_validate(case)

@router.post("/{case_id}/analyze", response_model=CaseResponse)
async def analyze_case(
    case_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Execute complete analysis for a case - Autenticació eliminada"""
    result = await db.execute(
        Case.__table__.select().where(Case.id == case_id)
    )
    case = result.first()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    case_service = CaseService(db)
    background_tasks.add_task(case_service.execute_case_analysis, case_id)
    
    # Update status
    await db.execute(
        Case.__table__.update()
        .where(Case.id == case_id)
        .values(status="analyzing")
    )
    await db.commit()
    
    return CaseResponse.model_validate(case)

@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: int,
    case_data: CaseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update case - Autenticació eliminada"""
    from sqlalchemy import select
    
    case_result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .where(Case.user_id == current_user.id)
    )
    case = case_result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    # Update fields
    update_data = case_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(case, key, value)
    
    await db.commit()
    await db.refresh(case)
    
    return CaseResponse.model_validate(case)

@router.post("/{case_id}/rerun", response_model=CaseResponse)
async def rerun_case_analysis(
    case_id: int,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Rerun case analysis - Re-execute analysis for an existing case"""
    from sqlalchemy import select
    from services.case_service import CaseService
    
    case_result = await db.execute(select(Case).where(Case.id == case_id))
    case = case_result.scalar_one_or_none()
    
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Reset status to pending
    case.status = "pending"
    await db.commit()
    
    # Get the original prompt if available
    from models.case import CasePrompt
    prompt_result = await db.execute(
        select(CasePrompt).where(CasePrompt.case_id == case_id).order_by(CasePrompt.created_at.desc())
    )
    prompt = prompt_result.scalar_one_or_none()
    
    # Execute analysis in background
    case_service = CaseService(db)
    background_tasks.add_task(case_service.execute_case_analysis, case_id)
    
    # Update status to analyzing
    case.status = "analyzing"
    await db.commit()
    await db.refresh(case)
    
    logger.info(f"Case {case_id} rerun initiated")
    
    return CaseResponse.model_validate(case)

@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete case"""
    result = await db.execute(
        select(Case)
        .where(Case.id == case_id)
        .where(Case.user_id == current_user.id)
    )
    case = result.scalar_one_or_none()

    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )

    await db.delete(case)
    await db.commit()

    return None

