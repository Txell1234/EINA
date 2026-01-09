# Pla d'integració immediata de fonts OSINT

## 1) Fonts prioritàries (10–15) i connector

| # | Font | Tipus | Connector | Notes d'accés |
| --- | --- | --- | --- | --- |
| 1 | Google News (topics / queries) | Notícies | RSS | RSS per temes/keywords, sense autenticació. |
| 2 | GDELT 2.1 Events | Notícies / geopolitic | API | API pública (JSON), filtres per país/tema. |
| 3 | GDELT 2.1 Doc | Notícies / mencions | API | API pública (JSON), cerca per keywords. |
| 4 | NewsAPI.org | Notícies | API | Requereix API key, límit de crèdits. |
| 5 | MediaStack | Notícies | API | Requereix API key, bon per regional. |
| 6 | Reuters (World/Business) | Notícies | RSS | RSS per seccions. |
| 7 | BBC News (World/Business) | Notícies | RSS | RSS per seccions. |
| 8 | The Guardian | Notícies | API | API pública amb key gratuïta. |
| 9 | El País / El Mundo (internacional) | Notícies | RSS | RSS per seccions. |
|10 | Al Jazeera (World/Middle East) | Notícies | RSS | RSS per seccions. |
|11 | Wikipedia RecentChanges | OSINT / events | API | MediaWiki API, canvis recents per idioma. |
|12 | GitHub Search (issues/repos) | OSINT / tech | API | API amb autenticació; útil per incidents i leaks. |
|13 | Reddit (subreddits focus) | Social | API | API OAuth, subreddit per tema. |
|14 | YouTube (channels/keywords) | Social | API | YouTube Data API v3, quotas. |
|15 | UN / EU / US Gov Press Releases | Institucional | RSS | RSS oficial per comunicats. |

> **Nota**: Si alguna API té restriccions, usar RSS o scraping lleuger com a fallback (p. ex. The Guardian RSS si quota baixa, o scraping amb `requests+readability`).

## 2) Esquema mínim d’ingestió

Esquema base per totes les fonts (canònic):

```json
{
  "source": "string",     // identificador de la font (p. ex. "gdelt", "bbc_rss")
  "title": "string",      // títol normalitzat
  "text": "string",       // cos de la notícia o fragment principal
  "time": "ISO-8601",     // data/hora UTC
  "author": "string",     // autor, si disponible
  "url": "string"         // URL original
}
```

Regles de normalització:
- `source`: slug estable (sense espais, minúscules).
- `time`: convertir a UTC i ISO-8601; si falta, usar `published_at` o data de captació.
- `text`: HTML netejat; límit inicial 5.000 caràcters.
- `author`: usar `source_name` o `byline` si l’autor no existeix.
- `url`: netejar paràmetres de tracking (`utm_*`).

## 3) Pipeline de normalització + detecció d’idioma + sentiment inicial

**Pipeline proposat (ordre):**
1. **Fetch**: recuperar payloads (RSS/API/scraping) amb timeout curt i reintents.
2. **Parse**: convertir a camps bàsics (títol, cos, data, URL, autor).
3. **Normalize**: aplicar l’esquema mínim, netejar HTML, canonicalitzar URL.
4. **Dedup**: hash de `title+url+time` per evitar duplicats.
5. **Language detection**: `langdetect` o `fasttext` (model lid.176). Guardar `lang`.
6. **Sentiment inicial**: regla ràpida (VADER per en/ca/es) o model lleuger.
7. **Persist**: escriure a `OSINTResult.data` amb camps canònics i metadades.

**Metadades addicionals recomanades (optatives):**
- `lang`, `sentiment_score`, `sentiment_label`, `raw_source`, `ingested_at`.

## 4) Intervals d’ingestió i límits de càrrega

| Tipus de font | Interval | Límit/consells |
| --- | --- | --- |
| RSS notícies (BBC, Reuters, Al Jazeera, etc.) | 15–30 min | 1-2 req/min per feed, cache ETag/If-Modified-Since. |
| APIs notícies (NewsAPI, MediaStack, Guardian) | 30–60 min | Respectar quota; batch per keywords. |
| GDELT Events/Doc | 15 min | Paginació controlada; finestra temporal curta. |
| Social (Reddit, YouTube) | 30–60 min | Quote limitada; prioritzar subreddits/llistes. |
| Institucionals (UN/EU/US) | 2–6 h | RSS estable; poc volum. |
| Wikipedia RecentChanges | 30 min | Limitar per llengua i namespace. |
| GitHub Search | 1–2 h | 5 req/min; cache resultats i usar `since`. |

**Límits recomanats per evitar bloquejos**:
- Concurrència màxima: 4–6 connectors en paral·lel.
- Backoff exponencial en errors 429/5xx.
- Reintents: 2 màxim per font (després ometre fins propera finestra).
- Respectar robots.txt per scraping i identificar User-Agent.

## 5) Fitxa resum (operativa)

- **Objectiu immediat**: activar 10–15 fonts amb RSS/API per cobertura global i social.
- **Estructura mínima**: `source`, `title`, `text`, `time`, `author`, `url`.
- **Pipeline base**: fetch → parse → normalize → dedup → lang → sentiment → persist.
- **Intervals**: 15–60 min per notícies i social; 2–6 h per institucionals.
- **Control de càrrega**: quotes + backoff + concurrència limitada.
