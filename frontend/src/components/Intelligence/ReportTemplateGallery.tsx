import './ReportTemplateGallery.css'

export type TemplateMeta = {
  id: string
  label: string
  label_ca: string
  description: string
  accent?: string
  primary?: string
}

const PREVIEW_STYLES: Record<string, { bg: string; accent: string; text: string; badge: string }> = {
  eina: {
    bg: 'linear-gradient(135deg, #f8fafc, #eef2f7)',
    accent: '#ff6b35',
    text: '#1e3a5f',
    badge: 'EINA · OSINT',
  },
  intelligence: {
    bg: '#0d1117',
    accent: '#f85149',
    text: '#f0f6fc',
    badge: 'INTEL BRIEF',
  },
  economist: {
    bg: '#faf9f7',
    accent: '#e3120b',
    text: '#1a1a1a',
    badge: 'Special Report',
  },
  graphics: {
    bg: 'linear-gradient(135deg, #0ea5e9, #6366f1)',
    accent: '#fff',
    text: '#fff',
    badge: 'Data Intel',
  },
}

type ReportTemplateGalleryProps = {
  templates: TemplateMeta[]
  selected: string
  onSelect: (id: string) => void
  onPreview?: (id: string) => void
}

export default function ReportTemplateGallery({
  templates,
  selected,
  onSelect,
  onPreview,
}: ReportTemplateGalleryProps) {
  return (
    <section className="template-gallery" data-testid="report-template-gallery">
      <h3>Plantilles d&apos;informe</h3>
      <p className="template-gallery__lead">
        Tria l&apos;estètica de l&apos;export: capçalera, gràfics SVG, KPIs i layout editorial.
      </p>
      <div className="template-gallery__grid">
        {templates.map((t) => {
          const style = PREVIEW_STYLES[t.id] ?? PREVIEW_STYLES.eina
          const isSelected = selected === t.id
          return (
            <button
              key={t.id}
              type="button"
              className={`template-card${isSelected ? ' template-card--selected' : ''}`}
              onClick={() => onSelect(t.id)}
              data-testid={`template-card-${t.id}`}
            >
              <div
                className="template-card__preview"
                style={{ background: style.bg, color: style.text }}
              >
                <span className="template-card__badge" style={{ color: style.accent }}>
                  {style.badge}
                </span>
                <div className="template-card__mock-title">Informe prospectiu</div>
                <div className="template-card__mock-bar">
                  <div className="template-card__mock-fill" style={{ background: style.accent, width: '62%' }} />
                </div>
                <div className="template-card__mock-kpis">
                  <span>68%</span>
                  <span>PLAUSIBLE</span>
                </div>
              </div>
              <div className="template-card__meta">
                <strong>{t.label_ca || t.label}</strong>
                <span>{t.description}</span>
              </div>
              {onPreview && (
                <span
                  className="template-card__preview-link"
                  role="presentation"
                  onClick={(e) => {
                    e.stopPropagation()
                    onPreview(t.id)
                  }}
                >
                  Vista prèvia HTML →
                </span>
              )}
            </button>
          )
        })}
      </div>
    </section>
  )
}
