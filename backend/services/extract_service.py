"""
Extract Service - structured extraction from OSINT sources
Pattern: github.com/pranaykotas/china-us-rhetoric
"""
import json
import logging
import re
from collections import Counter
from typing import Any, AsyncGenerator

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.extract import ExtractedStatement
from models.osint import OSINTQuery, OSINTResult
from services.llm_service import LLMService, llm_config_error_message
from services.event_bus_service import get_event_bus

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Analitza aquest article i extreu totes les declaracions fetes per actors (estats, institucions, empreses, individus, aliances) sobre altres actors o sobre situacions geopolítiques, econòmiques o de seguretat.

INCLOU: Declaracions sobre relacions bilaterals o multilaterals, rutes comercials, aliances, sancions, tecnologia, seguretat militar. Coded language: "Occident", "hegemonia", "potències occidentals" = actors específics.

EXCLOU: Declaracions purament domèstiques sense referència estrangera.

Per cada declaració, retorna JSON array amb objectes:
{
  "actor": "Nom",
  "actor_type": "state|institution|company|individual|alliance",
  "actor_importance": 1-5,
  "context": "On/quan",
  "statement": "Declaració o paràfrasi precisa",
  "topic": "Tema en 1-3 paraules",
  "framing": "ofensiu|defensiu|constructiu|amenaçador|conciliador|neutral",
  "posture_toward": "Actor objectiu",
  "posture_value": -2 a +2,
  "tone": "confrontational|assertive|cautious|neutral|cooperative|conciliatory",
  "tone_intensity": 1-5,
  "relevance_signals": ["senyal1","senyal2"]
}

posture_value: +2=molt favorable, +1=favorable, 0=neutral, -1=contrari, -2=molt contrari
Retorna ÚNICAMENT el JSON array. Si no hi ha declaracions rellevants: []

Article:
"""

CLEANUP_PROMPT = """Decideix si aquesta declaració és INTERNACIONAL o DOMÈSTICA.

Actor: {actor}
Declaració: {statement}
Context: {context}
Tema: {topic}
Senyals: {signals}

KEEP si: menciona actor estranger, coded language, competència estrangera implícita.
REMOVE si: política interna pura sense referència estrangera.

