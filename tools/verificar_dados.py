"""Conferencia de cobertura e consistencia dos recortes publicados."""
from collections import Counter
from pathlib import Path
import json

BASE = Path(__file__).resolve().parents[1] / 'dist/data'
catalog = json.loads((BASE/'catalogo.json').read_text(encoding='utf-8'))
exceptions = json.loads((BASE/'indice_car.json').read_text(encoding='utf-8'))
assert len(catalog['municipalities']) == 62
assert sum(m['count'] for m in catalog['municipalities']) == catalog['total'] == 98982
all_codes = set()
for m in catalog['municipalities']:
    code = m['code']
    records = json.loads((BASE/'cadastros'/f'{code}.json').read_text(encoding='utf-8'))
    geometries = json.loads((BASE/'geometrias'/f'{code}.json').read_text(encoding='utf-8'))
    display = json.loads((BASE/'mapa'/f'{code}.geojson').read_text(encoding='utf-8'))
    codes = {r['code'] for r in records}
    assert len(codes) == len(records) == m['count']
    assert codes == set(geometries) == {f['properties']['code'] for f in display['features']}
    assert not all_codes.intersection(codes)
    assert dict(Counter(r['status'] for r in records)) == m['statuses']
    for r in records:
        assert exceptions.get(r['code'], r['code'].split('-')[1]) == code
        assert geometries[r['code']]['type'] in ('Polygon', 'MultiPolygon')
        assert geometries[r['code']]['coordinates']
    all_codes.update(codes)
assert len(all_codes) == 98982
assert all(p.stat().st_size < 25 * 1024 * 1024 for p in BASE.rglob('*') if p.is_file())
print('OK: 62 municipios, 98.982 codigos unicos, recortes e geometrias consistentes; 129 excecoes de municipio indexadas.')
