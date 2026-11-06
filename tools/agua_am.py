"""Indicador de pressão sobre a água por município do Amazonas.

É um índice por regras, não uma medição: ele só olha para atividades que
costumam sujar ou assorear rios (mineração e desmatamento recente).
A turbidez medida por satélite ainda está em desenvolvimento.
"""
import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dist" / "data" / "ambiental" / "municipios"
SAIDA = RAIZ / "dist" / "data" / "agua" / "indicador.json"

# Data de referência do site (mesma do restante do painel).
REFERENCIA = "2026-11-05"
# Janela de 3 anos para "desmatamento recente".
DETER_DESDE = "2023-11-05"
PRODES_ANOS = (2023, 2024, 2025)

# Fases da ANM em que já existe extração autorizada (pedidos não contam).
ANM_EXTRACAO = {"LAVRA GARIMPEIRA", "CONCESSÃO DE LAVRA", "LICENCIAMENTO", "REGISTRO DE EXTRAÇÃO"}
DETER_DESMATAMENTO = {"DESMATAMENTO_CR", "DESMATAMENTO_VEG"}

PESOS = {"mineracao_deter": 0.35, "anm_extracao": 0.25, "desmatamento_recente": 0.40}


def contar(features):
    """Conta os sinais de pressão de um município a partir das feições."""
    c = {"mineracao_deter": 0, "anm_extracao": 0, "prodes_recente": 0, "deter_desmatamento_recente": 0}
    for f in features:
        p = f.get("properties") or {}
        camada, cat = p.get("layer"), p.get("category")
        if camada == "deter":
            if cat == "MINERACAO":
                c["mineracao_deter"] += 1
            elif cat in DETER_DESMATAMENTO and str(p.get("date") or "") >= DETER_DESDE:
                c["deter_desmatamento_recente"] += 1
        elif camada == "anm" and cat in ANM_EXTRACAO:
            c["anm_extracao"] += 1
        elif camada == "prodes" and p.get("year") in PRODES_ANOS:
            c["prodes_recente"] += 1
    c["desmatamento_recente"] = c["prodes_recente"] + c["deter_desmatamento_recente"]
    return c


def percentil(valor, todos):
    """0 quando não há sinal; senão, fração de municípios com valor <= este (0-100)."""
    if valor <= 0:
        return 0.0
    return 100.0 * sum(1 for v in todos if v <= valor) / len(todos)


def classe(score):
    return "baixa" if score < 34 else ("média" if score < 67 else "alta")


def calcular(contagens):
    """contagens: {codigo: dict de contar()}. Devolve {codigo: resultado}."""
    saida = {}
    colunas = {k: [c[k] for c in contagens.values()] for k in PESOS}
    for codigo, c in contagens.items():
        partes = {k: round(percentil(c[k], colunas[k]), 1) for k in PESOS}
        score = round(sum(PESOS[k] * partes[k] for k in PESOS))
        saida[codigo] = {"score": score, "classe": classe(score), "percentis": partes, "contagens": c}
    return saida


def main():
    arquivos = sorted(ENTRADA.glob("13?????.geojson"))
    if not arquivos:
        sys.exit("Nenhum GeoJSON municipal encontrado em " + str(ENTRADA))
    contagens = {}
    for arq in arquivos:
        contagens[arq.stem] = contar(json.loads(arq.read_text(encoding="utf-8"))["features"])
    doc = {
        "nome": "Indicador de pressão sobre a água",
        "aviso": "Estimativa por regras a partir de alertas de mineração e desmatamento. Medição de turbidez por satélite em desenvolvimento.",
        "referencia": REFERENCIA,
        "metodo": {
            "pesos": PESOS,
            "escala": "0-100, relativo entre os municípios do Amazonas (percentil de cada componente; 0 = nenhum sinal)",
            "classes": {"baixa": "<34", "média": "34-66", "alta": ">=67"},
            "janela_desmatamento": {"prodes_anos": list(PRODES_ANOS), "deter_desde": DETER_DESDE},
            "anm_fases": sorted(ANM_EXTRACAO),
            "fontes": ["INPE DETER (CC BY-SA 4.0)", "INPE PRODES (CC BY-SA 4.0)", "ANM SIGMINE"],
        },
        "municipios": calcular(contagens),
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(contagens)} municípios -> {SAIDA}")


if __name__ == "__main__":
    main()
