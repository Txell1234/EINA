import { useMemo } from 'react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

interface Node {
  id: string
  label: string
  type: string
  size?: number
}

interface Edge {
  source: string
  target: string
  weight?: number
  type?: string
}

interface NetworkGraphProps {
  nodes: Node[]
  edges: Edge[]
  title?: string
}

export default function NetworkGraph({ nodes, edges, title = "Network Graph" }: NetworkGraphProps) {
  // Calculate node connections for visualization
  const nodeConnections = useMemo(() => {
    const connections: { [key: string]: number } = {}
    edges.forEach(edge => {
      connections[edge.source] = (connections[edge.source] || 0) + 1
      connections[edge.target] = (connections[edge.target] || 0) + 1
    })
    return connections
  }, [edges])

  // Prepare data for chart (simplified network view)
  const chartData = useMemo(() => {
    return nodes.map(node => ({
      name: node.label,
      connections: nodeConnections[node.id] || 0,
      type: node.type
    }))
  }, [nodes, nodeConnections])

  return (
    <div className="network-graph-container">
      <h3>{title}</h3>
      <div className="network-stats">
        <div className="stat-item">
          <span className="stat-label">Nodes:</span>
          <span className="stat-value">{nodes.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Connections:</span>
          <span className="stat-value">{edges.length}</span>
        </div>
      </div>
      
      {/* Network visualization using SVG */}
      <div className="network-svg-container">
        <svg width="100%" height="400" viewBox="0 0 800 400">
          {/* Draw edges */}
          {edges.map((edge, idx) => {
            const sourceNode = nodes.find(n => n.id === edge.source)
            const targetNode = nodes.find(n => n.id === edge.target)
            if (!sourceNode || !targetNode) return null
            
            // Simple circular layout
            const sourceAngle = (nodes.indexOf(sourceNode) / nodes.length) * 2 * Math.PI
            const targetAngle = (nodes.indexOf(targetNode) / nodes.length) * 2 * Math.PI
            const sourceX = 400 + 150 * Math.cos(sourceAngle)
            const sourceY = 200 + 150 * Math.sin(sourceAngle)
            const targetX = 400 + 150 * Math.cos(targetAngle)
            const targetY = 200 + 150 * Math.sin(targetAngle)
            
            return (
              <line
                key={`edge-${idx}`}
                x1={sourceX}
                y1={sourceY}
                x2={targetX}
                y2={targetY}
                stroke="#888"
                strokeWidth={edge.weight || 1}
                opacity={0.6}
              />
            )
          })}
          
          {/* Draw nodes */}
          {nodes.map((node, idx) => {
            const angle = (idx / nodes.length) * 2 * Math.PI
            const x = 400 + 150 * Math.cos(angle)
            const y = 200 + 150 * Math.sin(angle)
            const connections = nodeConnections[node.id] || 0
            const radius = 10 + Math.min(connections * 2, 20)
            
            return (
              <g key={node.id}>
                <circle
                  cx={x}
                  cy={y}
                  r={radius}
                  fill={getNodeColor(node.type)}
                  stroke="#333"
                  strokeWidth={2}
                />
                <text
                  x={x}
                  y={y + radius + 12}
                  textAnchor="middle"
                  fontSize="10"
                  fill="#333"
                >
                  {node.label.length > 15 ? node.label.substring(0, 15) + '...' : node.label}
                </text>
              </g>
            )
          })}
        </svg>
      </div>
      
      {/* Connection chart */}
      <div className="connection-chart">
        <h4>Node Connections</h4>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" angle={-45} textAnchor="end" height={80} />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line type="monotone" dataKey="connections" stroke="#8884d8" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

function getNodeColor(type: string): string {
  const colors: { [key: string]: string } = {
    'person': '#ff6b35',
    'organization': '#4ecdc4',
    'domain': '#95e1d3',
    'ip': '#f38181',
    'email': '#a8e6cf',
    'location': '#ffd93d',
    'default': '#888'
  }
  return colors[type] || colors['default']
}









