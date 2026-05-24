import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Brain, RefreshCw, Search } from 'lucide-react'
import { useCase, type ActiveCase } from '../../contexts/CaseContext'
import { useCasesList } from '../../hooks/useCasesList'
import { countPromptLines, toActiveCase } from '../../utils/caseUtils'
import {
  dashboardService,
  geopoliticalService,
  syncService,
} from '../../services/api'
import VisualizationsDashboard from '../Visualizations/VisualizationsDashboard'
import CreateCaseModal from '../Dashboard/CreateCaseModal'
import './IntelligenceCenter.css'

export default function IntelligenceCenter() {
  const queryClient = useQueryClient()
  const { activeCase, setActiveCase } = useCase()
  const [selectedCaseId, setSelectedCaseId] = useState<number | null>(activeCase?.id ?? null)
  const [analyzeMsg, setAnalyzeMsg] = useState<string | null>(null)

  const { data: cases, isLoading: casesLoading } = useCasesList()

  useEffect(() => {
    if (activeCase?.id) {
      setSelectedCaseId((prev) => prev ?? activeCase.id)
    }
  }, [activeCase?.id])

  const selectedCase = cases?.find((c) => c.id === selectedCaseId) ?? null

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['intel-dashboard-metrics', selectedCaseId],
    queryFn: () => dashboardService.getMetrics(30, selectedCaseId),
    enabled: selectedCaseId !== null,
    refetchInterval: 60_000,
  })

  const { data: syncStatus } = useQuery({
    queryKey: ['intel-sync-status', selectedCaseId],
    queryFn: () => syncService.getStatus(selectedCaseId!),
    enabled: selectedCaseId !== null,
  })

  const handleCaseChange = (caseId: number | null) => {
    setSelectedCaseId(caseId)
    if (!caseId) return
    const c = cases?.find((x) => x.id === caseId)
    if (c) {
      setActiveCase(toActiveCase(c))
    }
  }

  const caseDescription =
    selectedCase?.description ?? activeCase?.description ?? null

  const handleCaseCreated = (created: ActiveCase) => {
    setSelectedCaseId(created.id)
    setActiveCase(created)
    queryClient.invalidateQueries({ queryKey: ['cases-list'] })
  }

  const analyzeMutation = useMutation({
    mutationFn: async () => {
      if (!selectedCaseId) throw new Error('Selecciona un cas')
      setAnalyzeMsg('Calculant riscos geopolítics…')
      await geopoliticalService.calculateRisks(selectedCaseId)
      setAnalyzeMsg('Extraient esdeveniments diplomàtics…')
      await geopoliticalService.extractEvents(selectedCaseId)
      setAnalyzeMsg('Sincronitzant dades OSINT…')
      await syncService.forceSync(selectedCaseId)
    },
    onSuccess: () => {
      setAnalyzeMsg('Anàlisi completada — dades actualitzades.')
      queryClient.invalidateQueries({ queryKey: ['geo-events-timeline'] })
      queryClient.invalidateQueries({ queryKey: ['geo-risks-predictions'] })
      queryClient.invalidateQueries({ queryKey: ['geo-risks-pred'] })
      queryClient.invalidateQueries({ queryKey: ['inv-risks'] })
      queryClient.invalidateQueries({ queryKey: ['source-reliability'] })
      queryClient.invalidateQueries({ queryKey: ['networkGraph'] })
      queryClient.invalidateQueries({ queryKey: ['trendAnalysis'] })
      queryClient.invalidateQueries({ queryKey: ['geographicLocations'] })
      queryClient.invalidateQueries({ queryKey: ['intel-dashboard-metrics'] })
      setTimeout(() => setAnalyzeMsg(null), 5000)
    },
    onError: (err: unknown) => {
      const msg =
        err instanceof Error ? err.message : 'Error durant l\'anàlisi. Revisa el backend.'
      setAnalyzeMsg(msg)
    },
  })

  const refreshAll = () => {
    queryClient.invalidateQueries()
    setAnalyzeMsg('Dades refrescades.')
    setTimeout(() => setAnalyzeMsg(null), 2500)
  }

  const totalMentions = metrics?.total_mentions?.total_mentions ?? 0
  const sentimentScore = metrics?.sentiment_score?.sentiment_score ?? 0
  const criticalAlerts = metrics?.critical_alerts?.critical_alerts ?? 0

  return (
    <div className="intelligence-center">
      <header className="intel-center-header">
        <p className="intel-center-kicker">Intelligence Unit</p>
        <h1 className="intel-center-title">Centre d&apos;intel·ligència geopolítica i financera</h1>
        <p className="intel-center-desc">
          Selecciona un cas, executa l&apos;anàlisi i explora mapes, timeline, xarxa d&apos;actors,
          riscos i mètriques OSINT connectades als endpoints del backend.
        </p>

        <div className="intel-center-toolbar">
          <select
            className="intel-case-select"
            value={selectedCaseId ?? ''}
            onChange={(e) =>
              handleCaseChange(e.target.value ? Number(e.target.value) : null)
            }
            disabled={casesLoading}
          >
            <option value="">
              {casesLoading ? 'Carregant casos…' : '— Selecciona un cas —'}
            </option>
            {cases?.map((c) => (
              <option key={c.id} value={c.id}>
                #{c.id} — {c.name}
              </option>
            ))}
          </select>

          <CreateCaseModal onCaseCreated={handleCaseCreated} />

          <button
            type="button"
            className="intel-action-btn primary"
            disabled={!selectedCaseId || analyzeMutation.isPending}
            onClick={() => analyzeMutation.mutate()}
          >
            <Brain size={15} />
            {analyzeMutation.isPending ? 'Analitzant…' : 'Executar anàlisi'}
          </button>

          <button
            type="button"
            className="intel-action-btn"
            disabled={!selectedCaseId}
            onClick={refreshAll}
          >
            <RefreshCw size={15} />
            Refrescar
          </button>

          {selectedCaseId ? (
            <Link to="/osint-collection" className="intel-action-btn">
              <Search size={15} />
              Recollida OSINT
            </Link>
          ) : null}
        </div>

        {analyzeMsg ? <p className="intel-analyze-msg">{analyzeMsg}</p> : null}

        {selectedCaseId ? (
          <>
            <div className="intel-status-bar">
              <span className="intel-status-pill">
                Cas: <strong>{selectedCase?.name ?? `#${selectedCaseId}`}</strong>
              </span>
              {syncStatus?.osint_queries_count != null ? (
                <span className="intel-status-pill">
                  Consultes OSINT: <strong>{syncStatus.osint_queries_count}</strong>
                </span>
              ) : null}
              {syncStatus?.synchronized != null ? (
                <span className="intel-status-pill">
                  Estat: <strong>{syncStatus.synchronized ? 'Sincronitzat' : syncStatus.status ?? 'Pendent'}</strong>
                </span>
              ) : null}
              {syncStatus?.last_sync ? (
                <span className="intel-status-pill">
                  Última sync:{' '}
                  <strong>{new Date(syncStatus.last_sync).toLocaleString('ca-ES')}</strong>
                </span>
              ) : null}
            </div>

            {caseDescription ? (
              <details className="intel-case-briefing">
                <summary>
                  Briefing del cas ({countPromptLines(caseDescription)} línies,{' '}
                  {caseDescription.length.toLocaleString()} caràcters)
                </summary>
                <pre className="intel-case-briefing-text">{caseDescription}</pre>
              </details>
            ) : null}

            {!metricsLoading && metrics ? (
              <div className="intel-kpi-row">
                <div className="intel-kpi">
                  <div className="intel-kpi-value">{totalMentions.toLocaleString()}</div>
                  <div className="intel-kpi-label">Mencions (30d)</div>
                </div>
                <div className="intel-kpi">
                  <div className="intel-kpi-value">{sentimentScore}%</div>
                  <div className="intel-kpi-label">Sentiment</div>
                </div>
                <div className="intel-kpi">
                  <div className="intel-kpi-value">{criticalAlerts}</div>
                  <div className="intel-kpi-label">Alertes</div>
                </div>
              </div>
            ) : null}
          </>
        ) : null}
      </header>

      {!selectedCaseId ? (
        <div className="card intel-empty-panel">
          <h2 className="intel-empty-title">Selecciona o crea un cas</h2>
          <p className="intel-empty-desc">
            Tria un cas al desplegable de dalt per carregar mapes, timeline, xarxa, finances i
            intel. Si encara no en tens cap, crea&apos;n un amb el modal o des del dashboard.
          </p>
          <div className="intel-empty-actions">
            <CreateCaseModal onCaseCreated={handleCaseCreated} />
            <Link to="/" className="btn btn-primary">
              Anar al dashboard
            </Link>
          </div>
        </div>
      ) : (
        <VisualizationsDashboard caseId={selectedCaseId} key={selectedCaseId} />
      )}
    </div>
  )
}
