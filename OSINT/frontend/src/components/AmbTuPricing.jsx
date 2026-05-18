import * as React from "react"

const NAVY = "#071C35"
const ACCENT = "#FF6A3D"
const ACCENT_HOVER = "#ff8a5c"
const ACCENT_ACTIVE = "#e55a2d"
const MUTED = "rgba(148, 163, 184, 0.9)"

const translations = {
  EN: {
    hero: "Run multilingual events instantly",
    sub: "AI translation, captions and multilingual audio for meetings and global events.",
    present: "Present",
    parcomm: "Parcomm",
    payEvent: "Pay per Event",
    payLess: "Pay Less · Stay Longer",
    before: "Before the event",
    during: "During the event",
    after: "After the event",
    addons: "Optional services",
    discount: "Discount code",
    discountPlaceholder: "Do you have a promo code?",
    discountApplied: "Discount applied",
    discountInvalid: "Invalid code",
    validating: "Verifying...",
    total: "Total",
    create: "Create event",
    contact: "Contact sales",
    calculator: "Event calculator",
    hours: "hours",
    attendees: "attendees",
    prep: "Event preparation",
    setup: "Technical setup",
    glossary: "Glossary upload",
    proGlossary: "Professional glossary",
    presentBefore:
      "Upload PPTX, PDF or video. Prepare glossary and configure presentation.",
    parcommBefore: "Create multilingual QR event and configure languages.",
    presentDuring:
      "Speak naturally while translation and captions run in real time.",
    parcommDuring: "Participants scan QR and listen or read translation.",
    afterText: "Automatic transcripts and AI summaries sent to attendees.",
    starter: "Starter",
    business: "Business",
    enterprise: "Enterprise",
    custom: "Custom",
    hoursMonthly: "hours monthly",
    liveTranslation: "Live translation",
    captions: "Captions",
    eventTranscripts: "Event transcripts",
    aiSummaries: "AI summaries",
    priorityProcessing: "Priority processing",
    advancedGlossary: "Advanced glossary",
    unlimitedEvents: "Unlimited events",
    largeAudiences: "Large audiences",
    dedicatedInfra: "Dedicated infrastructure",
    perMonth: "/month",
    popular: "Popular",
  },
  CA: {
    hero: "Organitza esdeveniments multilingües a l'instant",
    sub: "Traducció amb IA, subtítols i àudio multilingüe per reunions i esdeveniments.",
    present: "Present",
    parcomm: "Parcomm",
    payEvent: "Pagament per esdeveniment",
    payLess: "Paga menys · queda't més temps",
    before: "Abans de l'esdeveniment",
    during: "Durant l'esdeveniment",
    after: "Després de l'esdeveniment",
    addons: "Serveis opcionals",
    discount: "Codi descompte",
    discountPlaceholder: "Tens un codi promocional?",
    discountApplied: "Descompte aplicat",
    discountInvalid: "Codi no vàlid",
    validating: "Verificant...",
    total: "Total",
    create: "Crear esdeveniment",
    contact: "Contactar vendes",
    calculator: "Calculadora d'esdeveniments",
    hours: "hores",
    attendees: "assistents",
    prep: "Preparació d'esdeveniment",
    setup: "Configuració tècnica",
    glossary: "Pujada de glossari",
    proGlossary: "Glossari professional",
    presentBefore:
      "Puja PPTX, PDF o vídeo. Prepara el glossari i configura la presentació.",
    parcommBefore:
      "Crea un esdeveniment QR multilingüe i configura els idiomes.",
    presentDuring:
      "Parla amb naturalitat mentre la traducció i subtítols funcionen en temps real.",
    parcommDuring:
      "Els participants escanegen el QR i escolten o llegeixen la traducció.",
    afterText:
      "Transcripcions i resums amb IA enviats automàticament als assistents.",
    starter: "Starter",
    business: "Business",
    enterprise: "Enterprise",
    custom: "Personalitzat",
    hoursMonthly: "hores mensuals",
    liveTranslation: "Traducció en directe",
    captions: "Subtítols",
    eventTranscripts: "Transcripcions d'esdeveniments",
    aiSummaries: "Resums amb IA",
    priorityProcessing: "Processament prioritari",
    advancedGlossary: "Glossari avançat",
    unlimitedEvents: "Esdeveniments il·limitats",
    largeAudiences: "Grans audiències",
    dedicatedInfra: "Infraestructura dedicada",
    perMonth: "/mes",
    popular: "Popular",
  },
  ES: {
    hero: "Eventos multilingües al instante",
    sub: "Traducción IA, subtítulos y audio multilingüe para reuniones y eventos.",
    present: "Present",
    parcomm: "Parcomm",
    payEvent: "Pago por evento",
    payLess: "Paga menos · permanece más tiempo",
    before: "Antes del evento",
    during: "Durante el evento",
    after: "Después del evento",
    addons: "Servicios opcionales",
    discount: "Código descuento",
    discountPlaceholder: "¿Tienes un código promocional?",
    discountApplied: "Descuento aplicado",
    discountInvalid: "Código no válido",
    validating: "Verificando...",
    total: "Total",
    create: "Crear evento",
    contact: "Contactar ventas",
    calculator: "Calculadora de eventos",
    hours: "horas",
    attendees: "asistentes",
    prep: "Preparación del evento",
    setup: "Configuración técnica",
    glossary: "Subida de glosario",
    proGlossary: "Glosario profesional",
    presentBefore:
      "Sube PPTX, PDF o vídeo. Prepara el glosario y configura la presentación.",
    parcommBefore: "Crea evento QR multilingüe y configura los idiomas.",
    presentDuring:
      "Habla con naturalidad mientras la traducción y subtítulos funcionan en tiempo real.",
    parcommDuring:
      "Los participantes escanean el QR y escuchan o leen la traducción.",
    afterText:
      "Transcripciones y resúmenes IA enviados automáticamente a los asistentes.",
    starter: "Starter",
    business: "Business",
    enterprise: "Enterprise",
    custom: "Personalizado",
    hoursMonthly: "horas mensuales",
    liveTranslation: "Traducción en vivo",
    captions: "Subtítulos",
    eventTranscripts: "Transcripciones de eventos",
    aiSummaries: "Resúmenes IA",
    priorityProcessing: "Procesamiento prioritario",
    advancedGlossary: "Glosario avanzado",
    unlimitedEvents: "Eventos ilimitados",
    largeAudiences: "Grandes audiencias",
    dedicatedInfra: "Infraestructura dedicada",
    perMonth: "/mes",
    popular: "Popular",
  },
  FR: {
    hero: "Organisez des événements multilingues instantanément",
    sub: "Traduction IA, sous-titres et audio multilingue pour réunions et événements.",
    present: "Present",
    parcomm: "Parcomm",
    payEvent: "Paiement par événement",
    payLess: "Payez moins · Restez plus longtemps",
    before: "Avant l'événement",
    during: "Pendant l'événement",
    after: "Après l'événement",
    addons: "Services optionnels",
    discount: "Code promo",
    discountPlaceholder: "Avez-vous un code promo?",
    discountApplied: "Réduction appliquée",
    discountInvalid: "Code invalide",
    validating: "Vérification...",
    total: "Total",
    create: "Créer l'événement",
    contact: "Contacter les ventes",
    calculator: "Calculateur d'événements",
    hours: "heures",
    attendees: "participants",
    prep: "Préparation de l'événement",
    setup: "Configuration technique",
    glossary: "Téléchargement du glossaire",
    proGlossary: "Glossaire professionnel",
    presentBefore:
      "Téléchargez PPTX, PDF ou vidéo. Préparez le glossaire et configurez la présentation.",
    parcommBefore:
      "Créez un événement QR multilingue et configurez les langues.",
    presentDuring:
      "Parlez naturellement pendant que la traduction et les sous-titres s'affichent en temps réel.",
    parcommDuring:
      "Les participants scannent le QR et écoutent ou lisent la traduction.",
    afterText:
      "Transcriptions et résumés IA envoyés automatiquement aux participants.",
    starter: "Starter",
    business: "Business",
    enterprise: "Enterprise",
    custom: "Sur mesure",
    hoursMonthly: "heures par mois",
    liveTranslation: "Traduction en direct",
    captions: "Sous-titres",
    eventTranscripts: "Transcriptions d'événements",
    aiSummaries: "Résumés IA",
    priorityProcessing: "Traitement prioritaire",
    advancedGlossary: "Glossaire avancé",
    unlimitedEvents: "Événements illimités",
    largeAudiences: "Grandes audiences",
    dedicatedInfra: "Infrastructure dédiée",
    perMonth: "/mois",
    popular: "Populaire",
  },
}

