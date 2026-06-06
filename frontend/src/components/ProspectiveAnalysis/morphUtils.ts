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
