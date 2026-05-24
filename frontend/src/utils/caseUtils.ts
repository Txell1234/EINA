import type { ActiveCase } from '../contexts/CaseContext'

type CaseLike = {
  id?: number
  case_id?: number
  name?: string
  case_type?: string
  status?: string
  description?: string | null
}

export function toActiveCase(data: CaseLike | Record<string, unknown>): ActiveCase {
  const record = data as CaseLike
  const description =
    record.description != null && String(record.description).trim()
      ? String(record.description)
      : undefined

  return {
    id: Number(record.id ?? record.case_id),
    name: String(record.name ?? 'Nou cas'),
    case_type: String(record.case_type ?? 'general'),
    status: String(record.status ?? 'pending'),
    ...(description ? { description } : {}),
  }
}

export function countPromptLines(text?: string | null): number {
  if (!text?.trim()) return 0
  return text.split(/\r\n|\r|\n/).filter((line) => line.trim()).length
}

export function briefCaseDescription(text?: string | null, maxLen = 120): string | null {
  if (!text?.trim()) return null
  const normalized = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim()
  const firstLine = normalized.split('\n').find((line) => line.trim()) ?? normalized
  if (firstLine.length <= maxLen) return firstLine
  return `${firstLine.slice(0, maxLen - 1).trim()}…`
}
