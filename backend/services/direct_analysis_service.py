"""
Direct Analysis Service
Accepts raw text (report, article, intelligence brief, meeting notes)
and extracts a complete Godet analysis structure using Claude Sonnet.

Output:
  - hypothesis: the strategic conflict as a Godet hypothesis
  - context: system context paragraph
  - variables: list of MIC-MAC variables (code, name, type, desc)
  - actors: list of MACTOR actors (code, name, force, goals)
  - components: list of morphological components (code, name, configurations)
  - statements: list of extracted actor statements (posture_value, topic, etc.)
  - confidence: overall confidence score 0-1
  - warnings: list of quality warnings for the analyst
"""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from services.llm_service import LLMService

logger = logging.getLogger(__name__)

DIRECT_ANALYSIS_PROMPT = """Ets un expert en anàlisi d'intel·ligència estratègica i en la metodologia de prospectiva de l'escola Godet (LIPSOR).

A partir del text que t'aporto, extreu una anàlisi prospectiva completa estructurada.

REGLES CRÍTIQUES:
1. Variables MIC-MAC: han de ser MESURES DE VARIACIÓ, no temes genèrics.
   Format obligatori: "Grau en què [variable evoluciona]"
   CORRECTE: "Grau en què la BRI avança sense resistència significativa"
   INCORRECTE: "La BRI", "Economia de l'Índia"

2. Variables (8-12): mix d'internes (I, accionables pels actors) i externes (E, de l'entorn).

3. Actors (5-8): els que poden influir sobre l'evolució del sistema.
   Força 1-5: 5=cap d'estat/institució suprema, 4=ministre/gran institució,
   3=alt funcionari/institució important, 2=portaveu, 1=actor local/menor.

4. Components morfològics (3-5): dimensions sobre les quals el sistema pot evolucionar.
   Cada component té 2-4 configuracions mútuament excloents.

5. Hipòtesi: frase que descriu el conflicte estratègic central del text.
   Ha de ser una tensió entre forces o actors identificables.

6. Declaracions: extracte de les postures dels actors identificats.
   posture_value: +2=molt favorable, +1=favorable, 0=neutral, -1=contrari, -2=molt contrari

Retorna ÚNICAMENT un JSON amb aquesta estructura exacta (sense cap text fora del JSON):

{
  "hypothesis": "El conflicte entre X i Y per Z determinarà...",
  "context": "Paràgraf de 3-4 frases que descriu el sistema i el seu context",
  "confidence": 0.0-1.0,
  "warnings": ["avís 1 si text és massa curt o ambigu", "..."],
  "variables": [
    {
      "code": "A",
      "name": "Nom curt (màx 40 caràcters)",
      "type": "I",
      "desc": "Grau en què...",
      "rationale": "Per què és rellevant per a la hipòtesi"
    }
  ],
  "actors": [
    {
      "code": "CH",
      "name": "Nom de l'actor",
      "force": 4,
      "strategic_goals": ["objectiu 1", "objectiu 2"],
      "rationale": "Per què és un actor clau"
    }
  ],
  "components": [
    {
      "code": "C1",
      "name": "Dimensió morfològica",
      "configurations": [
        {"label": "Configuració A", "desc": "Descripció breu"},
        {"label": "Configuració B", "desc": "Descripció breu"}
      ]
    }
  ],
  "statements": [
    {
      "actor": "Nom actor",
      "posture_toward": "Actor o objecte de la postura",
      "posture_value": 2,
      "topic": "Tema en 1-3 paraules",
      "statement": "Declaració o postura observada",
      "framing": "ofensiu|defensiu|constructiu|amenaçador|conciliador|neutral"
    }
  ]
}

Text a analitzar:
"""


def _clean_json(text: str) -> str:
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]
    return re.sub(r",\s*([}\]])", r"\1", text.strip())


