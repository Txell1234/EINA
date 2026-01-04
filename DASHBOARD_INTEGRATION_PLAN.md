# Pla d'Integració del Dashboard OSINT Intelligence Center

## Anàlisi Comparativa: Dashboard Actual vs Dashboard de Referència

### 📊 Mètriques Principals (Top Row)

#### Dashboard de Referència:
1. **Mencions Totals**: 3.427 (+12%)
2. **Sentiment Score**: 72% (+5pts)
3. **Abast Estimat**: 1.2M (+23%)
4. **Taxa d'Engagement**: 8.4% (+1.2%)
5. **Alertes Crítiques**: 3 (+1)
6. **Trending Topics**: 12 (+3)

#### Dashboard Actual:
- Casos Actius
- Dades Recopilades
- Anàlisis Completats
- Recomanacions Generades

#### ✅ Funcionalitats Disponibles per Implementar:
- **DataExtractionService**: Ja extreu mètriques de xarxes socials (likes, comments, shares, views)
- **OSINTResult**: Totes les dades recopilades estan a la base de dades
- **AIService**: Ja calcula sentiment i genera prediccions
- **HeatmapService**: Ja agrega dades per ubicació

### 📈 Panells Detallats

#### 1. Fuentes de Datos (Data Sources)
**Referència**: Xarxes Socials (2,847), Mitjans Digitals (156), Fòrums i Blogs (93)

**Implementació**:
- Utilitzar `OSINTQuery.query_type` per agrupar per font
- Contar `OSINTResult` per cada tipus de query
- Endpoint: `GET /api/dashboard/sources` (nou)

