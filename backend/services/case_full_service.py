"""Aggregate related data for GET /cases/{id}/full."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_analysis import AIAnalysis
from models.osint import OSINTQuery, OSINTResult
from models.predictions import Prediction
from models.prospective_inquiry import ProspectiveInquiry


async def load_case_full_bundle(db: AsyncSession, case_id: int) -> dict:
    """Load OSINT, AI analyses and predictions linked to a case."""
    osint_rows: list[dict] = []
    q_result = await db.execute(
        select(OSINTQuery)
        .where(OSINTQuery.case_id == case_id)
        .order_by(OSINTQuery.created_at.desc())
        .limit(50)
    )
    queries = list(q_result.scalars().all())
    for query in queries:
        r_result = await db.execute(
            select(OSINTResult)
            .where(OSINTResult.query_id == query.id)
            .order_by(OSINTResult.created_at.desc())
            .limit(1)
        )
        latest = r_result.scalar_one_or_none()
        preview = None
        if latest and isinstance(latest.data, dict):
            data = latest.data
            preview = data.get("error") or data.get("message") or (
                f"{len(data.get('data', data.get('results', [])))} items"
                if isinstance(data.get("data") or data.get("results"), list)
                else None
            )
        osint_rows.append(
            {
                "query_id": query.id,
                "query_type": query.query_type,
                "status": str(query.status),
                "result_id": latest.id if latest else None,
                "result_status": latest.status if latest else None,
                "preview": preview,
                "created_at": query.created_at.isoformat() if query.created_at else None,
            }
        )

    ai_result = await db.execute(
        select(AIAnalysis)
        .where(AIAnalysis.case_id == case_id)
        .order_by(AIAnalysis.created_at.desc())
        .limit(30)
    )
    ai_rows = [
        {
            "id": row.id,
            "analysis_type": row.analysis_type,
            "confidence_score": row.confidence_score,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in ai_result.scalars().all()
    ]

    pred_result = await db.execute(
        select(Prediction)
        .where(Prediction.case_id == case_id)
        .order_by(Prediction.created_at.desc())
        .limit(30)
    )
    predictions = [
        {
            "id": row.id,
            "prediction_type": row.prediction_type,
            "confidence_percentage": row.confidence_percentage,
            "predicted_date": row.predicted_date.isoformat() if row.predicted_date else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in pred_result.scalars().all()
    ]

    inq_result = await db.execute(
        select(ProspectiveInquiry)
        .where(ProspectiveInquiry.case_id == case_id)
        .order_by(ProspectiveInquiry.created_at.desc())
        .limit(20)
    )
    inquiries = [
        {
            "id": row.id,
            "question": (row.question or "")[:120],
            "mode": row.mode,
            "status": row.status,
            "run_count": row.run_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in inq_result.scalars().all()
    ]

    return {
        "osint_data": osint_rows,
        "ai_analyses": ai_rows,
        "predictions": predictions,
        "prospective_inquiries": inquiries,
        "counts": {
            "osint_queries": len(osint_rows),
            "ai_analyses": len(ai_rows),
            "predictions": len(predictions),
            "inquiries": len(inquiries),
        },
    }
