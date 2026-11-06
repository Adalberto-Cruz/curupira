"""Índice de atenção AM por regras, a partir de cruzamentos e fontes locais.

Não coleta dados nem modifica os cruzamentos. Resultados gerados ficam fora
do commit; somente código/configuração são versionados.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import zipfile

import shapefile
from pyproj import Geod
import shapely
from shapely.geometry import Polygon, shape
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
CAR = re.compile(r'AM-13\d{5}-[0-9A-F]{32}')
GEOD = Geod(ellps='GRS80')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
        stream.write('\n')


def clean(geometry):
    geometry = shapely.force_2d(geometry)
    if not geometry.is_valid:
        geometry = shapely.make_valid(geometry, method='structure')
    return geometry


def polygonal(geometry):
    if geometry.geom_type in {'Polygon', 'MultiPolygon'}:
        return geometry
    return shapely.union_all([polygonal(g) for g in geometry.geoms]) if hasattr(geometry, 'geoms') else Polygon()


def hectares(geometry):
    geometry = polygonal(geometry)
    if geometry.is_empty:
        return 0.0
    parts = [geometry] if geometry.geom_type == 'Polygon' else list(geometry.geoms)
    return sum(abs(GEOD.geometry_area_perimeter(shapely.orient_polygons(g))[0]) for g in parts) / 10000


def prodes_metrics(car, geometries):
    total = hectares(car)
    if total <= 0 or not math.isfinite(total):
        raise ValueError('CAR sem área geodésica utilizável.')
    covered = hectares(car.intersection(shapely.union_all(geometries))) if geometries else 0.0
    # A fração do escore é limitada; a medida original fica disponível para auditoria.
    return total, covered, min(1.0, max(0.0, covered / total))


def validate_weights(w):
    if w['scope'] != 'AM' or w['critical_layers'] != ['ti', 'embargos'] or w['critical_score'] != 100:
        raise ValueError('Escopo/travas incompatíveis com a configuração aprovada.')
    values = [w['prodes']['max_points'], w['prodes']['fraction_for_max'],
              w['deter']['max_points'], *w['deter']['class_points'].values(),
              w['anm']['points_per_record'], w['anm']['max_points'],
              w['focos']['points_per_record'], w['focos']['max_points']]
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or not math.isfinite(v) or v < 0 for v in values):
        raise ValueError('Pesos devem ser números finitos não negativos.')
    if w['prodes']['fraction_for_max'] <= 0 or sum(w[k]['max_points'] for k in ['prodes','deter','anm','focos']) > 100:
        raise ValueError('Normalização/soma máxima dos pesos inválida.')
    if w['ranking'] != {'limit':20,'excluded_statuses':['CA'],'minimum_score_exclusive':0}:
        raise ValueError('Ranking deve usar top 20 positivo, excluindo CA.')


def score(overlaps, fraction, classes, w):
    validate_weights(w)
    if not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError('Fração PRODES fora de 0..1.')
    counts = {}
    for layer in ['ti','embargos','prodes','deter','anm','focos']:
        value = overlaps.get(layer, {}).get('count', 0)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError('Contagem inválida: ' + layer)
        counts[layer] = value
    if any(not isinstance(n,int) or isinstance(n,bool) or n < 0 for n in classes.values()):
        raise ValueError('Contagem DETER por classe inválida.')
    if sum(classes.values()) != counts['deter']:
        raise ValueError('Classes DETER não representam a contagem completa.')
    if any(c not in w['deter']['class_points'] for c in classes):
        raise ValueError('Classe DETER não configurada.')
    points = {
        'prodes': round(w['prodes']['max_points'] * min(1, fraction / w['prodes']['fraction_for_max']), 1),
        'deter': round(min(w['deter']['max_points'], sum(w['deter']['class_points'][c] * n for c,n in classes.items())), 1),
        'anm': round(min(w['anm']['max_points'], counts['anm'] * w['anm']['points_per_record']), 1),
        'focos': round(min(w['focos']['max_points'], counts['focos'] * w['focos']['points_per_record']), 1),
    }
    base = round(sum(points.values()), 1)
    locks = [layer for layer in w['critical_layers'] if counts[layer] > 0]
    value = 100 if locks else base
    points['trava'] = round(value - base, 1)
    return {'nota': value, 'travas': locks, 'contribuicoes': points, 'contagens': counts, 'classes_deter': dict(sorted(classes.items()))}


def rank(rows, records, weights):
    statuses = {r['code']: r['status'] for r in records}
    eligible = [code for code, row in rows.items() if statuses[code] not in weights['ranking']['excluded_statuses']
                and row['nota'] > weights['ranking']['minimum_score_exclusive']]
    return sorted(eligible, key=lambda code: (-rows[code]['nota'], code))[:weights['ranking']['limit']]


def load_source(path, layer, territory=None):
    geometries, ids, classes = [], {}, {}
    if territory is not None:
        shapely.prepare(territory.geometries)
    for f in read(path)['features']:
        if not f.get('geometry'):
            continue
        geometry = clean(shape(f['geometry']))
        if geometry.is_empty:
            continue
        if territory is not None and not any(territory.geometries[int(i)].intersects(geometry) for i in territory.query(geometry)):
            continue
        props = f['properties']
        identifier = 'prodes_' + str(props.get('uuid') or props['fid']) if layer == 'prodes' else f['id']
        if identifier in ids:
            raise ValueError('Identificador repetido na fonte ' + layer)
        ids[identifier] = len(geometries)
        geometries.append(geometry)
        if layer == 'deter':
            classes[len(geometries)-1] = props['classname']
    return geometries, ids, classes, STRtree(geometries)


def complete_indices(info, car, source, layer):
    geometries, ids, _, tree = source
    if not info or info['count'] == 0:
        return []
    if info.get('preview_limited'):
        indices = [int(i) for i in tree.query(car, predicate='intersects')]
    else:
        indices = [ids[r['record_id']] for r in info['records']]
        if any(not car.intersects(geometries[i]) for i in indices):
            raise ValueError('Cruzamento não reproduzido na fonte ' + layer)
    if len(indices) != info['count'] or len(set(indices)) != len(indices):
        raise ValueError(f'Contagem completa divergente na fonte {layer}: armazenada={info["count"]}, recuperada={len(indices)}')
    return indices


def run(dist, raw, output, deadline=None):
    if deadline and datetime.now(timezone.utc) >= deadline:
        raise ValueError('Prazo de estabilidade encerrado; manter publicação atual.')
    output = Path(output)
    if output.exists():
        raise ValueError('Saída já existe; preserve e use outro diretório.')
    weights_path = dist/'data/atencao/pesos.json'
    weights = read(weights_path);validate_weights(weights)
    weights_hash = sha(weights_path)
    source_paths = {'prodes':raw/'prodes_am.geojson','deter':raw/'deter_am.geojson',
                    'ibge':raw.parent/'ibge/AM_Municipios_2025.zip'}
    fingerprints = {k:sha(v) for k,v in source_paths.items()}
    # Mesmo filtro territorial do preparador dos cruzamentos: feições que
    # não intersectam a malha original AM não participam da recuperação.
    with zipfile.ZipFile(source_paths['ibge']) as archive:
        reader = shapefile.Reader(shp=archive.open('AM_Municipios_2025.shp'),
                                  shx=archive.open('AM_Municipios_2025.shx'),
                                  dbf=archive.open('AM_Municipios_2025.dbf'),encoding='utf-8')
        territory = STRtree([clean(shape(sr.shape.__geo_interface__)) for sr in reader.iterShapeRecords()])
    sources = {k:load_source(source_paths[k],k,territory) for k in ['prodes','deter']}
    catalog = read(dist/'data/catalogo.json')
    source_catalog = read(dist/'data/ambiental/catalogo.json')
    output.mkdir(parents=True)
    provenance = []; totals = Counter()
    for municipality in catalog['municipalities']:
        if deadline and datetime.now(timezone.utc) >= deadline:
            raise ValueError('Prazo de estabilidade encerrado; lote parcial não publicável.')
        code = municipality['code']
        paths = {k:dist/'data'/v/f'{code}.json' for k,v in [('records','cadastros'),('geometry','geometrias'),('crossings','ambiental/intersecoes')]}
        records = read(paths['records']); geometries = read(paths['geometry']); crossings = read(paths['crossings'])
        rows = {}
        for r in records:
            car_code = r['code']
            if not CAR.fullmatch(car_code) or car_code in rows or r['status'] not in {'AT','PE','SU','CA'}:
                raise ValueError('Código CAR inválido ou repetido.')
            car = clean(shape(geometries[car_code]))
            overlaps = crossings.get(car_code, {})
            try:
                prodes = complete_indices(overlaps.get('prodes'), car, sources['prodes'], 'prodes')
                deter = complete_indices(overlaps.get('deter'), car, sources['deter'], 'deter')
            except ValueError as error:
                raise ValueError(f'{car_code}: {error}') from error
            area, covered, fraction = prodes_metrics(car, [sources['prodes'][0][i] for i in prodes])
            classes = Counter(sources['deter'][2][i] for i in deter)
            row = score(overlaps, fraction, classes, weights)
            row.update({'area_car_ha':round(area,6),'prodes_no_car_ha':round(covered,6),'fracao_prodes':round(fraction,8),'situacao':r['status']})
            rows[car_code] = row
            totals['cars'] += 1;totals['critical'] += bool(row['travas']);totals['positive'] += row['nota'] > 0
        payload = {'version':weights['version'],'municipio':code,'disclaimer':weights['disclaimer'],
                   'weights_sha256':weights_hash,'by_car':rows,'top20':rank(rows, records, weights)}
        write(output/'municipios'/f'{code}.json',payload)
        provenance.append({'municipio':code,'cars':len(rows),'input_sha256':{k:sha(v) for k,v in paths.items()},
                           'output_sha256':sha(output/'municipios'/f'{code}.json')})
        print(json.dumps({'municipio':code,'cars':len(rows),'status':'ok'}),flush=True)
    if fingerprints != {k:sha(v) for k,v in source_paths.items()}:
        raise ValueError('Fonte alterada durante processamento.')
    if sha(weights_path) != weights_hash:
        raise ValueError('Pesos alterados durante processamento.')
    result = {'complete':True,'version':weights['version'],'scope':'AM','generated_at_utc':datetime.now(timezone.utc).isoformat(),
              'disclaimer':weights['disclaimer'],'weights_sha256':weights_hash,'source_sha256':fingerprints,
              'sources':[{k:s.get(k) for k in ['id','provider','url','collected_on','period_years','note']} for s in source_catalog['layers']],
              'totals':dict(totals),'municipalities':provenance}
    write(output/'manifesto.json',result)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--dist',type=Path,default=ROOT/'dist')
    p.add_argument('--raw',type=Path,default=ROOT.parent/'dados/amazonas/brutos/ambiental')
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--deadline-utc',help='ISO 8601; aborta sem manifesto completo se o prazo terminar.')
    args=p.parse_args()
    deadline=datetime.fromisoformat(args.deadline_utc.replace('Z','+00:00')) if args.deadline_utc else None
    print(json.dumps(run(args.dist,args.raw,args.output,deadline)['totals']))


if __name__=='__main__':main()
