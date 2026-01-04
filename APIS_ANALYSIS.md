# Anàlisi Completa de les APIs Existents i Funcionals

## 📊 Resum Executiu

Aquest document analitza totes les APIs integrades a la plataforma OSINT i com cada una alimenta les diferents seccions del dashboard de referència.

---

## 🔴 APIs de Xarxes Socials (Social Media)

### 1. **EnsembleData API** ⭐ PRINCIPAL
**API Key**: `ENSEMBLEDATA_API_KEY`  
**Estat**: ✅ Funcional  
**Documentació**: https://ensembledata.com/apis/docs  
**Pla**: Gratuït (50 units/dia), Pagament disponible

#### Funcionalitats:
- **TikTok**: User info, posts, hashtags, keywords, comments
- **Instagram**: User info, posts, hashtags, post info, comments
- **YouTube**: Channel info, videos, keywords, video info, comments
- **Threads**: User info, posts, keywords
- **Reddit**: Subreddit posts, comments
- **Twitter/X**: User info, tweets, post info
- **Twitch**: User info, streams, videos
- **Snapchat**: User info, stories

#### Dades que proporciona:
```json
{
  "id": "post_id",
  "text": "contingut del post",
  "like_count": 1234,
  "comment_count": 567,
  "share_count": 89,
  "view_count": 10000,
  "created_time": "2024-01-01T12:00:00Z",
  "user": {
    "username": "user123",
    "location": "Barcelona, Spain",
    "follower_count": 50000
  },
  "hashtags": ["#trending", "#topic"],
  "location": {
    "name": "Barcelona",
    "latitude": 41.3851,
    "longitude": 2.1734
  }
}
```

#### Com alimenta el Dashboard:

**1. Mencions Totals**:
- Suma de tots els posts/comments recopilats
- Font: `ensembledata_*_user_posts`, `ensembledata_*_hashtag_posts`, `ensembledata_*_keyword_posts`
- Càlcul: `COUNT(OSINTResult)` on `query_type LIKE 'ensembledata_%'`

**2. Abast Estimat**:
- Suma de `view_count` + `follower_count` dels usuaris
- Font: Tots els posts de EnsembleData
- Càlcul: `SUM(view_count) + SUM(user.follower_count)` (deduplicat per usuari)

**3. Taxa d'Engagement**:
- `(likes + comments + shares) / views * 100`
- Font: Tots els posts amb mètriques d'engagement
- Càlcul: `AVG((like_count + comment_count + share_count) / view_count)`

**4. Fuentes de Datos**:
- **Xarxes Socials**: Agrupar per plataforma (TikTok, Instagram, YouTube, etc.)
- Font: `query_type` de `OSINTQuery`
- Càlcul: `GROUP BY query_type` filtrant per `ensembledata_*`

**5. Trending Topics**:
- Extreure hashtags de tots els posts
- Agrupar per hashtag i calcular creixement
- Font: `hashtags` field de cada post
- Càlcul: Comparar comptadors entre períodes

**6. Anàlisi de Sentiment**:
- Analitzar text dels posts amb IA
- Classificar com positiu/neutral/negatiu
- Font: `text` field de cada post
- Càlcul: Utilitzar `AIService.analyze_sentiment()`

**7. Distribució Geogràfica**:
- Extreure `location` de posts i `user.location`
- Geolocalitzar amb IPStack o Nominatim
- Font: `location` field i `user.location`
- Càlcul: Agrupar per país/ciutat

**8. Heatmap**:
- Utilitzar coordenades de `location` field
- Agregar per intensitat (nombre de posts)
- Font: `location.latitude` i `location.longitude`
- Càlcul: `HeatmapService.generate_heatmap_data()`

---

### 2. **Reddit API** (Nativa)
**API Key**: No requerida (OAuth opcional)  
**Estat**: ✅ Funcional  
**Pla**: Gratuït amb límits

#### Funcionalitats:
- Cerca de posts per paraules clau
- Cerca per subreddit
- Extracció de comments

#### Com alimenta el Dashboard:
- **Fuentes de Datos**: "Fòrums i Blogs" → Reddit posts
- **Mencions**: Comptar posts i comments
- **Sentiment**: Analitzar text de posts/comments
- **Trending Topics**: Extreure paraules clau i subreddits populars

---

## 📰 APIs de Mitjans de Comunicació

### 3. **News API**
**API Key**: `NEWS_API_KEY`  
**Estat**: ✅ Funcional  
**Pla**: Gratuït (100 requests/dia), Pagament disponible

