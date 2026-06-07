import { useEffect } from 'react'
import { useI18n } from '../../contexts/I18nContext'
import { prospectiveService } from '../../services/api'
import CcaSuggestionsPanel from '../Intelligence/CcaSuggestionsPanel'
import MethodologyHint from './MethodologyHint'
import MorphExplorer from './MorphExplorer'
import {
  type IncompatRow,
  type MorphRow,
  isPairIncompatible,
  liveMorphTotal,
  morphConfigsFromText,
} from './morphUtils'
import './MorphBox.css'

export type MorphSpaceStats = {
  valid_combinations: number
  filtered_out?: number
  total_combinations?: number
  scenario_configs?: Array<{
    scenario_type: string
    config?: string
    possibility?: string
    probability?: string
  }>
}

type MorphBoxProps = {
  projectId: number
  inquiryId?: number | null
  morphRows: MorphRow[]
  setMorphRows: React.Dispatch<React.SetStateAction<MorphRow[]>>
  incompatibilities: IncompatRow[]
  setIncompatibilities: React.Dispatch<React.SetStateAction<IncompatRow[]>>
  morphSpaceStats: MorphSpaceStats | null
  setMorphSpaceStats: React.Dispatch<React.SetStateAction<MorphSpaceStats | null>>
  onBack: () => void
  onSave: () => void
  saving?: boolean
}

