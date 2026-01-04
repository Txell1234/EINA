import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { casesService } from '../../services/api'
import './KPIConfigurationModal.css'

interface KPIConfigurationModalProps {
  caseId: number
  isOpen: boolean
  onClose: () => void
  onSave: (selectedKpiIds: number[]) => void
}

interface KPI {
  id: number
  name: string
  metric_type?: string
  description?: string
  measurement_unit?: string
  kpi_type: string
}

interface CaseKPI {
  id: number
  kpi_id: number
  is_tracked: boolean
  kpi?: KPI
}

export default function KPIConfigurationModal({
  caseId,
  isOpen,
  onClose,
  onSave
}: KPIConfigurationModalProps) {
  const [selectedKpiIds, setSelectedKpiIds] = useState<number[]>([])
  const queryClient = useQueryClient()

  // Get case KPIs
  const { data: caseData } = useQuery({
    queryKey: ['case', caseId],
    queryFn: () => casesService.get(caseId),
    enabled: isOpen && caseId > 0
  })

  // Get available KPIs (this would need a new endpoint)
  // For now, we'll use the case KPIs
  const { data: caseKpis, isLoading } = useQuery({
    queryKey: ['case-kpis', caseId],
    queryFn: async () => {
      // This would call a new endpoint to get case KPIs
      // For now, return empty array
      return [] as CaseKPI[]
    },
    enabled: isOpen && caseId > 0
  })

  // Configure KPIs mutation
  const configureMutation = useMutation({
    mutationFn: async (kpiIds: number[]) => {
      const response = await fetch(`/api/visualizations/trends/${caseId}/configure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ kpi_ids: kpiIds })
      })
      if (!response.ok) throw new Error('Failed to configure KPIs')
      return response.json()
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['trendAnalysis', caseId] })
      onSave(selectedKpiIds)
      onClose()
    }
  })

  useEffect(() => {
    if (caseKpis) {
      const tracked = caseKpis
        .filter((ck: CaseKPI) => ck.is_tracked)
        .map((ck: CaseKPI) => ck.kpi_id)
      setSelectedKpiIds(tracked)
    }
  }, [caseKpis])

  const handleToggleKpi = (kpiId: number) => {
    setSelectedKpiIds(prev =>
      prev.includes(kpiId)
        ? prev.filter(id => id !== kpiId)
        : [...prev, kpiId]
    )
  }

  const handleSave = () => {
    configureMutation.mutate(selectedKpiIds)
  }

  if (!isOpen) return null

  // Group KPIs by metric type
  const kpisByType: Record<string, CaseKPI[]> = {}
  if (caseKpis) {
    caseKpis.forEach((ck: CaseKPI) => {
      const type = ck.kpi?.metric_type || 'other'
      if (!kpisByType[type]) kpisByType[type] = []
      kpisByType[type].push(ck)
    })
  }

  return (
    <div className="kpi-config-modal-overlay" onClick={onClose}>
      <div className="kpi-config-modal" onClick={(e) => e.stopPropagation()}>
        <div className="kpi-config-modal-header">
          <h2>Configurar KPIs per a l'Anàlisi</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>

        <div className="kpi-config-modal-content">
          {isLoading ? (
            <p>Carregant KPIs...</p>
          ) : caseKpis && caseKpis.length > 0 ? (
            <div className="kpi-groups">
              {Object.entries(kpisByType).map(([type, kpis]) => (
                <div key={type} className="kpi-group">
                  <h3 className="kpi-group-title">
                    {type === 'sentiment' && '📊 Sentiment'}
                    {type === 'volume' && '📈 Volum'}
                    {type === 'count' && '🔢 Comptadors'}
                    {type === 'trend' && '📉 Tendències'}
                    {type === 'engagement' && '💬 Engagament'}
                    {type === 'ratio' && '📊 Ratios'}
                    {type === 'other' && '📋 Altres'}
                    {!['sentiment', 'volume', 'count', 'trend', 'engagement', 'ratio'].includes(type) && `📋 ${type}`}
                  </h3>
                  <div className="kpi-list">
                    {kpis.map((ck: CaseKPI) => (
                      <label key={ck.id} className="kpi-item">
                        <input
                          type="checkbox"
                          checked={selectedKpiIds.includes(ck.kpi_id)}
                          onChange={() => handleToggleKpi(ck.kpi_id)}
                        />
                        <div className="kpi-info">
                          <span className="kpi-name">{ck.kpi?.name || `KPI ${ck.kpi_id}`}</span>
                          {ck.kpi?.description && (
                            <span className="kpi-description">{ck.kpi.description}</span>
                          )}
                          {ck.kpi?.measurement_unit && (
                            <span className="kpi-unit">({ck.kpi.measurement_unit})</span>
                          )}
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="no-kpis">
              <p>No hi ha KPIs disponibles per a aquest cas.</p>
              <p className="hint">Els KPIs es suggereixen quan crees un cas nou.</p>
            </div>
          )}
        </div>

        <div className="kpi-config-modal-footer">
          <button className="btn-cancel" onClick={onClose}>
            Cancel·lar
          </button>
          <button
            className="btn-save"
            onClick={handleSave}
            disabled={configureMutation.isPending || selectedKpiIds.length === 0}
          >
            {configureMutation.isPending ? 'Desant...' : `Desar (${selectedKpiIds.length} seleccionats)`}
          </button>
        </div>
      </div>
    </div>
  )
}