#### Funcionalitats:
- Cerca de notícies per paraules clau
- Filtres per idioma, país, categoria
- Ordenació per popularitat, data

#### Dades que proporciona:
```json
{
  "title": "Títol de la notícia",
  "description": "Descripció",
  "url": "https://...",
  "publishedAt": "2024-01-01T12:00:00Z",
  "source": {
    "name": "El País",
    "country": "ES"
  },
  "content": "Contingut complet..."
}
```

#### Com alimenta el Dashboard:

**1. Fuentes de Datos**:
- **Mitjans Digitals**: Comptar notícies recopilades
- Font: `OSINTQuery` amb `query_type = "google_news"`
- Càlcul: `COUNT(OSINTResult)` per aquest tipus

**2. Mencions Totals**:
- Sumar notícies recopilades
- Font: Totes les notícies de News API

**3. Sentiment**:
- Analitzar títols i descripcions
- Font: `title` i `description` fields
- Càlcul: `AIService.analyze_sentiment()`

**4. Distribució Geogràfica**:
- Utilitzar `source.country`
- Agrupar per país
- Font: `source.country` field

**5. Alertas Críticas**:
- Detectar notícies amb paraules clau de risc
- Font: `title` i `content` fields
- Càlcul: Detecció de paraules clau + sentiment negatiu

---

## 🌍 APIs de Geolocalització

### 4. **IPStack API** ⭐ CONFIGURADA
**API Key**: `IPSTACK_API_KEY = 1a821d41916c9af610ec68ef8353efeb`  
**Estat**: ✅ Configurada i Funcional  
**Pla**: Gratuït (10,000 requests/mes)

#### Funcionalitats:
- Geolocalització d'adreces IP
- Informació de país, regió, ciutat
- Coordenades (latitude, longitude)
- Informació d'ISP i connexió

#### Dades que proporciona:
```json
{
  "ip": "8.8.8.8",
  "country_name": "United States",
  "country_code": "US",
  "region_name": "California",
  "city": "Mountain View",
  "latitude": 37.4056,
  "longitude": -122.0775,
  "connection": {
    "isp": "Google LLC"
  }
}
```

#### Com alimenta el Dashboard:

**1. Heatmap**:
- Geolocalitzar IPs extretes de posts
- Crear punts al mapa amb coordenades
- Font: IPs extretes de `OSINTResult.data`
- Càlcul: `HeatmapService._extract_ip_addresses()` → `IPStackAPIService.get_ip_info()`

**2. Distribució Geogràfica**:
- Agrupar per país utilitzant `country_name`
- Comptar mencions per país
- Font: Resultats de geolocalització d'IPs
- Càlcul: `GROUP BY country_name`

**3. Mapa de Relacions**:
- Relacionar ubicacions basades en IPs compartides
- Font: IPs geolocalitzades
- Càlcul: `HeatmapService.extract_location_relationships()`

---

### 5. **Nominatim API** (OpenStreetMap)
**API Key**: No requerida  
**Estat**: ✅ Funcional  
**Pla**: Gratuït (1 request/segon)

#### Funcionalitats:
- Geocodificació (nom → coordenades)
- Reverse geocoding (coordenades → nom)
- Cerca de localitzacions

#### Com alimenta el Dashboard:

**1. Heatmap**:
- Geocodificar noms de localitzacions extretes de text
- Font: Noms de ciutats/països extrets de posts
- Càlcul: `NominatimAPIService.geocode()`

**2. Distribució Geogràfica**:
- Convertir noms de localitzacions a coordenades
- Font: `location` fields de posts i `user.location`
- Càlcul: `geographic.router.geocode_location()`

---

## 💰 APIs Financeres (per casos d'inversió)

### 6. **Alpha Vantage API**
**API Key**: `ALPHAVANTAGE_API_KEY`  
**Estat**: ✅ Integrada  
**Pla**: Gratuït (5 calls/min, 500/dia)

#### Funcionalitats:
- Dades de mercat d'accions
- Quotes en temps real
- Indicadors tècnics
- Dades històriques

#### Com alimenta el Dashboard:

**1. Informes d'Intel·ligència** (casos d'inversió):
- Anàlisi de tendències de mercat
- Comparació amb competidors
- Font: Dades de mercat d'empreses relacionades
- Càlcul: `InvestmentDashboard` component

