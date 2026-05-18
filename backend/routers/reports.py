"""
Reports router
"""
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.database import get_db
# Autenticació eliminada
from schemas.reports import ReportRequest, ReportResponse
from models.reports import Report, ReportStatus, ReportFormat
from services.report_service import ReportService

router = APIRouter()

@router.post("/generate", response_model=ReportResponse)
async def generate_report(
    request: ReportRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Generate comprehensive report"""
    report_service = ReportService(db)
    
    # Create report record
    new_report = Report(
        case_id=request.case_id,
        title=request.title or f"Reporte para caso {request.case_id}",
        status=ReportStatus.GENERATING,
        format=request.format or ReportFormat.PDF
    )
    db.add(new_report)
    await db.commit()
    await db.refresh(new_report)
    
    # Generate report in background
    background_tasks.add_task(
        report_service.generate_report,
        new_report.id
    )
    
    return ReportResponse.model_validate(new_report)

@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get report by ID"""
    result = await db.execute(
        Report.__table__.select().where(Report.id == report_id)
    )
    report = result.first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    return ReportResponse.from_orm(report)

@router.get("/{report_id}/export")
async def export_report(
    report_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Export report file"""
    result = await db.execute(
        Report.__table__.select().where(Report.id == report_id)
    )
    report = result.first()
    
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    
    if not report.file_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Report file not generated yet"
        )
    
    suffix = "pdf" if report.format == ReportFormat.PDF else "xlsx"
    media = (
        "application/pdf"
        if report.format == ReportFormat.PDF
        else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    return FileResponse(
        report.file_path,
        media_type=media,
        filename=f"report_{report_id}.{suffix}",
    )

