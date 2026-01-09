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

### 3. Análisis

- Revisa métricas avanzadas regularmente
- Monitorea alertas críticas
- Exporta reportes para documentación

### 4. Integración Cross-Módulo

- Usa análisis integral para visión completa
- Revisa correlaciones entre módulos
- Considera impacto de eventos en múltiples áreas

### 5. Definició d’objectius i governança de fonts (OSINT)

#### 5.1 Objectius principals

- **Opinió pública**: percepcions, sentiment i conversa pública sobre l’entitat.
- **Reputació corporativa**: credibilitat, confiança i imatge de marca.
- **Risc reputacional**: senyals de crisi, controvèrsies i dany potencial a la reputació.
- **Tendències socials**: temes emergents, narratives i canvis de context.

#### 5.2 Mapatge font ➜ objectiu

| Font | Opinió pública | Reputació corporativa | Risc reputacional | Tendències socials | Notes |
| --- | --- | --- | --- | --- | --- |
| Xarxes socials (Twitter/X, Instagram, TikTok, YouTube, Threads) | ✅ | ✅ | ✅ | ✅ | Alta velocitat, alta volatilitat |
| Mitjans de comunicació (news) | ✅ | ✅ | ✅ | ✅ | Context editorial, millor verificació |
| Fòrums i comunitats (Reddit, StackExchange) | ✅ | ➖ | ✅ | ✅ | Opinió qualitativa i early signals |
| Blogs i newsletters | ➖ | ✅ | ✅ | ✅ | Anàlisi de nínxol, menor volum |
| Registres públics i reguladors | ➖ | ✅ | ✅ | ➖ | Base per reputació i compliance |
| Informes corporatius (ESG, anuals) | ➖ | ✅ | ➖ | ➖ | Font pròpia, risc de biaix |
| ONG / think tanks | ➖ | ✅ | ✅ | ✅ | Autoritat temàtica, menys volum |
| Reviews i portals d’ocupació | ✅ | ✅ | ✅ | ✅ | Senyals interns i d’experiència |

#### 5.3 Score d’adequació per objectiu (1–5)

| Font | Opinió pública | Reputació corporativa | Risc reputacional | Tendències socials |
| --- | --- | --- | --- | --- |
| Xarxes socials | 5 | 4 | 4 | 5 |
| Mitjans de comunicació | 4 | 5 | 5 | 4 |
| Fòrums i comunitats | 4 | 2 | 4 | 4 |
| Blogs / newsletters | 2 | 4 | 3 | 4 |
| Registres públics / reguladors | 1 | 5 | 5 | 2 |
| Informes corporatius | 1 | 4 | 2 | 1 |
| ONG / think tanks | 2 | 4 | 4 | 3 |
| Reviews / portals d’ocupació | 4 | 4 | 4 | 3 |

#### 5.4 Fonts òptimes i fonts “sorolloses” per objectiu

- **Opinió pública**
  - Òptimes: xarxes socials, mitjans, fòrums.
  - Sorolloses: informes corporatius, registres públics (massa lents per sentiment).
- **Reputació corporativa**
  - Òptimes: mitjans, registres/reguladors, ONG/think tanks, informes ESG.
  - Sorolloses: xarxes socials no segmentades (molt volum i “noise”).
- **Risc reputacional**
  - Òptimes: mitjans, registres/reguladors, fòrums, xarxes socials segmentades.
  - Sorolloses: blogs no especialitzats, portals d’opinió generalista.
- **Tendències socials**
  - Òptimes: xarxes socials, fòrums, newsletters temàtiques.
  - Sorolloses: registres públics i informes anuals (retard temporal).

#### 5.5 Exclusions per alineació amb el context del projecte

Exclou fonts quan:

- No aporten senyal accionable per cap objectiu (score ≤ 2 en tots).
- Estan fora del sector/territori de l’entitat analitzada.
- Presenten biaix estructural o falta de verificació repetida.
- Generen volum desproporcionat respecte al valor analític (soroll > senyal).

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
