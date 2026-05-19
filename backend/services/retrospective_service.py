"""Godet retrospectiva — tendències històriques des d'OSINT per variable."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.osint import OSINTQuery, OSINTResult


def _extract_text(data: dict | None) -> str:
    if not data:
        return ""
    parts = [
        str(data.get("title", "")),
        str(data.get("content", "")),
        str(data.get("text", "")),
        str(data.get("summary", "")),
    ]
    return " ".join(parts)


def _parse_year(data: dict | None) -> int | None:
    if not data:
        return None
    for key in ("date", "published", "published_at", "timestamp"):
        raw = data.get(key)
        if not raw:
            continue
        s = str(raw)
        m = re.search(r"(20\d{2}|19\d{2})", s)
        if m:
            return int(m.group(1))
    return None


def _keywords(var: dict) -> list[str]:
    words: set[str] = set()
    for field in ("name", "desc", "description", "code"):
        text = str(var.get(field, "")).lower()
        for token in re.findall(r"[a-zà-ÿ0-9]{3,}", text):
            words.add(token)
    stop = {"grau", "que", "per", "the", "and", "del", "les", "amb", "una", "uns"}
    return [w for w in words if w not in stop][:12]


def _trend_label(values: list[int]) -> str:
    if len(values) < 2:
        return "estable"
    first_half = sum(values[: len(values) // 2])
    second_half = sum(values[len(values) // 2 :])
    if second_half > first_half * 1.25:
        return "pujant"
    if second_half < first_half * 0.75:
        return "baixant"
    return "estable"


class RetrospectiveService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_trends(self, case_id: int, variables: list[dict]) -> dict[str, Any]:
        current_year = datetime.now().year
        years = list(range(current_year - 9, current_year + 1))

        result = await self.db.execute(
            select(OSINTResult.data)
            .join(OSINTQuery, OSINTResult.query_id == OSINTQuery.id)
            .where(OSINTQuery.case_id == case_id)
        )
        articles = [row[0] for row in result.all() if row[0]]

        var_trends: list[dict] = []
        for var in variables:
            kws = _keywords(var)
            yearly = {y: 0 for y in years}
            for data in articles:
                text = _extract_text(data).lower()
                if not any(kw in text for kw in kws):
                    continue
                year = _parse_year(data) or current_year
                if year in yearly:
                    yearly[year] += 1
            series = [yearly[y] for y in years]
            var_trends.append(
                {
                    "code": var.get("code", ""),
                    "name": var.get("name", ""),
                    "keywords": kws,
                    "yearly": [
                        {"year": y, "mentions": yearly[y], "intensity": min(3, yearly[y])}
                        for y in years
                    ],
                    "total_mentions": sum(series),
                    "trend": _trend_label(series),
                    "micmac_hint": min(3, max(0, sum(series[-3:]) // 2)),
                }
            )

        return {
            "case_id": case_id,
            "period": f"{years[0]}–{years[-1]}",
            "osint_articles": len(articles),
            "variables": var_trends,
        }
