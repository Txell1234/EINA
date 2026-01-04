# Plan: Integrar Visualizaciones Avanzadas Estilo Economic Intelligence Unit

## Análisis del Estado Actual

### Backend (✅ Completo)
- Routers de visualizaciones: `/api/visualizations/network/{case_id}`, `/api/visualizations/trends/{case_id}`, `/api/visualizations/relationships/{case_id}`
- Router geográfico: `/api/geographic/locations/{case_id}`
- Endpoints de análisis IA: `/api/ai/analyze-concepts/{case_id}`, `/api/ai/analyze-trends/{case_id}`, `/api/ai/analyze-sentiment/{case_id}`
- Modelos de datos completos: Concept, Trend, Sentiment, OSINTResult, etc.

### Frontend (⚠️ Incompleto)
- Componentes básicos existen pero NO están integrados en todas las páginas
- Dashboard: Muestra datos hardcodeados, falta mapa mundial
- AI Analysis: Solo muestra listas simples, faltan visualizaciones avanzadas
- Investment Recommendations: No tiene mapas mundiales interactivos
- Visualizaciones solo accesibles desde modal en Dashboard

## Objetivos

1. **Dashboard**: Mapa mundial interactivo + métricas reales + visualizaciones integradas
2. **AI Analysis**: Word clouds, gráficos avanzados de conceptos, tendencias y sentiment
3. **Investment Recommendations**: Mapa mundial con heatmap de riesgos/oportunidades
4. **Todas las páginas**: Visualizaciones específicas del caso seleccionado con datos reales
5. **Estilo consistente**: Economic Intelligence Unit (colores profesionales, gráficos claros, diseño limpio)

## Implementación

### 1. Mejorar Dashboard (`frontend/src/components/Dashboard/Dashboard.tsx`)

**Cambios:**
- Agregar endpoint backend para métricas agregadas: `/api/cases/metrics`
- Integrar `GeographicMap` directamente en Dashboard (no solo en modal)
- Mostrar mapa mundial con todos los casos activos
- Calcular métricas reales desde backend:
  - Casos Activos: contar casos con status='analyzing' o 'pending'
  - Dades Recopilades: contar OSINTResult totales
  - Anàlisis Completats: contar casos con status='completed'
  - Recomanacions Generades: contar InvestmentRecommendation totales
- Agregar gráfico de actividad reciente (timeline)
- Integrar mini visualizaciones de tendencias

**Backend nuevo endpoint:**
```python
@router.get("/metrics")
async def get_dashboard_metrics(db: AsyncSession = Depends(get_db)):
    # Contar casos activos, OSINT results, análisis completados, recomendaciones
```

### 2. Mejorar AI Analysis (`frontend/src/components/AIAnalysis/AIAnalysis.tsx`)

**Cambios:**
- Agregar tabs: "Conceptes", "Tendències", "Sentiment"
- **Tab Conceptes:**
  - Word cloud de conceptos (usar librería react-wordcloud o similar)
  - Network graph de relaciones entre conceptos
  - Lista de conceptos con barras de confianza
- **Tab Tendències:**
  - Gráfico de líneas con predicciones (usar TrendAnalysis component)
  - Múltiples líneas para diferentes categorías
  - Área sombreada para predicciones futuras
- **Tab Sentiment:**
  - Gráfico de área temporal (positive/negative/neutral)
  - Indicadores de confianza
  - Distribución de sentiment por categoría

**Componentes nuevos:**
- `ConceptWordCloud.tsx`: Word cloud de conceptos
- `ConceptNetworkGraph.tsx`: Gráfico de red de conceptos
- `SentimentTimeline.tsx`: Gráfico temporal de sentiment

### 3. Mejorar Investment Recommendations (`frontend/src/components/InvestmentRecommendations/InvestmentRecommendations.tsx`)

**Cambios:**
- Agregar mapa mundial interactivo (usar GeographicMap con datos de riesgos)
- Mostrar países/regiones coloreados según nivel de riesgo:
  - Verde: Bajo riesgo / Oportunidad
  - Amarillo: Riesgo medio
  - Rojo: Alto riesgo
- Agregar filtros: Región (Global, Europe, Asia, Americas, Africa), Tipo de riesgo (Geopolítico, Político, Social)
- Mostrar tooltips con información de riesgo al hacer hover
- Integrar gráfico de evolución de riesgos (últimos 6 meses)
- Panel lateral con "TOP OPPORTUNITIES" y "TOP RISKS"

