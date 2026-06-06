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
from models.case import Case, CasePrompt
from models.osint import OSINTQuery, OSINTResult
from services.llm_service import LLMService, llm_config_error_message
from services.event_bus_service import get_event_bus
from services.article_enrichment_service import enrich_osint_items, enrich_single_article
from services.osint_data_utils import flatten_osint_items, osint_has_error, text_from_osint_item
from services.extract_validation import (
    effective_grounding_score,
    grounding_score,
    has_international_signal,
    is_verifiable_source,
    needs_llm_cleanup,
    validate_statements,
    GROUNDING_REVIEW_THRESHOLD,
    GROUNDING_THRESHOLD,
)
from schemas.analysis_scope import AnalysisScope
from services.case_topic_relevance import (
    CaseTopicProfile,
    build_case_topic_profile,
    is_article_on_topic,
    is_statement_on_topic,
    score_statement_relevance,
)
from app.config import settings

logger = logging.getLogger(__name__)


def _typology_fields(stmt: dict[str, Any]) -> dict[str, str | None]:
    from schemas.actor_typology import (
        classify_signal_type,
        infer_institution_subtype,
        normalize_actor_class,
    )

    actor = str(stmt.get("actor", ""))
    actor_type = normalize_actor_class(str(stmt.get("actor_type", "state")))
    inst_raw = stmt.get("institution_subtype")
    inst = str(inst_raw).strip() if inst_raw else infer_institution_subtype(actor, actor_type)
    sig_raw = stmt.get("signal_type")
    sig = str(sig_raw).strip() if sig_raw else classify_signal_type(
        str(stmt.get("statement", "")),
        str(stmt.get("topic", "")),
        actor_type,
    )
    return {"actor_type": actor_type, "institution_subtype": inst, "signal_type": sig}


EXTRACTION_PROMPT_BASE = """Analitza aquest article i extreu totes les declaracions fetes per actors (estats, institucions, empreses, individus, aliances) sobre altres actors o sobre situacions geopolítiques, econòmiques o de seguretat.

INCLOU: Declaracions sobre relacions bilaterals o multilaterals, rutes comercials, aliances, sancions, tecnologia, seguretat militar. Coded language: "Occident", "hegemonia", "potències occidentals" = actors específics.

EXCLOU: Declaracions purament domèstiques sense referència estrangera.

Per cada declaració, retorna JSON array amb objectes:
{
  "actor": "Nom",
  "actor_type": "state|institution|company|individual|alliance|multilateral",
  "institution_subtype": "government|ministry|multilateral_org|defense_agency|think_tank|trade_agency|ngo|regulator|political_party|financial_institution|corporate|unknown",
  "actor_importance": 1-5,
  "context": "On/quan",
  "statement": "Declaració o paràfrasi precisa",
  "source_quote": "Cita literal de l'article (15-40 paraules) que sustenta la declaració",
  "topic": "Tema en 1-3 paraules",
  "signal_type": "structural|episodic (opcional; structural=canvi de règim/política; episodic=esdeveniment puntual)",
  "framing": "ofensiu|defensiu|constructiu|amenaçador|conciliador|neutral",
  "posture_toward": "Actor objectiu",
  "posture_value": -2 a +2,
  "date": "Data aproximada de la declaració (YYYY-MM o YYYY-MM-DD si és coneguda)",
  "tone": "confrontational|assertive|cautious|neutral|cooperative|conciliatory",
  "tone_intensity": 1-5,
  "relevance_signals": ["senyal1","senyal2"]
}

REGLES CRÍTIQUES:
- NOMÉS extreu declaracions explícites o clarament paràfraseables des de l'article.
- NO inferis postures d'actors que no apareixen al text.
- Si no hi ha cita verificable, NO incloguis la declaració.
- source_quote ha de ser text literal copiat de l'article.
- Si l'article NO tracta del focus del cas indicat a sota, retorna [].

posture_value: +2=molt favorable, +1=favorable, 0=neutral, -1=contrari, -2=molt contrari
Retorna ÚNICAMENT el JSON array. Si no hi ha declaracions rellevants: []
"""

