"""
Extract Service - structured statement extraction from OSINT data
Pattern: github.com/pranaykotas/china-us-rhetoric/extract.py
Uses Claude Haiku for extraction and cleanup pass.
"""
from __future__ import annotations

import json
import logging
import os
import re
from collections import Counter
from typing import Any, AsyncGenerator

import anthropic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.extract import ExtractedStatement
from models.osint import OSINTQuery, OSINTResult

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """Analitza aquest article i extreu totes les declaracions fetes per actors (estats, institucions, empreses, individus, aliances) sobre altres actors o sobre situacions geopolítiques, econòmiques o de seguretat.

INCLOU:
- Declaracions que expressen postura, demanda, amenaça, oferta o valoració vers un altre actor
- Declaracions sobre relacions bilaterals o multilaterals
- Declaracions sobre rutes comercials, aliances, sancions, tecnologia, seguretat militar
- Declaracions sobre "Occident", "potències occidentals", "hegemonia" — són coded language per a actors específics

EXCLOU:
- Declaracions purament domèstiques (política interna, anticorrupció sense referència estrangera)
- Campanyes ideològiques sense actor estranger explícit o implícit
- Política industrial sense framing de competència o adversari extern

Per cada declaració rellevant, retorna:
- actor: Nom de l'actor que fa la declaració
- actor_type: "state" | "institution" | "company" | "individual" | "alliance"
- actor_importance: 1–5 (5=cap d'estat/òrgan suprem, 4=ministre/gran institució, 3=alt funcionari/general, 2=portaveu/departament secundari, 1=funcionari local/font menor)
- context: On/quan s'ha produït (conferència de premsa, discurs, comunicat, etc.)
- statement: Declaració exacta o paràfrasi precisa
- topic: Tema principal en 1–3 paraules (lliure)
- framing: Com emmarca el tema ("ofensiu" | "defensiu" | "constructiu" | "amenaçador" | "conciliador" | "neutral")
- posture_toward: Nom de l'actor objectiu (a qui va dirigida la postura)
- posture_value: –2 (molt contrari/hostil) a +2 (molt favorable/cooperatiu), 0=neutral
- tone: "confrontational" | "assertive" | "cautious" | "neutral" | "cooperative" | "conciliatory"
- tone_intensity: 1–5 (1=molt suau, 5=molt intens)
- relevance_signals: Array de paraules clau que confirmen la rellevància (ex: ["BRI", "QUAD", "sancions"])

Retorna ÚNICAMENT un array JSON. Si no hi ha declaracions rellevants, retorna [].

Format exacte:
[
  {
    "actor": "Nom",
    "actor_type": "state",
    "actor_importance": 4,
    "context": "Conferència de premsa del MFA",
    "statement": "Declaració o paràfrasi",
    "topic": "relacions bilaterals",
    "framing": "defensiu",
    "posture_toward": "Actor objectiu",
    "posture_value": -1,
    "tone": "assertive",
    "tone_intensity": 3,
    "relevance_signals": ["sancions", "comerç"]
  }
]

Article a analitzar:

"""

CLEANUP_PROMPT = """Revisa si aquesta declaració és INTERNACIONAL (fa referència a actors externs, relacions bilaterals, o competència estrangera implícita) o DOMÈSTICA (política purament interna sense actor estranger).

Declaració: {statement}
Actor: {actor}
Context: {context}
Tema: {topic}
Senyals de rellevància: {signals}

Respon ÚNICAMENT amb JSON:
{{"decision": "KEEP" | "REMOVE", "reason": "Explicació en 1 frase"}}

KEEP si:
- Menciona un actor estranger explícitament
- Usa "Occident", "potències hegemòniques" o similar (coded language)
- El tema (tecnologia, militar, comerç) té un adversari estranger implícit clar

REMOVE si:
- És purament sobre política interna, anticorrupció, objectius domèstics
- No hi ha cap referència ni implícita a actors estrangers
"""


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


def _grounding_score(statement: str, source_text: str) -> float:
    stmt_words = set(statement.lower().split())
    src_words = set(source_text.lower().split())
    if not stmt_words:
        return 0.0
    return len(stmt_words & src_words) / len(stmt_words)


