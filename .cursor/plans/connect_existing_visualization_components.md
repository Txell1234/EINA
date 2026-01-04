# Plan: Conectar Componentes de Visualización Existentes

## Análisis del Estado Actual

### Componentes que YA EXISTEN pero NO están conectados:

1. ✅ **NetworkGraph.tsx** - Existe y funciona, solo usado en modal de Dashboard
2. ✅ **TrendAnalysis.tsx** - Existe y funciona, solo usado en modal de Dashboard  
3. ✅ **RelationshipMap.tsx** - Existe y funciona, solo usado en modal de Dashboard
4. ✅ **GeographicMap.tsx** - Existe y funciona, solo usado en modal de Dashboard
5. ✅ **VisualizationsDashboard.tsx** - Existe y funciona, solo usado en modal de Dashboard

### Problemas Identificados:

1. **AIAnalysis.tsx**: 
   - Tiene datos de concepts, trends, sentiment desde backend
   - Solo muestra listas simples de texto
   - NO usa TrendAnalysis para visualizar tendencias
   - NO usa NetworkGraph/RelationshipMap para visualizar conceptos
   - NO tiene tabs para organizar visualizaciones

2. **InvestmentRecommendations.tsx**:
   - Tiene datos de riesgos y oportunidades desde backend
   - NO usa GeographicMap para mostrar mapa mundial con riesgos
   - Solo muestra cards simples

3. **Dashboard.tsx**:
   - Métricas hardcodeadas ("1,247", "8")
   - NO tiene mapa mundial integrado directamente
   - Activity hardcodeado
   - Visualizaciones solo en modal

## Solución: Conectar Componentes Existentes

### 1. AIAnalysis.tsx - Integrar Visualizaciones

**Cambios:**
- Agregar tabs: "Conceptes", "Tendències", "Sentiment"
- **Tab Conceptes:**
  - Usar `RelationshipMap` para mostrar relaciones entre conceptos
  - Convertir concepts a formato de relationships
  - Mostrar lista de conceptos con NetworkGraph si hay suficientes datos
- **Tab Tendències:**
  - Usar `TrendAnalysis` component directamente
  - Convertir trends data a formato TrendDataPoint[]
  - Mostrar gráfico con predicciones
- **Tab Sentiment:**
  - Usar `TrendAnalysis` con datos de sentiment temporal
  - Mostrar área chart con positive/negative/neutral

**Código necesario:**
```typescript
// En AIAnalysis.tsx
import TrendAnalysis from '../Visualizations/TrendAnalysis'
import RelationshipMap from '../Visualizations/RelationshipMap'

// Convertir trends a formato TrendAnalysis
const trendDataPoints = trends?.map(t => ({
  date: t.created_at || new Date().toISOString(),
  value: t.intensity || t.confidence || 0,
  category: t.category || 'main'
})) || []

// Convertir concepts a relationships
const conceptRelationships = concepts?.map(c => ({
  from: c.concept_name || c.name,
  to: c.related_concepts || 'General',
  type: c.concept_type || c.type || 'related',
  strength: Math.round((c.confidence || 0.5) * 10)
})) || []
```

### 2. InvestmentRecommendations.tsx - Integrar Mapa Mundial

**Cambios:**
- Agregar `GeographicMap` component
- Convertir riesgos a ubicaciones geográficas
- Mostrar mapa con colores según nivel de riesgo:
  - Verde: riesgo < 20%
  - Amarillo: riesgo 20-50%
  - Rojo: riesgo > 50%
- Agregar filtros por región y tipo de riesgo

**Código necesario:**
```typescript
// En InvestmentRecommendations.tsx
import GeographicMap from '../Visualizations/GeographicMap'
import { geographicService } from '../../services/api'

// Obtener ubicaciones del caso
const { data: locations } = useQuery({
  queryKey: ['geographic-locations', selectedCaseId],
  queryFn: () => geographicService.getLocations(selectedCaseId!),
  enabled: !!selectedCaseId
})

// Combinar con datos de riesgo
const locationsWithRisk = locations?.locations.map(loc => ({
  ...loc,
  riskLevel: getRiskForLocation(loc.name, risks)
}))
```

### 3. Dashboard.tsx - Integrar Mapa y Métricas Reales

**Cambios:**
- Crear endpoint backend `/api/cases/metrics` para métricas agregadas
- Reemplazar métricas hardcodeadas con datos reales
- Integrar `GeographicMap` directamente en Dashboard (no solo modal)
- Mostrar mapa mundial con todos los casos activos
- Obtener activity real desde backend

**Backend nuevo endpoint:**
```python
@router.get("/metrics")
async def get_dashboard_metrics(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Contar casos activos
    active_cases = await db.execute(
        select(func.count(Case.id)).where(
            Case.user_id == current_user["id"],
            Case.status.in_(["analyzing", "pending"])
        )
    )
    
    # Contar OSINT results
    osint_count = await db.execute(
        select(func.count(OSINTResult.id))
        .join(OSINTQuery).join(Case)
        .where(Case.user_id == current_user["id"])
    )
    
    # Contar análisis completados
    completed = await db.execute(
        select(func.count(Case.id)).where(
            Case.user_id == current_user["id"],
            Case.status == "completed"
        )
    )
    
    # Contar recomendaciones
    recommendations = await db.execute(
        select(func.count(InvestmentRecommendation.id))
        .join(Case)
        .where(Case.user_id == current_user["id"])
    )
    
    return {
        "active_cases": active_cases.scalar() or 0,
        "osint_data_collected": osint_count.scalar() or 0,
        "analyses_completed": completed.scalar() or 0,
        "recommendations_generated": recommendations.scalar() or 0
    }
```

**Frontend:**
```typescript
// En Dashboard.tsx
import GeographicMap from '../Visualizations/GeographicMap'
import { casesService } from '../../services/api'

// Obtener métricas reales
const { data: metrics } = useQuery({
  queryKey: ['dashboard-metrics'],
  queryFn: () => casesService.getMetrics()
})

// Obtener todas las ubicaciones de casos activos
const { data: allLocations } = useQuery({
  queryKey: ['all-case-locations'],
  queryFn: async () => {
    const locations = []
    for (const caseItem of cases || []) {
      try {
        const locs = await geographicService.getLocations(caseItem.id)
        locations.push(...(locs.locations || []))
      } catch (e) {
        // Ignore errors
      }
    }
    return { locations }
  },
  enabled: !!cases && cases.length > 0
})
```

## Archivos a Modificar

### Backend:
1. `backend/routers/cases.py` - Agregar endpoint `/api/cases/metrics`

### Frontend:
1. `frontend/src/components/AIAnalysis/AIAnalysis.tsx` - Agregar tabs y usar TrendAnalysis, RelationshipMap
2. `frontend/src/components/InvestmentRecommendations/InvestmentRecommendations.tsx` - Agregar GeographicMap
3. `frontend/src/components/Dashboard/Dashboard.tsx` - Integrar mapa y métricas reales
4. `frontend/src/services/api.ts` - Agregar método `casesService.getMetrics()`

## Orden de Implementación

1. **Backend: Endpoint de métricas** (5 min)
2. **Dashboard: Métricas reales y mapa** (15 min)
3. **AIAnalysis: Tabs y visualizaciones** (20 min)
4. **InvestmentRecommendations: Mapa mundial** (15 min)

## Resultado Esperado

- Dashboard muestra métricas reales y mapa mundial integrado
- AIAnalysis muestra gráficos avanzados de tendencias y conceptos
- InvestmentRecommendations muestra mapa mundial con riesgos
- Todos los componentes existentes están siendo utilizados
- Datos reales en todas las visualizaciones









