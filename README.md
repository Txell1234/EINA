# EINA — Plataforma d'Intel·ligència Estratègica

EINA és una plataforma d'anàlisi d'intel·ligència estratègica que implementa
la metodologia de prospectiva de l'escola Godet (MIC-MAC, MACTOR, anàlisi
morfològic) i l'alimenta amb dades OSINT en temps real.

**Pipeline complet:**
```
Fonts OSINT → Extracció estructurada (LLM) → Variables MIC-MAC →
Actors MACTOR → Espai morfològic → Escenaris narratius → Monitors d'alerta
```

## Característiques principals

- **Recollida OSINT**: GDELT (events geopolítics globals), RSS de think-tanks
  (IISS, Chatham House, RAND, CFR, CSIS, Brookings, Elcano), OpenSanctions,
  Reddit, GitHub, Wayback Machine, DNS/WHOIS, **xarxes socials** (TikTok, Instagram,
  X/Twitter, YouTube, Threads via EnsembleData)
- **Q2FS (pregunta analítica)**: pipeline inquiry amb parse híbrid, OSINT scoped,
  síntesi traçable, export PDF/HTML, dashboard batch rerun i mode lite/full
- **Extracció estructurada**: Claude Haiku extreu actors, declaracions i postures
  (–2..+2) dels articles OSINT, amb detecció d'al·lucinacions (grounding score)
- **Anàlisi prospectiva**: MIC-MAC (motricitat, dependència, VB/VR),
  MACTOR (mobilització, convergències), anàlisi morfològic
- **Escenaris**: 4 escenaris narratius (Infern/Tensió/Equilibri/Cel) generats
  per Claude Sonnet via streaming SSE, 380-440 paraules cadascun
- **Panel Delphi**: mode multi-expert per a matrius MIC-MAC amb consens i
  detecció de discrepàncies (σ > 1.0)
- **Monitors d'alerta**: indicadors d'alerta primerenca → queries OSINT
  automàtiques cada 30 minuts
- **Export**: informes complets en PDF (weasyprint) i DOCX (python-docx)
- **Multilingüe**: català, castellà, anglès, francès

## Inici ràpid (Docker)

**Prerequisit**: Docker Desktop instal·lat.

```bash
# 1. Clona el repo
git clone https://github.com/Txell1234/EINA.git
cd EINA

# 2. Configura les variables d'entorn
cp backend/env.example backend/.env
# Edita backend/.env:
#   SECRET_KEY  → genera amb: python -c "import secrets; print(secrets.token_hex(32))"
#   ANTHROPIC_API_KEY → clau de console.anthropic.com (o OPENAI_API_KEY)

# 3. Arrenca (desenvolupament — SQLite)
docker compose up --build

# 3b. Staging/producció (PostgreSQL + Redis + traces OTEL + Prometheus/Grafana)
docker compose -f docker-compose.yml -f docker-compose.full.yml --profile full up --build

# 4. Accedeix a http://localhost:3000
# 5. Crea un compte a la pantalla de registre

# 6. (Opcional) Carrega dades de demo
docker exec eina-backend python seed_demo.py
```

## Inici ràpid (local, sense Docker)

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

cp env.example .env
# Edita .env: SECRET_KEY i almenys una clau LLM (ANTHROPIC_API_KEY o OPENAI_API_KEY)

python -m app.main
# → http://localhost:8000/docs (Swagger)

# Frontend (terminal nova)
cd frontend
npm install
npm run dev
# → http://localhost:3000
```

## Primer ús

1. Registra't a http://localhost:3000
2. Crea un nou cas (p.ex. "Indo-Pacífic 2030")
3. Recull dades OSINT → selecciona **GDELT** o **RSS (IISS, CFR)**
4. Ves a **Anàlisi Prospectiva** → pas 0: extreu actors i postures
5. Defineix variables MIC-MAC → calcula (VB i VR s'identifiquen automàticament)
6. Defineix actors i objectius MACTOR → calcula convergències
7. Defineix components morfològics → genera escenaris via IA
8. Activa monitors d'alerta per a cada escenari
9. Descarrega l'informe complet en PDF o DOCX

## Stack tecnològic

- **Backend**: FastAPI (async) + SQLAlchemy 2.0 + SQLite/PostgreSQL
- **Frontend**: React 18 + TypeScript strict + Vite + Tanstack Query
- **LLM**: Anthropic Claude (Haiku per extracció, Sonnet per escenaris)
  o OpenAI (GPT-4o-mini / GPT-4o) o Google Gemini
- **Export**: WeasyPrint (PDF) + python-docx (DOCX)
- **Contenidors**: Docker + Nginx

## Variables d'entorn principals

| Variable | Obligatòria | Descripció |
|---|---|---|
| `SECRET_KEY` | ✓ | Clau JWT (genera amb `secrets.token_hex(32)`) |
| `ANTHROPIC_API_KEY` | Una d'aquestes | Clau Anthropic Claude |
| `OPENAI_API_KEY` | Una d'aquestes | Clau OpenAI |
| `GEMINI_API_KEY` | Una d'aquestes | Clau Google Gemini |
| `LLM_PROVIDER` | No | `auto` (defecte), `anthropic`, `openai`, `gemini` |
| `DATABASE_URL` | No | SQLite per defecte; PostgreSQL amb `--profile full` |
| `ENSEMBLEDATA_API_KEY` | No | Xarxes socials OSINT (TikTok, Instagram, X, etc.) |
| `REDIS_URL` | No | Cache Q2FS distribuïda (profile `full`) |
| `OTEL_ENABLED` | No | Traces OpenTelemetry → Jaeger (profile `full`) |
| `NEWS_API_KEY` | No | newsapi.org — millora la recollida de notícies |

## Observabilitat (profile `full`)

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3001 (admin/admin — canvia en producció)
- **Jaeger**: http://localhost:16686
- **Health ampliat**: `GET /health` inclou Redis, cache Q2FS i inquiry scheduler

## Tests

```bash
# Backend (274+ tests)
cd backend && python -m pytest tests/unit -q

# Frontend unitari (Vitest)
cd frontend && npm run test

# E2E Playwright (Q2FS + OSINT social)
cd frontend && npm run e2e
```

## Llicència

Tots els drets reservats © 2025-2026 Meritxell Perelló Pinto / Amb Tu
