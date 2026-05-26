import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, Marker, Popup, Circle, CircleMarker, useMap } from 'react-leaflet'
import { LatLngExpression } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import Heatmap from './Heatmap'
import { geopoliticalService } from '../../services/api'

// Fix para iconos de Leaflet en React
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

interface MapLayerConfig {
  id: string
  label: string
  visible: boolean
  color: string
}

const DEFAULT_LAYERS: MapLayerConfig[] = [
  { id: 'markers', label: 'Ubicacions', visible: true, color: '#1e3a5f' },
  { id: 'geo_risks', label: 'Riscos geopolítics', visible: true, color: '#dc3545' },
  { id: 'events', label: 'Esdeveniments', visible: false, color: '#ff6b35' },
  { id: 'infra', label: 'Infraestructures', visible: true, color: '#6c757d' },
]

const ZOOM_BY_LEVEL: Record<'world' | 'region' | 'city' | 'neighborhood', number> = {
  world: 2,
  region: 4,
  city: 8,
  neighborhood: 12,
}

const CRITICAL_INFRA_POINTS = [
  { lat: 22.3, lng: 114.2, name: 'Hong Kong', type: 'Port', icon: '🚢', country: 'Xina' },
  { lat: 1.27, lng: 103.82, name: 'Singapore', type: 'Port', icon: '🚢', country: 'Singapur' },
  { lat: 29.97, lng: 32.55, name: 'Suez Canal', type: 'Canal', icon: '⚓', country: 'Egipte' },
  { lat: 9.06, lng: -79.68, name: 'Panama Canal', type: 'Canal', icon: '⚓', country: 'Panamà' },
  { lat: 51.9, lng: 4.47, name: 'Rotterdam', type: 'Port', icon: '🚢', country: 'Països Baixos' },
  { lat: 37.7, lng: 122.5, name: 'Shanghai', type: 'Port', icon: '🚢', country: 'Xina' },
  { lat: 50.9, lng: -1.4, name: 'Southhampton (cables)', type: 'Infraestructura digital', icon: '🔌', country: 'UK' },
  { lat: 37.4, lng: -5.9, name: 'Sevilla (cables)', type: 'Infraestructura digital', icon: '🔌', country: 'Espanya' },
  { lat: 26.9, lng: 49.6, name: 'Ras Tanura (petroli)', type: 'Energia', icon: '⛽', country: 'Aràbia Saudita' },
  { lat: 60.4, lng: 5.3, name: 'Bergen (gas)', type: 'Energia', icon: '⛽', country: 'Noruega' },
  { lat: 51.1, lng: 17.0, name: 'Druzhba Pipeline', type: 'Oleoducte', icon: '🛢️', country: 'Polònia' },
  { lat: 37.3, lng: -121.9, name: 'Silicon Valley', type: 'Tecnologia', icon: '💻', country: 'EUA' },
  { lat: 35.7, lng: 139.7, name: 'Tokio Tech Hub', type: 'Tecnologia', icon: '💻', country: 'Japó' },
  { lat: 40.7, lng: -74.0, name: 'NYSE / Wall Street', type: 'Financer', icon: '📈', country: 'EUA' },
  { lat: 51.5, lng: -0.1, name: 'City of London', type: 'Financer', icon: '📈', country: 'UK' },
]

const COUNTRY_COORDS: Record<string, [number, number]> = {
  Spain: [40.4, -3.7],
  España: [40.4, -3.7],
  France: [48.9, 2.4],
  Germany: [52.5, 13.4],
  USA: [38.9, -77.0],
  'United States': [38.9, -77.0],
  China: [39.9, 116.4],
  Xina: [39.9, 116.4],
  Russia: [55.8, 37.6],
  Ukraine: [50.4, 30.5],
  UK: [51.5, -0.1],
  'United Kingdom': [51.5, -0.1],
  Israel: [31.8, 35.2],
  Iran: [35.7, 51.4],
  India: [28.6, 77.2],
  Brazil: [-15.8, -47.9],
  Mexico: [19.4, -99.1],
  Japan: [35.7, 139.7],
  'Saudi Arabia': [24.7, 46.7],
}

const OSINT_SOURCE_COLORS: Record<string, string> = {
  tavily: '#78b0a1',
  gdelt: '#4a90d9',
  google_news: '#e8a838',
  reddit: '#ff4500',
  rss: '#6c757d',
  nikkei: '#c0392b',
  bloomberg: '#2c3e50',
  other: '#888888',
}

