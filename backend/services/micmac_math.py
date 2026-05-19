"""Pure MIC-MAC sector math (Godet) — shared by API preview and persistence."""
from typing import Any, List, Optional


def matrix_multiply(a: List[List[int]], b: List[List[int]]) -> List[List[int]]:
    n = len(a)
    return [
        [sum(a[i][k] * b[k][j] for k in range(n)) for j in range(n)]
        for i in range(n)
    ]


def compute_micmac_pure(
    matrix: List[List[int]],
    variable_codes: Optional[List[str]] = None,
) -> dict[str, Any]:
    n = len(matrix)
    mot_d = [sum(matrix[i]) for i in range(n)]
    dep_d = [sum(matrix[i][j] for i in range(n)) for j in range(n)]
    avg_mot = sum(mot_d) / n if n else 0
    avg_dep = sum(dep_d) / n if n else 0

    indirect = matrix_multiply(matrix, matrix)
    mot_i = [sum(indirect[i]) for i in range(n)]
    dep_i = [sum(indirect[i][j] for i in range(n)) for j in range(n)]

    sectors = []
    for i in range(n):
        mot = mot_d[i]
        dep = dep_d[i]
        if mot >= avg_mot and dep >= avg_dep:
            sector = "Clau/Conflicte"
        elif mot >= avg_mot:
            sector = "Motriu"
        elif dep >= avg_dep:
            sector = "Resultant"
        else:
            sector = "Excluyent"
        code = variable_codes[i] if variable_codes and i < len(variable_codes) else str(i)
        sectors.append(
            {
                "index": i,
                "code": code,
                "sector": sector,
                "motricitat": mot,
                "dependencia": dep,
            }
        )

    key_sector = [s["index"] for s in sectors if s["sector"] == "Clau/Conflicte"]
    vb_idx = max(key_sector, key=lambda i: dep_d[i]) if key_sector else 0
    vr_idx = min(range(n), key=lambda i: abs(mot_d[i] - dep_d[i])) if n else 0

    return {
        "matrix_direct": matrix,
        "matrix_indirect": indirect,
        "motricitat_direct": mot_d,
        "dependencia_direct": dep_d,
        "motricitat_indirect": mot_i,
        "dependencia_indirect": dep_i,
        "sectors": sectors,
        "vb_index": vb_idx,
        "vr_index": vr_idx,
        "variable_blanc": {
            "index": vb_idx,
            "code": sectors[vb_idx]["code"] if vb_idx < len(sectors) else "",
        },
        "variable_risc": {
            "index": vr_idx,
            "code": sectors[vr_idx]["code"] if vr_idx < len(sectors) else "",
        },
    }
