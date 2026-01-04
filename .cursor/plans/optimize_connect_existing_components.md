# Plan Optimizado: Conectar Componentes Existentes (Sin Duplicar)

## Análisis: Lo que YA EXISTE

### Backend - Endpoints Existentes:
1. ✅ `/api/visualizations/trends/{case_id}` - Retorna TrendAnalysisResponse (data + prediction)
2. ✅ `/api/visualizations/relationships/{case_id}` - Retorna RelationshipMapResponse
3. ✅ `/api/visualizations/network/{case_id}` - Retorna NetworkGraphResponse
4. ✅ `/api/geographic/locations/{case_id}` - Retorna GeographicDataResponse
5. ✅ `/api/ai/concepts?case_id=X` - Retorna List[ConceptResponse]
6. ✅ `/api/ai/trends?case_id=X` - Retorna List[TrendResponse] (lista simple)
7. ✅ `/api/ai/sentiment?case_id=X` - Retorna List[SentimentResponse]

### Frontend - Servicios Existentes:
1. ✅ `visualizationsService.trendAnalysis(caseId)` - Ya conectado a endpoint correcto
2. ✅ `visualizationsService.relationshipMap(caseId)` - Ya conectado
3. ✅ `visualizationsService.networkGraph(caseId)` - Ya conectado
4. ✅ `geographicService.getLocations(caseId)` - Ya conectado
5. ✅ `aiAnalysisService.getConcepts(caseId)` - Conectado pero retorna lista simple
6. ✅ `aiAnalysisService.getTrends(caseId)` - Conectado pero retorna lista simple (NO usa visualizationsService)

### Frontend - Componentes Existentes:
1. ✅ `TrendAnalysis.tsx` - Componente completo, solo usado en VisualizationsDashboard (modal)
2. ✅ `RelationshipMap.tsx` - Componente completo, solo usado en VisualizationsDashboard (modal)
3. ✅ `NetworkGraph.tsx` - Componente completo, solo usado en VisualizationsDashboard (modal)
4. ✅ `GeographicMap.tsx` - Componente completo, solo usado en VisualizationsDashboard (modal)

## Problema: Componentes NO están conectados donde deberían

### AIAnalysis.tsx:
- ❌ Usa `aiAnalysisService.getTrends()` (lista simple) en lugar de `visualizationsService.trendAnalysis()` (datos formateados)
- ❌ NO usa `TrendAnalysis` component
- ❌ NO usa `RelationshipMap` component para conceptos
- ❌ Solo muestra listas de texto

### InvestmentRecommendations.tsx:
- ❌ NO usa `GeographicMap` component
- ❌ NO usa `geographicService.getLocations()`

### Dashboard.tsx:
- ❌ Métricas hardcodeadas ("1,247", "8")
- ❌ NO tiene endpoint de métricas (necesario crear)
- ❌ NO integra `GeographicMap` directamente (solo en modal)

## Solución Optimizada: Reutilizar lo Existente

### 1. AIAnalysis.tsx - Usar Servicios y Componentes Existentes

**Cambios mínimos:**
- Agregar tabs: "Conceptes", "Tendències", "Sentiment"
- **Tab Tendències:**
  - Cambiar de `aiAnalysisService.getTrends()` a `visualizationsService.trendAnalysis()`
  - Usar `TrendAnalysis` component directamente
- **Tab Conceptes:**
  - Usar `visualizationsService.relationshipMap()` para relaciones entre conceptos
  - Usar `RelationshipMap` component
- **Tab Sentiment:**
  - Convertir sentiment data a formato TrendDataPoint[] para usar `TrendAnalysis`

**Código:**
```typescript
// Reemplazar esto:
const { data: trends } = useQuery({
  queryKey: ['trends', selectedCaseId],
  queryFn: () => aiAnalysisService.getTrends(selectedCaseId!),
})

// Por esto:
const { data: trendData } = useQuery({
  queryKey: ['trendAnalysis', selectedCaseId],
  queryFn: () => visualizationsService.trendAnalysis(selectedCaseId!),
})

// Y usar TrendAnalysis component:
<TrendAnalysis 
  data={trendData?.data || []}
  predictionData={trendData?.prediction || []}
  showPrediction={!!trendData?.prediction}
/>
```

### 2. InvestmentRecommendations.tsx - Usar GeographicMap Existente

**Cambios mínimos:**
- Agregar query para `geographicService.getLocations(selectedCaseId)`
- Usar `GeographicMap` component directamente
- Combinar con datos de riesgos para colorear mapa

### 3. Dashboard.tsx - Solo Agregar Endpoint de Métricas

**Backend - Nuevo endpoint mínimo:**
```python
@router.get("/metrics")
async def get_dashboard_metrics(...):
    # Solo contar desde casos existentes
    active = count(Case where status in ['analyzing', 'pending'])
    osint_count = count(OSINTResult join Case)
    completed = count(Case where status='completed')
    recommendations = count(InvestmentRecommendation join Case)
    return {active_cases, osint_data_collected, analyses_completed, recommendations_generated}
```

**Frontend:**
- Agregar `casesService.getMetrics()` en api.ts
- Reemplazar valores hardcodeados con datos reales
- Opcional: Agregar `GeographicMap` con todas las ubicaciones de casos activos

## Archivos a Modificar (Mínimos)

### Backend:
1. `backend/routers/cases.py` - Agregar endpoint `/metrics` (1 endpoint nuevo)

### Frontend:
1. `frontend/src/components/AIAnalysis/AIAnalysis.tsx` - Cambiar servicios y agregar componentes existentes
2. `frontend/src/components/InvestmentRecommendations/InvestmentRecommendations.tsx` - Agregar GeographicMap
3. `frontend/src/components/Dashboard/Dashboard.tsx` - Métricas reales
4. `frontend/src/services/api.ts` - Agregar `casesService.getMetrics()`

## NO Crear Nada Nuevo

- ❌ NO crear nuevos componentes de visualización
- ❌ NO crear nuevos servicios
- ❌ NO crear nuevos endpoints de visualización
- ✅ Solo REUTILIZAR lo que ya existe
- ✅ Solo CONECTAR componentes existentes donde faltan

## Resultado

- AIAnalysis muestra TrendAnalysis y RelationshipMap (componentes existentes)
- InvestmentRecommendations muestra GeographicMap (componente existente)
- Dashboard muestra métricas reales (1 endpoint nuevo mínimo)
- Todo reutiliza código existente, sin duplicación









