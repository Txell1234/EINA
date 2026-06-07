import { useMemo, useState } from 'react'

import { useMutation, useQuery } from '@tanstack/react-query'

import {

  Bar,

  BarChart,

  CartesianGrid,

  Cell,

  ResponsiveContainer,

  Tooltip,

  XAxis,

  YAxis,

} from 'recharts'

import { intelligenceService } from '../../services/api'

import './AnalyticsLabPanel.css'



type Props = {

  caseId: number

  focusCompany?: string | null

  focusTicker?: string | null

}



const DEFAULT_EXPERIMENTS = ['tornado', 'monte_carlo', 'shap_attribution', 'sobol', 'commodity_matrix']



export function AnalyticsLabPanel({ caseId, focusCompany, focusTicker }: Props) {
  const [includeMarket, setIncludeMarket] = useState(false)
  const [confidenceScope, setConfidenceScope] = useState<'auto' | 'case' | 'entity'>('auto')

  const scopeForQuery =
    confidenceScope === 'auto' && focusCompany ? undefined : confidenceScope === 'auto' ? undefined : confidenceScope

  const { data: latest } = useQuery({
    queryKey: ['analytics-lab', caseId, focusCompany, confidenceScope],
    queryFn: () =>
      intelligenceService.getAnalyticsLabLatest(caseId, {
        focus_company: focusCompany ?? undefined,
        confidence_scope: scopeForQuery,
      }),
    enabled: caseId > 0,
  })

  const runMutation = useMutation({
    mutationFn: () =>
      intelligenceService.runAnalyticsLab(caseId, {
        focus_company: focusCompany ?? undefined,
        ticker: focusTicker ?? undefined,
        confidence_scope: confidenceScope,
        experiments: includeMarket
          ? [...DEFAULT_EXPERIMENTS, 'market_correlations']
          : DEFAULT_EXPERIMENTS,
        monte_carlo_samples: 500,
      }),
  })



  const result = runMutation.data ?? (latest?.found ? latest : null)



  const tornadoChart = useMemo(() => {

    if (!result?.tornado?.length) return []

    return result.tornado.slice(0, 8).map((row) => ({

      name: (row.label ?? row.component ?? '').slice(0, 22),

      swing: row.swing ?? 0,

      low: row.icg_at_low,

      high: row.icg_at_high,

      because: `±20% en ${row.label ?? row.component}: ${result?.confidence_scope === 'entity' ? 'ICE' : 'ICG'} ${row.icg_at_low}% → ${row.icg_at_high}%`,
    }))
  }, [result?.tornado, result?.confidence_scope])

  const mcHistogram = useMemo(() => result?.monte_carlo?.histogram ?? [], [result?.monte_carlo])



  const attributionChart = useMemo(() => {

    if (!result?.shap_attribution?.length) return []

    return result.shap_attribution.slice(0, 6).map((a) => ({

      name: (a.label ?? a.component ?? '').slice(0, 18),

      contribution: a.contribution ?? 0,

      share: a.share_pct,

    }))

  }, [result?.shap_attribution])



  return (

    <section className="analytics-lab card" data-testid="analytics-lab-panel">

      <header className="analytics-lab__header">

        <div>

          <h3>Analytics Lab</h3>

          <p className="analytics-lab__sub">

            Sensibilitat, Monte Carlo i correlacions sobre l&apos;ICG — fora del camí crític del creuament.

            Cada gràfic inclou justificació traçable (regles, no LLM).

          </p>

        </div>

        <div className="analytics-lab__actions">
          {focusCompany ? (
            <label className="analytics-lab__scope">
              Àmbit
              <select
                value={confidenceScope}
                onChange={(e) => setConfidenceScope(e.target.value as 'auto' | 'case' | 'entity')}
                aria-label="Àmbit confiança analytics"
              >
                <option value="auto">Auto (ICE si focus)</option>
                <option value="entity">ICE entitat</option>
                <option value="case">ICG cas</option>
              </select>
            </label>
          ) : null}
          <label className="analytics-lab__check">

            <input

              type="checkbox"

              checked={includeMarket}

              onChange={(e) => setIncludeMarket(e.target.checked)}

            />

            Correlacions ticker{focusTicker ? ` (${focusTicker})` : ''}

          </label>

          <button

            type="button"

            className="btn btn-primary"

            disabled={runMutation.isPending}

            onClick={() => runMutation.mutate()}

          >

            {runMutation.isPending ? 'Executant…' : 'Executar experiments'}

          </button>

        </div>

      </header>



      {runMutation.isError ? (

        <p className="analytics-lab__error">Error executant analytics lab.</p>

      ) : null}



      {!result ? (

        <p className="analytics-lab__empty">

          Encara no hi ha resultats. Executa intel·ligència al cas i després prem «Executar experiments».

        </p>

      ) : (

        <div className="analytics-lab__results">

          {result.cached ? <span className="analytics-lab__cached">Resultat en cache</span> : null}

          {result.base_icg != null ? (
            <p className="analytics-lab__base">
              {result.confidence_scope === 'entity' ? 'ICE' : 'ICG'} base: <strong>{result.base_icg}%</strong>
              {result.case_icg_baseline != null && result.confidence_scope === 'entity' ? (
                <> · ICG cas {result.case_icg_baseline}%</>
              ) : null}
              {result.entity_icg_delta != null && result.confidence_scope === 'entity' ? (
                <> · Δ {result.entity_icg_delta >= 0 ? '+' : ''}{result.entity_icg_delta} pp</>
              ) : null}
              {result.gma != null ? <> · GMA {result.gma}%</> : null}
            </p>
          ) : null}



          {tornadoChart.length > 0 ? (

            <div className="analytics-lab__block">

              <h4>Tornado — sensibilitat ±20%</h4>

              <p className="analytics-lab__justify">

                Mostra quin component mou més l&apos;ICG quan varia un 20%. Driver principal = barra més llarga.

              </p>

              <div className="analytics-lab__chart">

                <ResponsiveContainer width="100%" height={260}>

                  <BarChart data={tornadoChart} layout="vertical" margin={{ left: 8, right: 16 }}>

                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis type="number" unit=" pts" />

                    <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 11 }} />

                    <Tooltip

                      formatter={(v: number) => [`${v} pts`, 'Swing ICG']}

                      labelFormatter={(_, payload) =>

                        payload?.[0]?.payload?.because ?? ''

                      }

                    />

                    <Bar dataKey="swing" fill="#2563eb" radius={[0, 4, 4, 0]} />

                  </BarChart>

                </ResponsiveContainer>

              </div>

            </div>

          ) : null}



          {result.monte_carlo?.n ? (

            <div className="analytics-lab__block">

              <h4>Monte Carlo ({result.monte_carlo.n} mostres)</h4>

              <p className="analytics-lab__justify">

                Distribució de l&apos;ICG sota soroll gaussià als components. Àrea ampla = incertesa analítica.

              </p>

              <p className="analytics-lab__stats">

                Mitjana {result.monte_carlo.mean}% · P5 {result.monte_carlo.p5}% · P50{' '}

                {result.monte_carlo.p50}% · P95 {result.monte_carlo.p95}%

              </p>

              {mcHistogram.length > 0 ? (

                <div className="analytics-lab__chart">

                  <ResponsiveContainer width="100%" height={220}>

                    <BarChart data={mcHistogram} margin={{ bottom: 8 }}>

                      <CartesianGrid strokeDasharray="3 3" />

                      <XAxis dataKey="bin" tick={{ fontSize: 10 }} interval={1} angle={-25} textAnchor="end" height={50} />

                      <YAxis allowDecimals={false} />

                      <Tooltip formatter={(v: number) => [`${v} mostres`, 'Freqüència']} />

                      <Bar dataKey="count" fill="#7c3aed" radius={[3, 3, 0, 0]} />

                    </BarChart>

                  </ResponsiveContainer>

                </div>

              ) : null}

            </div>

          ) : null}



          {attributionChart.length > 0 ? (

            <div className="analytics-lab__block">

              <h4>Atribució lineal (SHAP-like)</h4>

              <p className="analytics-lab__justify">

                Contribució exacta de cada component a la mitjana ponderada de l&apos;ICG (weight × value).

              </p>

              <div className="analytics-lab__chart">

                <ResponsiveContainer width="100%" height={220}>

                  <BarChart data={attributionChart} margin={{ bottom: 8 }}>

                    <CartesianGrid strokeDasharray="3 3" />

                    <XAxis dataKey="name" tick={{ fontSize: 10 }} />

                    <YAxis unit=" pts" />

                    <Tooltip

                      formatter={(v: number, _n, p) => [

                        `${v} pts (${(p?.payload as { share?: number })?.share ?? '—'}%)`,

                        'Contribució',

                      ]}

                    />

                    <Bar dataKey="contribution" radius={[4, 4, 0, 0]}>

                      {attributionChart.map((entry, i) => (

                        <Cell key={entry.name} fill={entry.contribution >= 0 ? '#059669' : '#dc2626'} />

                      ))}

                    </Bar>

                  </BarChart>

                </ResponsiveContainer>

              </div>

            </div>

          ) : null}



          {(result.driver_interactions?.length ?? 0) > 0 ? (

            <div className="analytics-lab__block">

              <h4>Interaccions de drivers (regles)</h4>

              <ul className="analytics-lab__interactions">

                {result.driver_interactions!.map((ix: { pair: string; because: string; score: number }) => (

                  <li key={ix.pair}>

                    <strong>{ix.pair}</strong> (score {ix.score}): {ix.because}

                  </li>

                ))}

              </ul>

            </div>

          ) : null}



          {(result.sobol_first_order?.length ?? 0) > 0 ? (

            <div className="analytics-lab__block">

              <h4>Sobol 1r ordre</h4>

              <ul>

                {result.sobol_first_order!.slice(0, 5).map((s) => (

                  <li key={s.component}>

                    {s.label ?? s.component}: {s.sobol_first_order}

                  </li>

                ))}

              </ul>

            </div>

          ) : null}



          {result.commodity_matrix ? (

            <div className="analytics-lab__block">

              <h4>Matriu correlacions matèries / mercat</h4>

              {result.commodity_matrix.available ? (

                <>

                  <p className="analytics-lab__justify">{result.commodity_matrix.interpretation}</p>

                  <div className="analytics-lab__matrix-wrap">

                    <table className="analytics-lab__matrix">

                      <thead>

                        <tr>

                          <th>Actiu</th>

                          {(result.commodity_matrix.labels ?? []).map((l: string) => (

                            <th key={l}>{l}</th>

                          ))}

                        </tr>

                      </thead>

                      <tbody>

                        {(result.commodity_matrix.matrix ?? []).map((row: Record<string, unknown>) => (

                          <tr key={String(row.asset)}>

                            <td>{String(row.asset)}</td>

                            {(result.commodity_matrix.labels ?? []).map((l: string) => {

                              const v = row[l] as number | null | undefined

                              const cls =

                                v != null && v > 0.55

                                  ? 'analytics-lab__corr-high'

                                  : v != null && v < -0.35

                                    ? 'analytics-lab__corr-neg'

                                    : ''

                              return (

                                <td key={l} className={cls}>

                                  {v != null ? v.toFixed(2) : '—'}

                                </td>

                              )

                            })}

                          </tr>

                        ))}

                      </tbody>

                    </table>

                  </div>

                </>

              ) : (

                <p className="analytics-lab__warn">{result.commodity_matrix.reason}</p>

              )}

            </div>

          ) : null}



          {result.market_correlations ? (

            <div className="analytics-lab__block">

              <h4>Correlacions ticker focus</h4>

              {result.market_correlations.available ? (

                <ul>

                  {(result.market_correlations.correlations ?? []).map((c) => (

                    <li key={c.symbol}>

                      {c.benchmark}: r={c.correlation} (n={c.n})

                    </li>

                  ))}

                </ul>

              ) : (

                <p className="analytics-lab__warn">{result.market_correlations.reason}</p>

              )}

            </div>

          ) : null}

        </div>

      )}

    </section>

  )

}


