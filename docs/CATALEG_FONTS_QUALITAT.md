# Catàleg intern de qualitat de fonts

## Objectiu
Definir llindars de qualitat i classificar les fonts de dades utilitzades al sistema per assegurar la fiabilitat, la cobertura i l'accés, amb justificació clara per a cada font. Aquest catàleg serveix com a referència interna per a l'equip i stakeholders.

## Llindars de qualitat
S'utilitza una escala de 1 a 5 per a cada criteri:
- **Fiabilitat**: consistència, reputació, estabilitat d'API, qualitat de dades.
- **Cobertura**: amplitud/volum de dades i capacitat de cobrir casos d'ús clau.
- **Accés**: disponibilitat, cost, límits i facilitat d'ús (quota, API key, SLA).

### Criteris de classificació
- **Òptimes**: ≥4 en fiabilitat, cobertura i accés.
- **Bones**: ≥3 en tots els criteris i cap <3.
- **Acceptables**: ≥2 en tots els criteris i cap <2.
- **No recomanades**: qualsevol criteri <2 o limitacions crítiques (cost elevat sense alternativa, cobertura insuficient per a casos bàsics, o dependència massa restrictiva).

## Catàleg de fonts (decisions)

> Escales i justificacions basades en l'estat actual d'integració i ús descrit a `APIS_ANALYSIS.md`.

### Òptimes

**OpenAI API** (IA crítica) — *Fiabilitat 4 · Cobertura 5 · Accés 4*  
Justificació:
- Fiabilitat alta per a anàlisi i generació de resultats consistents.
- Cobertura transversal (sentiment, prediccions, informes) per a múltiples casos.
- Accés per pagament per ús però amb disponibilitat clara i estable.

**IPStack API** (geolocalització) — *Fiabilitat 4 · Cobertura 4 · Accés 4*  
Justificació:
- Fiabilitat estable amb dades d'IP estructurades.
- Cobertura suficient per geolocalització d'IPs a escala.
- Accés amb quota gratuïta mensual i configuració ja disponible.

### Bones

**EnsembleData API** (xarxes socials) — *Fiabilitat 4 · Cobertura 4 · Accés 3*  
Justificació:
- Bona reputació i fonts múltiples amb dades coherents.
- Cobertura àmplia de plataformes socials.
- Accés requereix API key i límits, però és viable per operació regular.

**News API** (mitjans digitals) — *Fiabilitat 3 · Cobertura 4 · Accés 3*  
Justificació:
- Fiabilitat correcta per notícies agregades.
- Cobertura notable per temes i països.
- Accés amb límits diaris i dependència d'API key.

**Nominatim API** (geocodificació) — *Fiabilitat 3 · Cobertura 3 · Accés 4*  
Justificació:
- Fiabilitat acceptable per a geocodificació bàsica.
- Cobertura suficient per ubicacions comunes.
- Accés gratuït, però amb límits estrictes per ús intensiu.

**GitHub API** (repositoris) — *Fiabilitat 4 · Cobertura 3 · Accés 3*  
Justificació:
- Fiabilitat alta per a dades de repositoris i activitat.
- Cobertura moderada (no cobreix fonts no tècniques).
- Accés amb límits, però escalable amb token.

**Wayback Machine API** (històrics web) — *Fiabilitat 3 · Cobertura 3 · Accés 4*  
Justificació:
- Fiabilitat acceptable per snapshots històrics.
- Cobertura útil, però no universal per totes les URLs.
- Accés gratuït i sense clau d'API.

**REST Countries API** (enriquiment països) — *Fiabilitat 3 · Cobertura 3 · Accés 4*  
Justificació:
- Fiabilitat correcta per dades de països.
- Cobertura suficient per enriquiment de geodades.
- Accés gratuït i simple.

**CoinGecko API** (criptomonedes) — *Fiabilitat 3 · Cobertura 3 · Accés 4*  
Justificació:
- Fiabilitat correcta per mercats cripto.
- Cobertura adequada per principals actius.
- Accés gratuït amb límits raonables.

### Acceptables

**Reddit API** (fòrums) — *Fiabilitat 3 · Cobertura 3 · Accés 2*  
Justificació:
- Fiabilitat acceptable, però pot variar per límits i canvis d'API.
- Cobertura moderada per discussions específiques.
- Accés limitat sense OAuth; pot requerir ajustos per volum.

**Alpha Vantage API** (finances) — *Fiabilitat 3 · Cobertura 2 · Accés 2*  
Justificació:
- Fiabilitat correcta però amb límits molt estrictes.
- Cobertura parcial per dades financeres i casos d'inversió.
- Accés restringit per quota baixa en pla gratuït.

**Finnhub API** (finances) — *Fiabilitat 3 · Cobertura 3 · Accés 2*  
Justificació:
- Fiabilitat acceptable per dades de mercat.
- Cobertura decent per notícies i mercats.
- Accés limitat per límits de quota gratuïta.

**Financial Modeling Prep API** (finances) — *Fiabilitat 3 · Cobertura 3 · Accés 2*  
Justificació:
- Fiabilitat acceptable per dades d'empreses.
- Cobertura moderada per casos d'inversió.
- Accés depèn d'API key i límits de pla gratuït.

**ExchangeRate API** (divises) — *Fiabilitat 3 · Cobertura 3 · Accés 2*  
Justificació:
- Fiabilitat correcta per divises.
- Cobertura suficient per casos comercials bàsics.
- Accés limitat per quota mensual reduïda.

**Fixer.io API** (divises) — *Fiabilitat 3 · Cobertura 2 · Accés 2*  
Justificació:
- Fiabilitat acceptable però amb límits estrictes.
- Cobertura limitada (similar a ExchangeRate, sense avantatge clar).
- Accés restringit per quota baixa.

**DNS/WHOIS Service** (OSINT tècnic) — *Fiabilitat 3 · Cobertura 2 · Accés 3*  
Justificació:
- Fiabilitat acceptable per consultes puntuals.
- Cobertura limitada a casos tècnics específics.
- Accés gratuït però pot requerir canvis de proveïdor segons volum.

### No recomanades

**Shodan API** (seguretat) — *Fiabilitat 4 · Cobertura 2 · Accés 1*  
Justificació:
- Fiabilitat alta per a dades de seguretat.
- Cobertura enfocada només en dispositius exposats (casos molt específics).
- Accés amb cost obligatori i dependència d'un compte de pagament.

**Permutable AI API** (geopolítica) — *Fiabilitat 3 · Cobertura 2 · Accés 1*  
Justificació:
- Fiabilitat acceptable, però dependència d'un trial/premium.
- Cobertura limitada a geopolítica; no cobreix la majoria de casos base.
- Accés restrictiu (trial/premium) i risc de discontinuïtat.

## Publicació del catàleg
- Ubicació interna: `docs/CATALEG_FONTS_QUALITAT.md` (aquest document).
- Públic intern objectiu: equip tècnic, producte i stakeholders.
- Canal recomanat: repositori intern + enllaç al tauler de projecte.

## Reavaluació periòdica (cada 3–6 mesos)
1. Revisar canvis de preus, SLA, límits i condicions d'ús de cada font.
2. Verificar mètriques de qualitat observades (errors, completitud, consistència).
3. Actualitzar puntuacions i classificació en aquest catàleg.
4. Comunicar canvis a l'equip i stakeholders.

**Darrera actualització**: 2026-01-09