**Backend nuevo endpoint:**
```python
@router.get("/geographic-risks/{case_id}")
async def get_geographic_risks(case_id: int):
    # Retornar ubicaciones con niveles de riesgo asociados
```

### 4. Integrar Visualizaciones en Todas las Páginas

**OSINT Collection:**
- Agregar mini mapa geográfico mostrando ubicaciones de búsquedas recientes
- Gráfico de actividad por herramienta OSINT

**Qualitative Analysis:**
- Radar chart de KPIs (usar Recharts)
- Gráfico de barras de confianza por framework
- Visualización de relaciones premisa → evidencia → conclusión

**Data Synchronization:**
- Timeline visual de sincronizaciones
- Gráfico de estado por módulo

### 5. Backend: Endpoints Adicionales Necesarios

**Nuevos endpoints:**
1. `/api/cases/metrics` - Métricas agregadas del dashboard
2. `/api/investments/geographic-risks/{case_id}` - Riesgos geográficos para mapa
3. `/api/ai/concepts-wordcloud/{case_id}` - Datos formateados para word cloud
4. `/api/ai/sentiment-timeline/{case_id}` - Datos temporales de sentiment

### 6. Estilo Economic Intelligence Unit

**Características del estilo:**
- Colores profesionales: Azul oscuro (#1a237e), Naranja (#ff6f00), Verde (#4caf50), Rojo (#f44336)
- Tipografía: Sans-serif clara, tamaños jerárquicos
- Gráficos: Líneas suaves, áreas con transparencia, colores consistentes
- Cards: Sombras sutiles, bordes redondeados, padding generoso
- Mapas: Estilo claro, marcadores distintivos, leyendas claras

**Archivo CSS global:**
- Crear `frontend/src/styles/eiu-theme.css` con variables CSS y estilos base

## Archivos a Modificar/Crear

### Backend:
1. `backend/routers/cases.py` - Agregar endpoint `/metrics`
2. `backend/routers/investments.py` - Agregar endpoint `/geographic-risks/{case_id}`
3. `backend/routers/ai_analysis.py` - Mejorar endpoints existentes para retornar datos formateados

### Frontend:
1. `frontend/src/components/Dashboard/Dashboard.tsx` - Integrar mapa y métricas reales
2. `frontend/src/components/AIAnalysis/AIAnalysis.tsx` - Agregar tabs y visualizaciones avanzadas
3. `frontend/src/components/InvestmentRecommendations/InvestmentRecommendations.tsx` - Agregar mapa mundial
4. `frontend/src/components/AIAnalysis/ConceptWordCloud.tsx` - Nuevo componente
5. `frontend/src/components/AIAnalysis/ConceptNetworkGraph.tsx` - Nuevo componente
6. `frontend/src/components/AIAnalysis/SentimentTimeline.tsx` - Nuevo componente
7. `frontend/src/styles/eiu-theme.css` - Nuevo archivo de estilos
8. `frontend/src/services/api.ts` - Agregar nuevos métodos de servicio

### Dependencias Frontend:
- `react-wordcloud` o `wordcloud` - Para word clouds
- Ya tenemos: `recharts`, `leaflet`, `react-leaflet`

## Orden de Implementación

1. **Fase 1: Backend - Endpoints de métricas y datos formateados**
   - Endpoint de métricas del dashboard
   - Mejorar endpoints de AI analysis para retornar datos formateados
   - Endpoint de riesgos geográficos

2. **Fase 2: Dashboard - Integración de mapa y métricas reales**
   - Conectar métricas reales
   - Integrar mapa mundial
   - Agregar gráfico de actividad

3. **Fase 3: AI Analysis - Visualizaciones avanzadas**
   - Agregar tabs
   - Implementar word cloud
   - Implementar gráficos de tendencias y sentiment

4. **Fase 4: Investment Recommendations - Mapa mundial**
   - Integrar mapa con datos de riesgos
   - Agregar filtros y tooltips
   - Panel de oportunidades y riesgos

5. **Fase 5: Estilo y pulido**
   - Aplicar tema EIU consistente
   - Ajustar colores y tipografía
   - Optimizar rendimiento

## Testing

- Verificar que todas las visualizaciones usan datos reales del backend
- Probar con casos que tienen datos y casos vacíos
- Verificar que los mapas se actualizan correctamente
- Probar filtros y tooltips
- Verificar responsividad en diferentes tamaños de pantalla









