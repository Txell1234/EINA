/**
 * Lightweight markdown → HTML for LLM scenario narratives (mirrors backend report_markdown.py).
 */
const BOLD_RE = /\*\*(.+?)\*\*/g
const ITALIC_RE = /(?<!\*)\*([^*]+?)\*(?!\*)/g
const NUMBERED_LINE_RE = /^\d+\.\s*(?:→|->)\s*(.*)$/
const NUMBERED_PLAIN_RE = /^\d+\.\s*(.*)$/
const ARROW_LINE_RE = /^(?:→|->)\s*(.*)$/

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function inlineMarkdownHtml(escaped: string): string {
  return escaped
    .replace(BOLD_RE, '<strong>$1</strong>')
    .replace(ITALIC_RE, '<em>$1</em>')
}

function splitBlocks(text: string): string[] {
  const normalized = (text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n').trim()
  if (!normalized) return []
  return normalized.split(/\n\n+/).map((b) => b.trim()).filter(Boolean)
}

function numberedMatch(line: string): RegExpMatchArray | null {
  const stripped = line.trim()
  return stripped.match(NUMBERED_LINE_RE) || stripped.match(NUMBERED_PLAIN_RE)
}

function formatBlockHtml(block: string): string {
  const lines = block.split('\n')
  const parts: string[] = []
  const proseBuffer: string[] = []
  let i = 0

  const flushProse = () => {
    if (!proseBuffer.length) return
    const inner = proseBuffer
      .map((ln) => inlineMarkdownHtml(escapeHtml(ln)))
      .join('<br/>')
    parts.push(`<p class="report-prose">${inner}</p>`)
    proseBuffer.length = 0
  }

  while (i < lines.length) {
    const stripped = lines[i].trim()
    if (!stripped) {
      i += 1
      continue
    }

    if (numberedMatch(stripped)) {
      flushProse()
      const items: string[] = []
      while (i < lines.length) {
        const cur = lines[i].trim()
        if (!cur) {
          i += 1
          continue
        }
        const match = numberedMatch(cur)
        if (!match) break
        items.push(`<li>${inlineMarkdownHtml(escapeHtml(match[1] ?? match[2] ?? ''))}</li>`)
        i += 1
      }
      parts.push(`<ol class="report-list report-list--numbered">${items.join('')}</ol>`)
      continue
    }

    if (ARROW_LINE_RE.test(stripped)) {
      flushProse()
      const items: string[] = []
      while (i < lines.length) {
        const cur = lines[i].trim()
        if (!cur) {
          i += 1
          continue
        }
        const match = cur.match(ARROW_LINE_RE)
        if (!match) break
        items.push(`<li>${inlineMarkdownHtml(escapeHtml(match[1] ?? ''))}</li>`)
        i += 1
      }
      parts.push(`<ul class="report-list">${items.join('')}</ul>`)
      continue
    }

    proseBuffer.push(stripped)
    i += 1
  }

  flushProse()
  return parts.join('\n')
}

export function formatProspectiveMarkdown(text: string): string {
  return splitBlocks(text)
    .map((block) => formatBlockHtml(block))
    .join('\n')
}