const glassStyle = {
  background:
    "linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0.05) 100%)",
  backdropFilter: "blur(24px)",
  WebkitBackdropFilter: "blur(24px)",
  border: "1px solid rgba(255, 255, 255, 0.2)",
  boxShadow:
    "0 8px 32px rgba(0, 0, 0, 0.25), inset 0 1px 0 rgba(255,255,255,0.15)",
}

const glassCardStyle = {
  ...glassStyle,
  padding: 40,
  borderRadius: 24,
  boxShadow:
    "0 24px 48px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255,255,255,0.15)",
  transition: "transform 0.3s ease, box-shadow 0.3s ease",
}

const Checkbox = ({ checked, onChange }) => (
  <div
    onClick={onChange}
    role="checkbox"
    aria-checked={checked}
    style={{
      width: 24,
      height: 24,
      borderRadius: 8,
      border: `2px solid ${checked ? ACCENT : "#cbd5e1"}`,
      background: checked ? ACCENT : "white",
      cursor: "pointer",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      flexShrink: 0,
      transition: "all 0.2s ease",
    }}
  >
    {checked && (
      <svg width="14" height="11" viewBox="0 0 14 11" fill="none">
        <path
          d="M1 5.5L5 9.5L13 1"
          stroke="white"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    )}
  </div>
)

