/**
 * EventTimeline — Cronologia d'esdeveniments diplomàtics i geopolítics
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { geopoliticalService } from '../../services/api'

interface TimelineEvent {
  id: number
  event_type: string
  title: string
  description?: string
  event_date: string
  countries: string[]
  importance: string
  impact_score: number
  sentiment_score?: number
  source_references?: string[]
  location?: string
}

interface RiskPrediction {
  country: string
  risk_3_months?: number
  risk_6_months?: number
  risk_12_months?: number
}

const EVENT_COLORS: Record<string, string> = {
  diplomatic: '#1e3a5f',
  conflict: '#dc3545',
  sanction: '#fd7e14',
  trade: '#28a745',
  cyberattack: '#6f42c1',
  treaty: '#20c997',
  election: '#0dcaf0',
  default: '#6c757d',
}

const EVENT_ICONS: Record<string, string> = {
  diplomatic: '🤝',
  conflict: '⚔️',
  sanction: '🚫',
  trade: '📦',
  cyberattack: '💻',
  treaty: '📄',
  election: '🗳️',
  default: '📋',
}

function importanceWeight(imp: string): number {
  return imp === 'critical' ? 4 : imp === 'high' ? 3 : imp === 'medium' ? 2 : 1
}

interface EventTimelineProps {
  caseId?: number
}

export default function EventTimeline({ caseId }: EventTimelineProps) {
  const [filterType, setFilterType] = useState<string>('all')
  const [filterDays, setFilterDays] = useState(90)
  const [showPredictions, setShowPredictions] = useState(false)

  const { data: eventsData, isLoading } = useQuery({
    queryKey: ['geo-events-timeline', caseId, filterType, filterDays],
    queryFn: () =>
      geopoliticalService.getEvents(
        caseId,
        filterType === 'all' ? undefined : filterType,
        filterDays,
      ),
    refetchInterval: 300_000,
  })

  const { data: risksData } = useQuery({
    queryKey: ['geo-risks-predictions', caseId],
    queryFn: () => geopoliticalService.getRisks(caseId),
    enabled: showPredictions,
  })

  const events: TimelineEvent[] = eventsData?.events ?? []
  const risks: RiskPrediction[] = Array.isArray(risksData) ? risksData : []

  const EVENT_TYPES = ['all', 'diplomatic', 'conflict', 'sanction', 'trade', 'cyberattack', 'treaty']

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
      <div
        style={{
          display: 'flex',
          gap: 'var(--spacing-md)',
          flexWrap: 'wrap',
          alignItems: 'center',
        }}
      >
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {EVENT_TYPES.map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setFilterType(t)}
              style={{
                padding: '4px 12px',
                borderRadius: '999px',
                cursor: 'pointer',
                border: `1px solid ${EVENT_COLORS[t] ?? EVENT_COLORS.default}`,
                background: filterType === t ? (EVENT_COLORS[t] ?? EVENT_COLORS.default) : 'transparent',
                color: filterType === t ? 'white' : (EVENT_COLORS[t] ?? EVENT_COLORS.default),
                fontSize: 'var(--font-size-xs)',
                fontWeight: 500,
                transition: 'all .15s',
                textTransform: 'capitalize',
              }}
            >
              {EVENT_ICONS[t] ?? '◈'} {t === 'all' ? 'Tots' : t}
            </button>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-600)' }}>Últims</span>
          {[30, 90, 180, 365].map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setFilterDays(d)}
              style={{
                padding: '3px 8px',
                borderRadius: 4,
                cursor: 'pointer',
                border: '1px solid var(--color-gray-300)',
                background: filterDays === d ? 'var(--color-primary)' : 'transparent',
                color: filterDays === d ? 'white' : 'var(--color-gray-600)',
                fontSize: 'var(--font-size-xs)',
              }}
            >
              {d}d
            </button>
          ))}
        </div>
        <label
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontSize: 'var(--font-size-xs)',
            cursor: 'pointer',
          }}
        >
          <input
            type="checkbox"
            checked={showPredictions}
            onChange={(e) => setShowPredictions(e.target.checked)}
          />
          Mostrar prediccions de risc
        </label>
      </div>

      {isLoading && (
        <div style={{ textAlign: 'center', padding: 'var(--spacing-xl)' }}>
          <div className="spinner" style={{ margin: '0 auto' }} />
        </div>
      )}

      {showPredictions && risks.length > 0 && (
        <div
          className="card"
          style={{
            background: 'rgba(30,58,95,0.03)',
            border: '1px solid rgba(30,58,95,0.15)',
          }}
        >
          <p
            style={{
              fontSize: 'var(--font-size-sm)',
              fontWeight: 600,
              color: 'var(--color-primary)',
              marginBottom: 'var(--spacing-sm)',
            }}
          >
            Prediccions de risc geopolític
          </p>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--spacing-sm)' }}>
            {risks.slice(0, 6).map((r, i) => (
              <div
                key={i}
                style={{
                  border: '1px solid var(--color-gray-200)',
                  borderRadius: 'var(--radius-sm)',
                  padding: 'var(--spacing-sm)',
                  minWidth: 140,
                  flex: 1,
                }}
              >
                <p
                  style={{
                    fontWeight: 600,
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-primary)',
                    margin: '0 0 6px',
                  }}
                >
                  {r.country}
                </p>
                {[
                  { label: '3 mesos', val: r.risk_3_months },
                  { label: '6 mesos', val: r.risk_6_months },
                  { label: '12 mesos', val: r.risk_12_months },
                ].map(({ label, val }) => {
                  if (val == null) return null
                  const col =
                    val > 70
                      ? 'var(--color-danger)'
                      : val > 40
                        ? 'var(--color-warning)'
                        : 'var(--color-success)'
                  return (
                    <div
                      key={label}
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        fontSize: 11,
                        marginBottom: 3,
                      }}
                    >
                      <span style={{ color: 'var(--color-gray-500)' }}>{label}</span>
                      <span style={{ fontWeight: 700, color: col }}>{Math.round(val)}/100</span>
                    </div>
                  )
                })}
              </div>
            ))}
          </div>
        </div>
      )}

      {events.length === 0 && !isLoading && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">📅</div>
            <h3 className="empty-state-title">Sense esdeveniments</h3>
            <p className="empty-state-desc">
              No hi ha esdeveniments diplomàtics registrats per als filtres seleccionats.
            </p>
          </div>
        </div>
      )}

      <div style={{ position: 'relative' }}>
        {events.length > 0 && (
          <div
            style={{
              position: 'absolute',
              left: 20,
              top: 0,
              bottom: 0,
              width: 2,
              background: 'var(--color-gray-200)',
              zIndex: 0,
            }}
          />
        )}

        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
          {[...events]
            .sort((a, b) => new Date(b.event_date).getTime() - new Date(a.event_date).getTime())
            .map((ev, i) => {
              const color = EVENT_COLORS[ev.event_type] ?? EVENT_COLORS.default
              const icon = EVENT_ICONS[ev.event_type] ?? EVENT_ICONS.default
              const weight = importanceWeight(ev.importance)
              const sentimentColor =
                (ev.sentiment_score ?? 0) > 0.2
                  ? 'var(--color-success)'
                  : (ev.sentiment_score ?? 0) < -0.2
                    ? 'var(--color-danger)'
                    : 'var(--color-gray-500)'

              return (
                <div
                  key={ev.id ?? i}
                  style={{
                    display: 'flex',
                    gap: 'var(--spacing-md)',
                    position: 'relative',
                    zIndex: 1,
                  }}
                >
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: '50%',
                      background: color,
                      color: 'white',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontSize: weight >= 3 ? 16 : 12,
                      flexShrink: 0,
                      border: '2px solid white',
                      boxShadow: weight >= 3 ? `0 0 0 3px ${color}40` : 'none',
                      zIndex: 2,
                    }}
                  >
                    {icon}
                  </div>

                  <div
                    style={{
                      flex: 1,
                      border: `1px solid ${color}30`,
                      borderLeft: `3px solid ${color}`,
                      borderRadius: 'var(--radius-sm)',
                      padding: 'var(--spacing-sm) var(--spacing-md)',
                      background: 'var(--color-white)',
                      marginBottom: 4,
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'flex-start',
                        flexWrap: 'wrap',
                        gap: 4,
                        marginBottom: 4,
                      }}
                    >
                      <span
                        style={{
                          fontWeight: 600,
                          fontSize: 'var(--font-size-sm)',
                          color: 'var(--color-gray-800)',
                          flex: 1,
                        }}
                      >
                        {ev.title}
                      </span>
                      <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                        <span style={{ fontSize: 10, color: 'var(--color-gray-400)' }}>
                          {new Date(ev.event_date).toLocaleDateString('ca-ES')}
                        </span>
                        {ev.importance === 'critical' || ev.importance === 'high' ? (
                          <span
                            style={{
                              fontSize: 10,
                              padding: '1px 6px',
                              borderRadius: '999px',
                              background: `${color}18`,
                              color,
                              fontWeight: 700,
                            }}
                          >
                            {ev.importance}
                          </span>
                        ) : null}
                      </div>
                    </div>

                    {ev.description && (
                      <p
                        style={{
                          fontSize: 'var(--font-size-xs)',
                          color: 'var(--color-gray-600)',
                          margin: '0 0 6px',
                          lineHeight: 1.5,
                        }}
                      >
                        {ev.description.slice(0, 200)}
                        {ev.description.length > 200 ? '...' : ''}
                      </p>
                    )}

                    <div
                      style={{
                        display: 'flex',
                        gap: 8,
                        flexWrap: 'wrap',
                        alignItems: 'center',
                      }}
                    >
                      {ev.countries?.slice(0, 4).map((c) => (
                        <span
                          key={c}
                          style={{
                            fontSize: 10,
                            padding: '1px 6px',
                            borderRadius: '999px',
                            background: 'rgba(30,58,95,0.08)',
                            color: 'var(--color-primary)',
                            fontWeight: 500,
                          }}
                        >
                          {c}
                        </span>
                      ))}
                      {ev.sentiment_score !== undefined && (
                        <span
                          style={{
                            fontSize: 10,
                            color: sentimentColor,
                            fontWeight: 600,
                            marginLeft: 'auto',
                          }}
                        >
                          Sentiment: {ev.sentiment_score > 0 ? '+' : ''}
                          {ev.sentiment_score?.toFixed(2)}
                        </span>
                      )}
                      {ev.source_references && ev.source_references.length > 0 && (
                        <a
                          href={ev.source_references[0]}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{ fontSize: 10, color: 'var(--color-primary)' }}
                        >
                          Font →
                        </a>
                      )}
                    </div>
                  </div>
                </div>
              )
            })}
        </div>
      </div>
    </div>
  )
}
