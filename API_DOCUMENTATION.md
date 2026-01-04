# Documentación de APIs - EINA Platform

## Introducción

EINA (OSINT Intelligence Platform) es una plataforma integral de análisis OSINT con IA que combina recopilación de datos, análisis cualitativo/cuantitativo y predicciones.

### Arquitectura de APIs

La plataforma utiliza FastAPI como framework backend, proporcionando endpoints RESTful organizados por módulos:
- **Autenticación**: `/api/auth`
- **Casos**: `/api/cases`
- **OSINT**: `/api/osint`
- **Análisis IA**: `/api/ai`
- **Reputación**: `/api/reputation`
- **Asuntos Públicos**: `/api/public-affairs`
- **Inversiones Avanzadas**: `/api/investment-advanced`
- **Geopolítica Avanzada**: `/api/geopolitical`
- **Integración**: `/api/integration`
- **Alertas**: `/api/alerts`
- **Dashboard**: `/api/dashboard`

### Autenticación

La mayoría de endpoints requieren autenticación mediante JWT tokens. Obtén un token mediante:

```bash
POST /api/auth/login
{
  "username": "usuario",
  "password": "contraseña"
}
```

Incluye el token en el header: `Authorization: Bearer <token>`

## Módulo de Reputación

### Endpoints

#### Listar Perfiles de Reputación
```http
GET /api/reputation/profiles?case_id={case_id}&entity_type={entity_type}
```

**Respuesta:**
```json
[
  {
    "id": 1,
    "entity_name": "TestCompany",
    "entity_type": "company",
    "reputation_score": 75.5,
    "sentiment_trend": "improving",
    "crisis_level": "none"
  }
]
```

#### Calcular Score de Reputación
```http
POST /api/reputation/analyze
{
  "entity_name": "TestCompany",
  "entity_type": "company",
  "case_id": 1
}
```

#### Obtener Score de Reputación
```http
GET /api/reputation/{entity_id}/score
```

#### Obtener Histórico
```http
GET /api/reputation/{entity_id}/history?days=30
```

#### Obtener Indicadores de Crisis
```http
GET /api/reputation/{entity_id}/crisis-indicators
```

**Respuesta:**
```json
{
  "crisis_level": "medium",
  "crisis_indicators": [
    {
      "type": "negative_sentiment_spike",
      "severity": "high",
      "description": "Aumento significativo de sentimiento negativo"
    }
  ],
  "recommendations": [
    "Activar protocolo de crisis",
    "Preparar comunicación de respuesta"
  ]
}
```

#### Análisis de Stakeholders
```http
GET /api/reputation/stakeholders?case_id={case_id}
```

## Módulo de Asuntos Públicos

### Endpoints

#### Listar Políticas
```http
GET /api/public-affairs/policies?case_id={case_id}&jurisdiction={jurisdiction}
```

#### Analizar Impacto de Política
```http
POST /api/public-affairs/analyze-impact?policy_topic={topic}&jurisdiction={jurisdiction}&case_id={case_id}
```

**Respuesta:**
```json
{
  "policy_id": 1,
  "policy_topic": "Climate Change",
  "jurisdiction": "global",
  "impact_score": 75.0,
  "impact_level": "high",
  "stakeholder_positions": {},
  "advocacy_opportunities": []
}
```

#### Identificar Stakeholders
```http
GET /api/public-affairs/stakeholders?case_id={case_id}&policy_topic={topic}
```

#### Oportunidades de Advocacy
```http
GET /api/public-affairs/advocacy-opportunities?case_id={case_id}
```

## Módulo de Inversiones Avanzadas

### Endpoints

#### Análisis ESG
```http
GET /api/investment-advanced/esg?case_id={case_id}&company_symbol={symbol}&country={country}
```

**Respuesta:**
```json
{
  "esg_score": 65.5,
  "environmental_score": 70.0,
  "social_score": 60.0,
  "governance_score": 66.5,
  "factors": {
    "environmental": ["Carbon emissions", "Renewable energy"],
    "social": ["Labor practices", "Community engagement"],
    "governance": ["Board diversity", "Transparency"]
  },
  "recommendations": [
    "Mejorar prácticas laborales",
    "Aumentar transparencia corporativa"
  ]
}
```

#### Evaluar Riesgo Regulatorio
```http
GET /api/investment-advanced/regulatory-risk?case_id={case_id}&country={country}&industry={industry}
```

#### Comparar Oportunidades de Mercado
```http
GET /api/investment-advanced/market-opportunities?case_id={case_id}&countries={countries}&industries={industries}
```

#### Impacto Geopolítico
```http
GET /api/investment-advanced/geopolitical-impact?case_id={case_id}&countries={countries}&investment_type={type}
```