EXTRACTION_PROMPT = EXTRACTION_PROMPT_BASE + "\nArticle:\n"


def _build_extraction_prompt(profile: CaseTopicProfile | None) -> str:
    if not profile or not profile.raw_text.strip():
        return EXTRACTION_PROMPT
    themes = ", ".join(sorted(profile.themes)) if profile.themes else "focus del cas"
    geos = ", ".join(sorted(profile.primary_geos)[:6]) if profile.primary_geos else "—"
    focus_block = f"""
FOCUS DEL CAS — NOMÉS declaracions rellevants per:
«{profile.focus_label}»
Context: {profile.raw_text[:450]}
Geografia / actors clau: {geos}
Temes: {themes}
EXCLOU declaracions d'articles sobre altres crisis o regions no vinculades (p.ex. Iran/Hormuz, Vaticà, política domèstica EUA) si el cas no hi fa referència.
"""
    return EXTRACTION_PROMPT_BASE + focus_block + "\nArticle:\n"

CLEANUP_PROMPT = """Decideix si aquesta declaració és rellevant per al CAS i INTERNACIONAL.

FOCUS DEL CAS: {case_focus}

Actor: {actor}
Declaració: {statement}
Context: {context}
Tema: {topic}
Senyals: {signals}

KEEP si: rellevant per al focus del cas I (menciona actor estranger, seguretat regional, aliances, sancions, etc.).
REMOVE si: fora del focus temàtic del cas (encara que sigui internacional) O política interna pura sense referència estrangera.

Respon ÚNICAMENT: {{"decision": "KEEP" o "REMOVE", "reason": "1 frase"}}"""

