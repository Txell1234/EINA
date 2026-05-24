type ValidationErrorItem = {
  msg?: string
  loc?: (string | number)[]
  type?: string
}

/** Converteix el camp `detail` d'una resposta FastAPI en text llegible. */
export function formatApiErrorDetail(detail: unknown, fallback = 'Error inesperat'): string {
  if (detail == null || detail === '') return fallback
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      if (typeof item === 'string') return item
      if (item && typeof item === 'object' && 'msg' in item) {
        const err = item as ValidationErrorItem
        const loc = Array.isArray(err.loc)
          ? err.loc.filter((part) => part !== 'body' && part !== 'query').join('.')
          : ''
        return loc ? `${loc}: ${err.msg}` : String(err.msg ?? fallback)
      }
      try {
        return JSON.stringify(item)
      } catch {
        return fallback
      }
    })
    return messages.filter(Boolean).join('; ') || fallback
  }
  if (typeof detail === 'object' && detail !== null && 'msg' in detail) {
    return String((detail as ValidationErrorItem).msg ?? fallback)
  }
  return fallback
}