## Módulo de Integración

### Endpoints

#### Análisis Integral
```http
POST /api/integration/comprehensive-analysis?case_id={case_id}&entity_name={name}&countries={countries}
```

**Respuesta:**
```json
{
  "case_id": 1,
  "assessment_date": "2025-12-28T00:00:00",
  "risks": {
    "reputation": {
      "reputation_score": 75.0,
      "reputation_risk": 25.0,
      "crisis_level": "none",
      "overall_level": "low"
    },
    "geopolitical": {
      "overall_risk": 45.0,
      "countries": ["USA", "China"],
      "overall_level": "medium"
    }
  },
  "overall_risk": {
    "overall_score": 35.0,
    "level": "low"
  },
  "recommendations": [
    "Monitorear eventos geopolíticos",
    "Mantener estrategia de reputación"
  ]
}
```

#### Impacto Geopolítico en Inversiones
```http
GET /api/integration/geopolitical-investment-impact?case_id={case_id}&countries={countries}&investment_type={type}
```

#### Correlación Reputación-Geopolítica
```http
GET /api/integration/reputation-geopolitical?entity_name={name}&case_id={case_id}
```

## Módulo Geopolítico Avanzado

### Endpoints

#### Análisis de Cadenas de Suministro
```http
GET /api/geopolitical/supply-chains?country={country}&industry={industry}&case_id={case_id}
```

#### Interdependencias Económicas
```http
GET /api/geopolitical/interdependencies?country1={country1}&country2={country2}&case_id={case_id}
```

#### Análisis de Escenarios
```http
POST /api/geopolitical/scenarios?case_id={case_id}&countries={countries}&time_horizon={horizon}
```

#### Riesgo Regulatorio
```http
GET /api/geopolitical/regulatory-risks?country={country}&industry={industry}&case_id={case_id}
```

## Dashboard

### Endpoints

#### Obtener Todas las Métricas
```http
GET /api/dashboard/metrics?days=7
```

**Respuesta:**
```json
{
  "total_mentions": {
    "total": 1500,
    "period_days": 7
  },
  "sentiment_score": {
    "average": 0.65,
    "period_days": 7
  },
  "advanced_metrics": {
    "reputation_risk_index": {
      "value": 25.5,
      "level": "low",
      "profiles_analyzed": 10
    },
    "geopolitical_risk_index": {
      "value": 45.0,
      "level": "medium",
      "countries_analyzed": 5
    },
    "investment_opportunity_score": {
      "value": 65.0,
      "level": "high"
    },
    "public_affairs_engagement_rate": {
      "value": 55.0,
      "osint_activities": 20
    },
    "cross_module_risk_correlation": {
      "value": 35.0,
      "level": "low",
      "components": 4
    }
  }
}
```

#### Métricas Avanzadas
```http
GET /api/dashboard/advanced-metrics?days=7
```

## Alertas

### Endpoints

#### Obtener Todas las Alertas
```http
GET /api/alerts?case_id={case_id}&entity_name={name}&countries={countries}
```

**Respuesta:**
```json
{
  "alerts": [
    {
      "type": "reputation_crisis",
      "title": "Crisis de Reputación Detectada",
      "description": "Aumento significativo de sentimiento negativo",
      "severity": "high",
      "timestamp": "2025-12-28T00:00:00",
      "details": {
        "entity_name": "TestCompany",
        "crisis_level": "high"
      }
    }
  ],
  "total_alerts": 5,
  "critical": 1,
  "high": 2,
  "medium": 2
}
```

## Casos de Uso

### Detección de Crisis de Reputación

1. Calcular score de reputación: `POST /api/reputation/analyze`
2. Obtener indicadores de crisis: `GET /api/reputation/{id}/crisis-indicators`
3. Si hay crisis, revisar alertas: `GET /api/alerts?entity_name={name}`

### Análisis de Política

1. Analizar impacto: `POST /api/public-affairs/analyze-impact`
2. Identificar stakeholders: `GET /api/public-affairs/stakeholders`
3. Obtener oportunidades: `GET /api/public-affairs/advocacy-opportunities`

### Análisis ESG

1. Analizar ESG: `GET /api/investment-advanced/esg`
2. Evaluar riesgo regulatorio: `GET /api/investment-advanced/regulatory-risk`
3. Comparar oportunidades: `GET /api/investment-advanced/market-opportunities`

### Análisis Integral

1. Generar análisis integral: `POST /api/integration/comprehensive-analysis`
2. Revisar correlaciones: `GET /api/integration/reputation-geopolitical`
3. Monitorear alertas: `GET /api/alerts`
