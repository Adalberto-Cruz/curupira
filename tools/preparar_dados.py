"""Prepara recortes publicos para a interface; preserva a geometria de origem."""
from pathlib import Path
from collections import defaultdict, Counter
import json, zipfile, hashlib, shutil
import shapefile
from shapely.geometry import shape, mapping

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = ROOT.parent / 'dados/amazonas'
OUT = ROOT / 'dist/data'
for sub in ['cadastros', 'mapa', 'geometrias']:
    (OUT/sub).mkdir(parents=True, exist_ok=True)

def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':'), allow_nan=False), encoding='utf-8')

summary = json.loads((ORIGIN/'processados/AM_CAR_publico.resumo.json').read_text(encoding='utf-8'))
manifest = json.loads((ORIGIN/'brutos/sicar/extracao.json').read_text(encoding='utf-8'))
z = zipfile.ZipFile(ORIGIN/'brutos/ibge/AM_Municipios_2025.zip')
reader = shapefile.Reader(shp=z.open('AM_Municipios_2025.shp'), shx=z.open('AM_Municipios_2025.shx'), dbf=z.open('AM_Municipios_2025.dbf'), encoding='utf-8')
municipalities = {}
municipal_ufs = {}
municipal_features = []
for record in reader.iterShapeRecords():
    p = record.record.as_dict()
    code = str(p['CD_MUN'])
    municipal_ufs[code] = p['SIGLA_UF']
    geometry = shape(record.shape.__geo_interface__)
    bounds = list(geometry.bounds)
    municipalities[code] = {'code':code, 'name':p['NM_MUN'], 'area_km2':p['AREA_KM2'], 'bounds':bounds}
    municipal_features.append({'type':'Feature','geometry':mapping(geometry.simplify(.001, preserve_topology=True)), 'properties':{'code':code,'name':p['NM_MUN']}})

features = json.loads((ORIGIN/'processados/AM_CAR_publico.geojson').read_text(encoding='utf-8'))['features']
by_municipality = defaultdict(list)
for f in features:
    by_municipality[str(f['properties']['cod_municipio_ibge'])].append(f)

car_municipality_index={f['properties']['cod_imovel']:code for code,items in by_municipality.items() for f in items if f['properties']['cod_imovel'].split('-')[1]!=code}
write(OUT/'indice_car.json',car_municipality_index)
for code, items in by_municipality.items():
    records, display, originals = [], [], {}
    for f in items:
        p=f['properties']
        geometry=shape(f['geometry'])
        records.append({'code':p['cod_imovel'], 'status':p['status_imovel'], 'area':p['area'], 'condition':p['condicao'], 'created':p['dat_criacao'], 'updated':p['data_atualizacao'], 'type':p['tipo_imovel'], 'modules':p['m_fiscal'], 'bounds':list(geometry.bounds)})
        display.append({'type':'Feature','geometry':mapping(geometry.simplify(.00012,preserve_topology=True)), 'properties':{'code':p['cod_imovel'],'status':p['status_imovel']}})
        originals[p['cod_imovel']]=f['geometry']
    write(OUT/'cadastros'/f'{code}.json',records)
    write(OUT/'mapa'/f'{code}.geojson',{'type':'FeatureCollection','features':display})
    write(OUT/'geometrias'/f'{code}.json',originals)
    municipalities[code]['count']=len(items)
    municipalities[code]['statuses']=dict(Counter(f['properties']['status_imovel'] for f in items))
    municipalities[code]['conditions']=dict(Counter(f['properties']['condicao'] for f in items))
    print(code,municipalities[code]['name'].encode('ascii','replace').decode(),len(items),flush=True)

write(OUT/'municipios.geojson',{'type':'FeatureCollection','features':municipal_features})
write(OUT/'catalogo.json',{
    'car_ufs':sorted({municipal_ufs[code] for code, items in by_municipality.items() if items}),
    'state':'Amazonas','uf':'AM','snapshot_date':'2026-11-05','snapshot_utc':manifest['fim_utc'],
    'total':summary['registros'],'statuses':summary['status_cadastrais_como_publicados'],
    'conditions':summary['condicoes_como_publicadas'],'municipalities':sorted(municipalities.values(), key=lambda x:x['name']),
    'total_area_km2':round(sum(m['area_km2'] for m in municipalities.values()),3),
    'source_sha256':summary['sha256_geojson'],
    'sources':[
        {'name':'SICAR / CAR','scope':'Perímetros e atributos cadastrais públicos','status':'integrado','url':'https://consulta.car.gov.br/','date':'05/11/2026'},
        {'name':'IBGE','scope':'Malha municipal 2025 e áreas territoriais','status':'integrado','url':'https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/UFs/AM/','date':'Malha 2025'},
        {'name':'APP e Reserva Legal','scope':'Polígonos internos e demonstrativos do CAR','status':'pendente','url':'https://www.gov.br/car/pt-br','date':None},
        {'name':'INPE / TerraBrasilis','scope':'PRODES e alertas DETER','status':'pendente','url':'https://terrabrasilis.dpi.inpe.br/','date':None},
        {'name':'MapBiomas','scope':'Fogo, cobertura e vetores de degradação','status':'pendente','url':'https://brasil.mapbiomas.org/','date':None},
        {'name':'Ibama, Funai e CNUC','scope':'Embargos, terras indígenas e áreas protegidas','status':'pendente','url':'https://www.gov.br/ibama/','date':None},
        {'name':'Biomassa e carbono','scope':'Estimativas de estoque, densidade e incerteza','status':'pendente','url':'https://climate.esa.int/en/projects/biomass/','date':None}
    ]})
write(OUT/'proveniencia.json',{'extracao':manifest,'validacao':summary,'exibicao':{'municipios':'Geometria simplificada em 0,001 grau para visualização.','imoveis':'Geometria simplificada em 0,00012 grau para visualização.','original':'Geometria de origem preservada em geometrias/<codigo_municipal>.json.','topologia':'Não validada; não constitui certificação ambiental.'}})
files=list(OUT.rglob('*'))
largest=max((p for p in files if p.is_file()),key=lambda p:p.stat().st_size)
assert len(municipalities)==62 and sum(m['count'] for m in municipalities.values())==98982
assert largest.stat().st_size < 25*1024*1024, f'Arquivo excede o limite: {largest}'
print(json.dumps({'municipios':len(municipalities),'registros':98982,'maior_arquivo':str(largest.relative_to(ROOT)),'maior_bytes':largest.stat().st_size,'total_bytes':sum(p.stat().st_size for p in files if p.is_file())}))
