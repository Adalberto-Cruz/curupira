"""Coleta vetores publicos do Amazonas com paginacao e proveniencia."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib, json, time, xml.etree.ElementTree as ET
import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'dados/amazonas/brutos/ambiental'
OUT.mkdir(parents=True, exist_ok=True)
ENDPOINT='https://terrabrasilis.dpi.inpe.br/geoserver/ows'

def get(url, params=None):
    for attempt in range(3):
        try:
            response=requests.get(url,params=params,timeout=90)
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt==2: raise
            time.sleep(2*(attempt+1))

def write(path,value):
    path.write_text(json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')

def wfs(name, layer, cql, sort, fields):
    directory=OUT/name
    directory.mkdir(exist_ok=True)
    params={'service':'WFS','version':'2.0.0','request':'GetFeature','typeNames':layer,'CQL_FILTER':cql}
    hits=get(ENDPOINT,{**params,'resultType':'hits'})
    (directory/'contagem_inicial.xml').write_bytes(hits.content)
    count=int(ET.fromstring(hits.content).attrib['numberMatched'])
    features=[];seen=set();offset=0;sources=[]
    while offset<count:
        path=directory/f'lote_{offset:06}.geojson'
        query={**params,'outputFormat':'application/json','srsName':'EPSG:4326','count':2000,'startIndex':offset,'sortBy':sort,'propertyName':','.join(fields)}
        if path.exists(): payload=path.read_bytes()
        else:
            response=get(ENDPOINT,query)
            payload=response.content
            parsed=response.json()
            if parsed.get('type')!='FeatureCollection': raise ValueError(f'Resposta inesperada: {name}')
            path.write_bytes(payload)
        data=json.loads(payload)
        batch=data['features']
        if not batch: raise ValueError(f'Paginacao truncada: {name}, offset {offset}')
        if int(data.get('numberMatched',count))!=count: raise ValueError('Contagem mudou durante a extracao.')
        for feature in batch:
            if feature['id'] in seen: raise ValueError(f'ID duplicado: {feature["id"]}')
            seen.add(feature['id'])
            features.append(feature)
        sources.append({'file':str(path.relative_to(OUT)),'request_url':requests.Request('GET',ENDPOINT,params=query).prepare().url,'sha256':hashlib.sha256(payload).hexdigest(),'count':len(batch)})
        offset+=len(batch)
        print(json.dumps({'dataset':name,'downloaded':offset,'total':count}),flush=True)
    final=get(ENDPOINT,{**params,'resultType':'hits'})
    if int(ET.fromstring(final.content).attrib['numberMatched'])!=count: raise ValueError('Contagem final divergente.')
    path=OUT/f'{name}.geojson';write(path,{'type':'FeatureCollection','features':features})
    write(OUT/f'{name}.fonte.json',{'provider':'INPE / TerraBrasilis','endpoint':ENDPOINT,'layer':layer,'filter':cql,'count':count,'unique_ids':len(seen),'downloaded_at_utc':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pages':sources})
    return {'dataset':name,'count':count,'status':'concluido'}

def embargos():
    endpoint='https://gis.ipaam.am.gov.br/server/rest/services/AREAS_EMBARGADAS_IBAMA_AM_PAMGIA/FeatureServer/0/query'
    count=get(endpoint,{'where':'1=1','returnCountOnly':'true','f':'json'}).json()['count']
    fields='objectid,seq_tad,num_tad,serie_tad,uf,cod_municipio,municipio,dat_embargo,dat_ult_alteracao,qtd_area_embargada,des_infracao'
    features=[];seen=set();offset=0;sources=[]
    directory=OUT/'embargos_ipaam';directory.mkdir(exist_ok=True)
    while offset<count:
        params={'where':'1=1','outFields':fields,'returnGeometry':'true','outSR':4326,'orderByFields':'objectid ASC','resultOffset':offset,'resultRecordCount':2000,'f':'geojson'}
        path=directory/f'lote_{offset:06}.geojson'
        if path.exists(): payload=path.read_bytes()
        else:
            response=get(endpoint,params);payload=response.content;data=response.json()
            if data.get('type')!='FeatureCollection': raise ValueError('Resposta ArcGIS inesperada.')
            path.write_bytes(payload)
        data=json.loads(payload);batch=data['features']
        if not batch: raise ValueError('Paginacao de embargos truncada.')
        for f in batch:
            ident=f['properties']['objectid']
            if ident in seen: raise ValueError('ID de embargo duplicado.')
            seen.add(ident);features.append(f)
        offset+=len(batch);sources.append({'file':str(path.relative_to(OUT)),'count':len(batch),'sha256':hashlib.sha256(payload).hexdigest()})
        print(json.dumps({'dataset':'embargos_ipaam','downloaded':offset,'total':count}),flush=True)
    if get(endpoint,{'where':'1=1','returnCountOnly':'true','f':'json'}).json()['count']!=count: raise ValueError('A contagem de embargos mudou.')
    path=OUT/'embargos_ipaam.geojson';write(path,{'type':'FeatureCollection','features':features})
    write(OUT/'embargos_ipaam.fonte.json',{'provider':'IPAAM - republicacao da base Ibama/Pamgia','endpoint':endpoint,'source_reference':'https://gis.ipaam.am.gov.br/server/rest/services/AREAS_EMBARGADAS_IBAMA_AM_PAMGIA/FeatureServer/0/iteminfo','count':count,'downloaded_at_utc':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'fields':fields,'pages':sources,'limitation':'A copia do IPAAM nao substitui a consulta vigente no Ibama; a intersecao geometrica nao atribui autoria da infracao.'})
    return {'dataset':'embargos_ipaam','count':count,'status':'concluido'}

if __name__=='__main__':
    jobs=[
        lambda:wfs('prodes_am','prodes-legal-amz:yearly_deforestation',"state='AM' AND year>=2008",'fid A',['fid','uuid','state','year','area_km','main_class','class_name','image_date','satellite','sensor','geom']),
        lambda:wfs('deter_am','deter-amz:deter_amz',"uf='AM'",'gid A',['gid','classname','view_date','sensor','satellite','areamunkm','municipality','mun_geocod','uf','publish_month','geom']),
        embargos]
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures=[pool.submit(job) for job in jobs]
        for future in futures:
            try: print(json.dumps(future.result()),flush=True)
            except Exception as exc: print(json.dumps({'error':str(exc)}),flush=True)