const CouponIcon = () => (
  <svg
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    style={{ flexShrink: 0 }}
  >
    <path
      d="M4 4h16a2 2 0 0 1 2 2v2l-2 1-2-1-2 1-2-1-2 1-2-1v10a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2z"
      stroke={ACCENT}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      fill="none"
    />
    <path
      d="M8 12h8M8 16h4"
      stroke={ACCENT}
      strokeWidth="2"
      strokeLinecap="round"
    />
  </svg>
)

const StepIcons = ["📤", "🎤", "📋"]

/**
 * Valida un codi de descompte via API. Els codis vàlids mai es revelen al client.
 * @param {string} code - Codi introduït per l'usuari
 * @param {string} apiBaseUrl - URL base del backend (ex: "http://localhost:8000")
 * @returns {Promise<{valid: boolean, percent?: number}>}
 */
const defaultValidateDiscount = async (code, apiBaseUrl = "") => {
  if (!code || !code.trim()) return { valid: false }
  const base = (apiBaseUrl || "").replace(/\/$/, "")
  const url = `${base}/api/validate-discount`
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: code.trim().toUpperCase() }),
    })
    const data = await res.json()
    return { valid: !!data?.valid, percent: data?.percent ?? 0 }
  } catch {
    return { valid: false }
  }
}

