"""
Prospective Service - MIC-MAC, MACTOR calculations + Anthropic Claude scenario generation
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.prospective import (
    MACTORObjective,
    MACTORResult,
    MICMACResult,
    MorphComponent,
    ProspectiveActor,
    ProspectiveProject,
    ProspectiveScenario,
    ProspectiveVariable,
)

logger = logging.getLogger(__name__)


def _matrix_multiply(A: List[List[int]], B: List[List[int]]) -> List[List[int]]:
    n = len(A)
    return [[sum(A[i][k] * B[k][j] for k in range(n)) for j in range(n)] for i in range(n)]


def calc_micmac(matrix: List[List[int]]) -> Dict[str, Any]:
    n = len(matrix)
    if n == 0:
        return {}
    indirect = _matrix_multiply(matrix, matrix)
    mot_d = [sum(matrix[i]) for i in range(n)]
    dep_d = [sum(matrix[i][j] for i in range(n)) for j in range(n)]
    avg_mot = sum(mot_d) / n
    avg_dep = sum(dep_d) / n

    def classify(mot: int, dep: int) -> str:
        if mot >= avg_mot and dep >= avg_dep:
            return "Clau/Conflicte"
        if mot >= avg_mot and dep < avg_dep:
            return "Motriu"
        if mot < avg_mot and dep >= avg_dep:
            return "Resultant"
        return "Excluyent"

    sectors = [{"index": i, "sector": classify(mot_d[i], dep_d[i])} for i in range(n)]
    key_sector = [i for i in range(n) if sectors[i]["sector"] == "Clau/Conflicte"]
    vb_idx = max(key_sector, key=lambda i: dep_d[i]) if key_sector else 0
    vr_idx = min(range(n), key=lambda i: abs(mot_d[i] - dep_d[i]))
    return {
        "matrix_direct": matrix,
        "matrix_indirect": indirect,
        "motricite_direct": mot_d,
        "dependence_direct": dep_d,
        "sectors": sectors,
        "vb_index": vb_idx,
        "vr_index": vr_idx,
    }


def calc_mactor(postures: List[List[int]]) -> Dict[str, Any]:
    na = len(postures)
    no = len(postures[0]) if postures else 0
    mob_actor = [sum(abs(postures[i][j]) for j in range(no)) for i in range(na)]
    mob_obj = [sum(abs(postures[i][j]) for i in range(na)) for j in range(no)]
    convergences = [
        [
            sum(
                1
                for k in range(no)
                if postures[i][k] != 0
                and postures[j][k] != 0
                and (postures[i][k] > 0) == (postures[j][k] > 0)
            )
            if i != j
            else 0
            for j in range(na)
        ]
        for i in range(na)
    ]
    return {
        "mobilisation_actors": mob_actor,
        "mobilisation_objectives": mob_obj,
        "convergences_matrix": convergences,
    }


ANTHROPIC_SYSTEM = """Ets un analista d'intel·ligència estratègica expert en prospectiva (escola Godet).
Generes narratives en català, en l'estil d'un informe d'intel·ligència professional.
Les narratives d'escenaris inclouen SEMPRE:
1. Condicions inicials (estat present del sistema)
2. Seqüència d'events (any 1, anys 2-3, anys 4-5)
3. Actors impulsors (qui fa qué i per quins motius)
4. Indicadors d'alerta primerenca (format: → indicador, un per línia)
5. Probabilitat i lògica de transició (condició de ruptura)
Total: 380-440 paraules. To analític."""


async def stream_scenario(
    api_key: str,
    hypothesis: str,
    context: str,
    scenario_def: Dict[str, Any],
    vb_name: str,
    top_actor: str,
) -> AsyncGenerator[str, None]:
    prompt = f"""Genera el "{scenario_def['name']}" per a un informe d'intel·ligència estratègica:

CONFLICTE: {hypothesis or 'Anàlisi geopolítica estratègica'}
CONTEXT: {context or ''}
VARIABLE CLAU (VB/VR del MIC-MAC): {vb_name}
ACTOR MÉS MOBILITZAT (MACTOR): {top_actor}
CONFIGURACIÓ MORFOLÒGICA: {scenario_def['config']}
PROBABILITAT ESTIMADA: {scenario_def['prob']}