const OSINT_SOURCE_LABELS: Record<string, string> = {
  tavily: 'Tavily',
  gdelt: 'GDELT',
  google_news: 'Google News',
  reddit: 'Reddit',
  rss: 'RSS',
  nikkei: 'Nikkei',
  bloomberg: 'Bloomberg',
  other: 'Altres',
}

function getMarkerColor(type: string) {
  const colors: Record<string, string> = {
    country: '#FF6B35',
    region: '#4ECDC4',
    city: '#95E1D3',
    neighborhood: '#F38181',
    point: '#A8E6CF',
  }
  return colors[type] || '#888'
}

function getOsintSourceColor(location: Location): string {
  const primary = location.data?.primary_osint_source as string | undefined
  if (primary && OSINT_SOURCE_COLORS[primary]) {
    return OSINT_SOURCE_COLORS[primary]
  }
  const sources = location.data?.osint_sources as Record<string, number> | undefined
  if (sources) {
    const top = Object.entries(sources).sort((a, b) => b[1] - a[1])[0]?.[0]
    if (top && OSINT_SOURCE_COLORS[top]) {
      return OSINT_SOURCE_COLORS[top]
    }
  }
  return getMarkerColor(location.type)
}

function formatOsintSourceBreakdown(data?: Record<string, unknown>): string | null {
  const sources = data?.osint_sources as Record<string, number> | undefined
  if (!sources || Object.keys(sources).length === 0) return null
  return Object.entries(sources)
    .sort((a, b) => b[1] - a[1])
    .map(([src, n]) => `${OSINT_SOURCE_LABELS[src] || src}: ${n}`)
    .join(', ')
}

function resolveRiskCoords(risk: {
  country: string
  location_lat?: number
  location_lng?: number
}): [number, number] | null {
  if (risk.location_lat != null && risk.location_lng != null) {
    return [risk.location_lat, risk.location_lng]
  }
  return COUNTRY_COORDS[risk.country] ?? null
}

function eventPosition(coords: unknown): [number, number] | null {
  if (!coords) return null
  if (Array.isArray(coords) && coords.length >= 2) {
    return [Number(coords[0]), Number(coords[1])]
  }
  if (typeof coords === 'object' && coords !== null && 'lat' in coords && 'lng' in coords) {
    const c = coords as { lat: number; lng: number }
    return [c.lat, c.lng]
  }
  return null
}

interface Location {
  id: string
  name: string
  latitude: number
  longitude: number
  type: 'country' | 'region' | 'city' | 'neighborhood' | 'point'
  data?: any
  count?: number
}

interface GeographicMapProps {
  locations: Location[]
  title?: string
  initialZoom?: number
  initialCenter?: LatLngExpression
  caseId?: number
  showHeatmap?: boolean
  heatmapMetric?: 'posts' | 'sentiment' | 'engagement'
  heatmapGranularity?: 'country' | 'region' | 'city' | 'municipality'
  /** Quan el mapa està dins una pestanya/modal, cal invalidar mida en mostrar-se */
  isActive?: boolean
}

function MapViewportController({
  center,
  zoom,
  zoomLevel,
  isActive = true,
}: {
  center: LatLngExpression
  zoom: number
  zoomLevel: 'world' | 'region' | 'city' | 'neighborhood'
  isActive?: boolean
}) {
  const map = useMap()

  useEffect(() => {
    if (!isActive) return
    const levelZoom = ZOOM_BY_LEVEL[zoomLevel] ?? zoom
    map.setView(center, levelZoom, { animate: false })
    const t = window.setTimeout(() => map.invalidateSize(), 80)
    return () => window.clearTimeout(t)
  }, [map, center, zoom, zoomLevel, isActive])

  useEffect(() => {
    if (!isActive) return
    const resize = () => map.invalidateSize()
    window.addEventListener('resize', resize)
    return () => window.removeEventListener('resize', resize)
  }, [map, isActive])

  return null
}

function MapSizeHandler({ isActive = true }: { isActive?: boolean }) {
  const map = useMap()

  useEffect(() => {
    if (!isActive) return
    const resize = () => map.invalidateSize()
    const timeout = window.setTimeout(resize, 0)
    window.addEventListener('resize', resize)
    return () => {
      window.clearTimeout(timeout)
      window.removeEventListener('resize', resize)
    }
  }, [map, isActive])

  return null
}

