"""
EINA — Seed de dades de demo
Crea un cas de mostra sobre l'Indo-Pacífic amb dades pre-carregades
per poder provar la plataforma sense fer crides reals a APIs externes.

Ús:
  python seed_demo.py                    # local
  docker exec eina-backend python seed_demo.py  # Docker
"""
from __future__ import annotations

import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# Allow override via env for Docker
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./osint_platform.db")


async def seed() -> None:
    # Late imports after env is set
    from app.database import AsyncSessionLocal, engine, Base
    from models.user import User
    from models.case import Case, CaseStatus, CaseType
    from models.osint import OSINTQuery, OSINTResult, QueryStatus
    from models.prospective import (
        ProspectiveProject, ProspectiveVariable,
        ProspectiveActor, MACTORObjective, MorphComponent,
        ProspectiveScenario, MICMACResult,
    )
    from services.micmac_math import compute_micmac_pure
    from passlib.context import CryptContext
    from sqlalchemy import select

    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Matriu MIC-MAC 5×5 coherent amb el cas Indo-Pacífic (diagonal = 0)
    # Files/columnes: A=Expansió BRI, B=Índia, C=QUAD, D=Corredors, E=UE
    DEMO_MICMAC_MATRIX = [
        [0, 1, 2, 3, 1],
        [2, 0, 2, 3, 2],
        [3, 1, 0, 2, 2],
        [2, 2, 2, 0, 2],
        [1, 1, 2, 2, 0],
    ]
    DEMO_VAR_CODES = ["A", "B", "C", "D", "E"]

    async def ensure_micmac_result(db_session, project_id: int) -> None:
        existing_micmac = (
            await db_session.execute(
                select(MICMACResult).where(MICMACResult.project_id == project_id)
            )
        ).scalar_one_or_none()
        if existing_micmac and existing_micmac.matrix_direct:
            return
        if existing_micmac:
            await db_session.delete(existing_micmac)
            await db_session.flush()
        micmac = compute_micmac_pure(DEMO_MICMAC_MATRIX, DEMO_VAR_CODES)
        db_session.add(
            MICMACResult(
                project_id=project_id,
                matrix_direct=micmac["matrix_direct"],
                matrix_indirect=micmac["matrix_indirect"],
                motricite_direct=micmac["motricitat_direct"],
                dependence_direct=micmac["dependencia_direct"],
                sectors=micmac["sectors"],
                vb_index=micmac["vb_index"],
                vr_index=micmac["vr_index"],
            )
        )
        print("[OK] Matriu MIC-MAC 5x5 demo creada (gràfic de sectors actiu)")

    # Ensure tables exist
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:

        # ── 1. Demo user ──────────────────────────────────────────────────
        existing = (await db.execute(select(User).where(User.email == "demo@eina.cat"))).scalar_one_or_none()
        if existing:
            print("[i] Demo user already exists (demo@eina.cat)")
            user = existing
        else:
            user = User(
                email="demo@eina.cat",
                hashed_password=pwd.hash("demo1234"),
                full_name="Meritxell Perelló",
                is_active=True,
                is_superuser=True,
            )
            db.add(user)
            await db.flush()
            print("[OK] Usuari creat: demo@eina.cat / demo1234")

        # ── 2. Demo case ──────────────────────────────────────────────────
        existing_case = (await db.execute(
            select(Case).where(Case.name == "Indo-Pacífic 2030")
        )).scalar_one_or_none()

        if existing_case:
            print("[i] Demo case already exists")
            case = existing_case
        else:
            case = Case(
                name="Indo-Pacífic 2030",
                description="Anàlisi prospectiva de la competència estratègica a la regió Indo-Pacífica. "
                            "Focus: Belt and Road Initiative, QUAD, corredors alternatius i posicionament de l'Índia.",
                case_type=CaseType.GEOPOLITICAL,
                status=CaseStatus.COMPLETED,
            )
            db.add(case)
            await db.flush()
            print(f"[OK] Cas creat: '{case.name}' (id={case.id})")

        # ── 3. Sample OSINT results ───────────────────────────────────────
        existing_queries = (await db.execute(
            select(OSINTQuery).where(OSINTQuery.case_id == case.id)
        )).scalars().all()

        if not existing_queries:
            sample_articles = [
                {
                    "title": "China's BRI Faces Growing Resistance in Southeast Asia",
                    "content": "Chinese Foreign Minister stated that the Belt and Road Initiative "
                               "remains a priority despite growing resistance from QUAD nations. "
                               "India has proposed alternative connectivity corridors as a response. "
                               "The QUAD alliance expressed strong opposition to BRI expansion in the region.",
                    "url": "https://example.com/bri-resistance",
                    "date": "2025-11-15",
                    "source": "gdelt",
                },
                {
                    "title": "India-US Strategic Partnership Deepens in Indo-Pacific",
                    "content": "India and the United States announced a new strategic partnership "
                               "to counter Chinese influence in the Indo-Pacific. "
                               "Prime Minister Modi declared India's commitment to a free and open Indo-Pacific. "
                               "The QUAD framework is being strengthened with new military exercises.",
                    "url": "https://example.com/india-us-partnership",
                    "date": "2025-11-20",
                    "source": "rss_feed",
                },
                {
                    "title": "EU Announces Indo-Pacific Strategy Update",
                    "content": "The European Union updated its Indo-Pacific strategy, "
                               "signaling a more active role in regional security. "
                               "EU officials expressed concern about BRI debt traps and "
                               "announced alternative infrastructure financing for partner countries.",
                    "url": "https://example.com/eu-indo-pacific",
                    "date": "2025-11-22",
                    "source": "rss_feed",
                },
            ]

            for art in sample_articles:
                q = OSINTQuery(
                    case_id=case.id,
                    query_type=art["source"],
                    query_params={"query": art["title"][:100]},
                    status=QueryStatus.COMPLETED,
                )
                db.add(q)
                await db.flush()
                r = OSINTResult(
                    query_id=q.id,
                    data={
                        "title": art["title"],
                        "content": art["content"],
                        "text": art["content"],
                        "url": art["url"],
                        "date": art["date"],
                        "source": art["source"],
                    },
                    status="completed",
                )
                db.add(r)
            print(f"[OK] {len(sample_articles)} articles OSINT de mostra creats")

        # ── 4. Prospective project ────────────────────────────────────────
        existing_proj = (await db.execute(
            select(ProspectiveProject).where(ProspectiveProject.case_id == case.id)
        )).scalar_one_or_none()

        if existing_proj:
            print("[i] Demo prospective project already exists")
            project = existing_proj
        else:
            project = ProspectiveProject(
                case_id=case.id,
                title="Indo-Pacífic 2030 — Anàlisi Prospectiva",
                hypothesis="La competència estratègica entre Xina i el bloc occidental (QUAD+UE) "
                           "per la influència a l'Indo-Pacífic determinarà l'arquitectura de seguretat "
                           "regional i el futur de la connectivitat econòmica global.",
                context="L'Indo-Pacífic engloba el 60% del PIB mundial i el 50% del comerç marítim. "
                        "La Belt and Road Initiative xinesa competeix amb els corredors alternatius "
                        "proposats per l'Índia i els socis occidentals. El QUAD (EUA, Japó, "
                        "Austràlia, Índia) s'ha consolidat com a contrapès estratègic.",
            )
            db.add(project)
            await db.flush()
            print(f"[OK] Projecte prospectiu creat (id={project.id})")

            # ── 5. Variables MIC-MAC ──────────────────────────────────────
            variables = [
                ("A", "Expansió BRI", "I",
                 "Grau en què la BRI avança sense resistència significativa"),
                ("B", "Influència Índia", "E",
                 "Grau d'influència de l'Índia sobre els països de l'Indo-Pacífic"),
                ("C", "Cohesió QUAD", "E",
                 "Grau de cohesió i capacitat d'acció del QUAD"),
                ("D", "Corredors Alternatius", "I",
                 "Grau en què els corredors indis i occidentals representen alternativa a la BRI"),
                ("E", "Postura UE", "E",
                 "Grau d'implicació activa de la UE a la regió Indo-Pacífica"),
            ]
            for i, (code, name, vtype, desc) in enumerate(variables):
                db.add(ProspectiveVariable(
                    project_id=project.id, code=code, name=name,
                    var_type=vtype, description=desc, order_index=i,
                ))
            print(f"[OK] {len(variables)} variables MIC-MAC creades")

            # ── 6. Actors MACTOR ──────────────────────────────────────────
            actors = [
                ("CH", "Xina", 5, ["Consolidar BRI", "Lideratge regional"]),
                ("IN", "Índia", 4, ["Lideratge Indo-Pacífic", "Corredors alternatius"]),
                ("QD", "QUAD", 4, ["Contenció BRI", "Ordre regional obert"]),
                ("UE", "Unió Europea", 3, ["Diversificació comercial", "Seguretat marítima"]),
            ]
            for i, (code, name, force, goals) in enumerate(actors):
                db.add(ProspectiveActor(
                    project_id=project.id, code=code, name=name,
                    force_score=float(force), strategic_goals=goals, order_index=i,
                ))

            objectives = [
                ("O1", "Expansió BRI sense obstacles"),
                ("O2", "Alternativa de connectivitat viable"),
                ("O3", "Cohesió del QUAD"),
                ("O4", "Implicació activa de la UE"),
            ]
            for i, (code, name) in enumerate(objectives):
                db.add(MACTORObjective(
                    project_id=project.id, code=code, name=name, order_index=i,
                ))
            print(f"[OK] {len(actors)} actors i {len(objectives)} objectius MACTOR creats")

            # ── 7. Morphological components ───────────────────────────────
            components = [
                ("C1", "Estat BRI", [
                    {"label": "Expansió plena", "desc": "La BRI avança sense obstacles significatius"},
                    {"label": "Estancament", "desc": "La BRI es consolida però no s'expandeix"},
                    {"label": "Retrocés", "desc": "La BRI perd terreny davant de les alternatives"},
                ]),
                ("C2", "Corredors Alternatius", [
                    {"label": "Consolidació", "desc": "Els corredors indis i occidentals es consoliden"},
                    {"label": "Progrés parcial", "desc": "Avenços parcialment operacionals"},
                ]),
                ("C3", "Cohesió QUAD", [
                    {"label": "Alta cohesió", "desc": "El QUAD actua de forma coordinada i efectiva"},
                    {"label": "Divisió interna", "desc": "El QUAD mostra fractures internes"},
                ]),
            ]
            for i, (code, name, configs) in enumerate(components):
                db.add(MorphComponent(
                    project_id=project.id, code=code, name=name,
                    configurations=configs, order_index=i,
                ))
            print(f"[OK] {len(components)} components morfològics creats (espai: 3x2x2=12 combinacions)")

            # ── 8. Demo scenarios (pre-generated, no LLM needed) ──────────
            scenarios = [
                {
                    "name": "Escenari Infern",
                    "scenario_type": "infern",
                    "probability": "BAIXA-MITJA",
                    "morphological_config": "Expansió plena BRI + Progrés parcial corredors + Divisió interna QUAD",
                    "narrative": """La Xina consolida la Belt and Road Initiative a l'Indo-Pacífic mentre el QUAD experimenta divisions internes que limiten la seva capacitat de resposta coordinada. Els corredors alternatius progressen parcialment però sense prou capital polític per a competir.

Any 1: La Xina firma nous acords BRI amb Sri Lanka, Bangladesh i les Maldives, incrementant la seva presència portuària. El QUAD es veu paralitzat per divergències entre EUA i Índia sobre l'abast de la resposta militar.

Anys 2-3: L'Índia, incapaç d'obtenir compromisos financers suficients dels socis occidentals, redueix l'ambició dels seus corredors alternatius. La UE es manté en una postura d'observació. Diverses capitals de l'ASEAN accepten condicions BRI davant l'absència d'alternatives viables.

Anys 4-5: La Xina controla infraestructura estratègica en 8 nous països de la regió. El QUAD existeix formalment però ha perdut credibilitat operativa. L'ordre marítim de l'Indo-Pacífic s'ha reconfigurado parcialment en favor dels interessos xinesos.

→ Creixement ≥15% en finançament BRI anual
→ Retirada EUA d'exercicis militars QUAD
→ Nous acords portuaris xinesos a l'Oceà Índic
→ Declaracions de neutralitat de membres ASEAN

Probabilitat BAIXA-MITJA: Requereix la coincidència de disfuncionalitat del QUAD i avançament BRI simultanis. La fortalesa de la coalició occidental fa aquest escenari poc probable però no descartable.""",
                },
                {
                    "name": "Escenari Tensió Crònica",
                    "scenario_type": "tensio",
                    "probability": "ALTA",
                    "morphological_config": "Estancament BRI + Progrés parcial corredors + Alta cohesió QUAD",
                    "narrative": """L'Indo-Pacífic s'estabilitza en un equilibri de competència crònica sense resolució definitiva. La BRI s'estanca davant la pressió del QUAD cohesionat, però els corredors alternatius progressen a ritme insuficient per a omplir el buit.

Any 1: El QUAD intensifica els exercicis militars i la coordinació diplomàtica. La Xina manté la BRI però enfronta resistència creixent en mercats clau. L'Índia llança el corredor IMEC amb suport limitat.

Anys 2-3: La competència s'institucionalitza. Cada potència consolida la seva esfera d'influència sense guanys decisius. Les economies de l'ASEAN es converteixen en el camp de batalla principal, diversificant deliberadament entre blocs.

Anys 4-5: L'Indo-Pacífic funciona amb dos sistemes de connectivitat paral·lels, ineficients però estables. Cap bloc ha guanyat, però el cost de la competència pesa sobre tots els actors.

→ Manteniment del ritme actual d'exercicis QUAD
→ Nous incidents marítims al Mar de la Xina Meridional
→ Anuncis BRI sense implementació efectiva
→ Avenços parcials del corredor IMEC

Probabilitat ALTA: Representa l'extrapolació de les tendències actuals sense ruptures majors. És l'escenari de menor esforç col·lectiu i, per tant, el més probable a curt-mig termini.""",
                },
                {
                    "name": "Escenari Equilibri Dinàmic",
                    "scenario_type": "equilibri",
                    "probability": "MITJA",
                    "morphological_config": "Estancament BRI + Consolidació corredors + Alta cohesió QUAD",
                    "narrative": """El QUAD cohesionat i els corredors alternatius consolidades ofereixen una alternativa creïble a la BRI, estabilitzant la regió en un equilibri multipolier dinàmic però gestionable.

Any 1: L'Índia, amb suport financer del G7, llança el corredor IMEC en fases concretes. El QUAD coordina una estratègia de connectivitat comú. La BRI enfrenta dificultats de finançament interns a la Xina.

Anys 2-3: Diversos països de l'ASEAN es decanten per l'alternativa occidental davant condicions més transparents. La UE augmenta la seva implicació estratègica. La Xina renegocia alguns projectes BRI amb menors contrapartides.

Anys 4-5: Dos sistemes de connectivitat competitius coexisteixen, amb els països de la regió exercint poder de negociació entre ambdós. L'Índia emergeix com a pivot indispensable de l'arquitectura regional.

→ Ratificació parlamentària del corredor IMEC en 3+ països
→ G7 anuncia finançament ≥$50B per a infraestructura Indo-Pacífica
→ Renegociació de 5+ projectes BRI existents
→ Acords de seguretat marítima QUAD ampliats

Probabilitat MITJA: Requereix manteniment de la cohesió occidental i implementació efectiva dels corredors alternatius, ambdós condicionals però possibles.""",
                },
                {
                    "name": "Escenari Cel",
                    "scenario_type": "cel",
                    "probability": "BAIXA",
                    "morphological_config": "Retrocés BRI + Consolidació corredors + Alta cohesió QUAD",
                    "narrative": """El retrocés de la BRI combinat amb la plena consolidació dels corredors alternatius i la màxima cohesió del QUAD transforma l'arquitectura de l'Indo-Pacífic de forma definitiva.

Any 1: Crisi financera interna xinesa força una retallada dràstica del finançament BRI. Diversos projectes s'aturen o es renegocien. El QUAD aprofita la finestra d'oportunitat per a accelerar la implementació dels corredors.

Anys 2-3: L'Índia i els socis occidentals assumeixen el lideratge de la connectivitat regional. La UE es compromet amb finançament i presència militar lleugera. Diverses capitals de l'ASEAN renegocien actius BRI.

Anys 4-5: L'Indo-Pacífic funciona sota una arquitectura de connectivitat multipolier amb preeminència occidental. La Xina manté influència però ha perdut el lideratge de la narrativa de la connectivitat global.

→ Reducció ≥30% en nous compromisos BRI anuals
→ Finalització de la primera fase del corredor IMEC
→ Incidents Xina-QUAD sense escalada gràcies a mecanismes de desescalada
→ 10+ països de l'ASEAN seleccionen alternatives a la BRI per a nous projectes

Probabilitat BAIXA: Requereix una crisi xinesa interna i una execució occidental impecable simultànies. Poc probable però cal monitoritzar els seus indicadors d'alerta.""",
                },
            ]
            for s in scenarios:
                db.add(ProspectiveScenario(
                    project_id=project.id,
                    **s,
                ))
            print(f"[OK] {len(scenarios)} escenaris prospectius pre-generats")

        demo_project = (
            await db.execute(
                select(ProspectiveProject).where(ProspectiveProject.case_id == case.id)
            )
        ).scalar_one_or_none()
        if demo_project:
            await ensure_micmac_result(db, demo_project.id)

        await db.commit()

    print("\n" + "=" * 60)
    print("EINA — Dades de demo carregades correctament")
    print("=" * 60)
    print("\n  Accedeix a http://localhost:3000")
    print("  Email:      demo@eina.cat")
    print("  Contrasenya: demo1234")
    print("\n  El cas 'Indo-Pacífic 2030' ja conté:")
    print("  - 3 articles OSINT de mostra")
    print("  - Projecte prospectiu complet (5 variables, 4 actors, 3 components)")
    print("  - Matriu MIC-MAC 5x5 preomplerta (gràfic de sectors)")
    print("  - 4 escenaris narratius pre-generats")
    print("\n  IMPORTANT: Canvia la contrasenya al primer ús!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())
