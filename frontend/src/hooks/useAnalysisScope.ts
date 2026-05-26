// @refresh reset
import { useCallback, useEffect, useState } from 'react'
import {
  AnalysisScope,
  DEFAULT_SCOPE,
  PeriodPreset,
  scopeToTimeRange,
} from '../types/analysisScope'

const storageKey = (caseId: number | null) => `eina-analysis-scope-${caseId ?? 'global'}`

function loadStored(caseId: number | null): AnalysisScope {
  try {
    const raw = sessionStorage.getItem(storageKey(caseId))
    if (raw) return { ...DEFAULT_SCOPE, ...JSON.parse(raw) }
  } catch {
    /* ignore */
  }
  return { ...DEFAULT_SCOPE }
}

export function useAnalysisScope(caseId: number | null) {
  const [scope, setScopeState] = useState<AnalysisScope>(() => loadStored(caseId))

  useEffect(() => {
    setScopeState(loadStored(caseId))
  }, [caseId])

  const setScope = useCallback(
    (patch: Partial<AnalysisScope> | ((prev: AnalysisScope) => AnalysisScope)) => {
      setScopeState((prev) => {
        const next = typeof patch === 'function' ? patch(prev) : { ...prev, ...patch }
        try {
          sessionStorage.setItem(storageKey(caseId), JSON.stringify(next))
        } catch {
          /* ignore */
        }
        return next
      })
    },
    [caseId],
  )

  const setPeriodPreset = useCallback(
    (preset: PeriodPreset) => {
      if (preset === 'custom') {
        setScope({ periodPreset: preset })
        return
      }
      const days = parseInt(preset, 10)
      const tr = scopeToTimeRange({ ...DEFAULT_SCOPE, periodPreset: preset, periodDays: days })
      setScope({
        periodPreset: preset,
        periodDays: days,
        startDate: tr?.start ?? '',
        endDate: tr?.end ?? '',
      })
    },
    [setScope],
  )

  const timeRange = scopeToTimeRange(scope)

  return { scope, setScope, setPeriodPreset, timeRange }
}
