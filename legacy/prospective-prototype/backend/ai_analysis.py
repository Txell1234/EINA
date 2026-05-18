"""AI analysis: OpenAI when available, else demo."""
import os
import json
from typing import List, Dict, Any

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def _extract_texts_from_osint(osint_list) -> str:
    texts = []
    for o in osint_list:
        if not o.raw_data:
            continue
        rd = o.raw_data
        if isinstance(rd, dict):
            for k, v in rd.items():
                if isinstance(v, str) and len(v) > 10:
                    texts.append(v[:800])
                elif isinstance(v, list):
                    for x in v[:3]:
                        if isinstance(x, dict):
                            texts.append(" ".join(str(y) for y in x.values() if y)[:500])
                        elif isinstance(x, str):
                            texts.append(x[:500])
        elif isinstance(rd, str):
            texts.append(rd[:800])
    return "\n\n".join(texts)[:6000]


def _analyze_with_openai(text: str) -> Dict[str, Any]:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"""Analitza el següent text recollit d'OSINT i extreu:
1. Els conceptes clau més rellevants (màxim 10), amb una puntuació de rellevància de 0 a 1.
2. Prediccions o tendències identificables (opcional).

Respon en JSON amb aquest format:
{{"concepts": [{{"concept": "nom", "relevance": 0.8}}], "predictions": {{"tendència1": {{"trend": "descripció", "confidence": 0.7}}}}}}

Text:
{text[:4000]}
"""
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        content = response.choices[0].message.content
        if content.strip().startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
        return json.loads(content)
    except Exception as e:
        return {"error": str(e), "concepts": [], "predictions": {}}


def analyze_concepts(osint_list) -> tuple[List[Dict], Dict, float]:
    """Return (concepts, predictions, confidence)."""
    text = _extract_texts_from_osint(osint_list)
    if not text.strip():
        return [{"concept": "sense dades", "relevance": 0}], {}, 0.5

    if OPENAI_API_KEY:
        result = _analyze_with_openai(text)
        if "error" in result:
            return [{"concept": "error", "relevance": 0}], {}, 0.5
        concepts = result.get("concepts", [])
        predictions = result.get("predictions", {})
        return concepts, predictions if isinstance(predictions, dict) else {}, 0.85
    else:
        concepts = [{"concept": "geopolítica", "relevance": 0.8}, {"concept": "risc", "relevance": 0.7}]
        return concepts, {}, 0.75
