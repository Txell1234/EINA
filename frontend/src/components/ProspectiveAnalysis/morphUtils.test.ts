import { describe, expect, it } from 'vitest'
import {
  isPairIncompatible,
  liveMorphTotal,
  morphConfigsFromText,
  enumerateValidCombinations,
  type IncompatRow,
} from './morphUtils'

describe('morphConfigsFromText', () => {
  it('splits lines and trims empties', () => {
    expect(morphConfigsFromText(' A \n\nB\n C ')).toEqual(['A', 'B', 'C'])
  })
})

describe('isPairIncompatible', () => {
  const rows: IncompatRow[] = [
    {
      component_a: 'X',
      config_a: '1',
      component_b: 'Y',
      config_b: '2',
    },
  ]

  it('detects direct and reversed pairs', () => {
    expect(isPairIncompatible(rows, 'X', '1', 'Y', '2')).toBe(true)
    expect(isPairIncompatible(rows, 'Y', '2', 'X', '1')).toBe(true)
    expect(isPairIncompatible(rows, 'X', '1', 'Y', '3')).toBe(false)
  })
})

describe('liveMorphTotal', () => {
  it('multiplies config counts per morph row', () => {
    const total = liveMorphTotal([
      { id: 'a', name: 'A', configsText: '1\n2' },
      { id: 'b', name: 'B', configsText: 'x\ny\nz' },
    ])
    expect(total).toBe(6)
  })

  it('treats empty config as 1', () => {
    expect(liveMorphTotal([{ id: 'a', name: 'A', configsText: '' }])).toBe(1)
  })
})

describe('enumerateValidCombinations', () => {
  const rows = [
    { id: 'C1', name: 'A', configsText: 'Opció A\nOpció B' },
    { id: 'C2', name: 'B', configsText: 'Opció A\nOpció B' },
  ]

  it('returns cartesian product when no incompatibilities', () => {
    const combos = enumerateValidCombinations(rows, [], 20)
    expect(combos).toHaveLength(4)
  })

  it('excludes incompatible pairs', () => {
    const incompat: IncompatRow[] = [
      { component_a: 'C1', config_a: 'Opció A', component_b: 'C2', config_b: 'Opció B' },
    ]
    const combos = enumerateValidCombinations(rows, incompat, 20)
    expect(combos).toHaveLength(3)
    expect(combos.some((c) => c.C1 === 'Opció A' && c.C2 === 'Opció B')).toBe(false)
  })
})
