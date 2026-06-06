import { describe, expect, it } from 'vitest'
import {
  isPairIncompatible,
  liveMorphTotal,
  morphConfigsFromText,
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