def _clean_json_response(text: str) -> str:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    text = text.strip()
    text = re.sub(r",\s*([}\]])", r"\1", text)
    return text


_CLEAN_DECISIONS_FOR_SUGGESTIONS = ("KEEP", "PENDING", "NEEDS_REVIEW")


class ExtractService:
    def __init__(self, db: AsyncSession):
        self.db = db
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.client = anthropic.Anthropic(api_key=api_key) if api_key else None

    async def extract_from_case(self, case_id: int) -> AsyncGenerator[dict[str, Any], None]:
        if not self.client:
            yield {"event": "error", "message": "ANTHROPIC_API_KEY no configurada"}
            return

        queries_r = await self.db.execute(select(OSINTQuery).where(OSINTQuery.case_id == case_id))
        queries = list(queries_r.scalars().all())

        osint_items: list[dict[str, Any]] = []
        for q in queries:
            results_r = await self.db.execute(select(OSINTResult).where(OSINTResult.query_id == q.id))
            for r in results_r.scalars().all():
                if r.data and isinstance(r.data, dict):
                    text = ""
                    for key in ("text", "content", "description", "title", "summary", "body"):
                        if key in r.data and r.data[key]:
                            text += str(r.data[key]) + "\n"
                    if len(text.strip()) > 80:
                        osint_items.append(
                            {
                                "id": r.id,
                                "text": text[:6000],
                                "url": r.data.get("url", "") or "",
                                "date": str(r.data.get("date", "") or ""),
                            }
                        )

        total = len(osint_items)
        yield {"event": "start", "total": total}

        total_extracted = 0

        for i, item in enumerate(osint_items):
            yield {
                "event": "progress",
                "current": i + 1,
                "total": total,
                "text": f"Processant font {i + 1}/{total}...",
            }

            statements = self._extract_from_text(item["text"])

            for stmt in statements:
                score = _grounding_score(stmt.get("statement", ""), item["text"])
                signals = stmt.get("relevance_signals", [])
                if not isinstance(signals, list):
                    signals = []

                obj = ExtractedStatement(
                    case_id=case_id,
                    osint_result_id=item["id"],
                    actor=stmt.get("actor", "") or "Desconegut",
                    actor_type=stmt.get("actor_type", "state"),
                    actor_importance=int(stmt.get("actor_importance", 3)),
                    context=stmt.get("context", ""),
                    statement=stmt.get("statement", ""),
                    topic=stmt.get("topic", ""),
                    framing=stmt.get("framing", "neutral"),
                    posture_toward=stmt.get("posture_toward", ""),
                    posture_value=int(stmt.get("posture_value", 0)),
                    tone=stmt.get("tone", "neutral"),
                    tone_intensity=int(stmt.get("tone_intensity", 3)),
                    relevance_signals=signals,
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
        yield {"event": "done", "total_extracted": total_extracted}

    def _extract_from_text(self, text: str) -> list[dict]:
        if not self.client or not text.strip():
            return []
        raw_text = ""
        try:
            message = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=4096,
                messages=[{"role": "user", "content": EXTRACTION_PROMPT + text}],
            )
            raw_text = message.content[0].text
            response_text = _clean_json_response(raw_text)
            result = json.loads(response_text)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            recovered = _recover_partial_json(raw_text)
            return recovered
        except Exception as e:
            logger.exception("Extract error: %s", e)
            return []

    async def cleanup_pass(self, case_id: int) -> dict[str, Any]:
        if not self.client:
            return {"error": "no api key"}

        pending_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(["PENDING", "NEEDS_REVIEW"]))
        )
        pending = list(pending_r.scalars().all())

        kept = 0
        removed = 0
        for stmt in pending:
            if stmt.relevance_signals and len(stmt.relevance_signals) >= 2:
                stmt.cleanup_decision = "KEEP"
                kept += 1
                continue

            prompt = CLEANUP_PROMPT.format(
                statement=(stmt.statement or "")[:400],
                actor=stmt.actor,
                context=(stmt.context or "")[:200],
                topic=stmt.topic,
                signals=str(stmt.relevance_signals),
            )
            try:
                message = self.client.messages.create(
                    model="claude-haiku-4-5-20251001",
                    max_tokens=100,
                    messages=[{"role": "user", "content": prompt}],
                )
                decision_raw = _clean_json_response(message.content[0].text)
                result = json.loads(decision_raw)
                stmt.cleanup_decision = result.get("decision", "KEEP")
                stmt.cleanup_reason = result.get("reason", "")
                if stmt.cleanup_decision == "KEEP":
                    kept += 1
                else:
                    removed += 1
            except Exception as e:
                logger.exception("Cleanup error for stmt %s: %s", stmt.id, e)
                stmt.cleanup_decision = "KEEP"
                kept += 1

        await self.db.commit()
        return {"kept": kept, "removed": removed}

    async def get_suggested_variables(self, case_id: int) -> list[dict]:
        stmts_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(
                ExtractedStatement.cleanup_decision.in_(_CLEAN_DECISIONS_FOR_SUGGESTIONS),
            )
        )
        stmts = list(stmts_r.scalars().all())

        if not stmts or not self.client:
            return []

        topics = list({s.topic for s in stmts if s.topic})[:20]
        actors = list({s.actor for s in stmts if s.actor})[:15]

        prompt = f"""A partir d'aquests temes i actors extrets de fonts OSINT, proposa 8–12 variables per a una anàlisi MIC-MAC.

Temes identificats: {', '.join(topics)}
Actors principals: {', '.join(actors)}

Per cada variable, retorna:
- code: Lletra (A, B, C...)
- name: Nom curt (màx 5 paraules)
- type: "I" (interna, accionable) o "E" (externa, contextual)
- desc: Definició operativa que comenci per "Grau en què..."

Retorna ÚNICAMENT un array JSON. Exemple:
[{{"code": "A", "name": "Expansió BRI", "type": "I", "desc": "Grau en què la BRI avança sense resistència significativa"}}]"""

        try:
            message = self.client.messages.create(
                model="claude-haiku-4-5-20251001",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            result = json.loads(_clean_json_response(message.content[0].text))
            return result if isinstance(result, list) else []
        except Exception as e:
            logger.exception("Variable suggestion error: %s", e)
            return []

    async def get_suggested_actors(self, case_id: int) -> list[dict]:
        stmts_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(_CLEAN_DECISIONS_FOR_SUGGESTIONS))
        )
        stmts = list(stmts_r.scalars().all())

        actor_counts = Counter(s.actor for s in stmts if s.actor)
        top_actors = actor_counts.most_common(8)

        suggested = []
        for i, (actor_name, count) in enumerate(top_actors):
            actor_stmts = [s for s in stmts if s.actor == actor_name]
            avg_importance = sum(s.actor_importance for s in actor_stmts) / len(actor_stmts)
            topics = list({s.topic for s in actor_stmts if s.topic})[:3]
            code = chr(65 + i) if i < 26 else f"A{i + 1}"
            suggested.append(
                {
                    "code": code,
                    "name": actor_name,
                    "force": min(5, max(1, round(avg_importance))),
                    "fins": topics,
                    "statement_count": count,
                }
            )
        return suggested

    async def get_suggested_postures(
        self,
        case_id: int,
        actors: list[str],
        objectives: list[str],
    ) -> list[list[int]]:
        stmts_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(_CLEAN_DECISIONS_FOR_SUGGESTIONS))
        )
        stmts = list(stmts_r.scalars().all())

        postures = [[0] * len(objectives) for _ in range(len(actors))]

        for i, actor in enumerate(actors):
            actor_stmts = [s for s in stmts if s.actor == actor]
            for j, obj in enumerate(objectives):
                ol = obj.lower()
                relevant = [
                    s
                    for s in actor_stmts
                    if ol in (s.topic or "").lower() or ol in (s.posture_toward or "").lower()
                ]
                if relevant:
                    avg = sum(s.posture_value for s in relevant) / len(relevant)
                    postures[i][j] = max(-2, min(2, round(avg)))

        return postures