export default function AmbTuPricing({
  validateDiscount,
  apiBaseUrl = "",
}) {
  const doValidate = React.useCallback(
    (code) =>
      validateDiscount
        ? validateDiscount(code)
        : defaultValidateDiscount(code, apiBaseUrl),
    [validateDiscount, apiBaseUrl]
  )
  const [lang, setLang] = React.useState("EN")
  const t = translations[lang]

  const [product, setProduct] = React.useState("present")
  const [mode, setMode] = React.useState("event")

  const [hours, setHours] = React.useState(4)
  const [attendees, setAttendees] = React.useState(50)

  const [prep, setPrep] = React.useState(false)
  const [setup, setSetup] = React.useState(false)
  const [glossary, setGlossary] = React.useState(false)
  const [proGlossary, setProGlossary] = React.useState(false)

  const [discount, setDiscount] = React.useState("")
  const [discountFocused, setDiscountFocused] = React.useState(false)
  const [discountStatus, setDiscountStatus] = React.useState(null)
  const [discountPercent, setDiscountPercent] = React.useState(0)
  const [validating, setValidating] = React.useState(false)
  const validateTimeoutRef = React.useRef(null)

  const presentPrices = { 1: 180, 2: 340, 3: 500, 4: 635 }
  const parcommPrices = { 1: 150, 2: 270, 3: 390, 4: 480 }

  let price =
    product === "present" ? presentPrices[hours] : parcommPrices[hours]

  if (prep) price += 65
  if (setup) price += 70
  if (glossary) price += 10
  if (proGlossary) price += 120

  if (product === "parcomm") {
    if (attendees > 50 && attendees <= 100) price += 40
    if (attendees > 100 && attendees <= 250) price += 90
    if (attendees > 250) price += 160
  }

  if (discountStatus === "valid" && discountPercent > 0) {
    price = price * (1 - discountPercent / 100)
  }

  const valueCards = [
    {
      title: t.before,
      text: product === "present" ? t.presentBefore : t.parcommBefore,
    },
    {
      title: t.during,
      text: product === "present" ? t.presentDuring : t.parcommDuring,
    },
    { title: t.after, text: t.afterText },
  ]

  const subscriptionPlans = [
    {
      name: t.starter,
      price: (product === "present" ? "590€" : "420€") + t.perMonth,
      features: [
        "4 " + t.hoursMonthly,
        t.liveTranslation,
        t.captions,
        t.eventTranscripts,
        t.aiSummaries,
      ],
    },
    {
      name: t.business,
      price: (product === "present" ? "1090€" : "820€") + t.perMonth,
      popular: true,
      features: [
        "8 " + t.hoursMonthly,
        t.priorityProcessing,
        t.advancedGlossary,
        t.eventTranscripts,
        t.aiSummaries,
      ],
    },
    {
      name: t.enterprise,
      price: t.custom,
      features: [t.unlimitedEvents, t.largeAudiences, t.dedicatedInfra],
    },
  ]

  const validateCode = React.useCallback(async () => {
    const code = discount.trim()
    if (!code) {
      setDiscountStatus(null)
      setDiscountPercent(0)
      return
    }
    setValidating(true)
    setDiscountStatus(null)
    try {
      const result = await doValidate(code)
      setDiscountStatus(result.valid ? "valid" : "invalid")
      setDiscountPercent(result.valid ? (result.percent ?? 5) : 0)
    } catch {
      setDiscountStatus("invalid")
      setDiscountPercent(0)
    } finally {
      setValidating(false)
    }
  }, [discount, doValidate])

  React.useEffect(() => {
    if (validateTimeoutRef.current) clearTimeout(validateTimeoutRef.current)
    if (!discount.trim()) {
      setDiscountStatus(null)
      setDiscountPercent(0)
      return
    }
    validateTimeoutRef.current = setTimeout(validateCode, 600)
    return () => {
      if (validateTimeoutRef.current) clearTimeout(validateTimeoutRef.current)
    }
  }, [discount, validateCode])

  const btnBase = {
    padding: "12px 24px",
    borderRadius: 16,
    border: "none",
    cursor: "pointer",
    fontWeight: 600,
    transition: "all 0.25s ease",
  }

  return (
    <div
      style={{
        padding: "clamp(40px, 8vw, 120px) clamp(16px, 4vw, 32px)",
        fontFamily: "'Poppins', 'DM Sans', system-ui, sans-serif",
        background:
          "radial-gradient(ellipse 140% 90% at 50% -30%, rgba(15,74,134,0.5) 0%, transparent 55%), radial-gradient(circle at 70% 20%, rgba(255,106,61,0.08) 0%, transparent 40%), radial-gradient(circle at 30% 0%, #0f4a86 0%, #071C35 55%, #020b18 100%)",
        color: "white",
        minHeight: "100vh",
        position: "relative",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\' opacity=\'0.04\'/%3E%3C/svg%3E")',
          pointerEvents: "none",
        }}
      />

      <div
        style={{
          position: "relative",
          zIndex: 1,
          maxWidth: 1140,
          margin: "0 auto",
        }}
      >
        <h1
          style={{
            fontSize: "clamp(36px, 5vw, 64px)",
            textAlign: "center",
            fontWeight: 800,
            marginBottom: 16,
            letterSpacing: "-0.02em",
            lineHeight: 1.2,
            textShadow: "0 4px 24px rgba(0,0,0,0.35)",
            animation: "fadeInDown 0.6s ease-out",
          }}
        >
          {t.hero}
        </h1>

        <p
          style={{
            textAlign: "center",
            marginBottom: 64,
            fontSize: "clamp(16px, 2vw, 18px)",
            maxWidth: 600,
            margin: "0 auto 64px",
            lineHeight: 1.6,
            color: MUTED,
          }}
        >
          {t.sub}
        </p>

        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginBottom: 48,
          }}
        >
          <div style={{ ...glassStyle, borderRadius: 24, padding: 6 }}>
            {["EN", "CA", "ES", "FR"].map((l) => (
              <button
                key={l}
                type="button"
                onClick={() => setLang(l)}
                style={{
                  ...btnBase,
                  background: lang === l ? ACCENT : "transparent",
                  color: "white",
                  fontWeight: lang === l ? 600 : 400,
                }}
                onMouseEnter={(e) => {
                  if (lang !== l) e.currentTarget.style.background = "rgba(255,255,255,0.08)"
                }}
                onMouseLeave={(e) => {
                  if (lang !== l) e.currentTarget.style.background = "transparent"
                }}
              >
                {l}
              </button>
            ))}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginBottom: 48,
          }}
        >
          <div style={{ ...glassStyle, borderRadius: 40, padding: 6 }}>
            <button
              type="button"
              onClick={() => setProduct("present")}
              style={{
                ...btnBase,
                padding: "12px 28px",
                borderRadius: 30,
                background: product === "present" ? ACCENT : "transparent",
                color: "white",
              }}
              onMouseEnter={(e) => {
                if (product !== "present") e.currentTarget.style.background = "rgba(255,255,255,0.08)"
              }}
              onMouseLeave={(e) => {
                if (product !== "present") e.currentTarget.style.background = "transparent"
              }}
            >
              {t.present}
            </button>
            <button
              type="button"
              onClick={() => setProduct("parcomm")}
              style={{
                ...btnBase,
                padding: "12px 28px",
                borderRadius: 30,
                background: product === "parcomm" ? ACCENT : "transparent",
                color: "white",
              }}
              onMouseEnter={(e) => {
                if (product !== "parcomm") e.currentTarget.style.background = "rgba(255,255,255,0.08)"
              }}
              onMouseLeave={(e) => {
                if (product !== "parcomm") e.currentTarget.style.background = "transparent"
              }}
            >
              {t.parcomm}
            </button>
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: 32,
            marginBottom: 80,
          }}
        >
          {valueCards.map((c, i) => (
            <div
              key={i}
              style={{
                ...glassCardStyle,
                position: "relative",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-8px)"
                e.currentTarget.style.boxShadow =
                  "0 32px 64px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.2)"
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)"
                e.currentTarget.style.boxShadow =
                  "0 24px 48px rgba(0, 0, 0, 0.3), inset 0 1px 0 rgba(255,255,255,0.15)"
              }}
            >
              <span
                style={{
                  position: "absolute",
                  top: 20,
                  right: 20,
                  fontSize: 14,
                  fontWeight: 700,
                  opacity: 0.4,
                  letterSpacing: "0.1em",
                }}
              >
                {String(i + 1).padStart(2, "0")}
              </span>
              <span
                style={{
                  fontSize: 36,
                  marginBottom: 12,
                  display: "block",
                }}
              >
                {StepIcons[i]}
              </span>
              <h3
                style={{
                  marginBottom: 12,
                  fontSize: 20,
                  fontWeight: 600,
                  letterSpacing: "-0.01em",
                }}
              >
                {c.title}
              </h3>
              <p style={{ opacity: 0.9, lineHeight: 1.7 }}>{c.text}</p>
            </div>
          ))}
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "center",
            marginBottom: 64,
          }}
        >
          <div style={{ ...glassStyle, borderRadius: 40, padding: 6 }}>
            <button
              type="button"
              onClick={() => setMode("event")}
              style={{
                ...btnBase,
                padding: "10px 24px",
                borderRadius: 30,
                background: mode === "event" ? ACCENT : "transparent",
                color: "white",
              }}
              onMouseEnter={(e) => {
                if (mode !== "event") e.currentTarget.style.background = "rgba(255,255,255,0.08)"
              }}
              onMouseLeave={(e) => {
                if (mode !== "event") e.currentTarget.style.background = "transparent"
              }}
            >
              {t.payEvent}
            </button>
            <button
              type="button"
              onClick={() => setMode("subscription")}
              style={{
                ...btnBase,
                padding: "10px 24px",
                borderRadius: 30,
                background: mode === "subscription" ? ACCENT : "transparent",
                color: "white",
              }}
              onMouseEnter={(e) => {
                if (mode !== "subscription") e.currentTarget.style.background = "rgba(255,255,255,0.08)"
              }}
              onMouseLeave={(e) => {
                if (mode !== "subscription") e.currentTarget.style.background = "transparent"
              }}
            >
              {t.payLess}
            </button>
          </div>
        </div>

        {mode === "event" ? (
          <div
            style={{
              maxWidth: 900,
              margin: "0 auto",
              background: "rgba(255,255,255,0.97)",
              backdropFilter: "blur(24px)",
              WebkitBackdropFilter: "blur(24px)",
              borderRadius: 28,
              padding: "clamp(32px, 5vw, 56px)",
              color: "#111",
              boxShadow:
                "0 40px 80px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.9)",
              border: "1px solid rgba(255,255,255,0.6)",
              animation: "fadeInUp 0.4s ease-out",
            }}
          >
            <h2
              style={{
                marginBottom: 28,
                fontSize: 28,
                fontWeight: 700,
                letterSpacing: "-0.02em",
              }}
            >
              {t.calculator}
            </h2>

            <div
              style={{
                display: "flex",
                flexWrap: "wrap",
                gap: 12,
                marginBottom: 28,
              }}
            >
              {[1, 2, 3, 4].map((h) => (
                <button
                  key={h}
                  type="button"
                  onClick={() => setHours(h)}
                  style={{
                    ...btnBase,
                    padding: "14px 28px",
                    borderRadius: 16,
                    background: hours === h ? ACCENT : "#f1f5f9",
                    color: hours === h ? "white" : "#334155",
                  }}
                  onMouseEnter={(e) => {
                    if (hours !== h) {
                      e.currentTarget.style.background = "#e2e8f0"
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (hours !== h) {
                      e.currentTarget.style.background = "#f1f5f9"
                    }
                  }}
                >
                  {h}h
                </button>
              ))}
            </div>

            {product === "parcomm" && (
              <div style={{ marginBottom: 28 }}>
                <label
                  style={{
                    display: "block",
                    marginBottom: 10,
                    fontWeight: 600,
                    fontSize: 14,
                  }}
                >
                  {t.attendees}
                </label>
                <select
                  value={attendees}
                  onChange={(e) => setAttendees(Number(e.target.value))}
                  style={{
                    padding: "14px 18px",
                    borderRadius: 14,
                    border: "2px solid #e2e8f0",
                    width: "100%",
                    maxWidth: 220,
                    fontSize: 16,
                    background: "white",
                    cursor: "pointer",
                  }}
                >
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                  <option value={250}>250</option>
                  <option value={500}>500</option>
                </select>
              </div>
            )}

            <div
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 16,
                marginBottom: 28,
              }}
            >
              {[
                [prep, setPrep, t.prep, 65],
                [setup, setSetup, t.setup, 70],
                [glossary, setGlossary, t.glossary, 10],
                [proGlossary, setProGlossary, t.proGlossary, 120],
              ].map(([checked, setter, label, add]) => (
                <label
                  key={label}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 14,
                    cursor: "pointer",
                    padding: "12px 0",
                    borderBottom: "1px solid #f1f5f9",
                  }}
                >
                  <Checkbox
                    checked={checked}
                    onChange={() => setter((v) => !v)}
                  />
                  <span style={{ flex: 1 }}>{label}</span>
                  <span
                    style={{
                      color: ACCENT,
                      fontWeight: 600,
                    }}
                  >
                    +{add}€
                  </span>
                </label>
              ))}
            </div>

            <div
              style={{
                marginTop: 32,
                marginBottom: 32,
                padding: 28,
                background:
                  "linear-gradient(135deg, rgba(255,106,61,0.08) 0%, rgba(7,28,53,0.03) 100%)",
                borderRadius: 20,
                border: `2px solid ${discountFocused ? ACCENT : "rgba(255,106,61,0.2)"}`,
                boxShadow: discountFocused
                  ? "0 0 0 4px rgba(255,106,61,0.12)"
                  : "0 4px 24px rgba(255,106,61,0.06)",
                transition: "all 0.25s ease",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 12,
                  marginBottom: 14,
                }}
              >
                <CouponIcon />
                <label
                  style={{
                    fontWeight: 700,
                    color: NAVY,
                    fontSize: 13,
                    textTransform: "uppercase",
                    letterSpacing: "0.08em",
                  }}
                >
                  {t.discount}
                </label>
              </div>
              <input
                placeholder={t.discountPlaceholder}
                value={discount}
                onChange={(e) => setDiscount(e.target.value)}
                onFocus={() => setDiscountFocused(true)}
                onBlur={() => setDiscountFocused(false)}
                autoComplete="off"
                style={{
                  padding: "18px 20px",
                  width: "100%",
                  borderRadius: 14,
                  border: `2px solid ${discountStatus === "invalid" ? "#ef4444" : "#e2e8f0"}`,
                  fontSize: 16,
                  background: "white",
                  outline: "none",
                  transition: "border-color 0.2s ease",
                }}
              />
              {validating && (
                <p
                  style={{
                    marginTop: 12,
                    fontSize: 14,
                    color: "#64748b",
                  }}
                >
                  {t.validating}
                </p>
              )}
              {!validating && discountStatus === "valid" && discountPercent > 0 && (
                <p
                  style={{
                    marginTop: 12,
                    padding: "8px 14px",
                    borderRadius: 10,
                    background: "rgba(34, 197, 94, 0.15)",
                    color: "#16a34a",
                    fontWeight: 600,
                    fontSize: 14,
                    display: "inline-flex",
                    alignItems: "center",
                    gap: 6,
                  }}
                >
                  ✓ {t.discountApplied} ({discountPercent}%)
                </p>
              )}
              {!validating && discountStatus === "invalid" && discount.trim() && (
                <p
                  style={{
                    marginTop: 12,
                    padding: "8px 14px",
                    borderRadius: 10,
                    background: "rgba(239, 68, 68, 0.1)",
                    color: "#dc2626",
                    fontWeight: 600,
                    fontSize: 14,
                  }}
                >
                  {t.discountInvalid}
                </p>
              )}
            </div>

            <h2
              style={{
                color: ACCENT,
                fontSize: "clamp(40px, 5vw, 52px)",
                fontWeight: 800,
                marginBottom: 4,
                letterSpacing: "-0.02em",
              }}
            >
              {Math.round(price)}€
            </h2>
            <p
              style={{
                opacity: 0.7,
                marginBottom: 24,
                fontSize: 15,
              }}
            >
              {t.total}
            </p>

            <button
              type="button"
              style={{
                width: "100%",
                padding: 20,
                background: `linear-gradient(135deg, ${NAVY} 0%, #0a2744 100%)`,
                color: "white",
                borderRadius: 16,
                border: "none",
                fontWeight: 700,
                fontSize: 17,
                cursor: "pointer",
                boxShadow: "0 8px 24px rgba(7,28,53,0.35)",
                transition: "transform 0.2s ease, box-shadow 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.transform = "translateY(-2px)"
                e.currentTarget.style.boxShadow =
                  "0 12px 32px rgba(7,28,53,0.45)"
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.transform = "translateY(0)"
                e.currentTarget.style.boxShadow =
                  "0 8px 24px rgba(7,28,53,0.35)"
              }}
            >
              {t.create}
            </button>
          </div>
        ) : (
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
              gap: 32,
              maxWidth: 1140,
              margin: "0 auto",
              animation: "fadeInUp 0.4s ease-out",
            }}
          >
            {subscriptionPlans.map((p, i) => (
              <div
                key={i}
                style={{
                  position: "relative",
                  background: "rgba(255,255,255,0.97)",
                  backdropFilter: "blur(20px)",
                  WebkitBackdropFilter: "blur(20px)",
                  padding: 40,
                  borderRadius: 28,
                  color: "#111",
                  border: p.popular
                    ? `3px solid ${ACCENT}`
                    : "1px solid rgba(0,0,0,0.06)",
                  boxShadow: p.popular
                    ? "0 24px 48px rgba(255,106,61,0.2), 0 0 60px rgba(255,106,61,0.08)"
                    : "0 20px 40px rgba(0,0,0,0.08)",
                  overflow: "hidden",
                  transition: "transform 0.3s ease, box-shadow 0.3s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.transform = "translateY(-12px)"
                  e.currentTarget.style.boxShadow = p.popular
                    ? "0 32px 64px rgba(255,106,61,0.25), 0 0 80px rgba(255,106,61,0.12)"
                    : "0 28px 56px rgba(0,0,0,0.12)"
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.transform = "translateY(0)"
                  e.currentTarget.style.boxShadow = p.popular
                    ? "0 24px 48px rgba(255,106,61,0.2), 0 0 60px rgba(255,106,61,0.08)"
                    : "0 20px 40px rgba(0,0,0,0.08)"
                }}
              >
                {p.popular && (
                  <div
                    style={{
                      position: "absolute",
                      top: 18,
                      right: -32,
                      background: ACCENT,
                      color: "white",
                      padding: "6px 40px",
                      fontSize: 12,
                      fontWeight: 700,
                      transform: "rotate(45deg)",
                      boxShadow: "0 4px 12px rgba(255,106,61,0.4)",
                    }}
                  >
                    {t.popular}
                  </div>
                )}
                <h3
                  style={{
                    fontSize: 24,
                    fontWeight: 700,
                    marginBottom: 12,
                    letterSpacing: "-0.02em",
                  }}
                >
                  {p.name}
                </h3>
                <div style={{ marginBottom: 28 }}>
                  <span
                    style={{
                      color: ACCENT,
                      fontSize: 36,
                      fontWeight: 800,
                      letterSpacing: "-0.02em",
                    }}
                  >
                    {p.price.includes("€")
                      ? p.price.split(t.perMonth)[0]
                      : p.price}
                  </span>
                  {p.price.includes("€") && (
                    <span
                      style={{
                        fontSize: 16,
                        color: "#64748b",
                        fontWeight: 500,
                      }}
                    >
                      {t.perMonth}
                    </span>
                  )}
                </div>
                <ul
                  style={{
                    lineHeight: 2.4,
                    listStyle: "none",
                    padding: 0,
                  }}
                >
                  {p.features.map((f, j) => (
                    <li
                      key={j}
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 10,
                      }}
                    >
                      <span
                        style={{
                          color: ACCENT,
                          fontSize: 18,
                        }}
                      >
                        ✓
                      </span>{" "}
                      {f}
                    </li>
                  ))}
                </ul>
                <button
                  type="button"
                  style={{
                    width: "100%",
                    padding: 18,
                    background: `linear-gradient(135deg, ${NAVY} 0%, #0a2744 100%)`,
                    color: "white",
                    borderRadius: 14,
                    border: "none",
                    fontWeight: 600,
                    marginTop: 28,
                    cursor: "pointer",
                    boxShadow: "0 8px 24px rgba(7,28,53,0.25)",
                    transition: "transform 0.2s ease, box-shadow 0.2s ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = "translateY(-2px)"
                    e.currentTarget.style.boxShadow =
                      "0 12px 32px rgba(7,28,53,0.35)"
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = "translateY(0)"
                    e.currentTarget.style.boxShadow =
                      "0 8px 24px rgba(7,28,53,0.25)"
                  }}
                >
                  {t.contact}
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <style>{`
        @keyframes fadeInDown {
          from { opacity: 0; transform: translateY(-20px); }
          to { opacity: 1; transform: translateY(0); }
        }
        @keyframes fadeInUp {
          from { opacity: 0; transform: translateY(20px); }
          to { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  )
}