Respon ÚNICAMENT: {{"decision": "KEEP" o "REMOVE", "reason": "1 frase"}}"""


def _recover_partial_json(text: str) -> list[dict]:
    text = text.strip()
    if not text.startswith("["):
        return []
    depth = 0
    last_complete = -1
    in_string = False
    escape_next = False
    for i, ch in enumerate(text):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                last_complete = i
    if last_complete == -1:
        return []
    candidate = text[: last_complete + 1] + "]"
    candidate = re.sub(r",\s*\]", "]", candidate)
    try:
        result = json.loads(candidate)
        return result if isinstance(result, list) else []
    except json.JSONDecodeError:
        return []


def _clean_json(text: str) -> str:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    text = text.strip()
    return re.sub(r",\s*([}\]])", r"\1", text)


def _grounding_score(statement: str, source_text: str) -> float:
    stmt_words = set(statement.lower().split())
    if not stmt_words:
        return 0.0
    src_words = set(source_text.lower().split())
    return len(stmt_words & src_words) / len(stmt_words)


def _text_from_osint_data(data: dict) -> str:
    if not isinstance(data, dict):
        return ""
    parts: list[str] = []
    for key in ("text", "content", "description", "title", "summary", "body", "snippet"):
        val = data.get(key)
        if val:
            parts.append(str(val))
    articles = data.get("articles") or data.get("items") or data.get("results")
    if isinstance(articles, list):
        for item in articles[:20]:
            if isinstance(item, dict):
                for key in ("title", "description", "content", "summary", "text"):
                    if item.get(key):
                        parts.append(str(item[key]))
    return " ".join(parts)


class ExtractService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMService(mode="extract")

    async def extract_from_case(self, case_id: int) -> AsyncGenerator[dict[str, Any], None]:
        if not self.llm.configured:
            yield {"event": "error", "message": llm_config_error_message()}
            return

        queries_r = await self.db.execute(select(OSINTQuery).where(OSINTQuery.case_id == case_id))
        queries = list(queries_r.scalars().all())

        items: list[dict[str, Any]] = []
        for q in queries:
            results_r = await self.db.execute(
                select(OSINTResult).where(OSINTResult.query_id == q.id)
            )
            for r in results_r.scalars().all():
                if not r.data:
                    continue
                text = _text_from_osint_data(r.data if isinstance(r.data, dict) else {})
                if len(text.strip()) > 80:
                    url = ""
                    date = ""
                    if isinstance(r.data, dict):
                        url = str(r.data.get("url", "") or "")
                        date = str(r.data.get("date", "") or r.data.get("publishedAt", "") or "")
                    items.append({"id": r.id, "text": text[:6000], "url": url, "date": date})

        total = len(items)
        yield {"event": "start", "total": total}

        total_extracted = 0
        for i, item in enumerate(items):
            yield {"event": "progress", "current": i + 1, "total": total}
            stmts = self._extract_from_text(item["text"])
            for stmt in stmts:
                score = _grounding_score(stmt.get("statement", ""), item["text"])
                obj = ExtractedStatement(
                    case_id=case_id,
                    osint_result_id=item["id"],
                    actor=str(stmt.get("actor", "")),
                    actor_type=str(stmt.get("actor_type", "state")),
                    actor_importance=int(stmt.get("actor_importance", 3)),
                    context=str(stmt.get("context", "")),
                    statement=str(stmt.get("statement", "")),
                    topic=str(stmt.get("topic", "")),
                    framing=str(stmt.get("framing", "neutral")),
                    posture_toward=str(stmt.get("posture_toward", "")),
                    posture_value=max(-2, min(2, int(stmt.get("posture_value", 0)))),
                    tone=str(stmt.get("tone", "neutral")),
                    tone_intensity=int(stmt.get("tone_intensity", 3)),
                    relevance_signals=stmt.get("relevance_signals") or [],
                    grounding_score=score,
                    cleanup_decision="NEEDS_REVIEW" if score < 0.08 else "PENDING",
                    source_url=item.get("url", ""),
                    source_date=item.get("date", ""),
                    source_text_excerpt=item["text"][:500],
                )
                self.db.add(obj)
                total_extracted += 1
            if (i + 1) % 5 == 0:
                await self.db.commit()
                yield {"event": "saved", "count": total_extracted}

        await self.db.commit()

        await get_event_bus().emit(
            {
                "source": "extract_service",
                "detail_type": "extraction.completed",
                "detail": {
                    "case_id": case_id,
                    "total_extracted": total_extracted,
                },
            }
        )

        yield {"event": "done", "total_extracted": total_extracted}

    def _extract_from_text(self, text: str) -> list[dict]:
        if not self.llm.configured or not text.strip():
            return []
        raw_response = ""
        try:
            raw_response = self.llm.complete(EXTRACTION_PROMPT + text, max_tokens=4096)
            raw = _clean_json(raw_response)
            result = json.loads(raw)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            return _recover_partial_json(raw_response)
        except Exception as e:
            logger.error("Extract error: %s", e)
            return []

    async def cleanup_pass(self, case_id: int) -> dict[str, int]:
        if not self.llm.configured:
            return {"kept": 0, "removed": 0, "error": "no api key"}

        pending_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(["PENDING", "NEEDS_REVIEW"]))
        )
        pending = list(pending_r.scalars().all())
        kept = removed = 0

        for stmt in pending:
            if stmt.relevance_signals and len(stmt.relevance_signals) >= 2:
                stmt.cleanup_decision = "KEEP"
                kept += 1
                continue
            prompt = CLEANUP_PROMPT.format(
                actor=stmt.actor,
                statement=stmt.statement[:400],
                context=stmt.context[:200],
                topic=stmt.topic,
                signals=str(stmt.relevance_signals),
            )
            try:
                raw = self.llm.complete(prompt, max_tokens=80)
                result = json.loads(_clean_json(raw))
                stmt.cleanup_decision = result.get("decision", "KEEP")
                stmt.cleanup_reason = result.get("reason", "")
                if stmt.cleanup_decision == "KEEP":
                    kept += 1
                else:
                    removed += 1
            except Exception:
                stmt.cleanup_decision = "KEEP"
                kept += 1

        await self.db.commit()
        return {"kept": kept, "removed": removed}

    async def get_suggested_variables(self, case_id: int) -> list[dict]:
        if not self.llm.configured:
            return []

        stmts_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(["KEEP", "PENDING", "NEEDS_REVIEW"]))
        )
        stmts = list(stmts_r.scalars().all())
        if not stmts:
            return []

        topics = list({s.topic for s in stmts if s.topic})[:20]
        actors = list({s.actor for s in stmts if s.actor})[:15]
        prompt = f"""A partir d'aquests temes i actors extrets de fonts OSINT, proposa 8-12 variables per a una anàlisi MIC-MAC.

Temes: {', '.join(topics)}
Actors principals: {', '.join(actors)}

Retorna ÚNICAMENT un JSON array:
[{{"code":"A","name":"Nom curt","type":"I","desc":"Grau en què..."}}]
type="I" si és intern (accionable), type="E" si és extern (contextual)."""

        try:
            raw = self.llm.complete(prompt, max_tokens=1500)
            result = json.loads(_clean_json(raw))
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.error("Variable suggestion error: %s", e)
            return []

    async def get_suggested_actors(self, case_id: int) -> list[dict]:
        stmts_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(["KEEP", "PENDING", "NEEDS_REVIEW"]))
        )
        stmts = list(stmts_r.scalars().all())
        actor_counts = Counter(s.actor for s in stmts if s.actor)
        suggested: list[dict] = []

        for i, (actor_name, count) in enumerate(actor_counts.most_common(8)):
            actor_stmts = [s for s in stmts if s.actor == actor_name]
            avg_importance = sum(s.actor_importance for s in actor_stmts) / len(actor_stmts)
            suggested.append(
                {
                    "code": chr(65 + i),
                    "name": actor_name,
                    "force": min(5, max(1, round(avg_importance))),
                    "fins": list({s.topic for s in actor_stmts if s.topic})[:3],
                    "statement_count": count,
                }
            )
        return suggested
