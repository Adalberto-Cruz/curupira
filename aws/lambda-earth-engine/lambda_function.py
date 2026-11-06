"""Lambda do Curupira: gera a camada Sentinel-2 (cor natural ou NDVI) de um município.

Mesma lógica do servidor local, só que rodando na AWS atrás do API Gateway.
O login do Earth Engine vem da variável EE_CREDENTIALS (conteúdo do arquivo
de credenciais do earthengine) e o projeto vem de GOOGLE_CLOUD_PROJECT.
"""
import json
import os
from datetime import date, timedelta
from pathlib import Path

ee = None
erro_inicio = None
MUNICIPIOS = {}


def iniciar():
    """Liga o Earth Engine uma vez por container (as chamadas seguintes reaproveitam)."""
    global ee, erro_inicio
    if ee is not None or erro_inicio:
        return
    try:
        cred = os.environ.get("EE_CREDENTIALS", "")
        projeto = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        if not cred or not projeto:
            raise RuntimeError("faltam EE_CREDENTIALS ou GOOGLE_CLOUD_PROJECT")
        json.loads(cred)  # confere se é JSON válido antes de gravar
        # a biblioteca procura o arquivo em ~/.config/earthengine; na Lambda só /tmp é gravável
        os.environ["HOME"] = "/tmp"
        pasta = Path("/tmp/.config/earthengine")
        pasta.mkdir(parents=True, exist_ok=True)
        (pasta / "credentials").write_text(cred, encoding="utf-8")
        import ee as _ee
        _ee.Initialize(project=projeto)
        geo = json.loads((Path(__file__).parent / "municipios.geojson").read_text(encoding="utf-8"))
        for f in geo.get("features", []):
            MUNICIPIOS[str(f["properties"].get("code"))] = f
        if not MUNICIPIOS:
            raise RuntimeError("malha municipal vazia")
        ee = _ee
    except Exception as e:  # guarda o erro para não tentar de novo a cada pedido
        erro_inicio = str(e)
        print("Falha ao iniciar Earth Engine:", type(e).__name__, erro_inicio)


def resposta(status, dados):
    return {"statusCode": status,
            "headers": {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"},
            "body": json.dumps(dados, ensure_ascii=False)}


def handler(event, context):
    iniciar()
    if ee is None:
        return resposta(503, {"error": "Serviço de imagens indisponível. Earth Engine não configurado na Lambda."})
    q = (event or {}).get("queryStringParameters") or {}
    try:
        inicio = date.fromisoformat(q.get("start", ""))
        fim = date.fromisoformat(q.get("end", ""))
        if inicio > fim or (fim - inicio).days > 366:
            raise ValueError
        produto = q.get("product", "rgb")
        nuvem = int(q.get("cloud", "30"))
        if produto not in ("rgb", "ndvi") or not 0 <= nuvem <= 100:
            raise ValueError
        feature = MUNICIPIOS.get(str(q.get("municipio", "")))
        if not feature:
            raise ValueError
    except (ValueError, TypeError):
        return resposta(400, {"error": "Revise município, datas (até 366 dias), produto e limite de nuvens."})
    try:
        regiao = ee.Geometry(feature["geometry"])
        colecao = (ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED").filterBounds(regiao)
                   .filterDate(inicio.isoformat(), (fim + timedelta(days=1)).isoformat())
                   .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", nuvem)))
        total = colecao.size().getInfo()
        if not total:
            return resposta(422, {"error": "Nenhuma cena atende ao período e ao limite de nuvens. Amplie os filtros."})

        def mascara(img):
            # tira nuvem, sombra e pixel sem dado usando a classificação SCL do próprio Sentinel-2
            scl = img.select("SCL")
            ok = (scl.neq(0).And(scl.neq(1)).And(scl.neq(3)).And(scl.neq(8))
                  .And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11)))
            return img.updateMask(ok).select(["B2", "B3", "B4", "B8"]).multiply(.0001)

        imagem = colecao.map(mascara).median().clip(regiao)
        vis = {"bands": ["B4", "B3", "B2"], "min": 0, "max": .3}
        if produto == "ndvi":
            imagem = imagem.normalizedDifference(["B8", "B4"])
            vis = {"min": -1, "max": 1, "palette": ["70452b", "e6d9a4", "277441"]}
        mapa = imagem.getMapId(vis)
        return resposta(200, {"url": mapa["tile_fetcher"].url_format, "count": total,
                              "start": inicio.isoformat(), "end": fim.isoformat(), "product": produto})
    except Exception as e:
        print("Erro Earth Engine:", type(e).__name__, str(e)[:300])
        return resposta(502, {"error": "Google Earth Engine não concluiu a consulta. Tente um período menor."})