export default function MorphBox({
  projectId,
  inquiryId,
  morphRows,
  setMorphRows,
  incompatibilities,
  setIncompatibilities,
  morphSpaceStats,
  setMorphSpaceStats,
  onBack,
  onSave,
  saving = false,
}: MorphBoxProps) {
  const { t } = useI18n()
  const total = liveMorphTotal(morphRows)

  const toggleCompatibility = (
    compA: string,
    cfgA: string,
    compB: string,
    cfgB: string,
    compatible: boolean,
  ) => {
    setIncompatibilities((prev) => {
      if (compatible) {
        return prev.filter(
          (inc) =>
            !(
              (inc.component_a === compA &&
                inc.config_a === cfgA &&
                inc.component_b === compB &&
                inc.config_b === cfgB) ||
              (inc.component_a === compB &&
                inc.config_a === cfgB &&
                inc.component_b === compA &&
                inc.config_b === cfgA)
            ),
        )
      }
      return [...prev, { component_a: compA, config_a: cfgA, component_b: compB, config_b: cfgB }]
    })
  }

  useEffect(() => {
    if (!projectId || incompatibilities.length === 0) return
    const timer = window.setTimeout(() => {
      void (async () => {
        try {
          const rules = incompatibilities.map((inc, i) => ({
            id: `live-${i}`,
            component_a: inc.component_a,
            config_a: inc.config_a,
            component_b: inc.component_b,
            config_b: inc.config_b,
            consistency: -1,
            selected: true,
          }))
          const preview = await prospectiveService.previewCcaSuggestions(projectId, rules)
          const after = preview.after as MorphSpaceStats | undefined
          if (after?.valid_combinations != null) {
            setMorphSpaceStats(after)
          }
        } catch {
          /* live preview optional */
        }
      })()
    }, 450)
    return () => window.clearTimeout(timer)
  }, [incompatibilities, projectId, inquiryId, setMorphSpaceStats])

  useEffect(() => {
    if (!projectId) return
    const timer = window.setTimeout(() => {
      void prospectiveService.getMorphSpace(projectId).then((stats) => {
        if (stats?.valid_combinations != null) {
          setMorphSpaceStats(stats as MorphSpaceStats)
        }
      }).catch(() => undefined)
    }, 600)
    return () => window.clearTimeout(timer)
  }, [morphRows, projectId, setMorphSpaceStats])

  return (
    <div className="morph-box" data-testid="morph-box">
      <h2 style={{ color: 'var(--color-primary)' }}>{t('morph.box.title')}</h2>
      <MethodologyHint title={t('morph.box.methodologyTitle')} defaultOpen={false}>
        <p>{t('morph.box.methodologyBody')}</p>
      </MethodologyHint>

      <CcaSuggestionsPanel
        projectId={projectId}
        inquiryId={inquiryId}
        onApplied={async (result) => {
          const stats = result.morph_stats as MorphSpaceStats
          if (stats) setMorphSpaceStats(stats)
          const rows =
            (result.incompatibilities as IncompatRow[] | undefined) ??
            (await prospectiveService.getCompatibilities(projectId))
          setIncompatibilities(rows)
        }}
      />

      {morphRows.map((m, idx) => (
        <div key={idx} className="card morph-box__component">
          <div className="prospective-field">
            <label>{t('morph.box.code')}</label>
            <input
              value={m.id}
              onChange={(e) =>
                setMorphRows((x) => x.map((row, i) => (i === idx ? { ...row, id: e.target.value } : row)))
              }
            />
          </div>
          <div className="prospective-field">
            <label>{t('morph.box.componentName')}</label>
            <input
              value={m.name}
              onChange={(e) =>
                setMorphRows((x) => x.map((row, i) => (i === idx ? { ...row, name: e.target.value } : row)))
              }
            />
          </div>
          <div className="prospective-field">
            <label>{t('morph.box.configs')}</label>
            <textarea
              rows={4}
              value={m.configsText}
              onChange={(e) =>
                setMorphRows((x) =>
                  x.map((row, i) => (i === idx ? { ...row, configsText: e.target.value } : row)),
                )
              }
            />
          </div>
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => setMorphRows((x) => x.filter((_, i) => i !== idx))}
          >
            {t('morph.box.remove')}
          </button>
        </div>
      ))}

      <button
        type="button"
        className="btn btn-primary"
        onClick={() =>
          setMorphRows((x) => [...x, { id: `C${x.length + 1}`, name: '', configsText: 'Estat A\nEstat B' }])
        }
      >
        {t('morph.box.addComponent')}
      </button>

      <MorphExplorer
        morphRows={morphRows}
        incompatibilities={incompatibilities}
        serverValid={morphSpaceStats?.valid_combinations ?? null}
      />

      <div className="card morph-box__matrix">
        <h3>{t('morph.box.matrixTitle')}</h3>
        <p className="morph-box__stats">
          {t('morph.box.totalCombinations')}: <strong>{total}</strong>
          {morphSpaceStats && (
            <>
              {' · '}
              {t('morph.box.validCombinations')}: <strong>{morphSpaceStats.valid_combinations}</strong>
              {morphSpaceStats.filtered_out != null && morphSpaceStats.filtered_out > 0 && (
                <span> ({morphSpaceStats.filtered_out} {t('morph.box.excluded')})</span>
              )}
            </>
          )}
        </p>
        {morphRows.flatMap((rowA, i) =>
          morphRows.slice(i + 1).map((rowB, jOff) => {
            const j = i + 1 + jOff
            const cfgsA = morphConfigsFromText(rowA.configsText)
            const cfgsB = morphConfigsFromText(rowB.configsText)
            if (cfgsA.length === 0 || cfgsB.length === 0) return null
            return (
              <div key={`${rowA.id}-${rowB.id}`} className="morph-box__pair">
                <h4>
                  {rowA.id || `C${i + 1}`} × {rowB.id || `C${j + 1}`}
                </h4>
                <div className="morph-box__table-wrap">
                  <table className="prospective-matrix morph-compat-table">
                    <thead>
                      <tr>
                        <th />
                        {cfgsB.map((cb) => (
                          <th key={cb}>{cb}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {cfgsA.map((ca) => (
                        <tr key={ca}>
                          <th>{ca}</th>
                          {cfgsB.map((cb) => {
                            const compatible = !isPairIncompatible(
                              incompatibilities,
                              rowA.id,
                              ca,
                              rowB.id,
                              cb,
                            )
                            return (
                              <td key={cb}>
                                <input
                                  type="checkbox"
                                  checked={compatible}
                                  onChange={(e) =>
                                    toggleCompatibility(rowA.id, ca, rowB.id, cb, e.target.checked)
                                  }
                                />
                              </td>
                            )
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          }),
        )}
        {morphSpaceStats?.scenario_configs && (
          <div className="morph-box__scenarios">
            <h4>{t('morph.box.scenarioConfigs')}</h4>
            <ul>
              {morphSpaceStats.scenario_configs.map((s) => (
                <li key={s.scenario_type}>
                  <strong>{s.scenario_type}</strong>: {s.config || '—'}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="prospective-actions">
        <button type="button" className="btn" onClick={onBack}>
          {t('morph.box.back')}
        </button>
        <button type="button" className="btn btn-accent" disabled={saving} onClick={onSave}>
          {t('morph.box.save')}
        </button>
      </div>
    </div>
  )
}
