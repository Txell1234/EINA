import { useMemo, useState } from 'react'
import { useI18n } from '../../contexts/I18nContext'
import {
  type IncompatRow,
  type MorphRow,
  enumerateValidCombinations,
  countValidCombinations,
  liveMorphTotal,
} from './morphUtils'
import './MorphExplorer.css'

type MorphExplorerProps = {
  morphRows: MorphRow[]
  incompatibilities: IncompatRow[]
  serverValid?: number | null
}

function formatCombo(combo: Record<string, string>): string {
  return Object.entries(combo)
    .map(([k, v]) => `${k}:${v}`)
    .join(' · ')
}

export default function MorphExplorer({ morphRows, incompatibilities, serverValid }: MorphExplorerProps) {
  const { t } = useI18n()
  const [filter, setFilter] = useState('')

  const counts = useMemo(
    () => countValidCombinations(morphRows, incompatibilities),
    [morphRows, incompatibilities],
  )

  const combinations = useMemo(
    () => enumerateValidCombinations(morphRows, incompatibilities, 200),
    [morphRows, incompatibilities],
  )

  const filtered = useMemo(() => {
    const q = filter.trim().toLowerCase()
    if (!q) return combinations
    return combinations.filter((c) => formatCombo(c).toLowerCase().includes(q))
  }, [combinations, filter])

  const totalRaw = liveMorphTotal(morphRows)

  return (
    <section className="morph-explorer card" data-testid="morph-explorer">
      <header className="morph-explorer__header">
        <h3>{t('morph.explorer.title')}</h3>
        <p className="morph-explorer__lead">{t('morph.explorer.subtitle')}</p>
      </header>

      <div className="morph-explorer__stats" data-testid="morph-explorer-stats">
        <span>
          {t('morph.explorer.total')}: <strong>{totalRaw}</strong>
        </span>
        <span>
          {t('morph.explorer.valid')}:{' '}
          <strong data-testid="morph-explorer-valid-count">
            {serverValid ?? counts.valid}
          </strong>
        </span>
        <span>
          {t('morph.explorer.filtered')}: <strong>{counts.filtered}</strong>
        </span>
        <span>
          {t('morph.explorer.shown')}: <strong>{filtered.length}</strong>
        </span>
      </div>

      <label className="morph-explorer__filter">
        {t('morph.explorer.filter')}
        <input
          type="search"
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder={t('morph.explorer.filterPlaceholder')}
          data-testid="morph-explorer-filter"
        />
      </label>

      {filtered.length === 0 ? (
        <p className="morph-explorer__empty">{t('morph.explorer.empty')}</p>
      ) : (
        <ul className="morph-explorer__list">
          {filtered.slice(0, 40).map((combo, idx) => (
            <li key={`${idx}-${formatCombo(combo)}`} className="morph-explorer__item">
              {formatCombo(combo)}
            </li>
          ))}
        </ul>
      )}
      {filtered.length > 40 && (
        <p className="morph-explorer__more">{t('morph.explorer.more', { count: filtered.length - 40 })}</p>
      )}
    </section>
  )
}
