/**
 * NetworkGraph — Force-directed actor relationship graph (SVG, no deps)
 */
import { useMemo, useState } from 'react'

interface Node {
  id: string
  label: string
  type: 'person' | 'organization' | 'state' | 'ngo' | 'domain' | 'ip' | 'email' | 'location' | string
  size?: number
  x?: number
  y?: number
  vx?: number
  vy?: number
}

interface Edge {
  source: string
  target: string
  weight?: number
  type?: 'financial' | 'political' | 'family' | 'subsidiary' | 'alliance' | 'conflict' | string
}

interface NetworkGraphProps {
  nodes: Node[]
  edges: Edge[]
  title?: string
  width?: number
  height?: number
}

const NODE_COLORS: Record<string, string> = {
  person: '#ff6b35',
  organization: '#1e3a5f',
  state: '#20c997',
  ngo: '#6f42c1',
  domain: '#0dcaf0',
  ip: '#fd7e14',
  email: '#6c757d',
  location: '#ffd93d',
  default: '#adb5bd',
}

const EDGE_COLORS: Record<string, string> = {
  financial: '#28a745',
  political: '#1e3a5f',
  family: '#fd7e14',
  subsidiary: '#20c997',
  alliance: '#0dcaf0',
  conflict: '#dc3545',
  default: '#adb5bd',
}

function nodeColor(type: string): string {
  return NODE_COLORS[type] ?? NODE_COLORS.default
}

function edgeColor(type?: string): string {
  return EDGE_COLORS[type ?? 'default'] ?? EDGE_COLORS.default
}

function runForceLayout(nodes: Node[], edges: Edge[], W: number, H: number, iterations = 80): Node[] {
  if (nodes.length === 0) return nodes

  const n = nodes.length
  const positioned = nodes.map((node, i) => ({
    ...node,
    x: W / 2 + W * 0.4 * Math.cos((2 * Math.PI * i) / n),
    y: H / 2 + H * 0.4 * Math.sin((2 * Math.PI * i) / n),
    vx: 0,
    vy: 0,
  }))

  const nodeMap = new Map(positioned.map((node) => [node.id, node]))

  for (let iter = 0; iter < iterations; iter++) {
    const cooling = 1 - iter / iterations

    for (let i = 0; i < positioned.length; i++) {
      for (let j = i + 1; j < positioned.length; j++) {
        const a = positioned[i]
        const b = positioned[j]
        const dx = (b.x ?? 0) - (a.x ?? 0)
        const dy = (b.y ?? 0) - (a.y ?? 0)
        const dist = Math.sqrt(dx * dx + dy * dy) || 1
        const force = (3000 / (dist * dist)) * cooling
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        a.vx! -= fx
        a.vy! -= fy
        b.vx! += fx
        b.vy! += fy
      }
    }

    for (const edge of edges) {
      const src = nodeMap.get(edge.source)
      const tgt = nodeMap.get(edge.target)
      if (!src || !tgt) continue
      const dx = (tgt.x ?? 0) - (src.x ?? 0)
      const dy = (tgt.y ?? 0) - (src.y ?? 0)
      const dist = Math.sqrt(dx * dx + dy * dy) || 1
      const desiredDist = 120
      const force = ((dist - desiredDist) / dist) * 0.05 * cooling
      const fx = dx * force
      const fy = dy * force
      src.vx! += fx
      src.vy! += fy
      tgt.vx! -= fx
      tgt.vy! -= fy
    }

    for (const node of positioned) {
      node.vx! += (W / 2 - (node.x ?? 0)) * 0.005 * cooling
      node.vy! += (H / 2 - (node.y ?? 0)) * 0.005 * cooling
    }

    for (const node of positioned) {
      node.x = Math.max(30, Math.min(W - 30, (node.x ?? 0) + node.vx!))
      node.y = Math.max(30, Math.min(H - 30, (node.y ?? 0) + node.vy!))
      node.vx! *= 0.8
      node.vy! *= 0.8
    }
  }

  return positioned
}

