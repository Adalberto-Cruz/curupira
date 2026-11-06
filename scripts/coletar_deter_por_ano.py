"""Evita tratar gid historico do DETER como identificador global unico."""
from pathlib import Path
from datetime import datetime, timezone
import json,hashlib,requests,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'dados/amazonas/brutos/ambiental'
ENDPOINT='https://terrabrasilis.dpi.inpe.br/geoserver/ows'
BASE={'service':'WFS','version':'2.0.0','request':'GetFeature','typeNames':'deter-amz:deter_amz'}
def call(extra):
    r=requests.get(ENDPOINT,params={**BASE,**extra},timeout=120);r.raise_for_status();return r
def hits(cql):return int(ET.fromstring(call({'CQL_FILTER':cql,'resultType':'hits'}).content).attrib['numberMatched'])
def first(order):return call({'CQL_FILTER':"uf='AM'",'outputFormat':'application/json','count':1,'sortBy':'view_date '+order}).json()['features'][0]['properties']['view_date']

if __name__=='__main__':
    low,high=first('A'),first('D');total=hits("uf='AM'")
    path=OUT/'deter_por_ano';path.mkdir(exist_ok=True)
    features=[];seen=set();sources=[]
    fields='gid,classname,view_date,sensor,satellite,areamunkm,municipality,mun_geocod,uf,publish_month,uc,areauckm,geom'
    for year in range(int(low[:4]),int(high[:4])+1):
        cql=f"uf='AM' AND view_date>='{year}-01-01' AND view_date<'{year+1}-01-01'"
        expected=hits(cql)
        if not expected:continue
        p=path/f'{year}.geojson'
        query={'CQL_FILTER':cql,'count':expected,'outputFormat':'application/json','srsName':'EPSG:4326','sortBy':'view_date A,gid A,mun_geocod A','propertyName':fields}
        if not p.exists():
            r=call(query);d=r.json()
            if d.get('type')!='FeatureCollection':raise ValueError('Resposta inesperada.')
            p.write_bytes(r.content)
        d=json.loads(p.read_text(encoding='utf-8'))
        if len(d['features'])!=expected:raise ValueError(f'Exportacao truncada no ano {year}: {len(d["features"])}/{expected}')
        for f in d['features']:
            source_id=f['id']
            key=hashlib.sha256(json.dumps({'properties':f['properties'],'geometry':f['geometry']},sort_keys=True,separators=(',',':')).encode()).hexdigest()
            # Mantem cada registro da fonte, inclusive eventual repeticao exata; nunca soma areas aqui.
            f['properties']['source_feature_id']=source_id
            f['properties']['record_sha256']=key
            f['id']='deter_'+key[:24]
            seen.add(key);features.append(f)
        sources.append({'year':year,'count':expected,'file':str(p.relative_to(OUT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'url':requests.Request('GET',ENDPOINT,params={**BASE,**query}).prepare().url})
        print(json.dumps({'dataset':'deter_am','year':year,'records':expected,'downloaded':len(features),'total':total}),flush=True)
    if len(features)!=total or hits("uf='AM'")!=total:raise ValueError('As particoes anuais nao cobrem a contagem da fonte.')
    output=OUT/'deter_am.geojson';output.write_text(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    (OUT/'deter_am.fonte.json').write_text(json.dumps({'provider':'INPE / TerraBrasilis','layer':'deter-amz:deter_amz','count':len(features),'unique_record_hashes':len(seen),'period':[low,high],'downloaded_at_utc':datetime.now(timezone.utc).isoformat(),'sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'partitions':sources,'limitation':'gid historico e reutilizado entre anos. Contagens referem-se a registros da camada; totais de area exigem uniao geometrica e recorte espacial. Alerta nao equivale a infracao confirmada.'},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'dataset':'deter_am','status':'concluido','count':len(features),'unique_hashes':len(seen)}),flush=True)