def _validate_result(result: dict) -> tuple[dict, list[str]]:
    """Validate and fix the extracted result. Returns (fixed_result, warnings)."""
    warnings: list[str] = list(result.get("warnings", []))

    for v in result.get("variables", []):
        if not v.get("desc", "").lower().startswith("grau en"):
            v["desc"] = f"Grau en què {v.get('name', 'la variable evoluciona')}"
            warnings.append(
                f"Variable {v.get('code', '?')}: descripció corregida al format Godet"
            )

    seen_codes: set[str] = set()
    for i, v in enumerate(result.get("variables", [])):
        code = v.get("code", "")
        if code in seen_codes:
            new_code = chr(65 + i)
            v["code"] = new_code
            warnings.append(f"Codi variable duplicat corregit: {code}→{new_code}")
        seen_codes.add(v.get("code", ""))

    for a in result.get("actors", []):
        force = a.get("force", 3)
        if not isinstance(force, int) or force < 1 or force > 5:
            a["force"] = 3
            warnings.append(f"Força actor {a.get('name', '?')} corregida a 3")

    for c in result.get("components", []):
        cfgs = c.get("configurations", [])
        if len(cfgs) < 2:
            warnings.append(
                f"Component {c.get('code', '?')} té menys de 2 configuracions"
            )
        if len(cfgs) > 4:
            c["configurations"] = cfgs[:4]
            warnings.append(
                f"Component {c.get('code', '?')} limitat a 4 configuracions"
            )

    conf = result.get("confidence", 0.5)
    if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
        result["confidence"] = 0.5

    n_vars = len(result.get("variables", []))
    n_actors = len(result.get("actors", []))
    if n_vars < 4:
        warnings.append(
            f"Poques variables ({n_vars}): el text pot ser massa curt o poc específic"
        )
    if n_actors < 2:
        warnings.append(
            f"Pocs actors ({n_actors}): comprova que el text descriu un conflicte entre parts"
        )

    return result, warnings


class DirectAnalysisService:
    def __init__(self):
        self.llm = LLMService()

    def analyze(self, text: str) -> dict[str, Any]:
        """
        Synchronous analysis — use in a thread pool for async contexts.
        Accepts raw text, returns full Godet analysis structure.
        """
        if not self.llm.configured:
            return {
                "error": "Cap proveïdor LLM configurat. "
                         "Afegeix ANTHROPIC_API_KEY o OPENAI_API_KEY al .env",
                "confidence": 0,
            }

        if len(text.strip()) < 100:
            return {
                "error": "El text és massa curt. "
                         "Proporciona almenys un paràgraf descriptiu del conflicte estratègic.",
                "confidence": 0,
            }

        truncated = text[:8000]
        if len(text) > 8000:
            truncated += (
                "\n\n[TEXT TRUNCAT — els primers 8.000 caràcters han estat analitzats. "
                f"El text original tenia {len(text):,} caràcters.]"
            )

        prompt = DIRECT_ANALYSIS_PROMPT + truncated
        raw = ""

        try:
            raw = self.llm.complete(
                prompt,
                max_tokens=4096,
                prefer_model="sonnet",
            )
            cleaned = _clean_json(raw)
            result = json.loads(cleaned)
        except json.JSONDecodeError:
            logger.error("DirectAnalysis: JSON parse failed, attempting recovery")
            result = self._recover_analysis(raw)
            if not result:
                return {
                    "error": "El model no ha retornat un JSON vàlid. Torna a intentar-ho.",
                    "confidence": 0,
                }
        except Exception as e:
            logger.error("DirectAnalysis error: %s", e)
            return {"error": str(e), "confidence": 0}

        result, new_warnings = _validate_result(result)
        result["warnings"] = list(set(result.get("warnings", []) + new_warnings))
        result["text_length"] = len(text)
        result["truncated"] = len(text) > 8000

        return result

    def _recover_analysis(self, raw: str) -> dict | None:
        """Try to extract a partial valid JSON from a malformed response."""
        start = raw.find("{")
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        candidate = re.sub(r",\s*([}\]])", r"\1", raw[start : i + 1])
                        return json.loads(candidate)
                    except json.JSONDecodeError:
                        return None
        return None
