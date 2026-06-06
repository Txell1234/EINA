import type { SupportedLocale } from '../i18n/types'

const LOCALE_MAP: Record<SupportedLocale, string> = {
  ca: 'ca-ES',
  es: 'es-ES',
  en: 'en-GB',
  fr: 'fr-FR',
}

export function localeToBcp47(locale: SupportedLocale): string {
  return LOCALE_MAP[locale] ?? 'ca-ES'
}

export function formatLocaleDate(
  locale: SupportedLocale,
  value: string | number | Date,
  options?: Intl.DateTimeFormatOptions,
): string {
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleDateString(localeToBcp47(locale), options)
}

export function formatLocaleDateTime(
  locale: SupportedLocale,
  value: string | number | Date,
  options?: Intl.DateTimeFormatOptions,
): string {
  const date = value instanceof Date ? value : new Date(value)
  if (Number.isNaN(date.getTime())) return ''
  return date.toLocaleString(localeToBcp47(locale), options)
}
