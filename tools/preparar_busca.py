"""Gera o indice pequeno da busca com os produtos locais IBGE 2025 da 2c-1."""
import gzip
import hashlib
import json
from pathlib import Path
from focos_brasil import ROOT, OUT, write_json


def build():
    manifest = json.loads((OUT/'manifesto.json').read_text(encoding='utf-8'))
    def product(descriptor):
        data = (OUT/descriptor['path']).read_bytes()
        if len(data) != descriptor['bytes'] or hashlib.sha256(data).hexdigest() != descriptor['sha256']:
            raise ValueError('Produto local diverge do manifesto: '+descriptor['path'])
        return json.loads(gzip.decompress(data))
    units = product(manifest['index'])['units']
    features = product(manifest['mesh'])['features']
    def coordinates(value):
        if isinstance(value[0], (int, float)):
            yield value
        else:
            for part in value:
                yield from coordinates(part)
    entries = []
    for i, (unit, feature) in enumerate(zip(units, features)):
        if feature['id'] != unit['code'] or feature['properties']['i'] != i:
            raise ValueError('Indice e malha local fora de ordem.')
        if unit['kind'] == 'operacional':
            continue
        points = list(coordinates(feature['geometry']['coordinates']))
        xs, ys = zip(*points)
        entries.append([unit['code'],unit['name'],unit['uf'],[min(xs),min(ys),max(xs),max(ys)]])
    if len(entries) != 5571:
        raise ValueError('Cobertura municipal inesperada.')
    return {'version':1,'mesh_year':2025,'source_index_sha256':manifest['index']['sha256'],
            'source_mesh_sha256':manifest['mesh']['sha256'],
            'fields':['code','name','uf','bounds'],'municipalities':entries}


if __name__ == '__main__':
    try:
        payload = write_json(ROOT/'dist/data/busca-municipios.json',build())
        print(f'OK: busca local, 5.571 unidades municipais, {len(payload):,} bytes. Nenhuma consulta externa.')
    except (OSError, ValueError, KeyError) as error:
        raise SystemExit('Falha ao preparar busca: '+str(error))
