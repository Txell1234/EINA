/**
 * RetroStep — Godet Retrospective Analysis (Step 1.5)
 * Shows temporal evolution of actor postures from OSINT data,
 * key events, topic dynamics, and MIC-MAC evidence scores.
 */
import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { prospectiveService } from '../../services/api'

interface ActorTrend {
  actor: string
  toward: string
  timeline: Array<{ period: string; avg_posture: number; n_statements: number }>
  overall_delta: number
  trend_direction: string
  total_statements: number
}

interface TopicDynamic {
  topic: string
  n_statements: number
  avg_posture: number
  most_hostile: string | null
  most_cooperative: string | null
  actor_postures: Record<string, number>
}

interface KeyEvent {
  date: string
  period: string
  actor: string
  toward: string
  posture_value: number
  topic: string
  statement: string
  framing: string
  source_url: string
}

interface ActorSummary {
  actor: string
  n_statements: number
  avg_posture: number
  hostile_pct: number
  cooperative_pct: number
  main_topics: string[]
  profile: string
}

interface RetroData {
  has_data: boolean
  message?: string
  total_statements: number
  dated_statements: number
  date_range: { earliest: string | null; latest: string | null }
  actor_trends: ActorTrend[]
  topic_dynamics: TopicDynamic[]
  key_events: KeyEvent[]
  actor_posture_summary: ActorSummary[]
  micmac_evidence: {
    pairs: Array<{ from_topic: string; to_topic: string; n_statements: number; confidence: number }>
    max_count: number
  }
}

function postureColor(v: number): string {
  if (v >= 2) return '#28a745'
  if (v >= 1) return '#85c985'
  if (v === 0) return '#6c757d'
  if (v >= -1) return '#e08040'
  return '#dc3545'
}

function postureLabel(v: number): string {
  if (v >= 2) return 'Molt favorable'
  if (v >= 1) return 'Favorable'
  if (v === 0) return 'Neutral'
  if (v >= -1) return 'Contrari'
  return 'Molt contrari'
}

function trendIcon(dir: string): string {
  if (dir === 'escalating') return '↘ Deteriorant'
  if (dir === 'improving') return '↗ Millorant'
  return '→ Estable'
}

function trendColor(dir: string): string {
  if (dir === 'escalating') return 'var(--color-danger)'
  if (dir === 'improving') return 'var(--color-success)'
  return 'var(--color-gray-500)'
}

interface RetroStepProps {
  projectId: number
  onNext: () => void
  onBack: () => void
}

