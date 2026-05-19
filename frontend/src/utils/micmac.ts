/** Pure MIC-MAC sector math (mirrors backend services/micmac_math.py). */

export interface MicmacSector {
  index: number
  code: string
  sector: string
  motricitat: number
  dependencia: number
}

export interface MicmacPreviewResult {
  sectors: MicmacSector[]
  vb_index: number
  vr_index: number
  variable_blanc: { index: number; code: string }
  variable_risc: { index: number; code: string }
  motricitat_direct: number[]
  dependencia_direct: number[]
}

function matrixMultiply(a: number[][], b: number[][]): number[][] {
  const n = a.length
  return Array.from({ length: n }, (_, i) =>
    Array.from({ length: n }, (_, j) =>
      a[i].reduce((sum, _, k) => sum + a[i][k] * b[k][j], 0),
    ),
  )
}

export function computeMicmacPreview(
  matrix: number[][],
  variableCodes?: string[],
): MicmacPreviewResult {
  const n = matrix.length
  const motD = matrix.map((row) => row.reduce((a, b) => a + b, 0))
  const depD = Array.from({ length: n }, (_, j) =>
    matrix.reduce((sum, row) => sum + row[j], 0),
  )
  const avgMot = n ? motD.reduce((a, b) => a + b, 0) / n : 0
  const avgDep = n ? depD.reduce((a, b) => a + b, 0) / n : 0

  const sectors: MicmacSector[] = []
  for (let i = 0; i < n; i++) {
    const mot = motD[i]
    const dep = depD[i]
    let sector: string
    if (mot >= avgMot && dep >= avgDep) sector = 'Clau/Conflicte'
    else if (mot >= avgMot) sector = 'Motriu'
    else if (dep >= avgDep) sector = 'Resultant'
    else sector = 'Excluyent'
    sectors.push({
      index: i,
      code: variableCodes?.[i] ?? String(i),
      sector,
      motricitat: mot,
      dependencia: dep,
    })
  }

  const keySector = sectors.filter((s) => s.sector === 'Clau/Conflicte').map((s) => s.index)
  const vbIdx = keySector.length ? keySector.reduce((best, i) => (depD[i] > depD[best] ? i : best)) : 0
  const vrIdx = n
    ? Array.from({ length: n }, (_, i) => i).reduce((best, i) =>
        Math.abs(motD[i] - depD[i]) < Math.abs(motD[best] - depD[best]) ? i : best,
      )
    : 0

  return {
    sectors,
    vb_index: vbIdx,
    vr_index: vrIdx,
    variable_blanc: { index: vbIdx, code: sectors[vbIdx]?.code ?? '' },
    variable_risc: { index: vrIdx, code: sectors[vrIdx]?.code ?? '' },
    motricitat_direct: motD,
    dependencia_direct: depD,
  }
}

export { matrixMultiply }
