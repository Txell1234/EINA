"""
Reasoning framework CRUD, seeding, LLM generation and prompt building.
"""
from __future__ import annotations

import json
import logging
import re
from copy import deepcopy
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.qualitative import ReasoningFramework, ReasoningFrameworkType

logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_SECTIONS = [
    {
        "key": "conclusions",
        "label": "Conclusions",
        "instruction": "Síntesi analítica estructurada segons el marc.",
    },
    {
        "key": "evidence",
        "label": "Evidència",
        "instruction": "Llista d'elements probatoris amb font i rellevància.",
    },
    {
        "key": "hypotheses",
        "label": "Hipòtesis",
        "instruction": "Hipòtesis operatives derivades del raonament.",
    },
    {
        "key": "uncertainties",
        "label": "Incerteses i límits",
        "instruction": "Buits d'informació, contradiccions i riscos d'interpretació.",
    },
]

BUILTIN_FRAMEWORKS: list[dict[str, Any]] = [
    {
        "name": "Deductive",
        "framework_type": ReasoningFrameworkType.DEDUCTIVE,
        "description": "Raonament des de principis generals a conclusions específiques",
        "definition": {
            "doctrine": "El coneixement válid es deriva de premisses generals verificables cap a conclusions particulars.",
            "epistemology": "Racionalisme aplicat: si les premisses són certes i la lògica és vàlida, la conclusió és necessària.",
            "ontology": "Fets observables com a instàncies de patrons o principis generals.",
            "methodology": "Identificar premisses majors i menors, aplicar regles lògiques, verificar validesa deductiva.",
            "analysis_steps": [
                {"order": 1, "title": "Premisses", "instruction": "Explicita principis, marcs normatius i supòsits.", "llm_hint": "Llista premisses classificades com a major/minor."},
                {"order": 2, "title": "Encadenament lògic", "instruction": "Deriva conclusions pas a pas sense saltar inferències.", "llm_hint": "Cada pas ha de referenciar la premissa anterior."},
                {"order": 3, "title": "Validació", "instruction": "Comprova coherència interna i contradiccions.", "llm_hint": "Senyala fallades lògiques o premisses febles."},
            ],
            "evidence_criteria": ["Coherència lògica", "Premisses verificables", "Absència de contradiccions internes"],
            "bias_checks": ["Confirmació de premisses prèvies", "Generalització indeguda"],
            "limitations": "No genera coneixement nou; depèn de la qualitat de les premisses.",
            "output_sections": DEFAULT_OUTPUT_SECTIONS,
            "application_notes": "Ideal per avaluar polítiques, compliment normatiu i implicacions directes.",
            "tags": ["lògica", "política", "normatiu"],
            "auto_apply": True,
        },
    },
    {
        "name": "Inductive",
        "framework_type": ReasoningFrameworkType.INDUCTIVE,
        "description": "Inferències basades en l'observació de patrons i tendències",
        "definition": {
            "doctrine": "Les regularitats observades permeten inferir patrons generals amb grau de confiança variable.",
            "epistemology": "Empirisme: el coneixement general s'extrau de mostres observables.",
            "ontology": "El món presenta patrons repetitius detectables en dades OSINT.",
            "methodology": "Recollir casos, codificar variables, detectar correlacions i tendències, generalitzar amb cautela.",
            "analysis_steps": [
                {"order": 1, "title": "Observacions", "instruction": "Inventaria fets i dades del cas.", "llm_hint": "Agrupa per tema, actor i temporalitat."},
                {"order": 2, "title": "Patrons", "instruction": "Identifica recurrències, anomalies i tendències.", "llm_hint": "Quantifica quan sigui possible."},
                {"order": 3, "title": "Generalització", "instruction": "Formula regles generals amb nivell de confiança.", "llm_hint": "Indica mida mostral i representativitat."},
            ],
            "evidence_criteria": ["Repetició en fonts independents", "Consistència temporal", "Diversitat de fonts"],
            "bias_checks": ["Mostra petita", "Survivorship bias", "Correlació ≠ causalitat"],
            "limitations": "Les generalitzacions poden quedar invalidades per nous casos.",
            "output_sections": DEFAULT_OUTPUT_SECTIONS,
            "application_notes": "Útil per tendències mediàtiques, narrativa pública i senyals febles.",
            "tags": ["patrons", "tendències", "OSINT"],
            "auto_apply": True,
        },
    },
    {
        "name": "Abductive",
        "framework_type": ReasoningFrameworkType.ABDUCTIVE,
        "description": "Generació d'hipòtesis més probables a partir d'informació incompleta",
        "definition": {
            "doctrine": "Davant dades incompletes, la millor explicació és la que maximitza plausibilitat i parsimònia.",
            "epistemology": "Inferència a la millor explicació (IBE).",
            "ontology": "Fets parcials que admeten múltiples interpretacions competitives.",
            "methodology": "Generar hipòtesis alternatives, comparar-los per plausibilitat, seleccionar la millor explicació.",
            "analysis_steps": [
                {"order": 1, "title": "Fets sorprenents", "instruction": "Què cal explicar? Què no encaixa amb el model habitual?", "llm_hint": "Separa fets de interpretacions."},
                {"order": 2, "title": "Hipòtesis competitives", "instruction": "Genera almenys 3 explicacions plausibles.", "llm_hint": "Inclou explicació conservadora i explicació disruptiva."},
                {"order": 3, "title": "Selecció", "instruction": "Compara per parsimònia, poder explicatiu i falsabilitat.", "llm_hint": "Justifica per què es descarten alternatives."},
            ],
            "evidence_criteria": ["Poder explicatiu", "Parsimònia", "Compatibilitat amb fonts creïbles"],
            "bias_checks": ["Narrativa única", "Ignorar alternatives", "Overfitting explicatiu"],
            "limitations": "La millor explicació no implica veritat; cal verificació posterior.",
            "output_sections": DEFAULT_OUTPUT_SECTIONS,
            "application_notes": "Ideal per intel·ligència anticipatòria i escenaris amb alta incertesa.",
            "tags": ["hipòtesis", "incertesa", "intel·ligència"],
            "auto_apply": True,
        },
    },
    {
        "name": "Causal",
        "framework_type": ReasoningFrameworkType.CAUSAL,
        "description": "Identificació de relacions de causa i efecte entre variables",
        "definition": {
            "doctrine": "Entendre el món requereix identificar mecanismes causals, no només correlacions.",
            "epistemology": "Realisme causal: els esdeveniments tenen drivers identificables.",
            "ontology": "Variables i actors en xarxes d'influència mútua.",
            "methodology": "Mapa causal, identificació de drivers, mediadors, moderadors i feedback loops.",
            "analysis_steps": [
                {"order": 1, "title": "Mapa causal", "instruction": "Identifica causes, efectes i variables intermèdies.", "llm_hint": "Diferencia causa necessària, suficient i contribuent."},
                {"order": 2, "title": "Mecanismes", "instruction": "Explica com A produeix B (cadena causal).", "llm_hint": "Inclou actors i incentius."},
                {"order": 3, "title": "Impacte", "instruction": "Estima magnitud, temporalitat i reversibilitat.", "llm_hint": "Senyala efectes de segona i tercera ordre."},
            ],
            "evidence_criteria": ["Temporalitat correcta", "Mecanisme plausible", "Coherència amb context"],
            "bias_checks": ["Post hoc ergo propter hoc", "Confounding", "Causalitat inversada"],
            "limitations": "En OSINT sovint només es tenen correlacions observables.",
            "output_sections": DEFAULT_OUTPUT_SECTIONS,
            "application_notes": "Útil per anàlisi geopolític, risc sistèmic i impacte de polítiques.",
            "tags": ["causalitat", "impacte", "geopolítica"],
            "auto_apply": True,
        },
    },
]


