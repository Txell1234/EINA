"""
Prospective Analysis Service - MIC-MAC, MACTOR, morphological, scenario narratives
"""
import logging
from typing import Any, AsyncGenerator, List, Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prospective import (
    MACTORObjective,
    MACTORPosture,
    MACTORResult,
    MICMACResult,
    MorphComponent,
    MorphIncompatibility,
    ProspectiveActor,
    ProspectiveProject,
    ProspectiveScenario,
    ProspectiveVariable,
    SMICResult,
)
from services.llm_service import LLMService, llm_config_error_message
from services.micmac_math import compute_micmac_pure, matrix_multiply
from services.morph_space import (
    DEFAULT_SMIC_CROSS,
    DEFAULT_SMIC_INITIAL,
    SCENARIO_TEMPLATES,
    build_scenario_specs,
    compute_smic_bayesian,
    compute_smic_final,
    filter_valid_combinations,
    format_morph_config,
    morph_space_stats,
)

logger = logging.getLogger(__name__)

PROB_MAP = {
    "ALTA": 0.65,
    "MITJA-ALTA": 0.55,
    "MITJA": 0.35,
    "BAIXA-MITJA": 0.20,
    "BAIXA": 0.10,
}


class ProspectiveService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_projects(self, case_id: Optional[int] = None) -> List[ProspectiveProject]:
        q = select(ProspectiveProject).order_by(ProspectiveProject.created_at.desc())
        if case_id is not None:
            q = q.where(ProspectiveProject.case_id == case_id)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    async def get_project(self, project_id: int) -> Optional[ProspectiveProject]:
        result = await self.db.execute(
            select(ProspectiveProject).where(ProspectiveProject.id == project_id)
        )
        return result.scalar_one_or_none()

    async def create_project(
        self,
        title: str,
        hypothesis: str = "",
        context: str = "",
        case_id: Optional[int] = None,
    ) -> ProspectiveProject:
        project = ProspectiveProject(
            title=title,
            hypothesis=hypothesis,
            context=context,
            case_id=case_id,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def save_variables(self, project_id: int, variables: List[dict]) -> None:
        await self.db.execute(
            delete(ProspectiveVariable).where(ProspectiveVariable.project_id == project_id)
        )
        for i, v in enumerate(variables):
            self.db.add(
                ProspectiveVariable(
                    project_id=project_id,
                    code=str(v.get("code", f"V{i + 1}")),
                    name=str(v.get("name", "")),
                    var_type=str(v.get("type", v.get("var_type", "I"))),
                    description=str(v.get("desc", v.get("description", ""))),
                    order_index=i,
                )
            )
        await self.db.flush()

    async def save_actors(self, project_id: int, actors: List[dict]) -> None:
        await self.db.execute(
            delete(ProspectiveActor).where(ProspectiveActor.project_id == project_id)
        )
        for i, a in enumerate(actors):
            fins = a.get("fins") or a.get("strategic_goals") or []
            if isinstance(fins, str):
                fins = [x.strip() for x in fins.split(",") if x.strip()]
            self.db.add(
                ProspectiveActor(
                    project_id=project_id,
                    code=str(a.get("code", f"A{i + 1}")),
                    name=str(a.get("name", "")),
                    strategic_goals=fins,
                    force_score=float(a.get("force", a.get("force_score", 3))),
                    order_index=i,
                )
            )
        await self.db.flush()

    async def save_objectives(self, project_id: int, objectives: List[dict]) -> None:
        await self.db.execute(
            delete(MACTORObjective).where(MACTORObjective.project_id == project_id)
        )
        for i, o in enumerate(objectives):
            self.db.add(
                MACTORObjective(
                    project_id=project_id,
                    code=str(o.get("id", o.get("code", f"O{i + 1}"))),
                    name=str(o.get("name", "")),
                    order_index=i,
                )
            )
        await self.db.commit()

    async def save_postures(
        self, project_id: int, actor_codes: List[str], objective_codes: List[str], postures: List[List[int]]
    ) -> None:
        await self.db.execute(
            delete(MACTORPosture).where(MACTORPosture.project_id == project_id)
        )
        for i, actor_code in enumerate(actor_codes):
            for j, obj_code in enumerate(objective_codes):
                val = postures[i][j] if i < len(postures) and j < len(postures[i]) else 0
                self.db.add(
                    MACTORPosture(
                        project_id=project_id,
                        actor_code=actor_code,
                        objective_code=obj_code,
                        posture_value=int(val),
                    )
                )
        await self.db.commit()

    async def save_components(self, project_id: int, components: List[dict]) -> None:
        await self.db.execute(
            delete(MorphComponent).where(MorphComponent.project_id == project_id)
        )
        for i, c in enumerate(components):
            configs = c.get("configs") or []
            if not configs and c.get("configsText"):
                configs = [
                    {"label": line.strip(), "desc": ""}
                    for line in str(c["configsText"]).split("\n")
                    if line.strip()
                ]
            self.db.add(
                MorphComponent(
                    project_id=project_id,
                    code=str(c.get("id", c.get("code", f"C{i + 1}"))),
                    name=str(c.get("name", "")),
                    configurations=configs,
                    order_index=i,
                )
            )
        await self.db.commit()

    async def preview_micmac(
        self, project_id: int, matrix: List[List[int]]
    ) -> dict[str, Any]:
        vars_r = await self.db.execute(
            select(ProspectiveVariable)
            .where(ProspectiveVariable.project_id == project_id)
            .order_by(ProspectiveVariable.order_index)
        )
        variables = list(vars_r.scalars().all())
        codes = [v.code for v in variables]
        return compute_micmac_pure(matrix, codes)

    async def compute_micmac(self, project_id: int, matrix: List[List[int]]) -> dict[str, Any]:
        result = await self.preview_micmac(project_id, matrix)
        await self.db.execute(delete(MICMACResult).where(MICMACResult.project_id == project_id))
        self.db.add(
            MICMACResult(
                project_id=project_id,
                matrix_direct=result["matrix_direct"],
                matrix_indirect=result["matrix_indirect"],
                motricite_direct=result["motricitat_direct"],
                dependence_direct=result["dependencia_direct"],
                sectors=result["sectors"],
                vb_index=result["vb_index"],
                vr_index=result["vr_index"],
            )
        )
        await self.db.commit()
        return result

    async def _load_morph_components(self, project_id: int) -> List[dict]:
        morph_r = await self.db.execute(
            select(MorphComponent)
            .where(MorphComponent.project_id == project_id)
            .order_by(MorphComponent.order_index)
        )
        return [
            {
                "code": m.code,
                "name": m.name,
                "configs": m.configurations or [],
            }
            for m in morph_r.scalars().all()
        ]

    async def get_incompatibilities(self, project_id: int) -> List[dict]:
        result = await self.db.execute(
            select(MorphIncompatibility).where(
                MorphIncompatibility.project_id == project_id
            )
        )
        return [
            {
                "component_a": r.component_a,
                "config_a": r.config_a,
                "component_b": r.component_b,
                "config_b": r.config_b,
            }
            for r in result.scalars().all()
        ]

    async def save_incompatibilities(
        self, project_id: int, incompatibilities: List[dict]
    ) -> dict[str, Any]:
        await self.db.execute(
            delete(MorphIncompatibility).where(
                MorphIncompatibility.project_id == project_id
            )
        )
        for inc in incompatibilities:
            self.db.add(
                MorphIncompatibility(
                    project_id=project_id,
                    component_a=str(inc.get("component_a", "")),
                    config_a=str(inc.get("config_a", "")),
                    component_b=str(inc.get("component_b", "")),
                    config_b=str(inc.get("config_b", "")),
                )
            )
        await self.db.commit()
        components = await self._load_morph_components(project_id)
        return morph_space_stats(components, incompatibilities)

    async def save_compatibility(self, project_id: int, pairs: List[dict]) -> dict[str, Any]:
        """Zwicky pairs API: [{comp_a, cfg_a, comp_b, cfg_b, compatible}]."""
        incompat = [
            {
                "component_a": p["comp_a"],
                "config_a": p["cfg_a"],
                "component_b": p["comp_b"],
                "config_b": p["cfg_b"],
            }
            for p in pairs
            if not p.get("compatible", True)
        ]
        await self.save_incompatibilities(project_id, incompat)
        return {"saved": len(pairs)}

    async def get_compatibility(self, project_id: int) -> List[dict]:
        rows = await self.get_incompatibilities(project_id)
        return [
            {
                "comp_a": r["component_a"],
                "cfg_a": r["config_a"],
                "comp_b": r["component_b"],
                "cfg_b": r["config_b"],
                "compatible": False,
            }
            for r in rows
        ]

    async def get_morphological_space(self, project_id: int) -> dict[str, Any]:
        components = await self._load_morph_components(project_id)
        incompatibilities = await self.get_incompatibilities(project_id)
        stats = morph_space_stats(components, incompatibilities)
        valid = filter_valid_combinations(components, incompatibilities)
        if not valid:
            valid = filter_valid_combinations(components, [])
        return {
            "total": stats["total_combinations"],
            "valid": stats["valid_combinations"],
            "excluded": stats["filtered_out"],
            "combos": [format_morph_config(c) for c in valid[:20]],
        }

    async def get_morph_space(self, project_id: int) -> dict[str, Any]:
        components = await self._load_morph_components(project_id)
        incompatibilities = await self.get_incompatibilities(project_id)
        stats = morph_space_stats(components, incompatibilities)
        specs = build_scenario_specs(components, incompatibilities)
        stats["scenario_configs"] = [
            {
                "scenario_type": s["scenario_type"],
                "config": s["config"],
                "possibility": s.get("possibility"),
                "possibility_rationale": s.get("possibility_rationale"),
                "probability": s.get("probability"),
            }
            for s in specs
        ]
        return stats

    async def get_smic(self, project_id: int) -> dict[str, Any]:
        result = await self.db.execute(
            select(SMICResult).where(SMICResult.project_id == project_id)
        )
        row = result.scalar_one_or_none()
        if not row:
            return {
                "initial_probs": DEFAULT_SMIC_INITIAL,
                "cross_matrix": DEFAULT_SMIC_CROSS,
                "final_probs": None,
                "final_labels": None,
            }
        return {
            "initial_probs": row.initial_probs or DEFAULT_SMIC_INITIAL,
            "cross_matrix": row.cross_matrix or DEFAULT_SMIC_CROSS,
            "final_probs": row.final_probs,
            "final_labels": row.final_labels,
        }

    async def save_and_compute_smic(
        self,
        project_id: int,
        initial_probs: List[float],
        cross_matrix: List[List[float]],
    ) -> dict[str, Any]:
        final_probs, final_labels = compute_smic_final(initial_probs, cross_matrix)
        result = await self.db.execute(
            select(SMICResult).where(SMICResult.project_id == project_id)
        )
        row = result.scalar_one_or_none()
        if row:
            row.initial_probs = initial_probs
            row.cross_matrix = cross_matrix
            row.final_probs = final_probs
            row.final_labels = final_labels
        else:
            self.db.add(
                SMICResult(
                    project_id=project_id,
                    initial_probs=initial_probs,
                    cross_matrix=cross_matrix,
                    final_probs=final_probs,
                    final_labels=final_labels,
                )
            )
        await self.db.commit()
        return {
            "initial_probs": initial_probs,
            "cross_matrix": cross_matrix,
            "final_probs": final_probs,
            "final_labels": final_labels,
        }

    async def compute_smic(
        self, project_id: int, conditional_matrix: List[List[float]]
    ) -> dict[str, Any]:
        """SMIC Bayesian: conditional_matrix[i][j] = P(j | i), updates scenario probabilities."""
        n = len(conditional_matrix)
        if n < 2:
            return {"error": "Cal almenys 2 escenaris"}

        scens_r = await self.db.execute(
            select(ProspectiveScenario)
            .where(ProspectiveScenario.project_id == project_id)
            .order_by(ProspectiveScenario.id)
        )
        scens = list(scens_r.scalars().all())

        prior = []
        for s in scens[:n]:
            key = (s.probability or "MITJA").upper().replace(" ", "_").replace("-", "_")
            prior.append(PROB_MAP.get(key, 0.35))
        if len(prior) < n:
            prior += [0.35] * (n - len(prior))

        adjusted, labels = compute_smic_bayesian(prior, conditional_matrix)

        results = []
        for i, (s, adj, lbl) in enumerate(zip(scens[:n], adjusted, labels)):
            results.append(
                {
                    "scenario_id": s.id,
                    "name": s.name,
                    "prior_probability": prior[i],
                    "adjusted_probability": adj,
                    "label": lbl,
                }
            )
            s.probability = lbl

        await self.db.commit()
        return {"results": results, "prior": prior, "adjusted": adjusted}

    async def compute_mactor(self, project_id: int, postures: List[List[int]]) -> dict[str, Any]:
        actors_r = await self.db.execute(
            select(ProspectiveActor)
            .where(ProspectiveActor.project_id == project_id)
            .order_by(ProspectiveActor.order_index)
        )
        objectives_r = await self.db.execute(
            select(MACTORObjective)
            .where(MACTORObjective.project_id == project_id)
            .order_by(MACTORObjective.order_index)
        )
        actors = list(actors_r.scalars().all())
        objectives = list(objectives_r.scalars().all())
        actor_codes = [a.code for a in actors]
        obj_codes = [o.code for o in objectives]

        await self.save_postures(project_id, actor_codes, obj_codes, postures)

        na = len(actors)
        no = len(objectives)
        mob_actor = [sum(abs(postures[i][j]) for j in range(no)) for i in range(na)]
        mob_obj = [sum(abs(postures[i][j]) for i in range(na)) for j in range(no)]

        convergences = [[0] * na for _ in range(na)]
        for i in range(na):
            for j in range(na):
                if i == j:
                    continue
                convergences[i][j] = sum(
                    1
                    for k in range(no)
                    if postures[i][k] != 0
                    and postures[j][k] != 0
                    and (postures[i][k] > 0) == (postures[j][k] > 0)
                )

        await self.db.execute(delete(MACTORResult).where(MACTORResult.project_id == project_id))
        self.db.add(
            MACTORResult(
                project_id=project_id,
                mobilisation_actors=mob_actor,
                mobilisation_objectives=mob_obj,
                convergences_matrix=convergences,
            )
        )
        await self.db.commit()

        return {
            "mobilisation_actors": mob_actor,
            "mobilisation_objectives": mob_obj,
            "convergences": convergences,
            "actor_codes": actor_codes,
            "objective_codes": obj_codes,
        }

    async def get_scenarios(self, project_id: int) -> List[dict]:
        from services.scenario_milestone_service import list_milestones_for_project

        result = await self.db.execute(
            select(ProspectiveScenario)
            .where(ProspectiveScenario.project_id == project_id)
            .order_by(ProspectiveScenario.id)
        )
        rows = result.scalars().all()
        milestones_by_scenario = await list_milestones_for_project(self.db, project_id)
        return [
            {
                "id": s.id,
                "name": s.name,
                "scenario_type": s.scenario_type,
                "possibility": getattr(s, "possibility", None) or "PLAUSIBLE",
                "possibility_rationale": getattr(s, "possibility_rationale", None) or "",
                "probability": s.probability,
                "narrative": s.narrative,
                "morphological_config": s.morphological_config,
                "milestones": milestones_by_scenario.get(s.id, []),
            }
            for s in rows
        ]

    async def _build_context(
        self, project_id: int, *, include_temporal_context: bool = False
    ) -> str:
        """Build rich Godet context for scenario generation LLM prompt."""
        project = await self.get_project(project_id)
        if not project:
            return ""

        vars_r = await self.db.execute(
            select(ProspectiveVariable)
            .where(ProspectiveVariable.project_id == project_id)
            .order_by(ProspectiveVariable.order_index)
        )
        actors_r = await self.db.execute(
            select(ProspectiveActor)
            .where(ProspectiveActor.project_id == project_id)
            .order_by(ProspectiveActor.order_index)
        )
        morph_r = await self.db.execute(
            select(MorphComponent)
            .where(MorphComponent.project_id == project_id)
            .order_by(MorphComponent.order_index)
        )
        micmac_r = await self.db.execute(
            select(MICMACResult).where(MICMACResult.project_id == project_id)
        )
        mactor_r = await self.db.execute(
            select(MACTORResult).where(MACTORResult.project_id == project_id)
        )

        variables = list(vars_r.scalars().all())
        actors = list(actors_r.scalars().all())
        morph = list(morph_r.scalars().all())
        micmac = micmac_r.scalar_one_or_none()
        mactor = mactor_r.scalar_one_or_none()

        parts: list[str] = [
            f"CONFLICTE ESTRATÈGIC: {project.hypothesis}",
            f"CONTEXT: {project.context}",
            "",
            f"VARIABLES DEL SISTEMA ({len(variables)}):",
        ]
        for v in variables:
            parts.append(f"  {v.code} ({v.var_type}): {v.name} — {v.description}")

        if micmac and micmac.sectors:
            parts += ["", "RESULTATS MIC-MAC (sectors Godet):"]
            for s in micmac.sectors:
                tag = ""
                if s["index"] == micmac.vb_index:
                    tag = " ← VARIABLE BLANC (palanca estratègica del sistema)"
                elif s["index"] == micmac.vr_index:
                    tag = " ← VARIABLE DE RISC (punt d'inestabilitat)"
                parts.append(
                    f"  {s['code']}: {s['sector']} "
                    f"(mot={s['motricitat']}, dep={s['dependencia']}){tag}"
                )
            if micmac.vb_index is not None and micmac.vb_index < len(variables):
                vb = variables[micmac.vb_index]
                parts.append(
                    f"\nLa VARIABLE BLANC és '{vb.code} — {vb.name}'. "
                    "Els escenaris han de mostrar com evoluciona com a eix central."
                )
            if micmac.vr_index is not None and micmac.vr_index < len(variables):
                vr = variables[micmac.vr_index]
                parts.append(
                    f"La VARIABLE DE RISC és '{vr.code} — {vr.name}'. "
                    "Petits canvis en ella bifurquen el futur."
                )

        if mactor and actors:
            mob = mactor.mobilisation_actors or []
            conv = mactor.convergences_matrix or []
            parts += ["", f"ACTORS ({len(actors)}):"]
            actor_mob = sorted(
                [(a, mob[i] if i < len(mob) else 0) for i, a in enumerate(actors)],
                key=lambda x: x[1],
                reverse=True,
            )
            for a, m in actor_mob:
                parts.append(
                    f"  {a.code}: {a.name} (força={a.force_score:.0f}, mobilització={m})"
                    f" — fins: {', '.join(a.strategic_goals or [])}"
                )
            if conv:
                max_v, pair = 0, ("", "")
                for i in range(len(actors)):
                    for j in range(len(actors)):
                        if i != j and i < len(conv) and j < len(conv[i]) and conv[i][j] > max_v:
                            max_v = conv[i][j]
                            pair = (actors[i].code, actors[j].code)
                if max_v > 0:
                    parts.append(
                        f"MÀXIMA CONVERGÈNCIA: {pair[0]}–{pair[1]} "
                        f"({max_v} objectius compartits) → aliança potencial."
                    )

        if morph:
            parts += ["", "COMPONENTS MORFOLÒGICS:"]
            incompatibilities = await self.get_incompatibilities(project_id)
            components_dict = [
                {"code": m.code, "name": m.name, "configs": m.configurations or []}
                for m in morph
            ]
            stats = morph_space_stats(components_dict, incompatibilities)
            for comp in stats["components"]:
                parts.append(
                    f"  {comp['code']}: {comp['name']} → "
                    + " | ".join(comp["configs"])
                )
            parts.append(
                f"Espai morfològic: {stats['valid_combinations']} combinacions vàlides "
                f"(de {stats['total_combinations']} totals, Zwicky)."
            )
            for sc in build_scenario_specs(components_dict, incompatibilities):
                if sc.get("config"):
                    parts.append(f"  → {sc['scenario_type']}: {sc['config']}")

        if include_temporal_context and project.case_id:
            from services.retrospective_service import RetrospectiveService

            retro = await RetrospectiveService(self.db).build_retrospective(
                project.case_id, project_id
            )
            if retro.get("has_data"):
                parts += ["", "RETROSPECTIVA I TENDÈNCIES (seqüència temporal):"]
                for ev in (retro.get("key_events") or [])[:10]:
                    if isinstance(ev, dict):
                        parts.append(
                            f"  - {ev.get('date', '')} {ev.get('title', ev.get('summary', ''))}"[:200]
                        )
                    else:
                        parts.append(f"  - {ev}")
                for ap in (retro.get("actor_posture_summary") or [])[:8]:
                    if isinstance(ap, dict):
                        parts.append(
                            f"  - Actor {ap.get('actor', '?')}: tendència {ap.get('trend', '—')}"
                        )

        return "\n".join(parts)

    async def stream_scenarios(
        self,
        project_id: int,
        *,
        include_temporal_context: bool = False,
    ) -> AsyncGenerator[dict[str, Any], None]:
        llm = LLMService(mode="scenario")
        if not llm.configured:
            yield {"event": "error", "message": llm_config_error_message()}
            return

        context = await self._build_context(
            project_id, include_temporal_context=include_temporal_context
        )
        components = await self._load_morph_components(project_id)
        incompatibilities = await self.get_incompatibilities(project_id)
        smic = await self.get_smic(project_id)
        prob_labels = smic.get("final_labels")

        specs = build_scenario_specs(components, incompatibilities, prob_labels)
        if not any(s.get("config") for s in specs):
            generic = {
                "infern": "Condicions màximament desfavorables",
                "tensio": "Tendència actual extrapolada sense ruptures",
                "equilibri": "Equilibri inestable amb dinàmiques positives emergents",
                "cel": "Condicions màximament favorables",
            }
            for s in specs:
                if not s.get("config"):
                    s["config"] = generic.get(s["scenario_type"], s["config"])

        await self.db.execute(
            delete(ProspectiveScenario).where(ProspectiveScenario.project_id == project_id)
        )
        await self.db.commit()

        for spec in specs:
            idx = spec["index"]
            yield {
                "event": "scenario_start",
                "index": idx,
                "name": spec["name"],
                "possibility": spec.get("possibility"),
                "prob": spec["probability"],
                "config": spec["config"],
            }

            system_prompt = (
                "Ets un analista d'intel·ligència estratègica expert en prospectiva (escola Godet). "
                "Escriu narratives analítiques en català, 380-440 paraules, amb condicions inicials, "
                "seqüència d'events (any 1, anys 2-3, anys 4-5), actors impulsors, indicadors d'alerta "
                "(format → indicador), possibilitat morfològica justificada i probabilitat estimada "
                "clarament diferenciades."
            )
            user_prompt = f"""Context de l'anàlisi:
{context}

Genera la narrativa de l'{spec['name']} ({spec['config']}).

DISTINGEIX OBLIGATÒRIAMENT:
- POSSIBILITAT (viabilitat lògica Zwicky): {spec.get('possibility', 'PLAUSIBLE')} — {spec.get('possibility_rationale', '')}
  Respon: aquest estat futur pot existir dins l'espai morfològic? Quines condicions lògiques el fan assolible?
- PROBABILITAT (likelihood SMIC/tendències): {spec['probability']}.
  Respon: quina és la probabilitat estimada que el sistema arribi realment a aquest escenari?

Inclou 4-5 indicadors d'alerta primerenca observables."""

            narrative = ""
            try:
                async for text in llm.stream(
                    user_prompt, system_prompt=system_prompt, max_tokens=1200
                ):
                    narrative += text
                    yield {"event": "chunk", "index": idx, "text": text}
            except Exception as e:
                logger.error("Scenario stream error: %s", e)
                yield {"event": "error", "index": idx, "message": str(e)}
                continue

            scenario = ProspectiveScenario(
                project_id=project_id,
                name=spec["name"],
                scenario_type=spec["scenario_type"],
                morphological_config=spec["config"],
                possibility=spec.get("possibility", "PLAUSIBLE"),
                possibility_rationale=spec.get("possibility_rationale", ""),
                probability=spec["probability"],
                narrative=narrative,
            )
            self.db.add(scenario)
            await self.db.commit()
            await self.db.refresh(scenario)

            from services.scenario_milestone_service import persist_milestones_for_scenario

            milestones = await persist_milestones_for_scenario(
                self.db, scenario.id, narrative
            )
            if milestones:
                yield {
                    "event": "milestones_saved",
                    "index": idx,
                    "scenario_id": scenario.id,
                    "count": len(milestones),
                }

            from services.event_bus_service import get_event_bus

            await get_event_bus().emit(
                {
                    "source": "prospective_service",
                    "detail_type": "scenario.generated",
                    "detail": {
                        "project_id": project_id,
                        "scenario_id": scenario.id,
                        "name": spec["name"],
                    },
                }
            )

            yield {"event": "scenario_done", "index": idx, "name": spec["name"]}

        yield {"event": "all_done"}

    async def apply_extraction(
        self, project_id: int, variables: List[dict], actors: List[dict]
    ) -> dict[str, Any]:
        mapped_vars = [
            {
                "code": v.get("code"),
                "name": v.get("name"),
                "type": v.get("type", "I"),
                "desc": v.get("desc", v.get("description", "")),
            }
            for v in variables
        ]
        mapped_actors = [
            {
                "code": a.get("code"),
                "name": a.get("name"),
                "force": a.get("force", 3),
                "fins": ", ".join(a.get("fins", [])) if isinstance(a.get("fins"), list) else a.get("fins", ""),
            }
            for a in actors
        ]
        await self.save_variables(project_id, mapped_vars)
        await self.save_actors(project_id, mapped_actors)
        return {"variables": mapped_vars, "actors": mapped_actors}

    async def submit_expert_vote(
        self,
        project_id: int,
        expert_id: str,
        expert_name: str,
        votes: list[dict],
    ) -> dict:
        from models.prospective import MICMACExpertVote
        from sqlalchemy import delete

        await self.db.execute(
            delete(MICMACExpertVote).where(
                MICMACExpertVote.project_id == project_id,
                MICMACExpertVote.expert_id == expert_id,
            )
        )
        await self.db.flush()

        for v in votes:
            self.db.add(
                MICMACExpertVote(
                    project_id=project_id,
                    expert_id=expert_id,
                    expert_name=expert_name,
                    row_index=int(v["row"]),
                    col_index=int(v["col"]),
                    vote_value=max(0, min(3, int(v["value"]))),
                )
            )
        await self.db.commit()
        return {"submitted": len(votes), "expert_id": expert_id}

    async def get_panel_consensus(self, project_id: int) -> dict:
        from collections import defaultdict
        import statistics

        from models.prospective import MICMACExpertVote

        rows = (
            await self.db.execute(
                select(MICMACExpertVote).where(MICMACExpertVote.project_id == project_id)
            )
        ).scalars().all()

        if not rows:
            return {"error": "Cap vot registrat. Convida experts al panel."}

        cell_votes: dict[tuple, list] = defaultdict(list)
        experts: set = set()
        for v in rows:
            cell_votes[(v.row_index, v.col_index)].append(v.vote_value)
            experts.add(v.expert_id)

        n = max(max(k) for k in cell_votes) + 1
        consensus = [[0.0] * n for _ in range(n)]
        stdev_m = [[0.0] * n for _ in range(n)]
        disagree = []

        for (r, c), vals in cell_votes.items():
            if r == c:
                continue
            avg = sum(vals) / len(vals)
            std = statistics.stdev(vals) if len(vals) > 1 else 0.0
            consensus[r][c] = round(avg, 2)
            stdev_m[r][c] = round(std, 2)
            if std > 1.0:
                disagree.append(
                    {
                        "row": r,
                        "col": c,
                        "avg": round(avg, 2),
                        "stdev": round(std, 2),
                        "votes": vals,
                        "n_experts": len(vals),
                    }
                )

        return {
            "consensus_matrix": consensus,
            "stdev_matrix": stdev_m,
            "n_experts": len(experts),
            "n_votes": len(rows),
            "high_disagreement": sorted(disagree, key=lambda x: -x["stdev"]),
            "coverage": len(cell_votes),
        }

    async def apply_consensus(self, project_id: int) -> dict:
        result = await self.get_panel_consensus(project_id)
        if "error" in result:
            return result
        matrix_int = [[round(v) for v in row] for row in result["consensus_matrix"]]
        return await self.compute_micmac(project_id, matrix_int)
