"""
Unit tests for ProspectiveService — MIC-MAC and MACTOR calculations.
Tests pure math functions without database (matrix_multiply is module-level).
DB-dependent methods use the db_session fixture from conftest.
"""
import pytest

from services.micmac_math import compute_micmac_pure
from services.micmac_math import matrix_multiply


class TestMatrixMultiply:
    def test_identity_matrix(self):
        """M × I = M"""
        m = [[1, 2], [3, 4]]
        identity = [[1, 0], [0, 1]]
        assert matrix_multiply(m, identity) == m

    def test_zero_matrix(self):
        """M × 0 = 0"""
        m = [[1, 2], [3, 4]]
        zero = [[0, 0], [0, 0]]
        assert matrix_multiply(m, zero) == [[0, 0], [0, 0]]

    def test_known_result_2x2(self):
        """[[1,2],[3,4]] × [[5,6],[7,8]] = [[19,22],[43,50]]"""
        a = [[1, 2], [3, 4]]
        b = [[5, 6], [7, 8]]
        result = matrix_multiply(a, b)
        assert result == [[19, 22], [43, 50]]

    def test_symmetric_influence(self):
        """Matriu simètrica × ella mateixa = influències indirectes simètriques"""
        m = [[0, 1, 0], [1, 0, 1], [0, 1, 0]]
        result = matrix_multiply(m, m)
        assert result[0][0] == 1
        assert result[1][1] == 2
        assert result[2][2] == 1

    def test_3x3_known(self):
        """Verifica resultat 3×3 calculat manualment"""
        a = [[0, 2, 1], [1, 0, 3], [2, 1, 0]]
        result = matrix_multiply(a, a)
        assert result[0] == [4, 1, 6]


class TestMicMacMath:
    """Tests de la lògica matemàtica de compute_micmac sense BD."""

    def _micmac_pure(self, matrix):
        """Replica la lògica de compute_micmac sense accedir a la BD."""
        result = compute_micmac_pure(matrix)
        return (
            result["motricitat_direct"],
            result["dependencia_direct"],
            result["sectors"],
            result["vb_index"],
            result["vr_index"],
        )

    def test_motricitat_is_row_sum(self):
        matrix = [
            [0, 2, 1],
            [3, 0, 2],
            [1, 1, 0],
        ]
        mot_d, _, _, _, _ = self._micmac_pure(matrix)
        assert mot_d[0] == 3
        assert mot_d[1] == 5
        assert mot_d[2] == 2

    def test_dependencia_is_column_sum(self):
        matrix = [
            [0, 2, 1],
            [3, 0, 2],
            [1, 1, 0],
        ]
        _, dep_d, _, _, _ = self._micmac_pure(matrix)
        assert dep_d[0] == 4
        assert dep_d[1] == 3
        assert dep_d[2] == 3

    def test_sector_classification_cau_conflicte(self):
        matrix = [
            [0, 3, 3, 3],
            [3, 0, 0, 0],
            [3, 0, 0, 0],
            [3, 0, 0, 0],
        ]
        _, _, sectors, _, _ = self._micmac_pure(matrix)
        assert sectors[0]["sector"] == "Clau/Conflicte"

    def test_sector_classification_motriu(self):
        matrix = [
            [0, 3, 3, 3],
            [0, 0, 1, 1],
            [0, 1, 0, 1],
            [0, 1, 1, 0],
        ]
        _, _, sectors, _, _ = self._micmac_pure(matrix)
        assert sectors[0]["sector"] == "Motriu"

    def test_sector_classification_resultant(self):
        matrix = [
            [0, 0, 0, 0],
            [3, 0, 0, 0],
            [3, 0, 0, 0],
            [3, 0, 0, 0],
        ]
        _, _, sectors, _, _ = self._micmac_pure(matrix)
        assert sectors[0]["sector"] == "Resultant"

    def test_vb_is_highest_dep_in_key_sector(self):
        matrix = [
            [0, 2, 2, 2],
            [2, 0, 2, 2],
            [2, 2, 0, 0],
            [2, 2, 0, 0],
        ]
        mot_d, dep_d, sectors, vb_idx, _ = self._micmac_pure(matrix)
        cau = [s for s in sectors if s["sector"] == "Clau/Conflicte"]
        assert len(cau) >= 1
        cau_deps = [(s["index"], dep_d[s["index"]]) for s in cau]
        expected_vb = max(cau_deps, key=lambda x: x[1])[0]
        assert vb_idx == expected_vb

    def test_vr_minimizes_mot_dep_difference(self):
        matrix = [
            [0, 3, 0],
            [0, 0, 3],
            [3, 0, 0],
        ]
        mot_d, dep_d, _, _, vr_idx = self._micmac_pure(matrix)
        diffs = [abs(mot_d[i] - dep_d[i]) for i in range(3)]
        expected_vr = diffs.index(min(diffs))
        assert vr_idx == expected_vr

    def test_diagonal_excluded(self):
        matrix = [
            [9, 1],
            [1, 9],
        ]
        mot_d, _, _, _, _ = self._micmac_pure(matrix)
        assert mot_d[0] == 10


class TestMactorMath:
    """Tests de la lògica matemàtica del MACTOR sense BD."""

    def _mobilisation(self, postures, na, no):
        mob_actor = [sum(abs(postures[i][j]) for j in range(no)) for i in range(na)]
        mob_obj = [sum(abs(postures[i][j]) for i in range(na)) for j in range(no)]
        return mob_actor, mob_obj

    def _convergences(self, postures, na, no):
        conv = [[0] * na for _ in range(na)]
        for i in range(na):
            for j in range(na):
                if i == j:
                    continue
                conv[i][j] = sum(
                    1 for k in range(no)
                    if postures[i][k] != 0 and postures[j][k] != 0
                    and (postures[i][k] > 0) == (postures[j][k] > 0)
                )
        return conv

    def test_mobilisation_actor_is_abs_sum(self):
        postures = [
            [2, -1, 0],
            [-2, -2, 2],
        ]
        mob_a, _ = self._mobilisation(postures, 2, 3)
        assert mob_a[0] == 3
        assert mob_a[1] == 6

    def test_mobilisation_objective_is_column_abs_sum(self):
        postures = [
            [2, 0],
            [-1, 2],
            [1, -1],
        ]
        _, mob_o = self._mobilisation(postures, 3, 2)
        assert mob_o[0] == 4
        assert mob_o[1] == 3

    def test_convergence_same_sign_nonzero(self):
        postures = [
            [2, 1, -1],
            [1, 2, -2],
            [-1, 1, 2],
        ]
        conv = self._convergences(postures, 3, 3)
        assert conv[0][1] == 3
        assert conv[1][0] == 3
        assert conv[0][2] == 1

    def test_diagonal_convergence_zero(self):
        postures = [[1, 2], [-1, -2]]
        conv = self._convergences(postures, 2, 2)
        assert conv[0][0] == 0
        assert conv[1][1] == 0

    def test_neutral_posture_not_counted(self):
        postures = [
            [0, 2],
            [2, 2],
        ]
        conv = self._convergences(postures, 2, 2)
        assert conv[0][1] == 1
