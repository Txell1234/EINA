import { useMemo, useState } from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts'

interface Relationship {
  from: string
  to: string
  type: string
  strength: number
}

interface RelationshipMapProps {
  relationships: Relationship[]
  title?: string
}

export default function RelationshipMap({ relationships, title = "Relationship Map" }: RelationshipMapProps) {
  const [selectedType, setSelectedType] = useState<string | null>(null)

  const filteredRelationships = useMemo(() => {
    if (!selectedType) return relationships
    return relationships.filter(r => r.type === selectedType)
  }, [relationships, selectedType])

  const relationshipTypes = useMemo(() => {
    const types: { [key: string]: number } = {}
    relationships.forEach(r => {
      types[r.type] = (types[r.type] || 0) + 1
    })
    return Object.entries(types).map(([type, count]) => ({ type, count }))
  }, [relationships])

  const entityConnections = useMemo(() => {
    const connections: { [key: string]: number } = {}
    relationships.forEach(r => {
      connections[r.from] = (connections[r.from] || 0) + 1
      connections[r.to] = (connections[r.to] || 0) + 1
    })
    return Object.entries(connections)
      .map(([entity, count]) => ({ entity, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10)
  }, [relationships])

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884d8', '#82ca9d', '#ffc658']

  return (
    <div className="relationship-map-container">
      <h3>{title}</h3>
      
      <div className="relationship-filters">
        <button 
          className={selectedType === null ? 'active' : ''}
          onClick={() => setSelectedType(null)}
        >
          All Types
        </button>
        {relationshipTypes.map(({ type }) => (
          <button
            key={type}
            className={selectedType === type ? 'active' : ''}
            onClick={() => setSelectedType(type)}
          >
            {type}
          </button>
        ))}
      </div>

      <div className="relationship-stats">
        <div className="stat-item">
          <span className="stat-label">Total Relationships:</span>
          <span className="stat-value">{relationships.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Types:</span>
          <span className="stat-value">{relationshipTypes.length}</span>
        </div>
        <div className="stat-item">
          <span className="stat-label">Filtered:</span>
          <span className="stat-value">{filteredRelationships.length}</span>
        </div>
      </div>

      <div className="relationship-visualization">
        <div className="relationship-chart">
          <h4>Relationship Types Distribution</h4>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={relationshipTypes}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ type, percent }) => `${type}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="count"
              >
                {relationshipTypes.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="top-entities">
          <h4>Most Connected Entities</h4>
          <div className="entity-list">
            {entityConnections.map(({ entity, count }, idx) => (
              <div key={entity} className="entity-item">
                <span className="entity-rank">#{idx + 1}</span>
                <span className="entity-name">{entity}</span>
                <span className="entity-count">{count} connections</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="relationship-list">
        <h4>Relationships {selectedType && `(${selectedType})`}</h4>
        <div className="relationships-table">
          <table>
            <thead>
              <tr>
                <th>From</th>
                <th>To</th>
                <th>Type</th>
                <th>Strength</th>
              </tr>
            </thead>
            <tbody>
              {filteredRelationships.slice(0, 20).map((rel, idx) => (
                <tr key={idx}>
                  <td>{rel.from}</td>
                  <td>{rel.to}</td>
                  <td><span className="type-badge">{rel.type}</span></td>
                  <td>
                    <div className="strength-bar">
                      <div 
                        className="strength-fill" 
                        style={{ width: `${(rel.strength / 10) * 100}%` }}
                      />
                      <span>{rel.strength}/10</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}









