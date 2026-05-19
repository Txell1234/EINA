interface MactorSociogramProps {
  actorCodes: string[]
  convergences: number[][]
  postures?: number[][]
  mobilisation?: number[]
  title?: string
}

function computeSignedEdges(
  actorCount: number,
  objectiveCount: number,
  convergences: number[][],
  postures?: number[][],
): Array<{ i: number; j: number; net: number; alliance: number; conflict: number }> {
  const edges: Array<{ i: number; j: number; net: number; alliance: number; conflict: number }> = []

  for (let i = 0; i < actorCount; i++) {
    for (let j = i + 1; j < actorCount; j++) {
      let alliance = convergences[i]?.[j] ?? 0
      let conflict = 0

      if (postures && postures.length === actorCount) {
        alliance = 0
        conflict = 0
        for (let k = 0; k < objectiveCount; k++) {
          const pi = postures[i]?.[k] ?? 0
          const pj = postures[j]?.[k] ?? 0
          if (pi === 0 || pj === 0) continue
          if ((pi > 0) === (pj > 0)) alliance++
          else conflict++
        }
      }

      const net = alliance - conflict
      if (net !== 0 || alliance > 0 || conflict > 0) {
        edges.push({ i, j, net, alliance, conflict })
      }
    }
  }

  return edges
}

export default function MactorSociogram({
  actorCodes,
  convergences,
  postures,
  mobilisation,
  title = 'Sociograma MACTOR — aliança (+) / conflicte (−)',
}: MactorSociogramProps) {
  const n = actorCodes.length
  if (n < 2) return null

  const objectiveCount = postures?.[0]?.length ?? 0
  const edges = computeSignedEdges(n, objectiveCount, convergences, postures)
  const maxNet = Math.max(...edges.map((e) => Math.abs(e.net)), 1)
  const maxMob = Math.max(...(mobilisation ?? [1]), 1)

  const W = 420
  const H = 420
  const cx = W / 2
  const cy = H / 2
  const radius = Math.min(W, H) * 0.34

  const nodePos = actorCodes.map((_, i) => {
    const angle = (2 * Math.PI * i) / n - Math.PI / 2
    return {
      x: cx + radius * Math.cos(angle),
      y: cy + radius * Math.sin(angle),
    }
  })

  const edgePath = (i: number, j: number, bend: number) => {
    const a = nodePos[i]
    const b = nodePos[j]
    const mx = (a.x + b.x) / 2
    const my = (a.y + b.y) / 2
    const dx = b.x - a.x
    const dy = b.y - a.y
    const len = Math.hypot(dx, dy) || 1
    const nx = -dy / len
    const ny = dx / len
    const cpx = mx + nx * bend
    const cpy = my + ny * bend
    return `M ${a.x} ${a.y} Q ${cpx} ${cpy} ${b.x} ${b.y}`
  }

  return (
    <div className="mactor-sociogram-wrap">
      <p className="mactor-sociogram-title">{title}</p>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="mactor-sociogram-svg"
        aria-label="Sociograma MACTOR"
      >
        {edges.map(({ i, j, net, alliance, conflict }) => {
          const isAlliance = net >= 0
          const strength = Math.abs(net) / maxNet
          const strokeWidth = 1.5 + strength * 5
          const color = isAlliance ? '#28a745' : '#dc3545'
          const bend = isAlliance ? 18 : -18
          const midT = 0.5
          const a = nodePos[i]
          const b = nodePos[j]
          const labelX = a.x + (b.x - a.x) * midT
          const labelY = a.y + (b.y - a.y) * midT - 6

          return (
            <g key={`${i}-${j}`}>
              <path
                d={edgePath(i, j, bend)}
                fill="none"
                stroke={color}
                strokeWidth={strokeWidth}
                opacity={0.75}
                markerEnd={`url(#mactor-arrow-${isAlliance ? 'plus' : 'minus'})`}
              />
              <text
                x={labelX}
                y={labelY}
                fontSize="10"
                fill={color}
                textAnchor="middle"
                fontWeight="700"
              >
                {isAlliance ? '+' : '−'}
                {Math.abs(net)}
              </text>
              <title>
                {actorCodes[i]} ↔ {actorCodes[j]}: aliança {alliance}, conflicte {conflict}
              </title>
            </g>
          )
        })}

        <defs>
          <marker
            id="mactor-arrow-plus"
            markerWidth="6"
            markerHeight="6"
            refX="5"
            refY="3"
            orient="auto"
          >
            <path d="M0,0 L6,3 L0,6 Z" fill="#28a745" />
          </marker>
          <marker
            id="mactor-arrow-minus"
            markerWidth="6"
            markerHeight="6"
            refX="5"
            refY="3"
            orient="auto"
          >
            <path d="M0,0 L6,3 L0,6 Z" fill="#dc3545" />
          </marker>
        </defs>

        {actorCodes.map((code, i) => {
          const mob = mobilisation?.[i] ?? 1
          const r = 14 + (mob / maxMob) * 12
          const { x, y } = nodePos[i]
          return (
            <g key={code}>
              <circle
                cx={x}
                cy={y}
                r={r}
                fill="var(--color-primary)"
                opacity={0.9}
                stroke="white"
                strokeWidth={2}
              />
              <text
                x={x}
                y={y + 4}
                fontSize="11"
                fontWeight="700"
                fill="white"
                textAnchor="middle"
              >
                {code}
              </text>
            </g>
          )
        })}
      </svg>
      <p className="mactor-sociogram-legend">
        Verd (+) = aliança · Vermell (−) = conflicte · Mida del node ∝ mobilització
      </p>
    </div>
  )
}
