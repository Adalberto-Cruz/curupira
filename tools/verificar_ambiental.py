"""Confere recortes ambientais contra o catálogo usado no mapa."""
from pathlib import Path
from collections import Counter
import json

base = Path(__file__).resolve().parents[1] / 'dist/data/ambiental'
catalog = json.loads((base / 'catalogo.json').read_text(encoding='utf-8'))
layers = {s['id'] for s in catalog['layers']}
assert len(layers) == 6
assert len(catalog['counts_by_municipality']) == 62
for code, expected in catalog['counts_by_municipality'].items():
    collection = json.loads((base / 'municipios' / f'{code}.geojson').read_text(encoding='utf-8'))
    assert collection['type'] == 'FeatureCollection'
    counts = Counter()
    identifiers = set()
    for feature in collection['features']:
        p = feature['properties']
        assert p['layer'] in layers
        assert feature['geometry'] and (feature['geometry'].get('coordinates') or feature['geometry'].get('geometries'))
        key = (p['layer'], p['record_id'])
        assert key not in identifiers, (code, key)
        identifiers.add(key)
        counts[p['layer']] += 1
    assert all(counts[k] == expected[k] for k in layers), code
print('OK: seis camadas, 62 recortes municipais, contagens e identificadores consistentes.')
