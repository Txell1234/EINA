export type IncompatRow = {
  component_a: string
  config_a: string
  component_b: string
  config_b: string
}

export type MorphRow = {
  id: string
  name: string
  configsText: string
}

export function morphConfigsFromText(text: string): string[] {
  return text
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
}

export function isPairIncompatible(
  list: IncompatRow[],
  compA: string,
  cfgA: string,
  compB: string,
  cfgB: string,
): boolean {
  return list.some(
    (inc) =>
      (inc.component_a === compA &&
        inc.config_a === cfgA &&
        inc.component_b === compB &&
        inc.config_b === cfgB) ||
      (inc.component_a === compB &&
        inc.config_a === cfgB &&
        inc.component_b === compA &&
        inc.config_b === cfgA),
  )
}

export function liveMorphTotal(morphRows: MorphRow[]): number {
  let total = 1
  for (const m of morphRows) {
    total *= Math.max(morphConfigsFromText(m.configsText).length, 1)
  }
  return total
}

export type MorphCombination = Record<string, string>

function componentsWithConfigs(morphRows: MorphRow[]): Array<{ id: string; configs: string[] }> {
  return morphRows
    .map((m) => ({ id: m.id, configs: morphConfigsFromText(m.configsText) }))
    .filter((c) => c.id && c.configs.length > 0)
}

/** Client-side valid Zwicky combinations (respects CCA incompatibilities). */
export function enumerateValidCombinations(
  morphRows: MorphRow[],
  incompatibilities: IncompatRow[],
  limit = 120,
): MorphCombination[] {
  const components = componentsWithConfigs(morphRows)
  if (components.length === 0) return []

  const results: MorphCombination[] = []

  const dfs = (index: number, current: MorphCombination) => {
    if (results.length >= limit) return
    if (index >= components.length) {
      results.push({ ...current })
      return
    }
    const comp = components[index]
    for (const cfg of comp.configs) {
      let ok = true
      for (let j = 0; j < index; j++) {
        const prev = components[j]
        if (isPairIncompatible(incompatibilities, comp.id, cfg, prev.id, current[prev.id])) {
          ok = false
          break
        }
      }
      if (!ok) continue
      current[comp.id] = cfg
      dfs(index + 1, current)
    }
  }

  dfs(0, {})
  return results
}

export function countValidCombinations(
  morphRows: MorphRow[],
  incompatibilities: IncompatRow[],
): { total: number; valid: number; filtered: number } {
  const total = liveMorphTotal(morphRows)
  const valid = enumerateValidCombinations(morphRows, incompatibilities, 10_000).length
  return { total, valid, filtered: Math.max(0, total - valid) }
}