Estructura obligatòria (text corrent, sense títols markdown):
Paràgraf 1 — CONDICIONS INICIALS: Estat actual.
Paràgraf 2 — SEQÜÈNCIA D'EVENTS: Cronologia anys 1, 2-3, 4-5.
Paràgraf 3 — ACTORS IMPULSORS: Qui fa qué, qui guanya, qui perd.
Paràgraf 4 — INDICADORS D'ALERTA (cada un en una línia → indicador).
Paràgraf 5 — PROBABILITAT {scenario_def['prob']} I LÒGICA DE TRANSICIÓ.
380-440 paraules. To analític."""

    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }
    body = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 1000,
        "stream": True,
        "system": ANTHROPIC_SYSTEM,
        "messages": [{"role": "user", "content": prompt}],
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=body,
        ) as response:
            if response.status_code != 200:
                error = await response.aread()
                raise RuntimeError(f"Anthropic API {response.status_code}: {error.decode()}")
            async for line in response.aiter_lines():
                if not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if not payload:
                    continue
                try:
                    data = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if data.get("type") != "content_block_delta":
                    continue
                delta = data.get("delta") or {}
                text = ""
                if delta.get("type") == "text_delta":
                    text = delta.get("text") or ""
                elif isinstance(delta, dict):
                    text = delta.get("text") or ""
                if text:
                    yield text


class ProspectiveService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_project(
        self,
        case_id: Optional[int],
        title: str,
        hypothesis: str,
        context: str,
    ) -> ProspectiveProject:
        project = ProspectiveProject(
            case_id=case_id,
            title=title,
            hypothesis=hypothesis,
            context=context,
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def get_project(self, project_id: int) -> Optional[ProspectiveProject]:
        result = await self.db.execute(select(ProspectiveProject).where(ProspectiveProject.id == project_id))
        return result.scalar_one_or_none()

    async def list_projects(self, case_id: Optional[int] = None) -> List[ProspectiveProject]:
        q = select(ProspectiveProject)
        if case_id is not None:
            q = q.where(ProspectiveProject.case_id == case_id)
        result = await self.db.execute(q.order_by(ProspectiveProject.created_at.desc()))
        return list(result.scalars().all())

    async def save_variables(self, project_id: int, variables: List[Dict[str, Any]]) -> int:
        existing = await self.db.execute(
            select(ProspectiveVariable).where(ProspectiveVariable.project_id == project_id)
        )
        for v in existing.scalars().all():
            self.db.delete(v)
        await self.db.flush()
        for i, v in enumerate(variables):
            obj = ProspectiveVariable(
                project_id=project_id,
                code=v.get("code", str(i))[:8],
                name=v.get("name", ""),
                var_type=v.get("type", "I"),
                description=v.get("desc", ""),
                order_index=i,
            )
            self.db.add(obj)
        await self.db.commit()
        return len(variables)

    async def save_actors(self, project_id: int, actors: List[Dict[str, Any]]) -> int:
        existing = await self.db.execute(
            select(ProspectiveActor).where(ProspectiveActor.project_id == project_id)
        )
        for a in existing.scalars().all():
            self.db.delete(a)
        await self.db.flush()
        for i, a in enumerate(actors):
            fins = a.get("fins", [])
            if isinstance(fins, str):
                goals = [x.strip() for x in fins.split(",") if x.strip()]
            else:
                goals = list(fins) if fins else []
            obj = ProspectiveActor(
                project_id=project_id,
                code=str(a.get("code", str(i)))[:8],
                name=a.get("name", ""),
                strategic_goals=goals,
                force_score=float(a.get("force", 3)),
                order_index=i,
            )
            self.db.add(obj)
        await self.db.commit()
        return len(actors)

    async def save_objectives(self, project_id: int, objectives: List[Dict[str, Any]]) -> int:
        existing = await self.db.execute(
            select(MACTORObjective).where(MACTORObjective.project_id == project_id)
        )
        for o in existing.scalars().all():
            self.db.delete(o)
        await self.db.flush()
        for i, o in enumerate(objectives):
            obj = MACTORObjective(
                project_id=project_id,
                code=str(o.get("id", str(i)))[:8],
                name=o.get("name", ""),
                order_index=i,
            )
            self.db.add(obj)
        await self.db.commit()
        return len(objectives)

    async def save_components(self, project_id: int, components: List[Dict[str, Any]]) -> int:
        existing = await self.db.execute(
            select(MorphComponent).where(MorphComponent.project_id == project_id)
        )
        for c in existing.scalars().all():
            self.db.delete(c)
        await self.db.flush()
        for i, c in enumerate(components):
            obj = MorphComponent(
                project_id=project_id,
                code=str(c.get("id", str(i)))[:8],
                name=c.get("name", ""),
                configurations=c.get("configs", []),
                order_index=i,
            )
            self.db.add(obj)
        await self.db.commit()
        return len(components)

    async def compute_micmac(self, project_id: int, matrix: List[List[int]]) -> Dict[str, Any]:
        result = calc_micmac(matrix)
        existing = await self.db.execute(select(MICMACResult).where(MICMACResult.project_id == project_id))
        mic_obj = existing.scalar_one_or_none()
        if mic_obj:
            mic_obj.matrix_direct = result["matrix_direct"]
            mic_obj.matrix_indirect = result["matrix_indirect"]
            mic_obj.motricite_direct = result["motricite_direct"]
            mic_obj.dependence_direct = result["dependence_direct"]
            mic_obj.sectors = result["sectors"]
            mic_obj.vb_index = result["vb_index"]
            mic_obj.vr_index = result["vr_index"]
        else:
            mic_obj = MICMACResult(
                project_id=project_id,
                matrix_direct=result["matrix_direct"],
                matrix_indirect=result["matrix_indirect"],
                motricite_direct=result["motricite_direct"],
                dependence_direct=result["dependence_direct"],
                sectors=result["sectors"],
                vb_index=result["vb_index"],
                vr_index=result["vr_index"],
            )
            self.db.add(mic_obj)
        await self.db.commit()
        return result

    async def compute_mactor(self, project_id: int, postures: List[List[int]]) -> Dict[str, Any]:
        result = calc_mactor(postures)
        existing = await self.db.execute(select(MACTORResult).where(MACTORResult.project_id == project_id))
        mac_obj = existing.scalar_one_or_none()
        if mac_obj:
            mac_obj.mobilisation_actors = result["mobilisation_actors"]
            mac_obj.mobilisation_objectives = result["mobilisation_objectives"]
            mac_obj.convergences_matrix = result["convergences_matrix"]
        else:
            mac_obj = MACTORResult(
                project_id=project_id,
                mobilisation_actors=result["mobilisation_actors"],
                mobilisation_objectives=result["mobilisation_objectives"],
                convergences_matrix=result["convergences_matrix"],
            )
            self.db.add(mac_obj)
        await self.db.commit()
        return result

    async def generate_scenarios_stream(self, project_id: int) -> AsyncGenerator[str, None]:
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key:
            yield f"data: {json.dumps({'event': 'error', 'message': 'ANTHROPIC_API_KEY no configurada'})}\n\n"
            return

        project = await self.get_project(project_id)
        if not project:
            yield f"data: {json.dumps({'event': 'error', 'message': 'Projecte no trobat'})}\n\n"
            return

        await self.db.execute(delete(ProspectiveScenario).where(ProspectiveScenario.project_id == project_id))
        await self.db.commit()

        variables_r = await self.db.execute(
            select(ProspectiveVariable)
            .where(ProspectiveVariable.project_id == project_id)
            .order_by(ProspectiveVariable.order_index)
        )
        variables = list(variables_r.scalars().all())

        actors_r = await self.db.execute(
            select(ProspectiveActor)
            .where(ProspectiveActor.project_id == project_id)
            .order_by(ProspectiveActor.order_index)
        )
        actors = list(actors_r.scalars().all())

        micmac_r = await self.db.execute(select(MICMACResult).where(MICMACResult.project_id == project_id))
        micmac = micmac_r.scalar_one_or_none()

        mactor_r = await self.db.execute(select(MACTORResult).where(MACTORResult.project_id == project_id))
        mactor = mactor_r.scalar_one_or_none()

        vb_name = "variable clau"
        if micmac and micmac.vb_index is not None and variables and micmac.vb_index < len(variables):
            vb_name = variables[micmac.vb_index].name

        top_actor = "actor principal"
        if mactor and mactor.mobilisation_actors and actors:
            top_idx = mactor.mobilisation_actors.index(max(mactor.mobilisation_actors))
            if top_idx < len(actors):
                top_actor = actors[top_idx].name

        scenario_defs = [
            {
                "name": "Escenari Infern",
                "type": "worst",
                "config": "Màxima expansió adversari + Resposta fragmentada + Actors passius",
                "prob": "BAIXA-MITJA",
            },
            {
                "name": "Escenari Tensió Crònica",
                "type": "intermediate-bad",
                "config": "Expansió moderada + Resposta parcial + Divisions internes",
                "prob": "ALTA",
            },
            {
                "name": "Escenari Equilibri Dinàmic",
                "type": "intermediate-good",
                "config": "Expansió estancada + Alternativa en construcció + Cohesió moderada",
                "prob": "MITJA",
            },
            {
                "name": "Escenari Cel",
                "type": "best",
                "config": "Retrocés expansió + Alternativa consolidada + Alta cohesió",
                "prob": "BAIXA",
            },
        ]

        for i, sc_def in enumerate(scenario_defs):
            yield (
                "data: "
                + json.dumps(
                    {
                        "event": "scenario_start",
                        "index": i,
                        "name": sc_def["name"],
                        "prob": sc_def["prob"],
                        "config": sc_def["config"],
                    }
                )
                + "\n\n"
            )
            full_text = ""
            try:
                async for chunk in stream_scenario(
                    api_key,
                    project.hypothesis or "",
                    project.context or "",
                    sc_def,
                    vb_name,
                    top_actor,
                ):
                    full_text += chunk
                    yield f"data: {json.dumps({'event': 'chunk', 'index': i, 'text': chunk})}\n\n"
            except Exception as e:
                logger.exception("Error generating scenario %s", i)
                yield f"data: {json.dumps({'event': 'error', 'index': i, 'message': str(e)})}\n\n"
                continue

            scenario = ProspectiveScenario(
                project_id=project_id,
                name=sc_def["name"],
                scenario_type=sc_def["type"],
                morphological_config=sc_def["config"],
                probability=sc_def["prob"].replace("-", "_"),
                narrative=full_text,
            )
            self.db.add(scenario)
            await self.db.commit()
            yield f"data: {json.dumps({'event': 'scenario_done', 'index': i})}\n\n"

        yield f"data: {json.dumps({'event': 'all_done'})}\n\n"
