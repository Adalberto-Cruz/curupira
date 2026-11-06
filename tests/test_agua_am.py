"""Testes da regra do indicador de pressão sobre a água."""
import sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import agua_am


def f(layer, category, **kw):
    return {"properties": {"layer": layer, "category": category, **kw}}


class TestAgua(unittest.TestCase):
    def test_contar_respeita_janelas_e_fases(self):
        c = agua_am.contar([
            f("deter", "MINERACAO", date="2018-01-01"),
            f("deter", "DESMATAMENTO_CR", date="2024-05-01"),
            f("deter", "DESMATAMENTO_CR", date="2020-05-01"),  # fora da janela
            f("anm", "LAVRA GARIMPEIRA"),
            f("anm", "REQUERIMENTO DE PESQUISA"),  # pedido não conta
            f("prodes", "d2024", year=2024),
            f("prodes", "d2015", year=2015),  # antigo
            {"properties": {}},  # feição sem camada
        ])
        self.assertEqual(c["mineracao_deter"], 1)
        self.assertEqual(c["anm_extracao"], 1)
        self.assertEqual(c["desmatamento_recente"], 2)

    def test_zero_sinal_da_zero(self):
        base = {"mineracao_deter": 0, "anm_extracao": 0, "desmatamento_recente": 0}
        r = agua_am.calcular({"a": dict(base), "b": {**base, "desmatamento_recente": 5}})
        self.assertEqual(r["a"]["score"], 0)
        self.assertEqual(r["a"]["classe"], "baixa")
        self.assertEqual(r["b"]["score"], 40)

    def test_maximo_em_tudo_da_100(self):
        r = agua_am.calcular({"a": {"mineracao_deter": 3, "anm_extracao": 3, "desmatamento_recente": 3},
                              "b": {"mineracao_deter": 1, "anm_extracao": 1, "desmatamento_recente": 1}})
        self.assertEqual(r["a"]["score"], 100)
        self.assertEqual(r["a"]["classe"], "alta")


if __name__ == "__main__":
    unittest.main()
