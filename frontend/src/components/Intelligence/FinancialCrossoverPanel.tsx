import { useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { casesService } from '../../services/api'
import './FinancialCrossoverPanel.css'

type FinancialCrossoverPanelProps = {
  caseId: number
}

type EvidenceRow = {
  kind?: string
  label?: string
  value?: string | number | null
  origin?: string
  because?: string
}

type ReasoningRow = {
  id?: string
  conclusion?: string
  because?: string
  formula?: string
  sources?: Array<{ origin?: string; field?: string; value?: unknown; label?: string; excerpt?: string }>
}

type AlignmentRow = {
  summary?: string
  because?: string
  sources?: ReasoningRow['sources']
}

type NumberExplanation = {
  value?: number
  because?: string
  formula?: string
  sources?: ReasoningRow['sources']
}

const SAMPLE_HINT = `Enganxa text d'InvestWatch/PRAAMS amb puntuacions 1-7, percentatges o recomanacions BUY/HOLD/SELL tal com apareixen a l'informe.`

const ORIGIN_LABELS: Record<string, string> = {
  informe_extern: 'Informe extern',
  eina_prospective: 'EINA · Escenaris',
  eina_investments: 'EINA · Inversions',
  eina_smic: 'EINA · SMIC',
  eina_policy_industry: 'EINA · Policy×Indústria',
}

export default function FinancialCrossoverPanel({ caseId }: FinancialCrossoverPanelProps) {
  const queryClient = useQueryClient()
  const fileRef = useRef<HTMLInputElement>(null)
  const [source, setSource] = useState('praams')
  const [title, setTitle] = useState('')
  const [text, setText] = useState('')
  const [externalWeight, setExternalWeight] = useState(0.35)
  const [crossoverResult, setCrossoverResult] = useState<Record<string, unknown> | null>(null)

  const { data: reports = [], isLoading } = useQuery({
    queryKey: ['financial-reports', caseId],
    queryFn: () => casesService.listFinancialReports(caseId),
  })

  const uploadMutation = useMutation({
    mutationFn: () =>
      casesService.uploadFinancialReport(caseId, {
        text,
        source,
        title,
        enrich_llm: false,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['financial-reports', caseId] })
      setText('')
    },
  })

  const fileMutation = useMutation({
    mutationFn: (file: File) =>
      casesService.uploadFinancialReportFile(caseId, file, { source, title, enrich_llm: false }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['financial-reports', caseId] })
    },
  })

  const crossoverMutation = useMutation({
    mutationFn: (payload: { report_id?: number; text?: string }) =>
      casesService.runFinancialCrossover(caseId, {
        ...payload,
        source,
        external_weight: externalWeight,
        enrich_llm: false,
      }),
    onSuccess: (data) => setCrossoverResult(data),
  })

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) fileMutation.mutate(file)
    e.target.value = ''
  }

  const crossover = crossoverResult?.crossover as Record<string, unknown> | undefined
  const numberExplanations = crossover?.final_numbers_explanations as Record<string, NumberExplanation> | undefined
  const externalEvidence = (crossover?.external_evidence as EvidenceRow[]) ?? []
  const einaEvidence = (crossover?.eina_evidence as EvidenceRow[]) ?? []
  const reasoning = (crossover?.reasoning as ReasoningRow[]) ?? []
  const alignments = (crossover?.alignments as AlignmentRow[]) ?? []
  const divergences = (crossover?.divergences as AlignmentRow[]) ?? []

  return (
    <section className="financial-crossover-panel card">
      <header className="financial-crossover-panel__header">
        <div>
          <h3>Informes financers × EINA</h3>
          <p className="financial-crossover-panel__sub">
            Creua informes (PRAAMS InvestWatch, research, PDF) amb escenaris, SMIC, inversions i
            Policy×Indústria. Totes les conclusions indiquen el <strong>per què</strong> amb les dades
            extretes — sense interpretació LLM.
          </p>
          <span className="financial-crossover-panel__badge">Només dades extretes · sense inferència LLM</span>
        </div>
      </header>

      <div className="financial-crossover-panel__form">
        <div className="financial-crossover-panel__row">
          <label>
            Font
            <select value={source} onChange={(e) => setSource(e.target.value)}>
              <option value="praams">PRAAMS / InvestWatch</option>
              <option value="bloomberg">Bloomberg / research</option>
              <option value="custom">Altres</option>
            </select>
          </label>
          <label>
            Títol (opcional)
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Ex. MHI InvestWatch" />
          </label>
        </div>

        <textarea
          rows={6}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder={SAMPLE_HINT}
        />

        <div className="financial-crossover-panel__actions">
          <button
            type="button"
            className="btn btn-primary"
            disabled={text.trim().length < 50 || uploadMutation.isPending}
            onClick={() => uploadMutation.mutate()}
          >
            {uploadMutation.isPending ? 'Desant…' : 'Desar informe'}
          </button>
          <button type="button" className="btn btn-secondary" onClick={() => fileRef.current?.click()}>
            Pujar fitxer (.txt, .pdf)
          </button>
          <input ref={fileRef} type="file" accept=".txt,.md,.pdf,.html,.csv" hidden onChange={handleFile} />
        </div>

        <label className="financial-crossover-panel__weight">
          Pes informe extern en números finals: {Math.round(externalWeight * 100)}%
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={externalWeight}
            onChange={(e) => setExternalWeight(parseFloat(e.target.value))}
          />
        </label>
      </div>

      {!isLoading && reports.length > 0 && (
        <div className="financial-crossover-panel__reports">
          <h4>Informes desats</h4>
          <ul>
            {(reports as Array<{ id: number; title?: string; source: string; parse_status: string }>).map((r) => (
              <li key={r.id}>
                <span>
                  #{r.id} — {r.title || r.source} ({r.parse_status})
                </span>
                <button
                  type="button"
                  className="btn btn-sm"
                  disabled={crossoverMutation.isPending}
                  onClick={() => crossoverMutation.mutate({ report_id: r.id })}
                >
                  Creuar
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {text.trim().length >= 50 && (
        <button
          type="button"
          className="btn btn-primary financial-crossover-panel__cross-inline"
          disabled={crossoverMutation.isPending}
          onClick={() => crossoverMutation.mutate({ text })}
        >
          {crossoverMutation.isPending ? 'Creuant…' : 'Crear crossover sense desar'}
        </button>
      )}

      {crossoverMutation.isError && (
        <p className="financial-crossover-panel__msg financial-crossover-panel__msg--error">
          Error en el crossover. Comprova que hi ha dades EINA (escenaris/inversions) al cas.
        </p>
      )}

      {crossover && (
        <div className="financial-crossover-panel__results">
          {typeof crossover.note === 'string' && (
            <p className="financial-crossover-panel__method-note">{crossover.note}</p>
          )}

          {externalEvidence.length > 0 && (
            <details className="financial-crossover-panel__evidence" open>
              <summary>Dades extretes de l&apos;informe ({externalEvidence.length})</summary>
              <table>
                <thead>
                  <tr>
                    <th>Camp</th>
                    <th>Valor</th>
                    <th>Per què comptem aquesta dada</th>
                  </tr>
                </thead>
                <tbody>
                  {externalEvidence.map((row, i) => (
                    <tr key={`ext-${row.label}-${i}`}>
                      <td>{row.label || row.kind}</td>
                      <td>{row.value ?? '—'}</td>
                      <td>{row.because}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          )}

          {einaEvidence.length > 0 && (
            <details className="financial-crossover-panel__evidence">
              <summary>Dades EINA del cas ({einaEvidence.length})</summary>
              <table>
                <thead>
                  <tr>
                    <th>Origen</th>
                    <th>Camp</th>
                    <th>Valor</th>
                    <th>Per què</th>
                  </tr>
                </thead>
                <tbody>
                  {einaEvidence.map((row, i) => (
                    <tr key={`eina-${row.label}-${i}`}>
                      <td>{ORIGIN_LABELS[row.origin ?? ''] ?? row.origin}</td>
                      <td>{row.label || row.kind}</td>
                      <td>{row.value ?? '—'}</td>
                      <td>{row.because}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </details>
          )}

          {numberExplanations && Object.keys(numberExplanations).length > 0 && (
            <div className="financial-crossover-panel__numbers-block">
              <h4>Números finals i el seu càlcul</h4>
              {Object.entries(numberExplanations).map(([key, expl]) => (
                <article key={key} className="financial-crossover-panel__number-card">
                  <h5>{key.replace(/_/g, ' ')}</h5>
                  <p className="financial-crossover-panel__number-value">{expl.value}</p>
                  <p className="financial-crossover-panel__because">
                    <strong>Per què:</strong> {expl.because}
                  </p>
                  {expl.formula && (
                    <p className="financial-crossover-panel__formula">
                      Fórmula: <code>{expl.formula}</code>
                    </p>
                  )}
                  {expl.sources && expl.sources.length > 0 && (
                    <ul className="financial-crossover-panel__sources">
                      {expl.sources.map((s, i) => (
                        <li key={`${s.field}-${i}`}>
                          {ORIGIN_LABELS[s.origin ?? ''] ?? s.origin}: {s.label ?? s.field} ={' '}
                          {String(s.value)}
                          {s.excerpt ? ` — «${s.excerpt.slice(0, 80)}…»` : ''}
                        </li>
                      ))}
                    </ul>
                  )}
                </article>
              ))}
            </div>
          )}

          {alignments.length > 0 && (
            <div className="financial-crossover-panel__align">
              <h5>Alineacions (amb motiu)</h5>
              {alignments.map((a) => (
                <article key={a.summary} className="financial-crossover-panel__judgment">
                  <p>{a.summary}</p>
                  <p className="financial-crossover-panel__because">
                    <strong>Per què:</strong> {a.because}
                  </p>
                </article>
              ))}
            </div>
          )}

          {divergences.length > 0 && (
            <div className="financial-crossover-panel__diverge">
              <h5>Divergències (amb motiu)</h5>
              {divergences.map((d) => (
                <article key={d.summary} className="financial-crossover-panel__judgment">
                  <p>{d.summary}</p>
                  <p className="financial-crossover-panel__because">
                    <strong>Per què:</strong> {d.because}
                  </p>
                </article>
              ))}
            </div>
          )}

          {reasoning.length > 0 && (
            <div className="financial-crossover-panel__conclusions">
              <h5>Raonament pas a pas</h5>
              <ol>
                {reasoning.map((r) => (
                  <li key={r.id}>
                    {r.conclusion}
                    <span className="financial-crossover-panel__because-inline"> — Per què: {r.because}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {(crossover.conclusions as string[])?.length > 0 && (
            <div className="financial-crossover-panel__conclusions">
              <h5>Resum</h5>
              <ul>
                {(crossover.conclusions as string[]).map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </section>
  )
}