**2. Alertas Críticas** (casos d'inversió):
- Detectar canvis significatius en preus
- Font: Quotes en temps real
- Càlcul: Comparar amb mitjana mòbil

---

### 7. **Finnhub API**
**API Key**: `FINNHUB_API_KEY`  
**Estat**: ✅ Integrada  
**Pla**: Gratuït (60 calls/min)

#### Funcionalitats:
- Dades de mercat financer
- Notícies financeres
- Dades de criptomonedes
- Dades econòmiques

#### Com alimenta el Dashboard:

**1. Informes d'Intel·ligència**:
- Anàlisi competitiva financera
- Font: Dades de mercat i notícies
- Càlcul: `AIService.expert_analysis()` per casos d'inversió

**2. Trending Topics** (financer):
- Temes financers trending
- Font: Notícies financeres
- Càlcul: Agrupar per paraules clau

---

### 8. **Financial Modeling Prep API**
**API Key**: `FINANCIAL_MODELING_PREP_API_KEY`  
**Estat**: ✅ Integrada  
**Pla**: Gratuït disponible

#### Funcionalitats:
- Dades financeres d'empreses
- Ratios financers
- Dades de guanys
- Dades de balanços

#### Com alimenta el Dashboard:

**1. Informes d'Intel·ligència** (casos d'inversió):
- Anàlisi financera profunda
- Comparació amb competidors
- Font: Dades financeres estructurades
- Càlcul: `InvestmentDashboard` component

---

## 🌐 APIs Geopolítiques

### 9. **Permutable AI API**
**API Key**: `PERMUTABLE_API_KEY`  
**Estat**: ✅ Integrada  
**Pla**: Requereix trial/premium

#### Funcionalitats:
- Dades geopolítiques estructurades
- Events geopolítics
- Relacions bilaterals
- Dades de tractats

#### Com alimenta el Dashboard:

**1. Informes d'Intel·ligència** (casos geopolítics):
- Anàlisi de relacions internacionals
- Detecció d'events significatius
- Font: Dades geopolítiques estructurades
- Càlcul: `GeopoliticalDashboard` component

**2. Alertas Críticas** (casos geopolítics):
- Detectar canvis en relacions bilaterals
- Font: Events geopolítics
- Càlcul: Comparar amb dades històriques

---

## 💱 APIs de Canvi de Divisa

### 10. **ExchangeRate API**
**API Key**: `EXCHANGERATE_API_KEY`  
**Estat**: ✅ Integrada  
**Pla**: Gratuït (1,500 requests/mes)

#### Funcionalitats:
- Taxes de canvi
- Conversió de divises
- Dades històriques

#### Com alimenta el Dashboard:

**1. Informes d'Intel·ligència** (casos comercials):
- Anàlisi de tendències de divises
- Impacte en comerç internacional
- Font: Taxes de canvi
- Càlcul: `BusinessDashboard` component

---

### 11. **Fixer.io API**
**API Key**: `FIXER_API_KEY`  
**Estat**: ✅ Integrada  
**Pla**: Gratuït (100 requests/mes)

#### Funcionalitats:
- Taxes de canvi en temps real
- Dades històriques
- Conversió de divises

#### Com alimenta el Dashboard:
- Similar a ExchangeRate API
- Backup o alternativa

---

## 🪙 APIs de Criptomonedes

### 12. **CoinGecko API**
**API Key**: Opcional (`COINGECKO_API_KEY`)  
**Estat**: ✅ Funcional sense API key  
**Pla**: Gratuït (10-50 calls/min)

#### Funcionalitats:
- Preus de criptomonedes
- Market cap
- Volum de negociació
- Dades històriques

#### Com alimenta el Dashboard:

**1. Informes d'Intel·ligència** (casos de criptomonedes):
- Anàlisi de tendències de preus
- Font: Dades de mercat
- Càlcul: `InvestmentDashboard` component

---

## 🗺️ APIs de Dades Geogràfiques

### 13. **REST Countries API** (via CountryAPIService)
**API Key**: No requerida  
**Estat**: ✅ Funcional  
**Pla**: Gratuït

#### Funcionalitats:
- Informació de països
- Dades demogràfiques
- Dades econòmiques
- Banderes i codis

#### Com alimenta el Dashboard:

**1. Distribució Geogràfica**:
- Enriquir dades de països amb informació addicional
- Mostrar banderes
- Font: `country_code` de geolocalització
- Càlcul: `CountryAPIService.get_country()`

---

## 🔍 APIs d'OSINT Tècnic

