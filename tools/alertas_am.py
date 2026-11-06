"""Gera o arquivo leve de alertas do Amazonas para a tela inicial do mapa.

Pega os alertas DETER (INPE) dos últimos 6 meses de cada município, vira
um ponto (centro do polígono) com classe, data, área e prioridade.
Prioridade é uma regra simples por classe e idade do alerta, não é IA.
"""
import json
import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = RAIZ / "dist" / "data" / "ambiental" / "municipios"
NOMES = RAIZ / "dist" / "data" / "catalogo.json"
SAIDA = RAIZ / "dist" / "data" / "alertas" / "am-6meses.json"

REFERENCIA = "2026-11-05"
DESDE = "2026-05-05"        # 6 meses
RECENTE = "2026-10-06"      # últimos 30 dias
GRAVES = {"DESMATAMENTO_CR", "DESMATAMENTO_VEG", "MINERACAO"}
FOGO_DEGRADACAO = {"CICATRIZ_DE_QUEIMADA", "DEGRADACAO"}
ORDEM = ["critica", "alta", "media", "baixa"]


def prioridade(classe, data):
    if classe in GRAVES:
        return "critica" if data >= RECENTE else "alta"
    if classe in FOGO_DEGRADACAO:
        return "alta" if data >= RECENTE else "media"
    return "baixa"  # corte seletivo e outros


def aneis(geom):
    if not geom:
        return []
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    if geom["type"] == "MultiPolygon":
        return geom["coordinates"]
    return []


def centro_e_area(geom):
    """Centro médio dos vértices e área aproximada em ha (shoelace em graus)."""
    xs, ys, area = [], [], 0.0
    for poly in aneis(geom):
        for i, anel in enumerate(poly):
            a = 0.0
            for (x1, y1), (x2, y2) in zip(anel, anel[1:]):
                a += x1 * y2 - x2 * y1
                if i == 0:
                    xs.append(x1); ys.append(y1)
            a = abs(a) / 2
            area += a if i == 0 else -a  # buraco desconta
    if not xs:
        return None, 0.0
    lat = sum(ys) / len(ys)
    ha = max(area, 0) * (111320 ** 2) * math.cos(math.radians(lat)) / 10000
    return (round(sum(xs) / len(xs), 5), round(lat, 5)), round(ha, 2)


def main():
    nomes = {}
    try:
        nomes = {m["code"]: m["name"] for m in json.loads(NOMES.read_text(encoding="utf-8"))["municipalities"]}
    except (OSError, KeyError, ValueError):
        print("aviso: catálogo sem nomes, usando o código")
    arquivos = sorted(ENTRADA.glob("13?????.geojson"))
    if not arquivos:
        sys.exit("Nenhum GeoJSON municipal em " + str(ENTRADA))
    pontos, grupos = [], {}
    for arq in arquivos:
        cod = arq.stem
        for f in json.loads(arq.read_text(encoding="utf-8"))["features"]:
            p = f.get("properties") or {}
            data = str(p.get("date") or "")[:10]
            if p.get("layer") != "deter" or not data or data < DESDE or data > REFERENCIA:
                continue
            centro, ha = centro_e_area(f.get("geometry"))
            if not centro:
                continue
            pr = prioridade(p.get("category"), data)
            pontos.append([centro[0], centro[1], cod, p.get("category"), data, ha, pr])
            g = grupos.setdefault(cod, {"nome": nomes.get(cod, cod), "total": 0, "ha": 0.0, "x": 0.0, "y": 0.0,
                                        "por_prioridade": dict.fromkeys(ORDEM, 0)})
            g["total"] += 1; g["ha"] += ha; g["x"] += centro[0]; g["y"] += centro[1]
            g["por_prioridade"][pr] += 1
    for g in grupos.values():
        g["x"] = round(g["x"] / g["total"], 4); g["y"] = round(g["y"] / g["total"], 4); g["ha"] = round(g["ha"], 1)
        g["maior"] = next(k for k in ORDEM if g["por_prioridade"][k])
    doc = {
        "fonte": "INPE DETER (CC BY-SA 4.0)",
        "periodo": [DESDE, REFERENCIA],
        "aviso": "Alertas reais do DETER/INPE. Prioridade por regra (classe e idade do alerta). Detecção por IA em imagens em desenvolvimento.",
        "regra": {"critica": "desmatamento ou mineração nos últimos 30 dias", "alta": "desmatamento/mineração mais antigo, ou queimada/degradação nos últimos 30 dias",
                  "media": "queimada ou degradação mais antiga", "baixa": "corte seletivo"},
        "campos": ["lon", "lat", "municipio", "classe", "data", "area_ha", "prioridade"],
        "pontos": pontos,
        "municipios": grupos,
    }
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(len(pontos), "alertas em", len(grupos), "municípios ->", SAIDA, SAIDA.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
