# Guías de Usuario - EINA Platform

## Guía de Inicio Rápido

### 1. Acceso a la Plataforma

1. Abre tu navegador y accede a la URL de la plataforma
2. Inicia sesión con tus credenciales (si es necesario)
3. Serás redirigido al Dashboard principal

### 2. Crear tu Primer Caso

1. En el Dashboard, haz clic en "Crear Caso"
2. Completa los campos:
   - **Nombre**: Nombre descriptivo del caso
   - **Descripción**: Descripción detallada
   - **Tipo**: Selecciona el tipo (Geopolítico, Inversión, Reputación, etc.)
3. Haz clic en "Crear"
4. El caso aparecerá en la lista de casos activos

### 3. Recopilar Datos OSINT

1. Selecciona un caso de la lista
2. Ve a "Recopilación OSINT"
3. Elige una fuente (Google News, Reddit, etc.)
4. Ingresa tu consulta
5. Haz clic en "Recopilar"
6. Los datos se guardarán automáticamente en el caso

## Guías por Módulo

### Módulo de Reputación

#### Analizar Reputación de una Entidad

1. Ve a "Dashboard de Reputación"
2. Ingresa el nombre de la entidad (empresa, país, persona, organización)
3. Selecciona el tipo de entidad
4. Haz clic en "Analizar"
5. Revisa:
   - **Score de Reputación**: Score agregado (0-100)
   - **Tendencia**: Mejorando, estable, deteriorándose
   - **Indicadores de Crisis**: Alertas si hay crisis
   - **Análisis de Stakeholders**: Influencia y sentimiento

#### Exportar Reporte de Reputación

1. En el Dashboard de Reputación, selecciona una entidad
2. Haz clic en "Exportar PDF" en la sección de histórico
3. El reporte se generará y descargará automáticamente

### Módulo de Asuntos Públicos

#### Analizar Impacto de una Política

1. Ve a "Dashboard de Asuntos Públicos"
2. Ingresa el ID del caso
3. Haz clic en "Analizar Política"
4. Ingresa:
   - **Tema de Política**: Ej. "Climate Change"
   - **Jurisdicción**: Ej. "global", "USA", "EU"
5. Revisa:
   - **Score de Impacto**: Impacto calculado
   - **Posiciones de Stakeholders**: Support, oppose, neutral
   - **Oportunidades de Advocacy**: Oportunidades identificadas

#### Filtrar Políticas

1. En el Dashboard de Asuntos Públicos
2. Usa los filtros:
   - **Jurisdicción**: Filtrar por jurisdicción
   - **Tipo de Política**: Filtrar por tipo
3. Los resultados se actualizarán automáticamente

### Módulo de Inversiones Avanzadas

#### Análisis ESG

1. Ve a "Dashboard de Inversiones Avanzadas"
2. Ingresa el ID del caso
3. (Opcional) Ingresa símbolo de empresa o país
4. Revisa:
   - **Score ESG Agregado**: Score combinado
   - **Scores Individuales**: Environmental, Social, Governance
   - **Factores Identificados**: Factores por categoría
   - **Recomendaciones**: Recomendaciones basadas en análisis

#### Comparar Oportunidades de Mercado

1. En el Dashboard de Inversiones Avanzadas
2. Ingresa países separados por comas (ej. "USA,China,Germany")
3. (Opcional) Ingresa industrias
4. Selecciona tipo de inversión
5. Revisa:
   - **Mejor Oportunidad**: País con mayor score
   - **Comparación por País**: Scores y riesgos
   - **Análisis por Industria**: Si se especificaron industrias

### Módulo de Integración

#### Análisis Integral de Riesgos

1. Ve a "Dashboard de Integración"
2. Ingresa:
   - **ID del Caso**: Caso a analizar
   - **Nombre de Entidad**: (Opcional)
   - **Países**: Separados por comas
3. Revisa:
   - **Evaluación Integral**: Riesgos por módulo
   - **Riesgo General**: Score agregado
   - **Correlaciones**: Correlaciones entre módulos
   - **Alertas Integradas**: Alertas de todos los módulos

#### Matriz de Correlaciones

1. En el Dashboard de Integración
2. Revisa la "Matriz de Correlaciones"
3. Identifica correlaciones fuertes entre módulos
4. Usa esta información para análisis estratégico

## Mejores Prácticas

### 1. Organización de Casos

- Usa nombres descriptivos para casos
- Agrupa casos relacionados por tipo
- Mantén descripciones actualizadas

### 2. Recopilación de Datos

- Recopila datos de múltiples fuentes
- Actualiza datos regularmente
- Verifica la calidad de los datos OSINT

### 2.1 Evaluación de Fuentes OSINT (Checklist y Scoring)

**Checklist por fuente (puntúa cada criterio del 1 al 5):**
- **Credibilitat**: Historial de precisión y autoridad.
- **Actualització**: Frecuencia y puntualidad de publicación.
- **Cobertura geogràfica**: Alcance regional o global relevante.
- **Grau de soroll**: Proporción de señal vs. ruido (menos ruido = mejor score).
- **Verificabilitat**: Facilidad para contrastar con fuentes independientes.

**Score total y umbral:**
1. Suma los cinco criterios (máximo 25).
2. **Elimina** o desprioriza fuentes con **score total < 12**.

**Marcado por objetivo (fuentes óptimas):**
- **Reputación corporativa**: prioriza alta credibilitat y verificabilitat.
- **Opinión pública**: prioriza actualització y cobertura geogràfica.
- **Riesgo**: prioriza credibilitat y bajo grau de soroll.

**Revisión trimestral:**
- Reevalúa el scoring cada trimestre.
- Ajusta el catálogo según cambios de calidad, cobertura o señales de ruido.

### 3. Análisis

- Revisa métricas avanzadas regularmente
- Monitorea alertas críticas
- Exporta reportes para documentación

### 4. Integración Cross-Módulo

- Usa análisis integral para visión completa
- Revisa correlaciones entre módulos
- Considera impacto de eventos en múltiples áreas

## Troubleshooting Común

### Problema: No se cargan los datos

**Solución:**
1. Verifica que el backend esté ejecutándose
2. Revisa la consola del navegador para errores
3. Intenta refrescar la página

### Problema: Error al analizar

**Solución:**
1. Verifica que haya datos OSINT en el caso
2. Asegúrate de que el caso esté activo
3. Revisa los logs del backend

### Problema: Métricas no se actualizan

**Solución:**
1. Haz clic en "Actualizar" en el dashboard
2. Verifica que haya datos recientes
3. Revisa el período de tiempo seleccionado