### 14. **Shodan API**
**API Key**: `SHODAN_API_KEY`  
**Estat**: ✅ Integrada (requereix compte pagament)  
**Pla**: Pagament requerit

#### Funcionalitats:
- Cerca de dispositius connectats a Internet
- Informació de ports oberts
- Vulnerabilitats
- Informació de servidors

#### Com alimenta el Dashboard:

**1. Alertas Críticas** (casos de seguretat):
- Detectar vulnerabilitats
- Font: Resultats de cerca Shodan
- Càlcul: Filtrar per vulnerabilitats conegudes

---

### 15. **GitHub API**
**API Key**: `GITHUB_TOKEN`  
**Estat**: ✅ Integrada  
**Pla**: Gratuït (5,000 requests/hora amb token)

#### Funcionalitats:
- Cerca de repositoris
- Informació d'usuaris
- Cerca de codi
- Informació de commits

#### Com alimenta el Dashboard:

**1. Fuentes de Datos**:
- **Repositoris**: Comptar repositoris relacionats
- Font: `OSINTQuery` amb `query_type = "github"`
- Càlcul: `COUNT(OSINTResult)`

**2. Trending Topics**:
- Extreure paraules clau de repositoris
- Font: Noms i descripcions de repositoris
- Càlcul: Agrupar per paraules clau

---

### 16. **Wayback Machine API**
**API Key**: No requerida  
**Estat**: ✅ Funcional  
**Pla**: Gratuït

#### Funcionalitats:
- Historial de pàgines web
- Snapshots històrics
- Cerca per URL i data

#### Com alimenta el Dashboard:

**1. Informes d'Intel·ligència**:
- Anàlisi de canvis en contingut web
- Font: Snapshots històrics
- Càlcul: Comparar versions diferents

---

### 17. **DNS/WHOIS Service**
**API Key**: No requerida  
**Estat**: ✅ Funcional  
**Pla**: Gratuït

#### Funcionalitats:
- DNS lookup
- WHOIS lookup
- Reverse DNS

#### Com alimenta el Dashboard:

**1. Alertas Críticas**:
- Detectar canvis en DNS
- Font: Resultats de DNS lookup
- Càlcul: Comparar amb registres anteriors

---

## 🤖 API d'Intel·ligència Artificial

### 18. **OpenAI API** ⭐ CRÍTICA
**API Key**: `OPENAI_API_KEY`  
**Estat**: ✅ Integrada  
**Pla**: Pagament per ús

#### Funcionalitats:
- Anàlisi de sentiment
- Extracció de conceptes
- Generació de prediccions
- Anàlisi expert (geopolítica, inversió, social, negoci)
- Suggeriment de KPIs
- Extracció de mètriques específiques

#### Com alimenta el Dashboard:

**1. Sentiment Score**:
- Analitzar text de tots els posts/notícies
- Classificar com positiu/neutral/negatiu
- Font: `text` field de `OSINTResult.data`
- Càlcul: `AIService.analyze_sentiment()` → Agregar per tots els casos

**2. Trending Topics**:
- Extreure conceptes principals
- Agrupar per tema
- Font: `Concept` model (generat per IA)
- Càlcul: `AIService.extract_concepts()` → Agrupar i comptar

**3. Alertas Críticas**:
- Generar prediccions de risc
- Detectar canvis sobtats
- Font: `AIPrediction` amb `prediction_type="risk"`
- Càlcul: `AIService.generate_prediction()` → Filtrar per alta confiança

**4. Informes d'Intel·ligència**:
- Generar anàlisis experts
- Font: `AIAnalysis` amb `analysis_type="expert"`
- Càlcul: `AIService.expert_analysis()` per cada domini

**5. Anàlisi de Sentiment Detallada**:
- Desglossar per categoria
- Font: Anàlisi de sentiment per post
- Càlcul: Agregar per categoria (positiu/neutral/negatiu)

---

## 📊 Resum: Com cada API alimenta el Dashboard

### Mètriques Principals:

| Mètrica | APIs que l'alimenten |
|---------|---------------------|
| **Mencions Totals** | EnsembleData, News API, Reddit, GitHub |
| **Sentiment Score** | OpenAI (analitza dades de EnsembleData, News API) |
| **Abast Estimat** | EnsembleData (view_count + follower_count) |
| **Taxa d'Engagement** | EnsembleData (likes + comments + shares / views) |
| **Alertes Crítiques** | OpenAI (prediccions), Shodan (vulnerabilitats) |
| **Trending Topics** | EnsembleData (hashtags), OpenAI (conceptes), GitHub (repositoris) |

