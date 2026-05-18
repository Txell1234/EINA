"""
Prospective Analysis Service - MIC-MAC, MACTOR, morphological, scenario narratives
"""
import json
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
    ProspectiveActor,
    ProspectiveProject,
    ProspectiveScenario,
    ProspectiveVariable,
)
from services.llm_service import LLMService, llm_config_error_message

logger = logging.getLogger(__name__)

SCENARIO_DEFINITIONS = [
    {
        "index": 0,
        "name": "Escenari Infern",
        "scenario_type": "infern",
        "probability": "BAIXA-MITJA",
        "config": "Màxima expansió adversari + resposta fragmentada",
    },
    {
        "index": 1,
        "name": "Escenari Tensió Crònica",
        "scenario_type": "tensio",
        "probability": "ALTA",
        "config": "Estancament parcial + divisió interna",
    },
    {
        "index": 2,
        "name": "Escenari Equilibri Dinàmic",
        "scenario_type": "equilibri",
        "probability": "MITJA",
        "config": "Alternativa en construcció + cohesió moderada",
    },
    {
        "index": 3,
        "name": "Escenari Cel",
        "scenario_type": "cel",
        "probability": "BAIXA",
        "config": "Retrocés expansió + alternativa consolidada",
    },
]


def matrix_multiply(a: List[List[int]], b: List[List[int]]) -> List[List[int]]:
    n = len(a)
    return [
        [sum(a[i][k] * b[k][j] for k in range(n)) for j in range(n)]
        for i in range(n)
    ]


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
        await self.db.commit()

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
        await self.db.commit()

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

    async def compute_micmac(self, project_id: int, matrix: List[List[int]]) -> dict[str, Any]:
        n = len(matrix)
        mot_d = [sum(matrix[i]) for i in range(n)]
        dep_d = [sum(matrix[i][j] for i in range(n)) for j in range(n)]
        avg_mot = sum(mot_d) / n if n else 0
        avg_dep = sum(dep_d) / n if n else 0

        indirect = matrix_multiply(matrix, matrix)
        mot_i = [sum(indirect[i]) for i in range(n)]
        dep_i = [sum(indirect[i][j] for i in range(n)) for j in range(n)]

        vars_r = await self.db.execute(
            select(ProspectiveVariable)
            .where(ProspectiveVariable.project_id == project_id)
            .order_by(ProspectiveVariable.order_index)
        )
        variables = list(vars_r.scalars().all())

        sectors = []
        for i in range(n):
            mot = mot_d[i]
            dep = dep_d[i]
            if mot >= avg_mot and dep >= avg_dep:
                sector = "Clau/Conflicte"
            elif mot >= avg_mot:
                sector = "Motriu"
            elif dep >= avg_dep:
                sector = "Resultant"
            else:
                sector = "Excluyent"
            label = variables[i].code if i < len(variables) else str(i)
            sectors.append({"index": i, "code": label, "sector": sector, "motricitat": mot, "dependencia": dep})

        key_sector = [s["index"] for s in sectors if s["sector"] == "Clau/Conflicte"]
        vb_idx = max(key_sector, key=lambda i: dep_d[i]) if key_sector else 0
        vr_idx = min(range(n), key=lambda i: abs(mot_d[i] - dep_d[i])) if n else 0

        await self.db.execute(delete(MICMACResult).where(MICMACResult.project_id == project_id))
        self.db.add(
            MICMACResult(
                project_id=project_id,
                matrix_direct=matrix,
                matrix_indirect=indirect,
                motricite_direct=mot_d,
                dependence_direct=dep_d,
                sectors=sectors,
                vb_index=vb_idx,
                vr_index=vr_idx,
            )
        )
        await self.db.commit()

        return {
            "matrix_direct": matrix,
            "matrix_indirect": indirect,
            "motricitat_direct": mot_d,
            "dependencia_direct": dep_d,
            "motricitat_indirect": mot_i,
            "dependencia_indirect": dep_i,
            "sectors": sectors,
            "variable_blanc": {"index": vb_idx, "code": sectors[vb_idx]["code"] if vb_idx < len(sectors) else ""},
            "variable_risc": {"index": vr_idx, "code": sectors[vr_idx]["code"] if vr_idx < len(sectors) else ""},
        }

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
        result = await self.db.execute(
            select(ProspectiveScenario)
            .where(ProspectiveScenario.project_id == project_id)
            .order_by(ProspectiveScenario.id)
        )
        rows = result.scalars().all()
        return [
            {
                "id": s.id,
                "name": s.name,
                "scenario_type": s.scenario_type,
                "probability": s.probability,
                "narrative": s.narrative,
                "morphological_config": s.morphological_config,
            }
            for s in rows
        ]

    async def _build_context(self, project_id: int) -> str:
        project = await self.get_project(project_id)
        if not project:
            return ""

        vars_r = await self.db.execute(
            select(ProspectiveVariable).where(ProspectiveVariable.project_id == project_id)
        )
        actors_r = await self.db.execute(
            select(ProspectiveActor).where(ProspectiveActor.project_id == project_id)
        )
        morph_r = await self.db.execute(
            select(MorphComponent).where(MorphComponent.project_id == project_id)
        )
        micmac_r = await self.db.execute(
            select(MICMACResult).where(MICMACResult.project_id == project_id)
        )

        variables = list(vars_r.scalars().all())
        actors = list(actors_r.scalars().all())
        morph = list(morph_r.scalars().all())
        micmac = micmac_r.scalar_one_or_none()

        parts = [
            f"Títol: {project.title}",
            f"Hipòtesi: {project.hypothesis}",
            f"Context: {project.context}",
            "Variables: " + ", ".join(f"{v.code} ({v.var_type}): {v.name}" for v in variables),
            "Actors: " + ", ".join(f"{a.code}: {a.name} (força {a.force_score})" for a in actors),
        ]
        if micmac and micmac.sectors:
            parts.append("Sectors MIC-MAC: " + json.dumps(micmac.sectors, ensure_ascii=False))
        if morph:
            parts.append(
                "Components morfològics: "
                + "; ".join(f"{m.code}: {m.name} ({len(m.configurations or [])} configs)" for m in morph)
            )
        return "\n".join(parts)

    async def stream_scenarios(self, project_id: int) -> AsyncGenerator[dict[str, Any], None]:
        llm = LLMService(mode="scenario")
        if not llm.configured:
            yield {"event": "error", "message": llm_config_error_message()}
            return

        context = await self._build_context(project_id)
        await self.db.execute(
            delete(ProspectiveScenario).where(ProspectiveScenario.project_id == project_id)
        )
        await self.db.commit()

        for spec in SCENARIO_DEFINITIONS:
            idx = spec["index"]
            yield {
                "event": "scenario_start",
                "index": idx,
                "name": spec["name"],
                "prob": spec["probability"],
                "config": spec["config"],
            }

            system_prompt = (
                "Ets un analista d'intel·ligència estratègica expert en prospectiva (escola Godet). "
                "Escriu narratives analítiques en català, 380-440 paraules, amb condicions inicials, "
                "seqüència d'events (any 1, anys 2-3, anys 4-5), actors impulsors, indicadors d'alerta "
                "(format → indicador) i probabilitat justificada."
            )
            user_prompt = f"""Context de l'anàlisi:
{context}

Genera la narrativa de l'{spec['name']} ({spec['config']}).
Probabilitat assignada: {spec['probability']}.
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
                probability=spec["probability"],
                narrative=narrative,
            )
            self.db.add(scenario)
            await self.db.commit()
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