export default function NetworkGraph({
  nodes,
  edges,
  title = 'Xarxa de relacions',
  width = 800,
  height = 500,
}: NetworkGraphProps) {
  const [selected, setSelected] = useState<string | null>(null)
  const [filterType, setFilterType] = useState<string>('all')

  const filteredNodes = useMemo(
    () => (filterType === 'all' ? nodes : nodes.filter((n) => n.type === filterType)),
    [nodes, filterType],
  )

  const filteredEdges = useMemo(() => {
    const nodeIds = new Set(filteredNodes.map((n) => n.id))
    return edges.filter((e) => nodeIds.has(e.source) && nodeIds.has(e.target))
  }, [filteredNodes, edges])

  const positioned = useMemo(
    () => runForceLayout(filteredNodes, filteredEdges, width, height),
    [filteredNodes, filteredEdges, width, height],
  )

  const nodeMap = useMemo(() => new Map(positioned.map((n) => [n.id, n])), [positioned])

  const connectionCount = useMemo(() => {
    const counts: Record<string, number> = {}
    filteredEdges.forEach((e) => {
      counts[e.source] = (counts[e.source] ?? 0) + 1
      counts[e.target] = (counts[e.target] ?? 0) + 1
    })
    return counts
  }, [filteredEdges])

  const selectedEdges = selected
    ? filteredEdges.filter((e) => e.source === selected || e.target === selected)
    : []

  const nodeTypes = [...new Set(nodes.map((n) => n.type))]

  if (nodes.length === 0) {
    return (
      <div className="card">
        <div className="empty-state">
          <div className="empty-state-icon">◎</div>
          <h3 className="empty-state-title">Xarxa buida</h3>
          <p className="empty-state-desc">No hi ha nodes ni connexions per a aquest cas.</p>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 'var(--spacing-sm)',
          flexWrap: 'wrap',
          gap: 'var(--spacing-sm)',
        }}
      >
        <h3
          style={{
            margin: 0,
            fontSize: 'var(--font-size-base)',
            fontWeight: 600,
            color: 'var(--color-primary)',
          }}
        >
          {title}
        </h3>
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {['all', ...nodeTypes].map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setFilterType(t)}
              style={{
                padding: '3px 10px',
                borderRadius: '999px',
                cursor: 'pointer',
                border: `1px solid ${nodeColor(t)}`,
                background: filterType === t ? nodeColor(t) : 'transparent',
                color: filterType === t ? 'white' : nodeColor(t),
                fontSize: 'var(--font-size-xs)',
                transition: 'all .15s',
                fontWeight: 500,
                textTransform: 'capitalize',
              }}
            >
              {t === 'all' ? 'Tots' : t}
            </button>
          ))}
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          gap: 'var(--spacing-md)',
          marginBottom: 'var(--spacing-sm)',
          flexWrap: 'wrap',
        }}
      >
        {[
          { label: 'Nodes', val: filteredNodes.length },
          { label: 'Connexions', val: filteredEdges.length },
          { label: 'Seleccionat', val: selected ? (nodeMap.get(selected)?.label ?? '—') : '—' },
          { label: 'Connexions selec.', val: selected ? selectedEdges.length : '—' },
        ].map(({ label, val }) => (
          <div
            key={label}
            style={{
              background: 'var(--color-gray-50)',
              border: '1px solid var(--color-gray-200)',
              borderRadius: 'var(--radius-sm)',
              padding: '4px 12px',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-500)' }}>{label}</div>
            <div style={{ fontWeight: 700, color: 'var(--color-primary)', fontSize: 'var(--font-size-sm)' }}>
              {val}
            </div>
          </div>
        ))}
      </div>

      <div
        style={{
          border: '1px solid var(--color-gray-200)',
          borderRadius: 'var(--radius-md)',
          overflow: 'hidden',
          background: '#fafbfc',
        }}
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: '100%', maxHeight: height, display: 'block', cursor: 'default' }}
          onClick={() => setSelected(null)}
        >
          {filteredEdges.map((edge, i) => {
            const src = nodeMap.get(edge.source)
            const tgt = nodeMap.get(edge.target)
            if (!src || !tgt) return null
            const isHighlighted = selected && (edge.source === selected || edge.target === selected)
            const col = edgeColor(edge.type)
            const w = edge.weight ? Math.min(edge.weight * 1.5, 4) : 1.5
            return (
              <line
                key={`e-${i}`}
                x1={src.x}
                y1={src.y}
                x2={tgt.x}
                y2={tgt.y}
                stroke={isHighlighted ? col : '#ccc'}
                strokeWidth={isHighlighted ? w + 1 : w}
                opacity={isHighlighted ? 1 : selected ? 0.15 : 0.6}
                strokeDasharray={edge.type === 'conflict' ? '5 3' : undefined}
              />
            )
          })}

          {positioned.map((node) => {
            const connections = connectionCount[node.id] ?? 0
            const r = 10 + Math.min(connections * 2.5, 18) + (node.size ?? 0) * 3
            const col = nodeColor(node.type)
            const isSelected = node.id === selected
            const isConnected = selected
              ? filteredEdges.some(
                  (e) =>
                    (e.source === selected && e.target === node.id) ||
                    (e.target === selected && e.source === node.id),
                )
              : true
            return (
              <g
                key={node.id}
                style={{ cursor: 'pointer' }}
                onClick={(e) => {
                  e.stopPropagation()
                  setSelected(isSelected ? null : node.id)
                }}
              >
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={r}
                  fill={col}
                  opacity={selected && !isSelected && !isConnected ? 0.2 : 0.9}
                  stroke={isSelected ? 'white' : col}
                  strokeWidth={isSelected ? 3 : 1.5}
                  style={{ filter: isSelected ? `drop-shadow(0 0 6px ${col})` : undefined }}
                />
                <text
                  x={node.x}
                  y={(node.y ?? 0) + r + 12}
                  textAnchor="middle"
                  fontSize={10}
                  fontWeight={isSelected ? 700 : 400}
                  fill={selected && !isSelected && !isConnected ? '#ccc' : '#333'}
                >
                  {node.label.length > 16 ? `${node.label.slice(0, 14)}…` : node.label}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      <div
        style={{
          display: 'flex',
          gap: 'var(--spacing-sm)',
          flexWrap: 'wrap',
          marginTop: 'var(--spacing-sm)',
        }}
      >
        {Object.entries(EDGE_COLORS)
          .filter(([k]) => k !== 'default')
          .map(([type, col]) => (
            <span key={type} style={{ fontSize: 10, display: 'flex', alignItems: 'center', gap: 4 }}>
              <span
                style={{
                  width: 20,
                  height: 2,
                  background: col,
                  display: 'inline-block',
                  borderRadius: 1,
                }}
              />
              <span style={{ color: 'var(--color-gray-600)', textTransform: 'capitalize' }}>{type}</span>
            </span>
          ))}
      </div>

      {selected && nodeMap.get(selected) && (
        <div
          style={{
            marginTop: 'var(--spacing-md)',
            padding: 'var(--spacing-md)',
            border: `2px solid ${nodeColor(nodeMap.get(selected)!.type)}`,
            borderRadius: 'var(--radius-md)',
            background: 'var(--color-gray-50)',
          }}
        >
          <p
            style={{
              fontWeight: 600,
              fontSize: 'var(--font-size-sm)',
              color: 'var(--color-primary)',
              margin: '0 0 8px',
            }}
          >
            {nodeMap.get(selected)?.label}
            <span
              style={{
                fontWeight: 400,
                color: 'var(--color-gray-500)',
                marginLeft: 8,
                textTransform: 'capitalize',
              }}
            >
              ({nodeMap.get(selected)?.type})
            </span>
          </p>
          <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-gray-600)', margin: '0 0 6px' }}>
            {selectedEdges.length} connexions directes
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
            {selectedEdges.map((e, i) => {
              const otherId = e.source === selected ? e.target : e.source
              const other = nodeMap.get(otherId)
              return (
                <div
                  key={i}
                  style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 'var(--font-size-xs)' }}
                >
                  <span
                    style={{
                      width: 30,
                      height: 2,
                      background: edgeColor(e.type),
                      display: 'inline-block',
                      borderRadius: 1,
                    }}
                  />
                  <span style={{ color: nodeColor(other?.type ?? ''), fontWeight: 500 }}>
                    {other?.label ?? otherId}
                  </span>
                  <span style={{ color: 'var(--color-gray-400)', textTransform: 'capitalize' }}>
                    ({e.type ?? 'connexió'})
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}