export default function RetroStep({ projectId, onNext, onBack }: RetroStepProps) {
  const [activeTab, setActiveTab] = useState<'actors' | 'topics' | 'events' | 'evidence'>('actors')

  const { data: retro, isLoading, error } = useQuery<RetroData>({
    queryKey: ['retrospective', projectId],
    queryFn: () => prospectiveService.getRetrospective(projectId),
    enabled: projectId > 0,
  })

  const TABS = [
    { id: 'actors' as const, label: "Evolució d'actors", count: retro?.actor_trends?.length ?? 0 },
    { id: 'topics' as const, label: 'Dinàmica de temes', count: retro?.topic_dynamics?.length ?? 0 },
    { id: 'events' as const, label: 'Esdeveniments clau', count: retro?.key_events?.length ?? 0 },
    { id: 'evidence' as const, label: 'Evidència MIC-MAC', count: retro?.micmac_evidence?.pairs?.length ?? 0 },
  ]

  return (
    <div>
      <div className="mhint" style={{ marginBottom: 'var(--spacing-lg)' }}>
        <div className="mhint-body" style={{ paddingTop: 'var(--spacing-sm)' }}>
          <p>
            La <strong>retrospectiva</strong> és el pas 1.5 de la cadena Godet.
            Respon: <em>&quot;Com hem arribat aquí?&quot;</em> abans de preguntar{' '}
            <em>&quot;On anem?&quot;</em>
          </p>
          <p>
            Usa les dades OSINT del cas per identificar{' '}
            <strong>tendències temporals</strong> de les postures dels actors,{' '}
            <strong>esdeveniments clau</strong> que van canviar la dinàmica, i{' '}
            <strong>evidència empírica</strong> per a les puntuacions de la matriu MIC-MAC.
          </p>
          <p style={{ marginBottom: 0 }}>
            <strong>Ús recomanat:</strong> Revisa la pestanya &quot;Evidència MIC-MAC&quot; mentre
            omplis la matriu del pas 3. Les parelles amb alta confiança estan ben
            documentades per les teves fonts OSINT.
          </p>
        </div>
      </div>

      <div className="prospective-actions" style={{ marginBottom: 'var(--spacing-lg)' }}>
        <button type="button" className="btn" onClick={onBack}>
          ← Enrere
        </button>
        <button type="button" className="btn btn-accent" onClick={onNext}>
          Continuar → Variables (pas 2)
        </button>
      </div>

      {isLoading && (
        <div className="card" style={{ textAlign: 'center', padding: 'var(--spacing-xl)' }}>
          <div className="spinner" style={{ margin: '0 auto 1rem' }} />
          <p style={{ color: 'var(--color-gray-600)', fontSize: 'var(--font-size-sm)' }}>
            Analitzant evolució temporal de les postures dels actors...
          </p>
        </div>
      )}

      {error && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">⚠</div>
            <h3 className="empty-state-title">Error carregant la retrospectiva</h3>
            <p className="empty-state-desc">Comprova que el projecte té un cas associat.</p>
          </div>
        </div>
      )}

      {retro && !retro.has_data && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">◎</div>
            <h3 className="empty-state-title">Sense dades d&apos;extracció</h3>
            <p className="empty-state-desc">
              {retro.message ||
                "Executa primer l'extracció OSINT (pas 0) per tenir dades retrospectives."}
            </p>
            <button type="button" className="btn btn-primary" onClick={onNext}>
              Saltar retrospectiva i continuar
            </button>
          </div>
        </div>
      )}

      {retro?.has_data && (
        <>
          <div
            style={{
              display: 'flex',
              gap: 'var(--spacing-md)',
              flexWrap: 'wrap',
              marginBottom: 'var(--spacing-lg)',
            }}
          >
            {[
              { label: 'Declaracions analitzades', value: retro.total_statements },
              { label: 'Amb data temporal', value: retro.dated_statements },
              { label: 'Des de', value: retro.date_range.earliest ?? '—' },
              { label: 'Fins a', value: retro.date_range.latest ?? '—' },
            ].map(({ label, value }) => (
              <div
                key={label}
                style={{
                  background: 'var(--color-gray-50)',
                  border: '1px solid var(--color-gray-200)',
                  borderRadius: 'var(--radius-md)',
                  padding: 'var(--spacing-md) var(--spacing-lg)',
                  flex: 1,
                  minWidth: 140,
                  textAlign: 'center',
                }}
              >
                <div
                  style={{
                    fontSize: 'var(--font-size-xl)',
                    fontWeight: 700,
                    color: 'var(--color-primary)',
                  }}
                >
                  {value}
                </div>
                <div
                  style={{
                    fontSize: 'var(--font-size-xs)',
                    color: 'var(--color-gray-500)',
                    marginTop: 2,
                  }}
                >
                  {label}
                </div>
              </div>
            ))}
          </div>

          <div className="card">
            <div
              style={{
                display: 'flex',
                gap: 0,
                borderBottom: '1px solid var(--color-gray-200)',
                marginBottom: 'var(--spacing-lg)',
              }}
            >
              {TABS.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setActiveTab(tab.id)}
                  style={{
                    padding: '10px 20px',
                    border: 'none',
                    borderBottom:
                      activeTab === tab.id
                        ? '2px solid var(--color-primary)'
                        : '2px solid transparent',
                    background: 'none',
                    color:
                      activeTab === tab.id ? 'var(--color-primary)' : 'var(--color-gray-500)',
                    fontWeight: activeTab === tab.id ? 600 : 400,
                    fontSize: 'var(--font-size-sm)',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 6,
                  }}
                >
                  {tab.label}
                  {tab.count > 0 && (
                    <span
                      style={{
                        background:
                          activeTab === tab.id ? 'var(--color-primary)' : 'var(--color-gray-200)',
                        color: activeTab === tab.id ? 'white' : 'var(--color-gray-600)',
                        borderRadius: '999px',
                        padding: '0 6px',
                        fontSize: '11px',
                        fontWeight: 600,
                      }}
                    >
                      {tab.count}
                    </span>
                  )}
                </button>
              ))}
            </div>

            {activeTab === 'actors' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-md)' }}>
                {retro.actor_trends.length === 0 && (
                  <p
                    style={{
                      color: 'var(--color-gray-500)',
                      fontSize: 'var(--font-size-sm)',
                      textAlign: 'center',
                      padding: 'var(--spacing-xl)',
                    }}
                  >
                    No hi ha prou dades amb data temporal per construir tendències.
                  </p>
                )}
                {retro.actor_trends.slice(0, 10).map((trend, i) => (
                  <div
                    key={i}
                    style={{
                      border: '1px solid var(--color-gray-200)',
                      borderRadius: 'var(--radius-md)',
                      padding: 'var(--spacing-md) var(--spacing-lg)',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 'var(--spacing-sm)',
                      }}
                    >
                      <div>
                        <strong
                          style={{ color: 'var(--color-primary)', fontSize: 'var(--font-size-sm)' }}
                        >
                          {trend.actor}
                        </strong>
                        <span
                          style={{
                            color: 'var(--color-gray-400)',
                            fontSize: 'var(--font-size-xs)',
                            margin: '0 6px',
                          }}
                        >
                          →
                        </span>
                        <strong style={{ fontSize: 'var(--font-size-sm)' }}>{trend.toward}</strong>
                      </div>
                      <div style={{ display: 'flex', gap: 'var(--spacing-sm)', alignItems: 'center' }}>
                        <span
                          style={{
                            fontSize: 'var(--font-size-xs)',
                            color: trendColor(trend.trend_direction),
                          }}
                        >
                          {trendIcon(trend.trend_direction)}
                        </span>
                        <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-400)' }}>
                          {trend.total_statements} declaracions
                        </span>
                      </div>
                    </div>
                    <div
                      style={{
                        display: 'flex',
                        gap: 4,
                        alignItems: 'flex-end',
                        flexWrap: 'wrap',
                        minHeight: 40,
                      }}
                    >
                      {trend.timeline.map((point, j) => {
                        const h = Math.abs(point.avg_posture) * 16 + 4
                        const col = postureColor(point.avg_posture)
                        return (
                          <div
                            key={j}
                            title={`${point.period}: ${point.avg_posture} (${point.n_statements} decl.)`}
                            style={{
                              display: 'flex',
                              flexDirection: 'column',
                              alignItems: 'center',
                              gap: 2,
                            }}
                          >
                            <div
                              style={{
                                width: 32,
                                height: h,
                                background: col,
                                borderRadius: '3px 3px 0 0',
                                opacity: 0.8,
                              }}
                            />
                            <span
                              style={{
                                fontSize: 9,
                                color: 'var(--color-gray-400)',
                                transform: 'rotate(-45deg)',
                                transformOrigin: 'top left',
                                whiteSpace: 'nowrap',
                                marginTop: 4,
                              }}
                            >
                              {point.period.replace(' ', "'")}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'topics' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                {retro.topic_dynamics.slice(0, 12).map((topic, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 'var(--spacing-md)',
                      padding: 'var(--spacing-sm) var(--spacing-md)',
                      border: '1px solid var(--color-gray-200)',
                      borderRadius: 'var(--radius-sm)',
                    }}
                  >
                    <span
                      style={{
                        flex: 1,
                        fontWeight: 500,
                        fontSize: 'var(--font-size-sm)',
                        color: 'var(--color-gray-800)',
                      }}
                    >
                      {topic.topic}
                    </span>
                    <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-400)' }}>
                      {topic.n_statements} decl.
                    </span>
                    <div
                      style={{
                        width: 12,
                        height: 12,
                        borderRadius: '50%',
                        background: postureColor(topic.avg_posture),
                      }}
                    />
                    <span
                      style={{
                        fontSize: 'var(--font-size-xs)',
                        color: postureColor(topic.avg_posture),
                        fontWeight: 500,
                        minWidth: 80,
                      }}
                    >
                      {postureLabel(Math.round(topic.avg_posture))}
                    </span>
                    {topic.most_hostile && (
                      <span style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-danger)' }}>
                        ↓ {topic.most_hostile}
                      </span>
                    )}
                    {topic.most_cooperative && (
                      <span
                        style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-success)' }}
                      >
                        ↑ {topic.most_cooperative}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'events' && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--spacing-sm)' }}>
                {retro.key_events.length === 0 && (
                  <p
                    style={{
                      color: 'var(--color-gray-500)',
                      fontSize: 'var(--font-size-sm)',
                      textAlign: 'center',
                      padding: 'var(--spacing-xl)',
                    }}
                  >
                    Cap declaració de màxima intensitat (|postura| ≥ 2) amb data disponible.
                  </p>
                )}
                {retro.key_events.slice(0, 20).map((ev, i) => (
                  <div
                    key={i}
                    style={{
                      padding: 'var(--spacing-sm) var(--spacing-md)',
                      border: '1px solid var(--color-gray-200)',
                      borderLeft: `3px solid ${postureColor(ev.posture_value)}`,
                      borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 4,
                      }}
                    >
                      <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-500)' }}>
                        {ev.date}
                        <span style={{ margin: '0 6px', color: 'var(--color-gray-300)' }}>·</span>
                        <strong style={{ color: 'var(--color-primary)' }}>{ev.actor}</strong>
                        <span style={{ color: 'var(--color-gray-400)', margin: '0 4px' }}>→</span>
                        {ev.toward}
                        <span style={{ margin: '0 6px', color: 'var(--color-gray-300)' }}>·</span>
                        {ev.topic}
                      </div>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: '999px',
                          background: `${postureColor(ev.posture_value)}20`,
                          color: postureColor(ev.posture_value),
                          fontSize: 10,
                          fontWeight: 700,
                        }}
                      >
                        {ev.posture_value > 0 ? '+' : ''}
                        {ev.posture_value} {postureLabel(ev.posture_value)}
                      </span>
                    </div>
                    <p
                      style={{
                        fontSize: 'var(--font-size-xs)',
                        color: 'var(--color-gray-700)',
                        margin: 0,
                        lineHeight: 1.5,
                      }}
                    >
                      {ev.statement}
                    </p>
                    {ev.source_url && (
                      <a
                        href={ev.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{
                          fontSize: 10,
                          color: 'var(--color-primary)',
                          display: 'block',
                          marginTop: 4,
                        }}
                      >
                        Font →
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}

            {activeTab === 'evidence' && (
              <div>
                <p
                  style={{
                    fontSize: 'var(--font-size-sm)',
                    color: 'var(--color-gray-600)',
                    marginBottom: 'var(--spacing-md)',
                    lineHeight: 1.6,
                  }}
                >
                  Cada fila és una parella de temes extrets de les teves fonts OSINT.
                  La <strong>confiança</strong> indica quantes declaracions suporten
                  una relació d&apos;influència entre ells.
                  Usa-ho com a guia per a les puntuacions de la matriu MIC-MAC.
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                  {(retro.micmac_evidence.pairs ?? []).slice(0, 30).map((pair, i) => (
                    <div
                      key={i}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 'var(--spacing-md)',
                        padding: '4px 8px',
                        fontSize: 'var(--font-size-xs)',
                        borderBottom: '1px solid var(--color-gray-100)',
                      }}
                    >
                      <span style={{ flex: 1, color: 'var(--color-gray-700)' }}>
                        <strong>{pair.from_topic}</strong>
                        <span style={{ color: 'var(--color-gray-400)', margin: '0 6px' }}>→</span>
                        {pair.to_topic}
                      </span>
                      <span style={{ color: 'var(--color-gray-500)', minWidth: 60 }}>
                        {pair.n_statements} decl.
                      </span>
                      <div
                        style={{
                          width: 80,
                          background: 'var(--color-gray-200)',
                          borderRadius: 3,
                          height: 6,
                        }}
                      >
                        <div
                          style={{
                            width: `${pair.confidence * 100}%`,
                            background:
                              pair.confidence > 0.6
                                ? 'var(--color-success)'
                                : pair.confidence > 0.3
                                  ? '#e6a817'
                                  : 'var(--color-gray-400)',
                            height: '100%',
                            borderRadius: 3,
                          }}
                        />
                      </div>
                      <span
                        style={{
                          minWidth: 36,
                          textAlign: 'right',
                          fontWeight: 600,
                          color:
                            pair.confidence > 0.6
                              ? 'var(--color-success)'
                              : pair.confidence > 0.3
                                ? '#9a7320'
                                : 'var(--color-gray-500)',
                        }}
                      >
                        {Math.round(pair.confidence * 100)}%
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}