CLEANUP_BATCH_PROMPT = """Classifica cada declaració com INTERNACIONAL (KEEP) o DOMÈSTICA (REMOVE).

INTERNACIONAL: menciona actor estranger, relacions bilaterals/multilaterals, seguretat regional,
sancions, aliances, coded language (Occident, hegemonia, potències occidentals).
DOMÈSTICA: política interna pura sense referència estrangera.

Retorna ÚNICAMENT un JSON array, mateix ordre:
[{{"decision": "KEEP" o "REMOVE", "reason": "1 frase"}}]

Declaracions:
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


def _clean_json(text: str) -> str:
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    text = text.strip()
    return re.sub(r",\s*([}\]])", r"\1", text)


def _format_source_date(date_val: str) -> str:
    if not date_val:
        return ""
    if date_val.isdigit():
        from datetime import datetime, timezone
        return datetime.fromtimestamp(int(date_val), tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    return date_val


def _coerce_article_url(article: dict[str, Any]) -> str:
    """Best-effort URL from normalized OSINT article fields."""
    url = str(article.get("url") or "").strip()
    if url:
        return url
    source = str(article.get("source") or "").strip()
    if source.startswith("http://") or source.startswith("https://"):
        return source
    if source and "." in source and " " not in source:
        return f"https://{source.lstrip('/')}"
    return ""


def _decide_cleanup(
    *,
    statement_text: str,
    context_text: str,
    topic_text: str,
    source_text: str,
    source_url: str,
    score: float | None,
    profile: CaseTopicProfile | None = None,
) -> tuple[str, str]:
    if profile and source_url and not source_url.startswith("direct-analysis:"):
        rel = score_statement_relevance(
            statement=statement_text,
            actor="",
            topic=topic_text,
            context=context_text,
            profile=profile,
        )
        min_rel = float(getattr(settings, "CASE_STATEMENT_RELEVANCE_MIN_SCORE", 0.22))
        if rel["score"] < min_rel:
            return "REMOVE", f"Fora del focus del cas «{profile.focus_label}» (rellevància {rel['score']:.2f})"

    verified = is_verifiable_source(source_url, source_text)
    if not verified:
        return "UNVERIFIED", "Sense URL o text font verificable"
    if score is None or score < GROUNDING_THRESHOLD:
        return "NEEDS_REVIEW", "Grounding baix respecte al text font"
    if has_international_signal(statement_text, context_text, topic_text, source_text):
        return "KEEP", "Senyal internacional detectada (regex)"
    if score < GROUNDING_REVIEW_THRESHOLD:
        return "NEEDS_REVIEW", ""
    return "PENDING", ""


class ExtractService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = LLMService(mode="extract")
        self._case_profile: CaseTopicProfile | None = None
        self._inquiry_scope = None

    async def _load_case_profile(self, case_id: int) -> CaseTopicProfile:
        case_r = await self.db.execute(select(Case).where(Case.id == case_id))
        case = case_r.scalar_one_or_none()
        if not case:
            return build_case_topic_profile("", "")

        prompt_r = await self.db.execute(
            select(CasePrompt)
            .where(CasePrompt.case_id == case_id)
            .order_by(CasePrompt.created_at.desc())
            .limit(1)
        )
        prompt = prompt_r.scalar_one_or_none()
        extra = ""
        if prompt and prompt.prompt:
            extra = prompt.prompt[:800]

        return build_case_topic_profile(
            case.name or "",
            case.description or "",
            extra,
        )

    async def extract_from_case(
        self,
        case_id: int,
        *,
        apply_scope: bool = False,
        scope: AnalysisScope | None = None,
    ) -> AsyncGenerator[dict[str, Any], None]:
        if not self.llm.configured:
            yield {"event": "error", "message": llm_config_error_message()}
            return

        self._case_profile = await self._load_case_profile(case_id)
        min_article_score = float(getattr(settings, "CASE_ARTICLE_RELEVANCE_MIN_SCORE", 0.28))

        from services.analysis_scope_service import load_active_inquiry_scope, resolve_scope_for_case

        self._inquiry_scope = await load_active_inquiry_scope(self.db, case_id)

        if apply_scope and scope is None:
            scope, inq = await resolve_scope_for_case(self.db, case_id)
            if inq:
                self._inquiry_scope = inq
        elif not apply_scope:
            from services.analysis_scope_service import should_auto_apply_scope

            if await should_auto_apply_scope(self.db, case_id):
                apply_scope = True
                scope, inq = await resolve_scope_for_case(self.db, case_id)
                if inq:
                    self._inquiry_scope = inq

        use_topic_filter = True
        if apply_scope and scope is not None:
            use_topic_filter = bool(scope.apply_topic_filter)
            if scope.min_relevance is not None:
                min_article_score = float(scope.min_relevance)

        from services.analysis_scope_service import (
            _article_in_date_range,
            _article_matches_domain,
        )

        queries_r = await self.db.execute(select(OSINTQuery).where(OSINTQuery.case_id == case_id))
        queries = list(queries_r.scalars().all())

        existing_urls_r = await self.db.execute(
            select(ExtractedStatement.source_url).where(
                ExtractedStatement.case_id == case_id,
                ExtractedStatement.source_url != "",
            )
        )
        already_extracted_urls = {row[0] for row in existing_urls_r.all() if row[0]}

        items: list[dict[str, Any]] = []
        skipped = 0
        skipped_off_topic = 0
        skipped_scope = 0
        for q in queries:
            results_r = await self.db.execute(
                select(OSINTResult).where(OSINTResult.query_id == q.id)
            )
            for r in results_r.scalars().all():
                if not r.data or not isinstance(r.data, dict):
                    continue
                if osint_has_error(r.data) or r.status == "error":
                    continue

                for article in flatten_osint_items(r.data):
                    url = _coerce_article_url(article)
                    if url and url in already_extracted_urls:
                        skipped += 1
                        continue
                    text = text_from_osint_item(article)
                    if len(text.strip()) < 80 and not url:
                        continue
                    date = _format_source_date(str(article.get("date") or ""))
                    title = str(article.get("title") or "")
                    body = text[:6000] if text else title

                    if apply_scope and scope:
                        art_for_scope = {
                            **article,
                            "published_date": date,
                            "title": title,
                            "url": url,
                        }
                        if scope.domains and not _article_matches_domain(art_for_scope, scope.domains):
                            skipped_scope += 1
                            continue
                        if not _article_in_date_range(art_for_scope, scope):
                            skipped_scope += 1
                            continue

                    if use_topic_filter and (self._case_profile or self._inquiry_scope):
                        if self._inquiry_scope:
                            from services.inquiry_scope import is_article_in_inquiry_scope

                            if not is_article_in_inquiry_scope(
                                body,
                                title,
                                inquiry=self._inquiry_scope,
                                min_score=min_article_score,
                            ):
                                skipped_off_topic += 1
                                continue
                        elif not is_article_on_topic(
                            body,
                            title,
                            self._case_profile,
                            min_score=min_article_score,
                        ):
                            skipped_off_topic += 1
                            continue
                    frontpage_score = float(
                        article.get("frontpage_score")
                        or article.get("importance_score")
                        or 0
                    )
                    items.append(
                        {
                            "id": r.id,
                            "text": text[:6000] if text else title,
                            "url": url,
                            "date": date,
                            "title": title,
                            "frontpage_score": frontpage_score,
                            "raw_article": article,
                        }
                    )

        if items:
            short_items = [
                it["raw_article"]
                for it in items
                if len(it.get("text", "").strip()) < 200
            ]
            if short_items:
                short_items.sort(
                    key=lambda a: -float(
                        a.get("frontpage_score") or a.get("importance_score") or 0
                    )
                )
                enriched = await enrich_osint_items(short_items)
                enriched_by_url = {
                    str(a.get("url") or ""): a for a in enriched if a.get("url")
                }
                for it in items:
                    url = it.get("url") or ""
                    if url and url in enriched_by_url:
                        ea = enriched_by_url[url]
                        text = text_from_osint_item(ea)
                        if text:
                            title = str(it.get("title") or ea.get("title") or "")
                            if title and title not in text:
                                text = f"{title}. {text}"
                            it["text"] = text[:6000]

        items = [it for it in items if len(it.get("text", "").strip()) >= 80]
        items.sort(
            key=lambda it: (-float(it.get("frontpage_score") or 0), -len(it.get("text") or ""))
        )

        for it in items:
            it.pop("raw_article", None)

        total = len(items)
        yield {
            "event": "start",
            "total": total,
            "skipped_existing": skipped,
            "skipped_off_topic": skipped_off_topic,
            "skipped_scope": skipped_scope,
            "apply_scope": apply_scope,
            "case_focus": self._case_profile.focus_label if self._case_profile else "",
        }

        total_extracted = 0
        for i, item in enumerate(items):
            yield {"event": "progress", "current": i + 1, "total": total}
            stmts = await self._extract_from_text(item["text"])
            for stmt in stmts:
                source_quote = str(stmt.get("source_quote") or "").strip()
                excerpt = source_quote if len(source_quote) >= 20 else item["text"][:500]
                score = effective_grounding_score(
                    str(stmt.get("statement", "")),
                    excerpt,
                    grounding_score(str(stmt.get("statement", "")), excerpt),
                )
                stmt_date = stmt.get("date", "")
                source_date = stmt_date if stmt_date else item.get("date", "")
                statement_text = str(stmt.get("statement", ""))
                context_text = str(stmt.get("context", "") or item.get("title", ""))
                topic_text = str(stmt.get("topic", ""))
                signals = stmt.get("relevance_signals") or []
                source_url = str(item.get("url") or "")

                cleanup_decision, cleanup_reason = _decide_cleanup(
                    statement_text=statement_text,
                    context_text=context_text,
                    topic_text=topic_text,
                    source_text=excerpt,
                    source_url=source_url,
                    score=score,
                    profile=self._case_profile,
                )

                typology = _typology_fields(stmt)
                obj = ExtractedStatement(
                    case_id=case_id,
                    osint_result_id=item["id"],
                    actor=str(stmt.get("actor", "")),
                    actor_type=typology["actor_type"] or "state",
                    institution_subtype=typology["institution_subtype"],
                    signal_type=typology["signal_type"],
                    actor_importance=int(stmt.get("actor_importance", 3)),
                    context=context_text,
                    statement=statement_text,
                    topic=topic_text,
                    framing=str(stmt.get("framing", "neutral")),
                    posture_toward=str(stmt.get("posture_toward", "")),
                    posture_value=max(-2, min(2, int(stmt.get("posture_value", 0)))),
                    tone=str(stmt.get("tone", "neutral")),
                    tone_intensity=int(stmt.get("tone_intensity", 3)),
                    relevance_signals=signals,
                    grounding_score=score,
                    cleanup_decision=cleanup_decision,
                    cleanup_reason=cleanup_reason,
                    source_url=source_url,
                    source_date=source_date,
                    source_text_excerpt=excerpt[:500],
                )
                self.db.add(obj)
                total_extracted += 1
            if (i + 1) % 5 == 0:
                await self.db.commit()
                yield {"event": "saved", "count": total_extracted}

        await self.db.commit()

        stmts_r = await self.db.execute(
            select(ExtractedStatement).where(ExtractedStatement.case_id == case_id)
        )
        validation = validate_statements(list(stmts_r.scalars().all()))

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

        yield {"event": "done", "total_extracted": total_extracted, "validation": validation, "skipped_off_topic": skipped_off_topic}

    async def _extract_from_text(self, text: str) -> list[dict]:
        if not self.llm.configured or not text.strip():
            return []
        raw_response = ""
        prompt = _build_extraction_prompt(self._case_profile)
        try:
            raw_response = await self.llm.acomplete(prompt + text, max_tokens=4096)
            raw = _clean_json(raw_response)
            result = json.loads(raw)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            return _recover_partial_json(raw_response)
        except Exception as e:
            logger.error("Extract error: %s", e)
            return []

    async def extract_single_article(
        self,
        case_id: int,
        *,
        title: str,
        url: str,
        date: str,
        text: str,
    ) -> dict[str, Any]:
        """Extract statements from one OSINT article (e.g. triggered alert match)."""
        from services.extract_validation import has_international_signal, validate_statements

        if url:
            dup_r = await self.db.execute(
                select(ExtractedStatement.id).where(
                    ExtractedStatement.case_id == case_id,
                    ExtractedStatement.source_url == url,
                ).limit(1)
            )
            if dup_r.scalar_one_or_none():
                return {
                    "statements_created": 0,
                    "statement_id": None,
                    "statements": [],
                    "skipped": "already_extracted",
                }

        body = text.strip()
        if title and title not in body:
            body = f"{title}. {body}"

        profile = await self._load_case_profile(case_id)
        self._case_profile = profile
        min_article = float(getattr(settings, "CASE_ARTICLE_RELEVANCE_MIN_SCORE", 0.28))
        if not is_article_on_topic(body, title, profile, min_score=min_article):
            return {
                "statements_created": 0,
                "statement_id": None,
                "statements": [],
                "skipped": "off_topic",
            }

        if url or body:
            enriched_item = await enrich_single_article(
                {"title": title, "url": url, "summary": body, "body": body}
            )
            body = text_from_osint_item(enriched_item)
            if title and title not in body:
                body = f"{title}. {body}"

        stmts = await self._extract_from_text(body[:6000])
        created_ids: list[int] = []
        preview: list[dict[str, Any]] = []

        for stmt in stmts:
            source_quote = str(stmt.get("source_quote") or "").strip()
            excerpt = source_quote if len(source_quote) >= 20 else body[:500]
            score = effective_grounding_score(
                str(stmt.get("statement", "")),
                excerpt,
                grounding_score(str(stmt.get("statement", "")), excerpt),
            )
            statement_text = str(stmt.get("statement", ""))
            context_text = str(stmt.get("context", "") or title)
            topic_text = str(stmt.get("topic", ""))

            cleanup_decision, cleanup_reason = _decide_cleanup(
                statement_text=statement_text,
                context_text=context_text,
                topic_text=topic_text,
                source_text=excerpt,
                source_url=url,
                score=score,
                profile=profile,
            )

            typology = _typology_fields(stmt)
            obj = ExtractedStatement(
                case_id=case_id,
                actor=str(stmt.get("actor", "")),
                actor_type=typology["actor_type"] or "state",
                institution_subtype=typology["institution_subtype"],
                signal_type=typology["signal_type"],
                actor_importance=int(stmt.get("actor_importance", 3)),
                context=context_text,
                statement=statement_text,
                topic=topic_text,
                framing=str(stmt.get("framing", "neutral")),
                posture_toward=str(stmt.get("posture_toward", "")),
                posture_value=max(-2, min(2, int(stmt.get("posture_value", 0)))),
                tone=str(stmt.get("tone", "neutral")),
                tone_intensity=int(stmt.get("tone_intensity", 3)),
                relevance_signals=stmt.get("relevance_signals") or [],
                grounding_score=score,
                cleanup_decision=cleanup_decision,
                cleanup_reason=cleanup_reason,
                source_url=url,
                source_date=date,
                source_text_excerpt=excerpt[:500],
            )
            self.db.add(obj)
            await self.db.flush()
            created_ids.append(obj.id)
            preview.append({
                "id": obj.id,
                "actor": obj.actor,
                "statement": obj.statement[:200],
                "posture_value": obj.posture_value,
            })

        await self.db.commit()
        return {
            "statements_created": len(created_ids),
            "statement_id": created_ids[0] if created_ids else None,
            "statements": preview,
        }

    async def cleanup_pass(self, case_id: int, batch_size: int = 12) -> dict[str, int]:
        if not self.llm.configured:
            return {"kept": 0, "removed": 0, "error": "no api key"}

        profile = await self._load_case_profile(case_id)
        case_focus = profile.focus_label if profile else "cas"

        pending_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(["PENDING", "NEEDS_REVIEW"]))
        )
        pending = list(pending_r.scalars().all())
        kept = removed = auto_kept = 0

        llm_candidates = [s for s in pending if needs_llm_cleanup(s)]
        for stmt in pending:
            if not needs_llm_cleanup(stmt):
                stmt.cleanup_decision = "KEEP"
                stmt.cleanup_reason = stmt.cleanup_reason or "Senyal internacional (pre-filtre)"
                auto_kept += 1
                kept += 1

        for start in range(0, len(llm_candidates), batch_size):
            batch = llm_candidates[start : start + batch_size]
            if len(batch) == 1:
                stmt = batch[0]
                prompt = CLEANUP_PROMPT.format(
                    case_focus=case_focus,
                    actor=stmt.actor,
                    statement=stmt.statement[:400],
                    context=stmt.context[:200],
                    topic=stmt.topic,
                    signals=str(stmt.relevance_signals),
                )
                try:
                    raw = await self.llm.acomplete(prompt, max_tokens=80)
                    result = json.loads(_clean_json(raw))
                    stmt.cleanup_decision = result.get("decision", "KEEP")
                    stmt.cleanup_reason = result.get("reason", "")
                except Exception:
                    stmt.cleanup_decision = "KEEP"
                    stmt.cleanup_reason = "Error classificació — conservat per defecte"
                if stmt.cleanup_decision == "KEEP":
                    kept += 1
                else:
                    removed += 1
                continue

            items_text = "\n\n".join(
                f"{i + 1}. Actor: {s.actor}\n   Declaració: {s.statement[:300]}\n"
                f"   Context: {s.context[:120]}\n   Tema: {s.topic}"
                for i, s in enumerate(batch)
            )
            try:
                raw = await self.llm.acomplete(CLEANUP_BATCH_PROMPT + items_text, max_tokens=800)
                results = json.loads(_clean_json(raw))
                if isinstance(results, list) and len(results) == len(batch):
                    for stmt, result in zip(batch, results):
                        stmt.cleanup_decision = result.get("decision", "KEEP")
                        stmt.cleanup_reason = result.get("reason", "")
                        if stmt.cleanup_decision == "KEEP":
                            kept += 1
                        else:
                            removed += 1
                    continue
            except Exception as e:
                logger.warning("Batch cleanup fallit, fallback individual: %s", e)

            for stmt in batch:
                prompt = CLEANUP_PROMPT.format(
                    case_focus=case_focus,
                    actor=stmt.actor,
                    statement=stmt.statement[:400],
                    context=stmt.context[:200],
                    topic=stmt.topic,
                    signals=str(stmt.relevance_signals),
                )
                try:
                    raw = await self.llm.acomplete(prompt, max_tokens=80)
                    result = json.loads(_clean_json(raw))
                    stmt.cleanup_decision = result.get("decision", "KEEP")
                    stmt.cleanup_reason = result.get("reason", "")
                except Exception:
                    stmt.cleanup_decision = "KEEP"
                if stmt.cleanup_decision == "KEEP":
                    kept += 1
                else:
                    removed += 1

        await self.db.commit()
        return {"kept": kept, "removed": removed, "auto_kept_regex": auto_kept}

    async def reclassify_case_relevance(self, case_id: int) -> dict[str, Any]:
        """Mark existing statements as REMOVE when off-topic for the case focus."""
        profile = await self._load_case_profile(case_id)
        min_rel = float(getattr(settings, "CASE_STATEMENT_RELEVANCE_MIN_SCORE", 0.22))
        stmts_r = await self.db.execute(
            select(ExtractedStatement).where(ExtractedStatement.case_id == case_id)
        )
        removed = 0
        kept = 0
        for stmt in stmts_r.scalars().all():
            url = (stmt.source_url or "").strip()
            if url.startswith("direct-analysis:"):
                kept += 1
                continue
            if stmt.cleanup_decision == "REMOVE":
                removed += 1
                continue
            rel = score_statement_relevance(
                statement=stmt.statement or "",
                actor=stmt.actor or "",
                topic=stmt.topic or "",
                context=stmt.context or "",
                profile=profile,
            )
            if rel["score"] < min_rel:
                stmt.cleanup_decision = "REMOVE"
                stmt.cleanup_reason = (
                    f"Fora del focus «{profile.focus_label}» (rellevància {rel['score']:.2f})"
                )
                removed += 1
            else:
                kept += 1
        await self.db.commit()
        return {
            "case_focus": profile.focus_label,
            "kept": kept,
            "removed": removed,
            "min_score": min_rel,
        }

    async def validate_case(self, case_id: int) -> dict[str, Any]:
        stmts_r = await self.db.execute(
            select(ExtractedStatement).where(ExtractedStatement.case_id == case_id)
        )
        return validate_statements(list(stmts_r.scalars().all()))

    async def get_suggested_variables(self, case_id: int) -> list[dict]:
        if not self.llm.configured:
            return []

        stmts_r = await self.db.execute(
            select(ExtractedStatement)
            .where(ExtractedStatement.case_id == case_id)
            .where(ExtractedStatement.cleanup_decision.in_(["KEEP", "PENDING", "NEEDS_REVIEW", "UNVERIFIED"]))
        )
        stmts = list(stmts_r.scalars().all())
        if not stmts:
            return []

        topics = list({s.topic for s in stmts if s.topic})[:20]
        actors = list({s.actor for s in stmts if s.actor})[:15]
        await self.db.commit()
        prompt = f"""A partir d'aquests temes i actors extrets de fonts OSINT, proposa 8-12 variables per a una anàlisi MIC-MAC.

Temes: {', '.join(topics)}
Actors principals: {', '.join(actors)}

Retorna ÚNICAMENT un JSON array:
[{{"code":"A","name":"Nom curt","type":"I","desc":"Grau en què..."}}]
type="I" si és intern (accionable), type="E" si és extern (contextual)."""

        try:
            raw = await self.llm.acomplete(prompt, max_tokens=1500)
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
