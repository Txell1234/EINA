import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import { LatLngExpression } from 'leaflet'
import 'leaflet/dist/leaflet.css'
import L from 'leaflet'
import { heatmapService } from '../../services/api'
import './Heatmap.css'

// Fix para iconos de Leaflet en React
delete (L.Icon.Default.prototype as any)._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

interface HeatmapPoint {
  lat: number
  lng: number
  intensity: number
  metadata: {
    location_name: string
    count?: number
    sentiment?: number
    engagement?: number
    themes?: string[]
    dominant_theme?: string
    source_breakdown?: Record<string, number>
  }
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

function formatSourceBreakdown(breakdown?: Record<string, number>): string {
  if (!breakdown || Object.keys(breakdown).length === 0) return ''
  return Object.entries(breakdown)
    .sort((a, b) => b[1] - a[1])
    .map(([src, n]) => `${OSINT_SOURCE_LABELS[src] || src}: ${n}`)
    .join(', ')
}

interface LocationRelationship {
  source_location: {  // Changed from 'from'
    location: string
    lat: number
    lng: number
  }
  target_location: {  // Changed from 'to'
    location: string
    lat: number
    lng: number
  }
  strength: number
  type: string
  count: number
}

interface HeatmapProps {
  caseId: number
  metricType: 'posts' | 'sentiment' | 'engagement' | 'custom'
  granularity?: 'country' | 'region' | 'city' | 'municipality'
  timeRange?: { start: string; end: string }
  platform?: string
  customMetric?: string
  isActive?: boolean
}

// Heatmap Layer Component with relationships (arrows)
function HeatmapLayer({ points, relationships }: { points: HeatmapPoint[]; relationships?: LocationRelationship[] }) {
  const map = useMap()

  useEffect(() => {
    if (!points || points.length === 0) return

    const circles: L.Circle[] = []
    const arrows: L.Polyline[] = []
    
    // Create heatmap visualization using circles with varying opacity and size
    points.forEach((point) => {
      // Calculate radius based on intensity (scaled appropriately)
      const baseRadius = 5000 // 5km base radius
      const radius = baseRadius * (0.5 + point.intensity * 1.5) // Scale from 2.5km to 12.5km
      
      // Opacity based on intensity
      const opacity = Math.max(0.2, Math.min(0.8, point.intensity * 0.8))
      
      // Color based on theme, sentiment, or intensity
      const color = getColorForIntensity(
        point.intensity, 
        point.metadata.sentiment, 
        point.metadata.dominant_theme
      )
      
      const circle = L.circle([point.lat, point.lng], {
        radius: radius, // in meters
        fillColor: color,
        fillOpacity: opacity,
        color: color,
        weight: 2,
        opacity: 0.6
      })
      
      // Add popup with metadata
      const themesList = point.metadata.themes?.join(', ') || point.metadata.dominant_theme || 'N/A'
      const sourcesList = formatSourceBreakdown(point.metadata.source_breakdown)
      const popupContent = `
        <div style="padding: 0.5rem; min-width: 200px;">
          <strong>${point.metadata.location_name}</strong><br/>
          ${point.metadata.count !== undefined ? `Posts: ${point.metadata.count}<br/>` : ''}
          ${point.metadata.sentiment !== undefined ? `Sentiment: ${point.metadata.sentiment.toFixed(2)}<br/>` : ''}
          ${point.metadata.engagement !== undefined ? `Engagement: ${point.metadata.engagement}<br/>` : ''}
          ${point.metadata.themes ? `Temàtiques: ${themesList}<br/>` : ''}
          ${sourcesList ? `Fuentes OSINT: ${sourcesList}<br/>` : ''}
          Intensitat: ${(point.intensity * 100).toFixed(1)}%
        </div>
      `
      circle.bindPopup(popupContent)
      
      circle.addTo(map)
      circles.push(circle)
    })

    // Draw relationship arrows
    if (relationships && relationships.length > 0) {
      relationships.forEach((rel) => {
        const fromLat = rel.source_location.lat  // Changed from 'rel.from.lat'
        const fromLng = rel.source_location.lng  // Changed from 'rel.from.lng'
        const toLat = rel.target_location.lat    // Changed from 'rel.to.lat'
        const toLng = rel.target_location.lng    // Changed from 'rel.to.lng'
        
        // Create curved arrow using bezier curve approximation
        const midLat = (fromLat + toLat) / 2
        const midLng = (fromLng + toLng) / 2
        
        // Calculate perpendicular offset for curve
        const dx = toLng - fromLng
        const dy = toLat - fromLat
        const distance = Math.sqrt(dx * dx + dy * dy)
        if (distance === 0) return
        const offset = distance * 0.1 // 10% offset for curve
        
        // Perpendicular vector
        const perpLat = -dy / distance * offset
        const perpLng = dx / distance * offset
        
        const curveLat = midLat + perpLat
        const curveLng = midLng + perpLng
        
        // Create curved polyline
        const arrow = L.polyline(
          [[fromLat, fromLng], [curveLat, curveLng], [toLat, toLng]],
          {
            color: '#667eea',
            weight: Math.max(2, rel.strength * 3),
            opacity: Math.min(0.8, 0.3 + rel.strength * 0.5),
            dashArray: '5, 5'
          }
        )
        
        // Add arrowhead marker at the end
        const arrowhead = L.marker([toLat, toLng], {
          icon: L.divIcon({
            className: 'arrowhead-marker',
            html: `<div style="
              width: 0;
              height: 0;
              border-left: 8px solid transparent;
              border-right: 8px solid transparent;
              border-top: 12px solid #667eea;
              transform: rotate(${Math.atan2(dy, dx) * 180 / Math.PI}deg);
            "></div>`,
            iconSize: [16, 16],
            iconAnchor: [8, 8]
          })
        })
        
        // Popup for relationship
        const relPopup = `
          <div style="padding: 0.5rem;">
            <strong>Relació</strong><br/>
            ${rel.source_location.location} → ${rel.target_location.location}<br/>
            Força: ${rel.strength.toFixed(2)}<br/>
            Mencions: ${rel.count}
          </div>
        `
        arrow.bindPopup(relPopup)
        
        arrow.addTo(map)
        arrowhead.addTo(map)
        arrows.push(arrow)
      })
    }

    // Cleanup function
    return () => {
      circles.forEach(circle => map.removeLayer(circle))
      arrows.forEach(arrow => map.removeLayer(arrow))
    }
  }, [map, points, relationships])

  return null
}

function MapSizeHandler({ isActive = true }: { isActive?: boolean }) {
  const map = useMap()

  useEffect(() => {
    if (!isActive) return
    const resize = () => map.invalidateSize()
    const timeout = window.setTimeout(resize, 80)
    window.addEventListener('resize', resize)
    return () => {
      window.clearTimeout(timeout)
      window.removeEventListener('resize', resize)
    }
  }, [map, isActive])

  return null
}

function getColorForTheme(theme?: string, sentiment?: number): string {
  // Theme-based colors
  const themeColors: Record<string, string> = {
    "reputation": "#667eea",      // Purple
    "crisis": "#dc3545",           // Red
    "support": "#28a745",          // Green
    "opposition": "#fd7e14",       // Orange
    "policy": "#17a2b8",           // Cyan
    "economic": "#ffc107",         // Yellow
    "social": "#6f42c1",           // Indigo
    "environmental": "#20c997",    // Teal
    "general": "#6c757d"           // Gray
  }
  
  if (theme && themeColors[theme]) {
    return themeColors[theme]
  }
  
  // Fallback to sentiment-based colors
  if (sentiment !== undefined) {
    if (sentiment > 0.3) return '#28a745' // Green (positive)
    if (sentiment < -0.3) return '#dc3545' // Red (negative)
    return '#ffc107' // Yellow (neutral)
  }
  
  // Default: blue
  return '#007bff'
}

function getColorForIntensity(intensity: number, sentiment?: number, theme?: string): string {
  // Use theme color if available
  if (theme) {
    return getColorForTheme(theme, sentiment)
  }
  
  // Otherwise use sentiment or intensity
  if (sentiment !== undefined) {
    if (sentiment > 0.3) return '#28a745' // Green
    if (sentiment < -0.3) return '#dc3545' // Red
    return '#ffc107' // Yellow
  }
  
  // Color based on intensity: blue to red
  if (intensity < 0.2) return '#007bff' // Blue
  if (intensity < 0.4) return '#17a2b8' // Cyan
  if (intensity < 0.6) return '#28a745' // Green
  if (intensity < 0.8) return '#ffc107' // Yellow
  return '#dc3545' // Red
}

export default function Heatmap({
  caseId,
  metricType,
  granularity = 'city',
  timeRange,
  platform,
  customMetric,
  isActive = true,
}: HeatmapProps) {
  const [selectedPoint, setSelectedPoint] = useState<HeatmapPoint | null>(null)

  const timeRangeParam =
    timeRange?.start && timeRange?.end ? { start: timeRange.start, end: timeRange.end } : undefined

  const { data: heatmapData, isLoading, error } = useQuery({
    queryKey: ['heatmap', caseId, metricType, granularity, platform, timeRange, customMetric],
    queryFn: async () => {
      if (caseId === 0) {
        return heatmapService.getDashboardSummary(granularity)
      }
      if (metricType === 'custom' && customMetric) {
        return heatmapService.getCustom(caseId, customMetric, granularity, platform, timeRangeParam)
      }
      if (metricType === 'sentiment') {
        return heatmapService.getSentiment(caseId, granularity, platform, timeRangeParam)
      }
      if (metricType === 'engagement') {
        return heatmapService.getEngagement(caseId, granularity, platform, timeRangeParam)
      }
      return heatmapService.getPosts(caseId, granularity, platform, timeRangeParam)
    },
    enabled: caseId !== undefined && caseId !== null,
  })

  const points: HeatmapPoint[] = heatmapData?.points || []
  const relationships: LocationRelationship[] = heatmapData?.relationships || []

  // Calculate map center and zoom
  const mapCenter = useMemo(() => {
    if (points.length === 0) return [42.5462, 1.6016] as LatLngExpression // Default: Andorra
    
    const avgLat = points.reduce((sum, p) => sum + p.lat, 0) / points.length
    const avgLng = points.reduce((sum, p) => sum + p.lng, 0) / points.length
    return [avgLat, avgLng] as LatLngExpression
  }, [points])

  const mapZoom = useMemo(() => {
    if (points.length === 0) return 6
    
    const lats = points.map(p => p.lat)
    const lngs = points.map(p => p.lng)
    const latRange = Math.max(...lats) - Math.min(...lats)
    const lngRange = Math.max(...lngs) - Math.min(...lngs)
    const maxRange = Math.max(latRange, lngRange)
    
    if (maxRange > 50) return 2  // World
    if (maxRange > 10) return 4  // Region
    if (maxRange > 1) return 8   // City
    return 12  // Municipality
  }, [points])

  const globalSourceBreakdown = useMemo(() => {
    const totals: Record<string, number> = {}
    for (const point of points) {
      const sb = point.metadata.source_breakdown
      if (!sb) continue
      for (const [src, n] of Object.entries(sb)) {
        totals[src] = (totals[src] || 0) + n
      }
    }
    return totals
  }, [points])

  if (isLoading) {
    return (
      <div className="heatmap-container">
        <div className="heatmap-loading">Carregant mapa de calor...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="heatmap-container">
        <div className="heatmap-error">Error carregant mapa de calor: {String(error)}</div>
      </div>
    )
  }

  if (!heatmapData || points.length === 0) {
    return (
      <div className="heatmap-container">
        <div className="heatmap-empty">No hi ha dades de calor per aquest cas — mapa base visible.</div>
        <div className="heatmap-map-wrapper">
          <MapContainer
            center={[20, 0]}
            zoom={2}
            style={{ height: '500px', width: '100%' }}
            scrollWheelZoom={true}
          >
            <MapSizeHandler isActive={isActive} />
            <TileLayer
              attribution='&copy; OpenStreetMap'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
          </MapContainer>
        </div>
      </div>
    )
  }

  return (
    <div className="heatmap-container">
      <div className="heatmap-header">
        <h3>Mapa de Calor - {metricType.charAt(0).toUpperCase() + metricType.slice(1)}</h3>
        <div className="heatmap-stats">
          <span>Punts: {heatmapData.total_points}</span>
          <span>Posts: {heatmapData.total_posts}</span>
          {heatmapData.platform && <span>Plataforma: {heatmapData.platform}</span>}
        </div>
      </div>

      <div className="heatmap-map-wrapper">
        <MapContainer
          center={mapCenter}
          zoom={mapZoom}
          style={{ height: '500px', width: '100%' }}
          scrollWheelZoom={true}
        >
          <MapSizeHandler isActive={isActive} />
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <HeatmapLayer points={points} relationships={relationships} />
        </MapContainer>
      </div>

      <div className="heatmap-legend">
        <div className="legend-title">Intensitat</div>
        <div className="legend-gradient">
          <span style={{ color: '#007bff' }}>Baixa</span>
          <div className="gradient-bar">
            <div style={{ background: 'linear-gradient(to right, #007bff, #17a2b8, #28a745, #ffc107, #dc3545)' }}></div>
          </div>
          <span style={{ color: '#dc3545' }}>Alta</span>
        </div>
        <div className="legend-themes">
          <div className="legend-title">Temàtiques:</div>
          <div className="theme-items">
            <span style={{ color: '#667eea' }}>●</span> Reputació
            <span style={{ color: '#dc3545' }}>●</span> Crisi
            <span style={{ color: '#28a745' }}>●</span> Suport
            <span style={{ color: '#fd7e14' }}>●</span> Oposició
            <span style={{ color: '#17a2b8' }}>●</span> Política
            <span style={{ color: '#ffc107' }}>●</span> Econòmic
            <span style={{ color: '#6f42c1' }}>●</span> Social
            <span style={{ color: '#20c997' }}>●</span> Medi Ambient
          </div>
        </div>
        {Object.keys(globalSourceBreakdown).length > 0 && (
          <div className="legend-sources">
            <div className="legend-title">Fuentes OSINT:</div>
            <div className="theme-items">
              {Object.entries(globalSourceBreakdown)
                .sort((a, b) => b[1] - a[1])
                .map(([src, count]) => (
                  <span key={src} style={{ marginRight: '0.75rem' }}>
                    <span style={{ color: OSINT_SOURCE_COLORS[src] || OSINT_SOURCE_COLORS.other }}>●</span>{' '}
                    {OSINT_SOURCE_LABELS[src] || src} ({count})
                  </span>
                ))}
            </div>
          </div>
        )}
        {metricType === 'sentiment' && (
          <div className="legend-sentiment">
            <span style={{ color: '#28a745' }}>●</span> Positiu
            <span style={{ color: '#ffc107' }}>●</span> Neutral
            <span style={{ color: '#dc3545' }}>●</span> Negatiu
          </div>
        )}
        {relationships && relationships.length > 0 && (
          <div className="legend-relationships">
            <div className="legend-title">Relacions:</div>
            <div>Fletxes mostren connexions entre ubicacions</div>
            <div>Grosor = Força de la relació</div>
          </div>
        )}
      </div>

      {selectedPoint && (
        <div className="heatmap-popup">
          <h4>{selectedPoint.metadata.location_name}</h4>
          <div className="popup-details">
            {selectedPoint.metadata.count !== undefined && (
              <div>Posts: {selectedPoint.metadata.count}</div>
            )}
            {selectedPoint.metadata.sentiment !== undefined && (
              <div>Sentiment: {selectedPoint.metadata.sentiment.toFixed(2)}</div>
            )}
            {selectedPoint.metadata.engagement !== undefined && (
              <div>Engagement: {selectedPoint.metadata.engagement}</div>
            )}
            {formatSourceBreakdown(selectedPoint.metadata.source_breakdown) && (
              <div>Fuentes OSINT: {formatSourceBreakdown(selectedPoint.metadata.source_breakdown)}</div>
            )}
            <div>Intensitat: {(selectedPoint.intensity * 100).toFixed(1)}%</div>
          </div>
        </div>
      )}
    </div>
  )
}
