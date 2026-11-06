"""Catalogo limitado de aquisicoes reais; nao baixa todas as bandas raster."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json, requests, time

ROOT=Path(__file__).resolve().parents[2]
CATALOG=json.loads((ROOT/'site-hibama/dist/data/catalogo.json').read_text(encoding='utf-8'))
OUTPUT=ROOT/'dados/amazonas/processados/imagens_catalogadas.json'
CACHE=ROOT/'dados/amazonas/brutos/stac';CACHE.mkdir(parents=True,exist_ok=True)
SOURCES=[
    ('Microsoft Planetary Computer','https://planetarycomputer.microsoft.com/api/stac/v1','sentinel-2-l2a',True),
    ('Microsoft Planetary Computer','https://planetarycomputer.microsoft.com/api/stac/v1','sentinel-1-rtc',False),
    ('Microsoft Planetary Computer','https://planetarycomputer.microsoft.com/api/stac/v1','landsat-c2-l2',True),
    ('INPE / Brazil Data Cube','https://data.inpe.br/bdc/stac/v1','S2-16D-2',False),
    ('INPE / Brazil Data Cube','https://data.inpe.br/bdc/stac/v1','CB4A-WPM-L4-DN-1',False),
]
def job(municipality,source):
    provider,endpoint,collection,optical=source
    path=CACHE/f'{municipality["code"]}_{collection}.json'
    if path.exists():data=json.loads(path.read_text(encoding='utf-8'))
    else:
        params={'collections':collection,'bbox':','.join(map(str,municipality['bounds'])),'datetime':'2026-01-01T00:00:00Z/2026-11-05T23:59:59Z','limit':2,'sortby':'-datetime'}
        if provider.startswith('INPE'):params.pop('sortby',None)
        if optical:params['query']=json.dumps({'eo:cloud_cover':{'lt':40}})
        for attempt in range(3):
            try:
                r=requests.get(endpoint+'/search',params=params,timeout=35);r.raise_for_status();data=r.json()
                if data.get('type')!='FeatureCollection':raise ValueError('Resposta STAC inesperada.')
                path.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8');break
            except Exception:
                if attempt==2:raise
                time.sleep(2)
    items=[]
    for feature in data['features']:
        p=feature.get('properties',{})
        items.append({'id':feature['id'],'collection':feature.get('collection',collection),'provider':provider,'municipality':municipality['code'],'municipality_name':municipality['name'],'datetime':p.get('datetime') or p.get('start_datetime'),'end_datetime':p.get('end_datetime'),'cloud_cover_tile_percent':p.get('eo:cloud_cover'),'bbox':feature.get('bbox'),'footprint':feature.get('geometry'),'assets':[{ 'name':key,'href':asset.get('href'),'type':asset.get('type'),'roles':asset.get('roles',[])} for key,asset in feature.get('assets',{}).items()],'source_url':next((l['href'] for l in feature.get('links',[]) if l.get('rel')=='self'),f'{endpoint}/collections/{collection}/items/{feature["id"]}')})
    return {'municipality':municipality['code'],'collection':collection,'items':items}

if __name__=='__main__':
    items=[];errors=[];completed=0
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures={pool.submit(job,m,s):(m,s) for m in CATALOG['municipalities'] for s in SOURCES}
        for future in as_completed(futures):
            m,s=futures[future]
            try:items.extend(future.result()['items'])
            except Exception as e:errors.append({'municipality':m['code'],'collection':s[2],'error':type(e).__name__})
            completed+=1
            if completed%25==0:print(json.dumps({'queries_completed':completed,'items':len(items),'errors':len(errors)}),flush=True)
    result={'generated_at_utc':datetime.now(timezone.utc).isoformat(),'scope':'Selecao de ate duas aquisicoes por municipio e colecao; nao e o acervo completo.','time_range':['2026-01-01','2026-11-05'],'query_count':completed,'municipalities':62,'max_items_per_municipality_collection':2,'raster_bands_downloaded':False,'cloud_note':'Percentual de nuvens e da cena/tile, nao da area do imovel; ainda e necessario aplicar mascara por pixel.','asset_access_note':'URLs de dados podem exigir assinatura temporaria do provedor; o coletor Python assina em memoria quando necessario.','items':items,'errors':errors}
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print(json.dumps({'status':'concluido','items':len(items),'queries':completed,'errors':len(errors)}),flush=True)