def empty_definition() -> dict[str, Any]:
    return {
        "doctrine": "",
        "epistemology": "",
        "ontology": "",
        "methodology": "",
        "analysis_steps": [],
        "evidence_criteria": [],
        "bias_checks": [],
        "limitations": "",
        "output_sections": deepcopy(DEFAULT_OUTPUT_SECTIONS),
        "system_prompt_override": "",
        "application_notes": "",
        "tags": [],
        "auto_apply": True,
    }


def framework_to_dict(fw: ReasoningFramework) -> dict[str, Any]:
    return {
        "id": fw.id,
        "name": fw.name,
        "framework_type": fw.framework_type.value if hasattr(fw.framework_type, "value") else str(fw.framework_type),
        "description": fw.description,
        "definition": fw.definition or empty_definition(),
        "is_custom": bool(fw.is_custom),
        "user_id": fw.user_id,
        "is_active": bool(fw.is_active),
        "created_at": fw.created_at,
        "updated_at": fw.updated_at,
    }


def build_system_prompt(
    framework_name: str,
    framework_type: str,
    description: str | None,
    definition: dict[str, Any] | None,
) -> str:
    """Build LLM system prompt from framework definition."""
    defn = definition or {}
    override = (defn.get("system_prompt_override") or "").strip()
    if override:
        return override

    parts = [
        f"Ets un analista d'intel·ligència expert aplicant el marc de raonament «{framework_name}» ({framework_type}).",
    ]
    if description:
        parts.append(f"Descripció: {description}")

    for key, label in [
        ("doctrine", "Doctrina"),
        ("epistemology", "Epistemologia"),
        ("ontology", "Ontologia"),
        ("methodology", "Metodologia"),
    ]:
        val = (defn.get(key) or "").strip()
        if val:
            parts.append(f"{label}: {val}")

    steps = defn.get("analysis_steps") or []
    if steps:
        parts.append("\nPassos d'anàlisi obligatoris:")
        for step in sorted(steps, key=lambda s: s.get("order", 0)):
            title = step.get("title", "Pas")
            instruction = step.get("instruction", "")
            hint = step.get("llm_hint", "")
            line = f"{step.get('order', '?')}. {title}: {instruction}"
            if hint:
                line += f" ({hint})"
            parts.append(line)

    criteria = defn.get("evidence_criteria") or []
    if criteria:
        parts.append("\nCriteris d'evidència: " + "; ".join(criteria))

    biases = defn.get("bias_checks") or []
    if biases:
        parts.append("Comprovacions de biaix: " + "; ".join(biases))

    limitations = (defn.get("limitations") or "").strip()
    if limitations:
        parts.append(f"Límits del marc: {limitations}")

    sections = defn.get("output_sections") or DEFAULT_OUTPUT_SECTIONS
    section_keys = [s.get("key") for s in sections if s.get("key")]
    parts.append(
        "\nRespon ÚNICAMENT en JSON vàlid amb aquestes claus: "
        + ", ".join(section_keys + ["confidence"])
        + ". "
        "confidence és un float 0-1. evidence ha de ser una llista d'objectes amb text, source i relevance."
    )
    return "\n".join(parts)