#### 2. Trending Topics
**Referència**: Hashtags amb creixement (#CalidadServicio +156%, #AtenciónCliente +89%)

**Implementació**:
- Extreure hashtags de `OSINTResult.data` (ja fet parcialment)
- Calcular creixement comparant períodes
- Utilitzar `Concept` de `AIAnalysis` per temes detectats
- Endpoint: `GET /api/dashboard/trending-topics?days=7` (nou)

#### 3. Alertas Críticas
**Referència**: Pic de mencions negatives, Comparació amb competidor, Contingut viral

**Implementació**:
- Utilitzar `AIPrediction` amb `prediction_type="risk"`
- Detectar canvis sobtats en sentiment (comparar amb mitjana)
- Utilitzar `DataExtractionService.extract_sentiment_metrics`
- Endpoint: `GET /api/dashboard/alerts` (nou)

#### 4. Anàlisi de Sentiment
**Referència**: Positiu 63% (2.156), Neutral 29% (984), Negatiu 8% (287)

**Implementació**:
- Agregar sentiment de tots els casos
- Utilitzar `DataExtractionService.extract_sentiment_metrics`
- Calcular percentatges i canvis
- Endpoint: `GET /api/dashboard/sentiment?days=7` (nou)

#### 5. Distribució Geogràfica
**Referència**: Espanya 68% (1.847), Mèxic 74% (432), Argentina 61% (298)

**Implementació**:
- Utilitzar `HeatmapService` amb granularity="country"
- Agregar per país utilitzant `geographic.router`
- Endpoint: `GET /api/dashboard/geographic-distribution` (nou)

#### 6. Informes de Intel·ligència
**Referència**: Anàlisi Competitiu Setmanal, Detecció de Crisis, Oportunitats

**Implementació**:
- Utilitzar `AIAnalysis` amb `analysis_type="expert"`
- Generar informes automàtics amb `ResearchExecutorService`
- Endpoint: `GET /api/dashboard/intelligence-reports` (nou)

### 🗺️ Visualitzacions de Mapa

#### Heatmap
**Estat Actual**: ✅ Implementat
- `HeatmapService.generate_heatmap_data`
- Endpoint: `GET /api/heatmap/dashboard/summary`
- Frontend: `DashboardHeatmapSummary` component

**Millores Necessàries**:
- Afegir filtres per temàtica (colors diferents)
- Afegir línia temporal (24h, 7 dies, 30 dies, 90 dies)
- Mostrar intensitat per sentiment

#### Mapa de Relacions
**Estat Actual**: ✅ Implementat parcialment
- `HeatmapService.extract_location_relationships`
- Fletxes entre ubicacions

**Millores Necessàries**:
- Visualització més clara de les relacions
- Filtres per tipus de relació
- Grups de relacions

#### Distribució Geogràfica
**Estat Actual**: ✅ Implementat
- `GeographicMap` component
- `geographic.router` endpoints

**Millores Necessàries**:
- Agregació per país amb percentatges
- Filtres per plataforma
- Comparació temporal

## 📋 Pla d'Implementació

### Fase 1: Endpoints Backend (Nou Servei de Dashboard)

#### 1.1. Crear `DashboardService`
```python
# backend/services/dashboard_service.py
- get_total_mentions(days: int) -> Dict
- get_sentiment_score(days: int) -> Dict
- get_estimated_reach(days: int) -> Dict
- get_engagement_rate(days: int) -> Dict
- get_critical_alerts() -> List[Dict]
- get_trending_topics(days: int) -> List[Dict]
- get_data_sources() -> List[Dict]
- get_geographic_distribution() -> List[Dict]
- get_intelligence_reports() -> List[Dict]
```

#### 1.2. Crear Router de Dashboard
```python
# backend/routers/dashboard.py
- GET /api/dashboard/metrics?days=7
- GET /api/dashboard/sources
- GET /api/dashboard/trending-topics?days=7
- GET /api/dashboard/alerts
- GET /api/dashboard/sentiment?days=7
- GET /api/dashboard/geographic-distribution
- GET /api/dashboard/intelligence-reports
```

### Fase 2: Frontend - Components Nous

#### 2.1. Component de Mètriques Principals
```typescript
// frontend/src/components/Dashboard/MetricsCards.tsx
- MetricCard amb canvis percentuals
- Indicadors de tendència (↑↓)
- Colors diferents per tipus de mètrica
```

#### 2.2. Component de Fuentes de Datos
```typescript
// frontend/src/components/Dashboard/DataSourcesPanel.tsx
- Llista de fonts amb comptadors
- Indicadors actiu/inactiu
- Percentatges
```

#### 2.3. Component de Trending Topics
```typescript
// frontend/src/components/Dashboard/TrendingTopicsPanel.tsx
- Llista de hashtags/temes
- Gràfics de creixement
- Filtres (Todo, Positivo, Negativo)
- Barres de percentatge
```

#### 2.4. Component d'Alertes Crítiques
```typescript
// frontend/src/components/Dashboard/CriticalAlertsPanel.tsx
- Llista d'alertes amb detalls
- Indicadors de severitat
- Timestamps
- Accions ràpides
```

#### 2.5. Component d'Anàlisi de Sentiment
```typescript
// frontend/src/components/Dashboard/SentimentAnalysisPanel.tsx
- Gràfic de barres horitzontals
- Percentatges per categoria
- Canvis percentuals
- Comptadors
```

#### 2.6. Component de Distribució Geogràfica
```typescript
// frontend/src/components/Dashboard/GeographicDistributionPanel.tsx
- Llista de països amb banderes
- Percentatges i comptadors
- Enllaç al mapa interactiu
```

#### 2.7. Component d'Informes d'Intel·ligència
```typescript
// frontend/src/components/Dashboard/IntelligenceReportsPanel.tsx
- Llista d'informes generats
- Nivell de confiança
- Timestamps
- Botons "Ver Completo"
```

### Fase 3: Millores de Visualització

#### 3.1. Millores del Heatmap
- Filtres per temàtica (colors)
- Línia temporal (24h, 7 dies, 30 dies, 90 dies)
- Llegenda millorada
- Popups amb més informació

#### 3.2. Mapa de Relacions
- Visualització més clara
- Filtres per tipus
- Grups de relacions
- Animacions

#### 3.3. Header del Dashboard
- Títol "OSINT Intelligence Center"
- Indicador "EN VIU" (Live)
- Selector de període (24h, 7 dies, 30 dies, 90 dies)
- Botons Actualitzar i Exportar

## 🔧 Integració amb APIs Existents

### APIs que ja funcionen:
1. ✅ **EnsembleData API**: TikTok, Instagram, YouTube, Threads, Reddit, Twitter/X
2. ✅ **IPStack API**: Geolocalització d'IPs (configurada)
3. ✅ **Nominatim API**: Geocodificació de localitzacions
4. ✅ **OpenAI API**: Anàlisi de sentiment, extracció de conceptes, prediccions
5. ✅ **DataExtractionService**: Extracció de mètriques estructurades

### Dades Disponibles:
- `OSINTResult.data`: Totes les dades recopilades
- `AIAnalysis`: Anàlisis d'IA amb conceptes i prediccions
- `CaseKPI`: KPIs vinculats als casos
- `Concept`: Conceptes extrets per IA
- `AIPrediction`: Prediccions de tendències i riscos

## 📊 Estructura de Dades Necessària

### Mètriques Principals:
```typescript
interface DashboardMetrics {
  total_mentions: number;
  total_mentions_change: number; // %
  sentiment_score: number; // 0-100
  sentiment_score_change: number; // points
  estimated_reach: number;
  estimated_reach_change: number; // %
  engagement_rate: number; // %
  engagement_rate_change: number; // %
  critical_alerts: number;
  critical_alerts_change: number;
  trending_topics: number;
  trending_topics_change: number;
}
```

### Fuentes de Datos:
```typescript
interface DataSource {
  name: string;
  type: 'social' | 'media' | 'forum' | 'blog';
  mentions: number;
  is_active: boolean;
  percentage?: number;
}
```

### Trending Topics:
```typescript
interface TrendingTopic {
  name: string;
  mentions: number;
  growth: number; // %
  sentiment: number; // 0-100
  category: 'positive' | 'negative' | 'neutral';
}
```

### Alertes Crítiques:
```typescript
interface CriticalAlert {
  id: string;
  type: 'negative_spike' | 'competitor_comparison' | 'viral_content';
  title: string;
  severity: number; // 0-100
  platform: string;
  mentions: number;
  time_ago: string;
  details: Dict;
}
```

## 🎨 Disseny Visual

### Colors i Estil:
- **Header**: Fons fosc (#1e3a5f) amb text blanc
- **Cards**: Fons blanc amb ombres subtils
- **Mètriques Positives**: Verd (#28a745)
- **Mètriques Negatives**: Vermell (#dc3545)
- **Alertes**: Taronja (#ff6b35)
- **Heatmap**: Escala de colors segons intensitat i sentiment

### Layout:
- **Top Row**: 6 mètriques principals en grid
- **Middle Row**: 3 panells (Fuentes, Trending, Alertas)
- **Bottom Row**: 3 panells (Sentiment, Geographic, Reports)
- **Map Section**: Heatmap i mapa de relacions a sota

## 🚀 Priorització

### Alta Prioritat (Fase 1):
1. Endpoints de dashboard (backend)
2. Mètriques principals (frontend)
3. Fuentes de Datos
4. Trending Topics
5. Alertes Crítiques

### Mitjana Prioritat (Fase 2):
1. Anàlisi de Sentiment detallada
2. Distribució Geogràfica
3. Millores del Heatmap
4. Header amb selector de període

### Baixa Prioritat (Fase 3):
1. Informes d'Intel·ligència
2. Mapa de Relacions millorat
3. Exportació de dades
4. Animacions i transicions

## 📝 Notes d'Implementació

1. **Performance**: Utilitzar cache per mètriques agregades
2. **Real-time**: WebSockets o polling cada 10 segons (ja implementat)
3. **Filtres Temporals**: Tots els endpoints han de suportar `days` parameter
4. **Agregació**: Utilitzar `DataExtractionService` per processar dades OSINT
5. **IA**: Utilitzar `AIService` per detectar alertes i tendències