### Panells Detallats:

| Panell | APIs que l'alimenten |
|--------|---------------------|
| **Fuentes de Datos** | EnsembleData, News API, Reddit, GitHub |
| **Trending Topics** | EnsembleData (hashtags), OpenAI (conceptes) |
| **Alertas Críticas** | OpenAI (prediccions), Shodan, News API (notícies de risc) |
| **Anàlisi de Sentiment** | OpenAI (analitza dades de totes les fonts) |
| **Distribució Geogràfica** | IPStack, Nominatim, EnsembleData (location fields) |
| **Informes d'Intel·ligència** | OpenAI (anàlisi expert), Permutable (geopolítica), Alpha Vantage/Finnhub (finances) |

### Visualitzacions:

| Visualització | APIs que l'alimenten |
|--------------|---------------------|
| **Heatmap** | IPStack (geolocalització IPs), Nominatim (geocodificació), EnsembleData (location fields) |
| **Mapa de Relacions** | IPStack, Nominatim (per relacionar ubicacions) |
| **Gràfics de Sentiment** | OpenAI (analitza dades de totes les fonts) |

---

## 🔄 Flux de Dades al Dashboard

```
┌─────────────────────────────────────────────────────────┐
│                    APIs Externes                        │
├─────────────────────────────────────────────────────────┤
│ EnsembleData → Posts/Comentaris de Xarxes Socials      │
│ News API → Notícies de Mitjans Digitals                │
│ IPStack → Geolocalització d'IPs                       │
│ Nominatim → Geocodificació de Localitzacions           │
│ OpenAI → Anàlisi de Sentiment i Conceptes             │
│ GitHub/Reddit → Dades Addicionals                      │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│              Processament i Agregació                   │
├─────────────────────────────────────────────────────────┤
│ DataExtractionService → Extreu mètriques estructurades │
│ HeatmapService → Agrega per ubicació                   │
│ AIService → Analitza sentiment i genera prediccions    │
│ DashboardService → Agrega totes les dades              │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                    Dashboard Frontend                    │
├─────────────────────────────────────────────────────────┤
│ Mètriques Principals (6 cards)                         │
│ Panells Detallats (6 panells)                          │
│ Visualitzacions (Heatmap, Mapa, Gràfics)              │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ APIs Configurades i Funcionals

### Totalment Funcionals (amb API key configurada):
1. ✅ **IPStack API** - Configurada (`1a821d41916c9af610ec68ef8353efeb`)
2. ✅ **OpenAI API** - Requereix configuració a `.env`
3. ⚠️ **EnsembleData API** - Requereix API key a `.env`
4. ⚠️ **News API** - Requereix API key a `.env`

### Funcionals sense API key:
1. ✅ **Nominatim API** - Funciona sense API key
2. ✅ **CoinGecko API** - Funciona sense API key (amb límits)
3. ✅ **Country API** - Funciona sense API key
4. ✅ **Wayback API** - Funciona sense API key
5. ✅ **DNS/WHOIS** - Funciona sense API key
6. ✅ **Reddit API** - Funciona sense API key (amb límits)

### Requereixen configuració addicional:
1. ⚠️ **EnsembleData API** - Crítica per xarxes socials
2. ⚠️ **News API** - Important per mitjans digitals
3. ⚠️ **OpenAI API** - Crítica per anàlisi d'IA
4. ⚠️ **Shodan API** - Requereix compte pagament
5. ⚠️ **Permutable API** - Requereix trial/premium

---

## 🎯 Recomanacions d'Implementació

### Prioritat Alta:
1. **EnsembleData API** - Font principal de dades de xarxes socials
2. **OpenAI API** - Necessària per anàlisi de sentiment i prediccions
3. **IPStack API** - Ja configurada ✅

### Prioritat Mitjana:
1. **News API** - Important per mitjans digitals
2. **Nominatim API** - Ja funciona ✅

### Prioritat Baixa:
1. APIs financeres (per casos específics d'inversió)
2. APIs geopolítiques (per casos específics)
3. Shodan (requereix pagament)

---

## 📝 Notes Finals

- **IPStack API** està configurada i funcionant ✅
- **EnsembleData API** és crítica per alimentar la majoria de mètriques del dashboard
- **OpenAI API** és necessària per anàlisi de sentiment i generació d'alertes
- Totes les APIs estan integrades al codi, només cal configurar les API keys al `.env`



