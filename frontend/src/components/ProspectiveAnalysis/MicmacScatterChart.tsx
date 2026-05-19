import type { MicmacPreviewResult } from '../../utils/micmac'

const COLORS: Record<string, string> = {
  Motriu: '#1e3a5f',
  'Clau/Conflicte': '#dc3545',
  Resultant: '#28a745',
  Excluyent: '#6c757d',
  Autònom: '#6c757d',
}

interface MicmacScatterChartProps {
  result: MicmacPreviewResult | Record<string, unknown>
  title?: string
  live?: boolean
}

export default function MicmacScatterChart({
  result,
  title = 'Gràfic motricitat / dependència — Sectors Godet',
  live = false,
}: MicmacScatterChartProps) {
  const sectors = (result.sectors as Array<{
    index: number
    code: string
    sector: string
    motricitat: number
    dependencia: number
  }>) ?? []

  if (sectors.length === 0) return null

  const vbFromKey = result.vb_index as number | undefined
  const vrFromKey = result.vr_index as number | undefined
  const vbFromObj = (result.variable_blanc as { index: number } | undefined)?.index
  const vrFromObj = (result.variable_risc as { index: number } | undefined)?.index
  const vbIdx = vbFromKey ?? vbFromObj ?? -1
  const vrIdx = vrFromKey ?? vrFromObj ?? -1

  const allMot = sectors.map((s) => s.motricitat)
  const allDep = sectors.map((s) => s.dependencia)
  const maxMot = Math.max(...allMot, 1)
  const maxDep = Math.max(...allDep, 1)
  const avgMot = allMot.reduce((a, b) => a + b, 0) / allMot.length
  const avgDep = allDep.reduce((a, b) => a + b, 0) / allDep.length

  const W = 480
  const H = 380
  const PAD = 52
  const toX = (dep: number) => PAD + (dep / maxDep) * (W - PAD * 2)
  const toY = (mot: number) => H - PAD - (mot / maxMot) * (H - PAD * 2)
  const avgX = toX(avgDep)
  const avgY = toY(avgMot)

  return (
    <div className="micmac-chart-wrap">
      <p className="micmac-chart-title">
        {title}
        {live && (
          <span className="micmac-live-badge" style={{ marginLeft: 8, fontSize: '0.75rem', color: '#28a745' }}>
            ● Vista prèvia en viu
          </span>
        )}
      </p>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        style={{
          width: '100%',
          maxWidth: W,
          border: '1px solid var(--color-gray-200)',
          borderRadius: 'var(--radius-md)',
          background: '#fafbfc',
        }}
        aria-label="Gràfic MIC-MAC"
      >
        <rect x={PAD} y={PAD} width={avgX - PAD} height={avgY - PAD} fill="rgba(30,58,95,0.07)" />
        <rect x={avgX} y={PAD} width={W - PAD - avgX} height={avgY - PAD} fill="rgba(220,53,69,0.08)" />
        <rect x={avgX} y={avgY} width={W - PAD - avgX} height={H - PAD - avgY} fill="rgba(40,167,69,0.07)" />
        <rect x={PAD} y={avgY} width={avgX - PAD} height={H - PAD - avgY} fill="rgba(108,117,125,0.05)" />

        <text x={PAD + 6} y={PAD + 16} fontSize="10" fill="#1e3a5f" fontWeight="600">Motriu</text>
        <text x={avgX + 4} y={PAD + 16} fontSize="10" fill="#dc3545" fontWeight="600">Clau/Conflicte</text>
        <text x={avgX + 4} y={H - PAD - 6} fontSize="10" fill="#28a745" fontWeight="600">Resultant</text>
        <text x={PAD + 6} y={H - PAD - 6} fontSize="10" fill="#6c757d" fontWeight="600">Autònom</text>

        <line x1={avgX} y1={PAD} x2={avgX} y2={H - PAD} stroke="#bbb" strokeWidth="1" strokeDasharray="4 3" />
        <line x1={PAD} y1={avgY} x2={W - PAD} y2={avgY} stroke="#bbb" strokeWidth="1" strokeDasharray="4 3" />

        <line x1={PAD} y1={PAD} x2={PAD} y2={H - PAD} stroke="#999" strokeWidth="1.5" />
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#999" strokeWidth="1.5" />
        <text x={W / 2} y={H - 8} fontSize="11" fill="#6c757d" textAnchor="middle">Dependència →</text>
        <text
          x={14}
          y={H / 2}
          fontSize="11"
          fill="#6c757d"
          textAnchor="middle"
          transform={`rotate(-90,14,${H / 2})`}
        >
          Motricitat →
        </text>

        {sectors.map((s) => {
          const cx = toX(s.dependencia)
          const cy = toY(s.motricitat)
          const col = COLORS[s.sector] ?? '#6c757d'
          const isVB = s.index === vbIdx
          const isVR = s.index === vrIdx && s.index !== vbIdx
          const r = isVB || isVR ? 11 : 8
          return (
            <g key={s.index}>
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill={col}
                opacity={0.85}
                stroke={isVB ? '#d4a843' : isVR ? '#ff4444' : 'white'}
                strokeWidth={isVB || isVR ? 2.5 : 1.5}
              />
              <text x={cx + r + 3} y={cy + 4} fontSize="11" fontWeight="600" fill={col}>
                {s.code}
                {isVB ? ' VB' : isVR ? ' VR' : ''}
              </text>
            </g>
          )
        })}
      </svg>

      <div className="micmac-sectors-legend">
        {([
          { l: 'Motriu', c: '#1e3a5f', d: 'Alta mot, baixa dep' },
          { l: 'Clau/Conflicte', c: '#dc3545', d: 'Alta mot, alta dep' },
          { l: 'Resultant', c: '#28a745', d: 'Baixa mot, alta dep' },
          { l: 'Autònom', c: '#6c757d', d: 'Baixa mot, baixa dep' },
        ] as const).map(({ l, c, d }) => (
          <span key={l} className="micmac-legend-item">
            <span className="micmac-legend-dot" style={{ background: c }} />
            <strong>{l}</strong> — {d}
          </span>
        ))}
      </div>
    </div>
  )
}
