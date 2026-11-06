"""Recortes territoriais e intersecoes preliminares. Nao avalia legalidade."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import json,zipfile,hashlib,shapefile
from shapely.geometry import shape,mapping
from shapely import make_valid, prepare
from shapely.strtree import STRtree
from paleta import load_palette

ROOT=Path(__file__).resolve().parents[1];TASK=ROOT.parent
RAW=TASK/'dados/amazonas/brutos/ambiental';OUT=ROOT/'dist/data/ambiental'
try:palette=load_palette(OUT/'paleta.json')
except ValueError as error:raise SystemExit(str(error))
for directory in ['municipios','intersecoes']:(OUT/directory).mkdir(parents=True,exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,d):p.write_text(json.dumps(d,ensure_ascii=False,separators=(',',':'),allow_nan=False),encoding='utf-8')
def safe(v):return str(v or '')
def stable(v):return hashlib.sha256(safe(v).encode()).hexdigest()[:20]
def stamp(value):
    if isinstance(value,(int,float)):
        return datetime.fromtimestamp(value/1000,timezone.utc).date().isoformat()
    return safe(value)[:10]

catalog=read(ROOT/'dist/data/catalogo.json');mcodes=[m['code'] for m in catalog['municipalities']]
z=zipfile.ZipFile(TASK/'dados/amazonas/brutos/ibge/AM_Municipios_2025.zip')
r=shapefile.Reader(shp=z.open('AM_Municipios_2025.shp'),shx=z.open('AM_Municipios_2025.shx'),dbf=z.open('AM_Municipios_2025.dbf'),encoding='utf-8')
municipal_geometries={sr.record.as_dict()['CD_MUN']:make_valid(shape(sr.shape.__geo_interface__)) for sr in r.iterShapeRecords()}
mtree=STRtree([municipal_geometries[c] for c in mcodes])

specs=[
 {'id':'ti','name':'Terras Indígenas','provider':'Funai','url':'https://www.gov.br/funai/pt-br/atuacao/terras-indigenas/geoprocessamento-e-mapas','kind':'Limite oficial','note':'Fases e limites publicados pela Funai. Interseção não determina, isoladamente, irregularidade ou titularidade.'},
 {'id':'anm','name':'Processos minerários','provider':'ANM / SIGMINE','url':'https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/','kind':'Registro administrativo','note':'Processo ou título minerário não comprova lavra em operação, garimpo observado nem licença ambiental.'},
 {'id':'embargos','name':'Áreas embargadas','provider':'IPAAM / cópia Ibama–Pamgia','url':'https://gis.ipaam.am.gov.br/server/rest/services/AREAS_EMBARGADAS_IBAMA_AM_PAMGIA/FeatureServer/0','kind':'Registro republicado','note':'Cópia publicada pelo IPAAM. Consulte a vigência no Ibama. Interseção geométrica não atribui autoria da infração.'},
 {'id':'prodes','name':'Supressão PRODES','provider':'INPE / TerraBrasilis','url':'https://data.inpe.br/biomasbr/prodes-monitoramento-anual-da-supressao-de-vegetacao-nativa/','kind':'Mapeamento oficial','note':'Incrementos da camada Amazônia Legal, ano>=2008. Contagens são polígonos, não taxas municipais. Não identifica, sozinho, o uso posterior ou a legalidade.'},
 {'id':'deter','name':'Alertas DETER','provider':'INPE / TerraBrasilis','url':'https://terrabrasilis.dpi.inpe.br/','kind':'Alerta de alteração','note':'Alerta não é infração confirmada. gid histórico é reutilizado entre anos; registros têm identificador composto. Áreas sobrepostas não são somadas.'},
 {'id':'focos','name':'Focos de calor','provider':'INPE / Programa Queimadas','url':'https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/diario/Brasil/','kind':'Detecção de fogo ativo','note':'29/10 a 04/11/2026; todos os satélites. Detecções não equivalem a incêndios únicos nem a hectares queimados. A localização tem incerteza dependente do sensor.'},
]

def raw_features(layer):
    if layer=='anm':
        z=zipfile.ZipFile(RAW/'anm_am.zip');stem=next(n[:-4] for n in z.namelist() if n.lower().endswith('.shp'))
        r=shapefile.Reader(shp=z.open(stem+'.shp'),shx=z.open(stem+'.shx'),dbf=z.open(stem+'.dbf'),encoding='utf-8')
        for sr in r.iterShapeRecords():yield {'type':'Feature','geometry':sr.shape.__geo_interface__,'properties':sr.record.as_dict()}
    else:
        filename={'ti':'funai_am.json','embargos':'embargos_ipaam.geojson','prodes':'prodes_am.geojson','deter':'deter_am.geojson','focos':'focos/AM_focos_20261029_20261104.geojson'}[layer]
        yield from read(RAW/filename)['features']

def properties(layer,f):
    p=f['properties']
    if layer=='ti':return {'record_id':'ti_'+safe(p['terrai_codigo']),'title':p['terrai_nome'],'category':p.get('fase_ti'),'date':p.get('data_atualizacao'),'code':p['terrai_codigo'],'modality':p.get('modalidade_ti')}
    if layer=='anm':return {'record_id':'anm_'+stable(p.get('ID') or p['PROCESSO'])+'_'+stable(p['PROCESSO']),'title':p['PROCESSO'],'category':p.get('FASE'),'date':None,'mineral':p.get('SUBS'),'use':p.get('USO'),'declared_area_ha':p.get('AREA_HA')}
    if layer=='embargos':return {'record_id':'embargo_'+safe(p['objectid']),'title':safe(p.get('num_tad'))+safe(p.get('serie_tad')),'category':'Área embargada publicada','date':stamp(p.get('dat_embargo')),'updated':stamp(p.get('dat_ult_alteracao')),'municipality_source':p.get('municipio'),'term_sequence':p.get('seq_tad'),'declared_area_ha':p.get('qtd_area_embargada')}
    if layer=='prodes':return {'record_id':'prodes_'+safe(p.get('uuid') or p['fid']),'title':'PRODES '+safe(p.get('year')),'category':p.get('class_name'),'date':p.get('image_date'),'year':p.get('year'),'source_id':p.get('uuid'),'satellite':p.get('satellite')}
    if layer=='deter':return {'record_id':f['id'],'title':safe(p.get('classname')),'category':p.get('classname'),'date':p.get('view_date'),'year':int(p['view_date'][:4]),'source_id':p.get('gid'),'satellite':p.get('satellite'),'municipality_source':p.get('municipality')}
    return {'record_id':'foco_'+safe(p['id']),'title':p.get('satelite'),'category':'Foco de calor','date':p.get('datetime_utc'),'year':2026,'municipality_source':p.get('municipio'),'frp':p.get('frp')}

for geometry in municipal_geometries.values():prepare(geometry)
per_muni=defaultdict(list)
overlaps={c:{} for c in mcodes}
counts={c:{} for c in mcodes}
for spec in specs:
    layer=spec['id'];originals=[];metadata=[];source_count=0;invalid=0;empty=0;outside=0
    for feature in raw_features(layer):
        source_count+=1
        if not feature.get('geometry'):empty+=1;continue
        g=shape(feature['geometry'])
        repaired=not g.is_valid
        if repaired:g=make_valid(g,method='structure');invalid+=1
        if g.is_empty:empty+=1;continue
        matches=[i for i in mtree.query(g) if municipal_geometries[mcodes[int(i)]].intersects(g)]
        if not len(matches):outside+=1;continue
        p={**properties(layer,feature),'layer':layer,'geometry_repaired_for_processing':repaired}
        originals.append(g);metadata.append(p)
        display={'type':'Feature','geometry':mapping(g if layer=='focos' else g.simplify(.00015,preserve_topology=True)),'properties':p}
        for i in matches:per_muni[mcodes[int(i)]].append(display)
    tree=STRtree(originals)
    counts_layer=Counter()
    for i,code in enumerate(mcodes):
        counts[code][layer]=sum(f['properties']['layer']==layer for f in per_muni[code])
        geos=read(ROOT/'dist/data/geometrias'/f'{code}.json')
        for car_code,geometry in geos.items():
            g=shape(geometry)
            if not g.is_valid:g=make_valid(g,method='structure')
            hits=tree.query(g,predicate='intersects')
            if not len(hits):continue
            records=[metadata[int(j)] for j in hits]
            # Previa limitada; todas as feicoes estao disponiveis no recorte municipal.
            overlaps[code].setdefault(car_code,{})[layer]={'count':len(records),'records':records[:20],'preview_limited':len(records)>20}
            counts_layer[code]+=1
        if (i+1)%15==0:print(json.dumps({'layer':layer,'municipalities_processed':i+1}),flush=True)
    dates=sorted(safe(p.get('date')) for p in metadata if p.get('date'))
    years=Counter(p['year'] for p in metadata if p.get('year'))
    spec.update({'source_records':source_count,'spatial_records':len(originals),'source_geometries_repaired':invalid,'empty_geometries':empty,'outside_municipal_mesh':outside,'cars_intersecting':sum(counts_layer.values()),'period_years':sorted(years),'counts_by_year':dict(years),'collected_on':'2026-11-05'})
    print(json.dumps({'layer':layer,'source_records':source_count,'spatial_records':len(originals),'cars_intersecting':spec['cars_intersecting'],'repaired':invalid}),flush=True)

for code in mcodes:
    write(OUT/'municipios'/f'{code}.geojson',{'type':'FeatureCollection','features':per_muni[code]})
    write(OUT/'intersecoes'/f'{code}.json',overlaps[code])
write(OUT/'catalogo.json',{'generated_at_utc':datetime.now(timezone.utc).isoformat(),'layers':specs,'palette_file':'paleta.json','counts_by_municipality':counts,'method':'Intersecoes com geometria de origem do CAR e malha IBGE2025. Geometrias invalidas sao reparadas com make_valid (structure) apenas na copia de processamento e sinalizadas. Sem buffer de posicao para focos; nao e atribuicao causal nem avaliacao juridica.','display_geometry':'Simplificada em0,00015grau. Indices foram calculados com geometrias de origem/reparadas.','preview_record_limit':20,'coverage_note':'Recortes sao por intersecao; uma feicao pode aparecer em mais de um municipio. Contagens municipais nao devem ser somadas como total estadual.'})
largest=max((p for p in OUT.rglob('*') if p.is_file()),key=lambda p:p.stat().st_size)
assert largest.stat().st_size<25*1024*1024,f'Arquivo muito grande: {largest}'
print(json.dumps({'status':'concluido','largest_file':str(largest.relative_to(OUT)),'largest_bytes':largest.stat().st_size}),flush=True)
