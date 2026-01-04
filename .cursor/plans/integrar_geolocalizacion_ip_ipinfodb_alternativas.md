# Plan: Integrar Geolocalización por IP (IPInfoDB y Alternativas)

## Anàlisi del Servei

Segons la recerca, IPInfoDB ja no accepta nous registres per a la seva API. En canvi, recomanen IP2Location.io. Tanmateix, hi ha alternatives gratuïtes millors:

### Alternatives Gratuïtes:

1. **IPinfo.io** (Recomanat)
   - API gratuïta amb límits: 50,000 requests/mes
   - Precisa a nivell de país i ASN
   - Informació: país, regió, ciutat, coordenades, ISP, ASN
   - API key gratuïta disponible
   - Documentació: https://ipinfo.io/developers

2. **IPLocate.io**
   - Bases de dades gratuïtes descarregables (CSV, MMDB)
   - Precisa a nivell de país
   - Llicència CC BY-SA 4.0
   - No requereix API key per descarregar

3. **IP2Location.io** (Recomanat per IPInfoDB)
   - API gratuïta amb límits
   - Precisa geolocalització
   - Requereix registre

## Implementació Recomanada: IPinfo.io

### Fase 1: Crear Integració IPinfo
- Crear `backend/integrations/ipinfo_api.py`
- Implementar mètodes:
  - `get_ip_info(ip: str)` - Informació completa d'una IP
  - `get_batch_info(ips: List[str])` - Múltiples IPs (opcional)
- Incloure informació: país, regió, ciutat, coordenades, ISP, ASN, timezone

### Fase 2: Integrar amb OSINT Service
- Afegir suport per `ip_geolocation` a `OSINTService`
- Permetre geolocalització d'IPs trobades en resultats OSINT
- Enriquir resultats amb dades geogràfiques

### Fase 3: Endpoints API
- Afegir a `backend/routers/osint_collection.py`:
  - `POST /api/osint/ip-geolocation` - Geolocalitzar una IP
- Afegir a `backend/routers/geographic.py`:
  - `GET /api/geographic/ip/{ip_address}` - Obtenir ubicació d'una IP

### Fase 4: Frontend
- Afegir formulari per geolocalització d'IP a `OSINTCollection.tsx`
- Mostrar resultats en mapa geogràfic
- Integrar amb `GeographicMap` component

## Configuració

Afegir a `backend/app/config.py`:
- `IPINFO_API_KEY` (opcional, però recomanat per majors límits)

Afegir a `backend/env.example`:
- Instruccions per obtenir API key gratuïta de IPinfo

## Estructura de Fitxers

```
backend/integrations/
  - ipinfo_api.py (nou)
```

## Endpoints Nous

- `POST /api/osint/ip-geolocation` - Geolocalitzar IP
- `GET /api/geographic/ip/{ip_address}` - Obtenir ubicació d'IP

## Beneficis

1. **Geolocalització automàtica** - Obtenir ubicació de IPs trobades en investigacions OSINT
2. **Enriquiment de dades** - Afegir coordenades i informació geogràfica a resultats
3. **Visualització en mapes** - Mostrar IPs en mapes geogràfics
4. **Gratuït** - IPinfo ofereix 50,000 requests/mes gratuïtes

## Alternatives si IPinfo no està disponible

Si l'usuari no pot obtenir API key de IPinfo, implementar fallback a:
- IPLocate.io (base de dades descarregable)
- O usar una base de dades local MMDB