export default function GeographicMap({ 
  locations, 
  title = "Geographic Map",
  initialZoom = 2,
  initialCenter = [20, 0] as LatLngExpression,
  caseId,
  showHeatmap = false,
  heatmapMetric = 'posts',
  heatmapGranularity = 'city',
  isActive = true,
}: GeographicMapProps) {
  const [zoomLevel, setZoomLevel] = useState<'world' | 'region' | 'city' | 'neighborhood'>('world')
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null)
  const [viewMode, setViewMode] = useState<'markers' | 'heatmap'>(showHeatmap ? 'heatmap' : 'markers')
  const [layers, setLayers] = useState<MapLayerConfig[]>(DEFAULT_LAYERS)

  const isLayerVisible = (id: string) => layers.find((l) => l.id === id)?.visible ?? false
  const toggleLayer = (id: string) =>
    setLayers((prev) => prev.map((l) => (l.id === id ? { ...l, visible: !l.visible } : l)))

  const { data: geoRisks } = useQuery({
    queryKey: ['geo-risks-map', caseId],
    queryFn: () => geopoliticalService.getRisks(caseId),
    enabled: !!caseId && isLayerVisible('geo_risks'),
  })

  const { data: geoEvents } = useQuery({
    queryKey: ['geo-events-map', caseId],
    queryFn: () => geopoliticalService.getEvents(caseId),
    enabled: !!caseId && isLayerVisible('events'),
  })

  const riskItems = (Array.isArray(geoRisks) ? geoRisks : []) as Array<{
    country: string
    overall_risk_score: number
    location_lat?: number
    location_lng?: number
  }>

  const eventItems = (geoEvents?.events ?? []) as Array<{
    location_coordinates?: unknown
    title: string
    event_type: string
    importance: string
  }>

  // Calcular centro y zoom basado en ubicaciones
  const mapCenter = useMemo(() => {
    if (locations.length === 0) return initialCenter
    
    const avgLat = locations.reduce((sum, loc) => sum + loc.latitude, 0) / locations.length
    const avgLng = locations.reduce((sum, loc) => sum + loc.longitude, 0) / locations.length
    return [avgLat, avgLng] as LatLngExpression
  }, [locations, initialCenter])

  const mapZoom = useMemo(() => {
    if (locations.length === 0) return initialZoom
    
    // Determinar zoom basado en dispersión
    const lats = locations.map(l => l.latitude)
    const lngs = locations.map(l => l.longitude)
    const latRange = Math.max(...lats) - Math.min(...lats)
    const lngRange = Math.max(...lngs) - Math.min(...lngs)
    const maxRange = Math.max(latRange, lngRange)
    
    if (maxRange > 50) return 2  // Mundo
    if (maxRange > 10) return 4  // Región
    if (maxRange > 1) return 8   // Ciudad
    return 12  // Barrio
  }, [locations, initialZoom])

  // Agrupar ubicaciones por tipo
  const locationsByType = useMemo(() => {
    const grouped: { [key: string]: Location[] } = {
      country: [],
      region: [],
      city: [],
      neighborhood: [],
      point: []
    }
    locations.forEach(loc => {
      if (grouped[loc.type]) {
        grouped[loc.type].push(loc)
      }
    })
    return grouped
  }, [locations])

  const getMarkerSize = (type: string, count?: number) => {
    const baseSize = {
      country: 15,
      region: 12,
      city: 10,
      neighborhood: 8,
      point: 6
    }[type] || 8
    
    return count ? baseSize + Math.min(count / 10, 5) : baseSize
  }

  // Show heatmap if enabled and caseId provided
  if (showHeatmap && caseId && viewMode === 'heatmap') {
    return (
      <div className="geographic-map-container">
        <div className="map-header">
          <h3>{title}</h3>
          <div className="view-mode-toggle">
            <button type="button" onClick={() => setViewMode('markers')}>
              Marcadors
            </button>
            <button type="button" className="active" onClick={() => setViewMode('heatmap')}>
              Mapa de Calor
            </button>
          </div>
        </div>
        <Heatmap
          caseId={caseId}
          metricType={heatmapMetric}
          granularity={heatmapGranularity}
          isActive={isActive}
        />
      </div>
    )
  }

  // If viewMode is heatmap and we have caseId, show heatmap
  if (viewMode === 'heatmap' && caseId) {
    return (
      <div className="geographic-map-container">
        <div className="map-header">
          <h3>{title}</h3>
          <div className="view-mode-toggle">
            <button type="button" onClick={() => setViewMode('markers')}>
              Marcadors
            </button>
            <button type="button" className="active" onClick={() => setViewMode('heatmap')}>
              Mapa de Calor
            </button>
          </div>
        </div>
        <Heatmap
          caseId={caseId}
          metricType={heatmapMetric || 'posts'}
          granularity={heatmapGranularity || 'city'}
        />
      </div>
    )
  }

  return (
    <div className="geographic-map-container">
      <div className="map-header">
        <h3>{title}</h3>
        {caseId && (
          <div className="view-mode-toggle">
            <button
              className={viewMode === 'markers' ? 'active' : ''}
              onClick={() => setViewMode('markers')}
            >
              Marcadors
            </button>
            <button
              className={viewMode === 'heatmap' ? 'active' : ''}
              onClick={() => setViewMode('heatmap')}
            >
              Mapa de Calor
            </button>
          </div>
        )}
      </div>

      <div
        style={{
          display: 'flex',
          gap: 'var(--spacing-sm)',
          flexWrap: 'wrap',
          padding: 'var(--spacing-sm) 0',
          marginBottom: 'var(--spacing-sm)',
        }}
      >
        <span
          style={{
            fontSize: 'var(--font-size-xs)',
            fontWeight: 600,
            color: 'var(--color-gray-600)',
            alignSelf: 'center',
          }}
        >
          Capes:
        </span>
        {layers.map((layer) => (
          <button
            key={layer.id}
            type="button"
            onClick={() => toggleLayer(layer.id)}
            style={{
              padding: '3px 10px',
              borderRadius: '999px',
              border: `1px solid ${layer.color}`,
              background: layer.visible ? layer.color : 'transparent',
              color: layer.visible ? 'white' : layer.color,
              fontSize: 'var(--font-size-xs)',
              fontWeight: 500,
              cursor: 'pointer',
              transition: 'all .15s',
            }}
          >
            {layer.label}
          </button>
        ))}
      </div>

      <div
        style={{
          display: 'flex',
          gap: 'var(--spacing-md)',
          flexWrap: 'wrap',
          padding: '0 0 var(--spacing-sm)',
          fontSize: 'var(--font-size-xs)',
          color: 'var(--color-gray-600)',
        }}
      >
        <span style={{ fontWeight: 600, alignSelf: 'center' }}>Fuentes OSINT:</span>
        {Object.entries(OSINT_SOURCE_COLORS).map(([key, color]) => (
          <span key={key} style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: '50%',
                background: color,
                display: 'inline-block',
              }}
            />
            {OSINT_SOURCE_LABELS[key] || key}
          </span>
        ))}
      </div>

      <div className="map-controls">
        <div className="zoom-buttons">
          <button 
            className={zoomLevel === 'world' ? 'active' : ''}
            onClick={() => setZoomLevel('world')}
          >
            Mundo
          </button>
          <button 
            className={zoomLevel === 'region' ? 'active' : ''}
            onClick={() => setZoomLevel('region')}
          >
            Región
          </button>
          <button 
            className={zoomLevel === 'city' ? 'active' : ''}
            onClick={() => setZoomLevel('city')}
          >
            Ciudad
          </button>
          <button 
            className={zoomLevel === 'neighborhood' ? 'active' : ''}
            onClick={() => setZoomLevel('neighborhood')}
          >
            Barrio
          </button>
        </div>
        
        <div className="location-stats">
          <div className="stat-item">
            <span className="stat-label">Total:</span>
            <span className="stat-value">{locations.length}</span>
          </div>
          {Object.entries(locationsByType).map(([type, locs]) => 
            locs.length > 0 && (
              <div key={type} className="stat-item">
                <span className="stat-label">{type}:</span>
                <span className="stat-value">{locs.length}</span>
              </div>
            )
          )}
        </div>
      </div>

      <div className="map-wrapper">
        {locations.length === 0 && (
          <p className="map-empty-hint">
            Sense punts del cas encara — capes d&apos;infraestructura i riscos geopolítics actives.
            Recull OSINT o extreu declaracions per omplir ubicacions.
          </p>
        )}
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          style={{ height: '500px', width: '100%' }}
          scrollWheelZoom={true}
        >
          <MapViewportController
            center={mapCenter}
            zoom={mapZoom}
            zoomLevel={zoomLevel}
            isActive={isActive}
          />
          <MapSizeHandler isActive={isActive} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          {isLayerVisible('markers') &&
            locations.map((location) => {
              const sourceColor = getOsintSourceColor(location)
              const radius = getMarkerSize(location.type, location.count)
              const sourceBreakdown = formatOsintSourceBreakdown(location.data)
              return (
                <CircleMarker
                  key={location.id}
                  center={[location.latitude, location.longitude]}
                  radius={radius}
                  pathOptions={{
                    fillColor: sourceColor,
                    fillOpacity: 0.85,
                    color: sourceColor,
                    weight: 2,
                  }}
                  eventHandlers={{
                    click: () => setSelectedLocation(location),
                  }}
                >
                  <Popup>
                    <div className="location-popup">
                      <h4>{location.name}</h4>
                      <p>
                        <strong>Tipo:</strong> {location.type}
                      </p>
                      {location.count && (
                        <p>
                          <strong>Eventos:</strong> {location.count}
                        </p>
                      )}
                      {sourceBreakdown && (
                        <p>
                          <strong>Fuentes OSINT:</strong> {sourceBreakdown}
                        </p>
                      )}
                      {location.data?.primary_osint_source && (
                        <p>
                          <strong>Fuente principal:</strong>{' '}
                          {OSINT_SOURCE_LABELS[String(location.data.primary_osint_source)] ||
                            String(location.data.primary_osint_source)}
                        </p>
                      )}
                    </div>
                  </Popup>
                </CircleMarker>
              )
            })}

          {isLayerVisible('markers') &&
            locations.map(
              (location) =>
                location.count &&
                location.count > 1 && (
                  <Circle
                    key={`circle-${location.id}`}
                    center={[location.latitude, location.longitude]}
                    radius={location.count * 1000}
                    pathOptions={{
                      fillColor: getOsintSourceColor(location),
                      fillOpacity: 0.2,
                      color: getOsintSourceColor(location),
                      weight: 2,
                    }}
                  />
                ),
            )}

          {isLayerVisible('geo_risks') &&
            riskItems.map((risk, i) => {
              const pos = resolveRiskCoords(risk)
              if (!pos) return null
              return (
                <Circle
                  key={`risk-${i}`}
                  center={pos}
                  radius={risk.overall_risk_score * 5000}
                  pathOptions={{
                    fillColor:
                      risk.overall_risk_score > 70
                        ? '#dc3545'
                        : risk.overall_risk_score > 40
                          ? '#ffc107'
                          : '#28a745',
                    fillOpacity: 0.25,
                    color:
                      risk.overall_risk_score > 70
                        ? '#dc3545'
                        : risk.overall_risk_score > 40
                          ? '#ffc107'
                          : '#28a745',
                    weight: 1.5,
                  }}
                >
                  <Popup>
                    <strong>{risk.country}</strong>
                    <br />
                    Risc global: {risk.overall_risk_score}/100
                  </Popup>
                </Circle>
              )
            })}

          {isLayerVisible('events') &&
            eventItems.map((ev, i) => {
              const pos = eventPosition(ev.location_coordinates)
              if (!pos) return null
              return (
                <Marker
                  key={`ev-${i}`}
                  position={pos}
                  icon={L.divIcon({
                    html: '<div style="background:#ff6b35;color:white;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:10px;font-weight:700;border:2px solid white;box-shadow:0 1px 3px rgba(0,0,0,.3)">⚡</div>',
                    className: '',
                    iconSize: [20, 20],
                    iconAnchor: [10, 10],
                  })}
                >
                  <Popup>
                    <strong>{ev.title}</strong>
                    <br />
                    Tipus: {ev.event_type}
                    <br />
                    Importància: {ev.importance}
                  </Popup>
                </Marker>
              )
            })}

          {isLayerVisible('infra') &&
            CRITICAL_INFRA_POINTS.map((pt, i) => (
              <Marker
                key={`infra-${i}`}
                position={[pt.lat, pt.lng]}
                icon={L.divIcon({
                  html: `<div style="background:#495057;color:white;border-radius:3px;padding:1px 4px;font-size:9px;font-weight:700;border:1px solid white;box-shadow:0 1px 2px rgba(0,0,0,.3);white-space:nowrap">${pt.icon} ${pt.name}</div>`,
                  className: '',
                  iconAnchor: [20, 10],
                })}
              >
                <Popup>
                  <strong>{pt.name}</strong>
                  <br />
                  Tipus: {pt.type}
                  <br />
                  {pt.country && `País: ${pt.country}`}
                </Popup>
              </Marker>
            ))}
        </MapContainer>
      </div>

      {selectedLocation && (
        <div className="location-details">
          <h4>Detalles: {selectedLocation.name}</h4>
          <div className="details-content">
            <p><strong>Coordenadas:</strong> {selectedLocation.latitude}, {selectedLocation.longitude}</p>
            <p><strong>Tipo:</strong> {selectedLocation.type}</p>
            {selectedLocation.data && (
              <div>
                <strong>Datos adicionales:</strong>
                <pre>{JSON.stringify(selectedLocation.data, null, 2)}</pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

