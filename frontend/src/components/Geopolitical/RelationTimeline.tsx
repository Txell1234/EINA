import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { geopoliticalService } from '../../services/api'
import './RelationTimeline.css'

interface RelationTimelineProps {
  country1: string
  country2: string
  days?: number
}

interface TimelineEvent {
  id: number
  type: string
  title: string
  date: string
  importance: string
  impact: number
}

interface TimelineTreaty {
  id: number
  name: string
  type: string
  signing_date: string
  status: string
}

export default function RelationTimeline({ country1, country2, days = 90 }: RelationTimelineProps) {
  const [selectedView, setSelectedView] = useState<'all' | 'events' | 'treaties'>('all')

  const { data: timelineData, isLoading } = useQuery({
    queryKey: ['relation-timeline', country1, country2, days],
    queryFn: () => geopoliticalService.getRelationTimeline(country1, country2, days),
    enabled: !!country1 && !!country2
  })

  if (isLoading) {
    return <div className="timeline-loading">Carregant timeline de relació...</div>
  }

  if (!timelineData || timelineData.error) {
    return (
      <div className="timeline-error">
        <p>No s'ha trobat relació entre {country1} i {country2}</p>
        <p className="error-hint">Intenta extreure relacions des de dades OSINT primer</p>
      </div>
    )
  }

  const relation = timelineData.relation
  const events: TimelineEvent[] = timelineData.events || []
  const treaties: TimelineTreaty[] = timelineData.treaties || []

  // Combinar events i treaties ordenats per data
  const allItems = [
    ...events.map(e => ({ ...e, itemType: 'event' as const })),
    ...treaties.map(t => ({ ...t, itemType: 'treaty' as const, date: t.signing_date }))
  ].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime())

  const filteredItems = selectedView === 'all' 
    ? allItems 
    : selectedView === 'events' 
    ? allItems.filter(i => i.itemType === 'event')
    : allItems.filter(i => i.itemType === 'treaty')

  const getTrendColor = (trend: string) => {
    switch (trend) {
      case 'improving': return '#28a745'
      case 'deteriorating': return '#dc3545'
      default: return '#6c757d'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'improving': return '#28a745'
      case 'deteriorating': return '#dc3545'
      case 'critical': return '#dc3545'
      default: return '#6c757d'
    }
  }

  const getEventTypeIcon = (type: string) => {
    const icons: Record<string, string> = {
      'summit': '🤝',
      'treaty_signing': '📜',
      'sanction': '⚠️',
      'diplomatic_visit': '✈️',
      'trade_agreement': '💼',
      'alliance_change': '🔗',
      'conflict': '⚔️'
    }
    return icons[type] || '📅'
  }

  const getImportanceColor = (importance: string) => {
    switch (importance) {
      case 'high': return '#dc3545'
      case 'medium': return '#ffc107'
      default: return '#6c757d'
    }
  }

  return (
    <div className="relation-timeline">
      {/* Header amb informació de relació */}
      <div className="timeline-header">
        <div className="relation-summary">
          <h3>
            {relation.country1} ↔ {relation.country2}
          </h3>
          <div className="relation-metrics">
            <div className="metric-item">
              <span className="metric-label">Score de Relació:</span>
              <span 
                className="metric-value" 
                style={{ color: relation.score >= 70 ? '#28a745' : relation.score <= 30 ? '#dc3545' : '#6c757d' }}
              >
                {relation.score.toFixed(1)}/100
              </span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Estat:</span>
              <span 
                className="metric-badge"
                style={{ backgroundColor: getStatusColor(relation.status) }}
              >
                {relation.status}
              </span>
            </div>
            <div className="metric-item">
              <span className="metric-label">Tendència:</span>
              <span 
                className="metric-badge"
                style={{ backgroundColor: getTrendColor(relation.trend) }}
              >
                {relation.trend}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Filtres */}
      <div className="timeline-filters">
        <button
          className={`filter-btn ${selectedView === 'all' ? 'active' : ''}`}
          onClick={() => setSelectedView('all')}
        >
          Tot ({allItems.length})
        </button>
        <button
          className={`filter-btn ${selectedView === 'events' ? 'active' : ''}`}
          onClick={() => setSelectedView('events')}
        >
          Esdeveniments ({events.length})
        </button>
        <button
          className={`filter-btn ${selectedView === 'treaties' ? 'active' : ''}`}
          onClick={() => setSelectedView('treaties')}
        >
          Tractats ({treaties.length})
        </button>
      </div>

      {/* Timeline */}
      <div className="timeline-container">
        {filteredItems.length === 0 ? (
          <div className="timeline-empty">
            No hi ha esdeveniments o tractats en aquest període
          </div>
        ) : (
          <div className="timeline">
            {filteredItems.map((item, index) => (
              <div key={item.id || index} className="timeline-item">
                <div className="timeline-marker">
                  <span className="marker-icon">
                    {item.itemType === 'event' 
                      ? getEventTypeIcon((item as TimelineEvent).type)
                      : '📜'}
                  </span>
                </div>
                <div className="timeline-content">
                  <div className="timeline-item-header">
                    <h4>{item.itemType === 'event' ? (item as TimelineEvent).title : (item as TimelineTreaty).name}</h4>
                    <div className="timeline-item-meta">
                      {item.itemType === 'event' && (
                        <span 
                          className="importance-badge"
                          style={{ backgroundColor: getImportanceColor((item as TimelineEvent).importance) }}
                        >
                          {(item as TimelineEvent).importance}
                        </span>
                      )}
                      <span className="timeline-date">
                        {new Date(item.date).toLocaleDateString('ca-ES', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric'
                        })}
                      </span>
                    </div>
                  </div>
                  <div className="timeline-item-body">
                    {item.itemType === 'event' ? (
                      <>
                        <div className="event-type">
                          Tipus: {(item as TimelineEvent).type.replace('_', ' ')}
                        </div>
                        <div className="impact-score">
                          Impacte: {(item as TimelineEvent).impact.toFixed(1)}/100
                        </div>
                      </>
                    ) : (
                      <>
                        <div className="treaty-type">
                          Tipus: {(item as TimelineTreaty).type || 'N/A'}
                        </div>
                        <div className="treaty-status">
                          Estat: {(item as TimelineTreaty).status}
                        </div>
                      </>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