def _clean_json(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


class ReasoningFrameworkService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_frameworks(self, include_inactive: bool = False) -> list[dict[str, Any]]:
        q = select(ReasoningFramework).order_by(
            ReasoningFramework.is_custom.asc(),
            ReasoningFramework.name.asc(),
        )
        if not include_inactive:
            q = q.where(ReasoningFramework.is_active == True)
        rows = (await self.db.execute(q)).scalars().all()
        return [framework_to_dict(r) for r in rows]

    async def get_framework(self, framework_id: int) -> dict[str, Any] | None:
        r = await self.db.execute(
            select(ReasoningFramework).where(ReasoningFramework.id == framework_id)
        )
        fw = r.scalar_one_or_none()
        return framework_to_dict(fw) if fw else None

    async def get_framework_model(self, framework_id: int) -> ReasoningFramework | None:
        r = await self.db.execute(
            select(ReasoningFramework).where(ReasoningFramework.id == framework_id)
        )
        return r.scalar_one_or_none()

    async def create_framework(
        self,
        *,
        name: str,
        framework_type: ReasoningFrameworkType,
        description: str | None,
        definition: dict[str, Any] | None,
        user_id: int | None,
        is_custom: bool = True,
    ) -> dict[str, Any]:
        fw = ReasoningFramework(
            name=name.strip(),
            framework_type=framework_type,
            description=description,
            definition=definition or empty_definition(),
            is_custom=is_custom,
            user_id=user_id,
            is_active=True,
        )
        self.db.add(fw)
        await self.db.commit()
        await self.db.refresh(fw)
        return framework_to_dict(fw)

    async def update_framework(
        self,
        framework_id: int,
        *,
        name: str | None = None,
        framework_type: ReasoningFrameworkType | None = None,
        description: str | None = None,
        definition: dict[str, Any] | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any] | None:
        fw = await self.get_framework_model(framework_id)
        if not fw:
            return None
        if name is not None:
            fw.name = name.strip()
        if framework_type is not None:
            fw.framework_type = framework_type
        if description is not None:
            fw.description = description
        if definition is not None:
            fw.definition = definition
        if is_active is not None:
            fw.is_active = is_active
        await self.db.commit()
        await self.db.refresh(fw)
        return framework_to_dict(fw)

    async def delete_framework(self, framework_id: int) -> bool:
        fw = await self.get_framework_model(framework_id)
        if not fw:
            return False
        fw.is_active = False
        await self.db.commit()
        return True

    async def seed_builtin_frameworks(self) -> int:
        """Ensure built-in frameworks exist with definitions."""
        created = 0
        for spec in BUILTIN_FRAMEWORKS:
            r = await self.db.execute(
                select(ReasoningFramework).where(
                    func.lower(ReasoningFramework.name) == spec["name"].lower()
                )
            )
            existing = r.scalar_one_or_none()
            if existing:
                if not existing.definition:
                    existing.definition = spec["definition"]
                    existing.description = spec.get("description") or existing.description
                    existing.is_custom = False
                continue
            self.db.add(
                ReasoningFramework(
                    name=spec["name"],
                    framework_type=spec["framework_type"],
                    description=spec.get("description"),
                    definition=spec.get("definition"),
                    is_custom=False,
                    is_active=True,
                )
            )
            created += 1
        if created:
            await self.db.commit()
            logger.info("Seeded %d reasoning frameworks", created)
        else:
            await self.db.commit()
        return created

    async def generate_from_brief(
        self,
        brief: str,
        *,
        framework_type: ReasoningFrameworkType = ReasoningFrameworkType.CUSTOM,
        language: str = "ca",
    ) -> dict[str, Any]:
        """Use LLM to draft a full framework definition from a short brief."""
        from services.llm_service import LLMService, resolve_provider

        if not resolve_provider():
            raise ValueError("Cap proveïdor LLM configurat. Configura OPENAI, ANTHROPIC o GEMINI al .env.")

        llm = LLMService()
        system = (
            "Ets un metodòleg d'anàlisi d'intel·ligència. Genera marcs de raonament detallats per a OSINT. "
            "Respon ÚNICAMENT JSON vàlid amb: name, description, definition (objecte complet amb doctrine, "
            "epistemology, ontology, methodology, analysis_steps[], evidence_criteria[], bias_checks[], "
            "limitations, output_sections[], application_notes, tags[], auto_apply)."
        )
        user = (
            f"Idioma de sortida: {language}.\n"
            f"Tipus base: {framework_type.value}.\n"
            f"Brief de l'analista:\n{brief.strip()}\n\n"
            "analysis_steps ha de tenir 3-6 passos amb order, title, instruction, llm_hint. "
            "output_sections ha d'incloure conclusions, evidence, hypotheses, uncertainties."
        )
        raw = await llm.acomplete(user, system_prompt=system, max_tokens=4000)
        try:
            data = json.loads(_clean_json(raw))
        except json.JSONDecodeError as exc:
            raise ValueError(f"El LLM no ha retornat JSON vàlid: {exc}") from exc

        definition = data.get("definition") or empty_definition()
        if not definition.get("output_sections"):
            definition["output_sections"] = deepcopy(DEFAULT_OUTPUT_SECTIONS)

        return {
            "name": data.get("name") or "Marc personalitzat",
            "description": data.get("description") or "",
            "framework_type": framework_type.value,
            "definition": definition,
            "is_custom": True,
            "auto_apply": definition.get("auto_apply", True),
        }

    async def preview_analysis(
        self,
        framework_id: int,
        premise: str,
        *,
        case_context: str = "",
    ) -> dict[str, Any]:
        """Preview how the framework applies to a premise without persisting."""
        fw = await self.get_framework_model(framework_id)
        if not fw:
            raise LookupError("Marc no trobat")

        from services.ai_service import AIService

        ai = AIService()
        system_prompt = build_system_prompt(
            fw.name,
            fw.framework_type.value if hasattr(fw.framework_type, "value") else str(fw.framework_type),
            fw.description,
            fw.definition,
        )
        user_prompt = premise.strip()
        if case_context.strip():
            user_prompt += f"\n\nContext del cas:\n{case_context.strip()[:3000]}"

        return await ai.analyze_with_framework(
            premise=user_prompt,
            framework=fw.name,
            kpis=[],
            framework_definition=fw.definition,
            system_prompt_override=system_prompt,
        )
