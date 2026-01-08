import { useEffect, useMemo, useState } from 'react'
import { MapContainer, TileLayer, Marker, Popup, Circle, useMap } from 'react-leaflet'
import { LatLngExpression } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import Heatmap from './Heatmap'
import { heatmapService } from '../../services/api'

// Fix para iconos de Leaflet en React
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

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
}

function MapSizeHandler() {
  const map = useMap()

  useEffect(() => {
    const resize = () => map.invalidateSize()
    const timeout = window.setTimeout(resize, 0)
    window.addEventListener('resize', resize)
    return () => {
      window.clearTimeout(timeout)
      window.removeEventListener('resize', resize)
    }
  }, [map])

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
  heatmapGranularity = 'city'
}: GeographicMapProps) {
  const [zoomLevel, setZoomLevel] = useState<'world' | 'region' | 'city' | 'neighborhood'>('world')
  const [selectedLocation, setSelectedLocation] = useState<Location | null>(null)
  const [viewMode, setViewMode] = useState<'markers' | 'heatmap'>('markers')

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

  const getMarkerColor = (type: string) => {
    const colors: { [key: string]: string } = {
      country: '#FF6B35',
      region: '#4ECDC4',
      city: '#95E1D3',
      neighborhood: '#F38181',
      point: '#A8E6CF'
    }
    return colors[type] || '#888'
  }

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
        </div>
        <Heatmap
          caseId={caseId}
          metricType={heatmapMetric}
          granularity={heatmapGranularity}
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
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          style={{ height: '500px', width: '100%' }}
          scrollWheelZoom={true}
        >
          <MapSizeHandler />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          
          {locations.map((location) => (
            <Marker
              key={location.id}
              position={[location.latitude, location.longitude]}
              eventHandlers={{
                click: () => setSelectedLocation(location)
              }}
            >
              <Popup>
                <div className="location-popup">
                  <h4>{location.name}</h4>
                  <p><strong>Tipo:</strong> {location.type}</p>
                  {location.count && <p><strong>Eventos:</strong> {location.count}</p>}
                  {location.data && (
                    <div className="location-data">
                      <pre>{JSON.stringify(location.data, null, 2)}</pre>
                    </div>
                  )}
                </div>
              </Popup>
            </Marker>
          ))}
          
          {/* Círculos para mostrar concentración */}
          {locations.map((location) => (
            location.count && location.count > 1 && (
              <Circle
                key={`circle-${location.id}`}
                center={[location.latitude, location.longitude]}
                radius={location.count * 1000}
                pathOptions={{
                  fillColor: getMarkerColor(location.type),
                  fillOpacity: 0.2,
                  color: getMarkerColor(location.type),
                  weight: 2
                }}
              />
            )
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

