"""Confere fontes, produtos, conservacao integral e amostra espacial independente."""
from collections import Counter
from pathlib import Path
import gzip
import hashlib
import json
import numpy as np
import shapely
from focos_brasil import OUT, RAW, PROCESSED, load_mesh, normalized_rows, read_json


def main():
    m = read_json(OUT/'manifesto.json')
    assert m['stage'] == '2c-1' and m['series'] == 'reference'
    assert m['classes'] == [0, 10, 50, 200, 1000, 5000]
    assert m['default_period'] == {'start': '2025-11', 'end': '2026-10'}
    assert m['coverage']['2026-11']['status'] == 'provisional'
    assert '2026-12' not in m['coverage']
    assert len(m['sources']) == 36
    assert {s['year'] for s in m['sources'] if s['kind']=='annual'} == set(range(2003,2026))
    assert all(s['year']==2026 for s in m['sources'] if s['kind']=='monthly')
    assert [(s['year'],s['month']) for s in m['sources'] if s['kind']=='comparison_sample'] == [(2025,4)]
    for source in m['sources']:
        path = RAW/source['path']
        assert path.stat().st_size == source['bytes']
        with path.open('rb') as stream:
            assert hashlib.file_digest(stream,'sha256').hexdigest() == source['sha256']
    def product(descriptor):
        data=(OUT/descriptor['path']).read_bytes()
        assert len(data)==descriptor['bytes'] and hashlib.sha256(data).hexdigest()==descriptor['sha256']
        payload=gzip.decompress(data)
        assert len(payload)==descriptor['uncompressed_bytes']
        return json.loads(payload)
    index=product(m['index'])['units']; geo=product(m['mesh'])
    assert len(index)==len(geo['features'])==5573
    assert len({u['code'] for u in index})==5573
    assert sum(u['kind']=='operacional' for u in index)==2
    assert m['mesh']['bytes']<=2_000_000
    shapes=shapely.from_geojson([json.dumps(f['geometry']) for f in geo['features']])
    assert all(shapely.is_valid(shapes)) and not any(shapely.is_empty(shapes))
    assert all(f['id']==u['code'] and f['properties']['i']==i for i,(f,u) in enumerate(zip(geo['features'],index)))
    original, geometries, _ = load_mesh()
    code_index={u['code']:i for i,u in enumerate(original)}
    matrices={y:np.zeros((5573,12),dtype=np.int64) for y in m['years']}
    total=unassigned=spatial=0
    for audit in m['audit']:
        a=audit['audit']; statuses=Counter(); counted=missed=0
        assert a['rows_read']==a['excluded_satellite']+a['reference_rows']
        assert a['reference_rows']==a['unique_rows']+a['duplicate_rows']
        assert a['unique_rows']==a['counted_rows']+a['unassigned_rows']
        for j,row in enumerate(normalized_rows(PROCESSED/audit['normalized'])):
            statuses[row['assignment']]+=1
            code=row['municipio_ibge2025']; year=row['datetime_utc'][:4]; month=int(row['datetime_utc'][5:7])
            if code:
                i=code_index[code]; assert original[i]['kind']!='operacional'
                matrices[year][i,month-1]+=1; counted+=1
                if j%10000==0:
                    assert geometries[i].covers(shapely.Point(float(row['longitude']),float(row['latitude'])))
                    spatial+=1
            else:
                missed+=1
            if year=='2026': assert row['satellite']=='AQUA_M-T'
        assert dict(statuses)==audit['assignment_status']
        assert (counted,missed)==(a['counted_rows'],a['unassigned_rows'])
        total+=counted; unassigned+=missed
        print('OK normalizado: '+audit['source_path'],flush=True)
    for year,descriptor in m['years'].items():
        data=product(descriptor); matrix=matrices[year]
        assert descriptor['bytes']<=150_000
        for i,u in enumerate(index):
            if u['kind']=='operacional': assert data['monthly'][i] is None and data['annual'][i] is None
            else:
                assert data['monthly'][i]==matrix[i].tolist()
                assert data['annual'][i]==int(matrix[i].sum())
        assert int(matrix.sum())==descriptor['counted']
    sample=m['comparison_sample']
    assert sample['same_detection_multiset'] and sample['annual_only']==sample['monthly_only']==0
    print(f'OK focos Brasil: {total:,} atribuidos; {unassigned} sem municipio; {spatial} coberturas espaciais conferidas; 36 hashes; 24 anos.')


if __name__=='__main__':
    main()
