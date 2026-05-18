# Historial unificat de branques

Totes les branques s'han **fusionat a `master`** amb merge commits (`--no-ff`), de manera que l'historial complet es conserva a GitHub. Res s'ha esborrat del repositori.

## Branca única de treball

**`master`** — conté tot el codi actiu + tot el contingut de les antigues branques.

## Merge commits (preserven l'historial de cada branca)

| Merge commit | Branca original | Contingut |
|--------------|-----------------|-----------|
| `21a3d0b` | `codex/maltego-freemium` | Maltego, event bus, FMP |
| `28cdfc1` | `codex/ensembledata` | EnsembleData guardrails |
| `6aef400` | `codex/ensembledata-normalize` | Normalització paràmetres, I18n, dashboard |
| `ce0a72d` | `codex/integration-diagnostics` | Diagnòstic integracions |
| `efb4bde` | `codex/integration-diagnostics` (variant) | Integració status |
| `f5be464` | `codex/requirements-pins` | Pins de dependències |
| `9d61baf` | `codex/osint-errors` | Errors OSINT i mètriques qualitat |
| `0bd8e1f` | `feature/prospective-ui-redesign` | Prototip monorepo (vegeu `legacy/` i `OSINT/`) |

Cherry-picks directes (abans dels merges):

| Commit | Branca | Contingut |
|--------|--------|-----------|
| `85dfd33` | `codex/api-cost-mvp` | Classificació APIs |
| `c512ca2` | `codex/catalog-quality` | Catàleg fonts qualitat |
| `12aa35c` | `codex/source-checklist` | Checklist avaluació |
| `abdf88b` | `codex/intelligence-cycle` | Cicle intel·ligència |
| `bd15338` | `codex/ingestion-plan` | Pla ingestió |
| `338f616` | `codex/objectives-governance` | Objectius i governança |
| `10060f7` | `codex/osint-catalog` | Catàleg OSINT + dades JSON |

## Tags de reserva

Cada branca antiga té un tag `archive/*` que apunta al commit original:

```bash
git tag -l "archive/*"
git log archive/codex/osint-catalog
git show archive/feature/prospective-ui-redesign
```

## On trobar contingut específic

| Contingut | Ubicació |
|-----------|----------|
| App principal (backend + frontend) | `/backend`, `/frontend` |
| Prototip antic prospectiu | `/legacy/prospective-prototype/` |
| Còpia del prototip (merge historial) | `/OSINT/` |
| Documentació OSINT | `/docs/`, `/data/`, `/APIS_ANALYSIS.md` |
| Catàleg fonts | `/data/osint_sources.json`, `/docs/OSINT_CATALOG.md` |

## Recuperar un fitxer d'una branca antiga

```bash
git checkout archive/codex/osint-catalog -- ruta/del/fitxer
```
