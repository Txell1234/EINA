# Arxiu de branques unificades

El 2026-05-19 es van consolidar totes les branques a `master`. **Cap commit s'ha perdut** — tot el contingut està preservat aquí o via tags `archive/*`.

## Branca principal (codi actiu)

| Tag / ref | Commit | Contingut |
|-----------|--------|-----------|
| `master` | `e497973`+ | Backend complet, prospectiva, extracció, LLM multi-proveïdor, build frontend |

## Contingut recuperat de branques `codex/*`

| Tag | Commit | Recuperat a master |
|-----|--------|-------------------|
| `archive/codex/api-cost-mvp` | `9d80e06` | `docs/USER_GUIDES.md` (classificació APIs) |
| `archive/codex/catalog-quality` | `633b855` | `docs/CATALEG_FONTS_QUALITAT.md` |
| `archive/codex/source-checklist` | `cd35e46` | `docs/USER_GUIDES.md` (checklist avaluació fonts) |
| `archive/codex/intelligence-cycle` | `9ff899d` | `docs/DEVELOPER_GUIDE.md` (cicle intel·ligència) |
| `archive/codex/ingestion-plan` | `0039c71` | `docs/INGESTION_PLAN.md` |
| `archive/codex/objectives-governance` | `e6e7b84` | `docs/USER_GUIDES.md` (objectius i governança) |
| `archive/codex/osint-catalog` | `e67277c` | `data/osint_*.json`, `docs/OSINT_CATALOG.md`, `scripts/import_osint_resources.py` |
| `archive/codex/maltego-freemium` | `7a51f06` | `maltego_api.py`, `event_bus_service.py`, `financial_modeling_prep_api.py` |
| `archive/codex/ensembledata` | `1af0a37` | Millores parcials (ja cobertes parcialment a master) |
| `archive/codex/ensembledata-normalize` | `2184c0a` | `rss_api.py`, `I18nContext.tsx` |
| `archive/codex/osint-errors` | `6a6d3e1` | Lògica fusionada manualment on calia |
| `archive/codex/integration-diagnostics` | `ccdba86` | Referència al tag (canvis de codi superposats amb master) |
| `archive/codex/requirements-pins` | `93babe2` | Referència al tag (requirements ja actualitzats a master) |

## Prototip anterior

| Tag | Commit | Ubicació |
|-----|--------|----------|
| `archive/feature/prospective-ui-redesign` | `51be167` | `legacy/prospective-prototype/` (prototype React+Flask anterior) |

## Com recuperar un commit complet

```bash
git show archive/codex/osint-catalog
git checkout archive/codex/osint-catalog -- ruta/fitxer
```
