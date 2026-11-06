"""Normaliza focos e gera somente contagens e coropletico da Etapa 2c-1."""
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
import argparse
import csv
import gzip
import hashlib
import json

import numpy as np
import shapely

from focos_brasil import (RAW, OUT, PROCESSED, METHOD_VERSION, CLASSES, CLASS_COLORS,
                         MunicipalAssigner, load_mesh, normalize, normalized_rows,
                         raw_rows, read_json, write_gzip_json, write_json)

FIELDS = ['id', 'datetime_utc', 'longitude', 'latitude', 'municipio_ibge2025',
          'municipio_origem_id', 'municipio_origem_nome', 'uf_origem', 'assignment', 'satellite']


def process_source(spec, raw, processed, assigner, mesh_hash):
    key = f"{spec['kind']}-{spec['year']}"+(f"-{spec['month']:02}" if 'month' in spec else '')
    target = processed/'normalizados'/(key+'.csv.gz')
    cache = processed/'auditoria'/(key+'.json')
    fingerprint = hashlib.sha256(f"{METHOD_VERSION}:{mesh_hash}:{spec['sha256']}".encode()).hexdigest()
    if target.exists() and cache.exists():
        previous = read_json(cache)
        if previous['fingerprint'] == fingerprint:
            print('Reutilizado: '+key, flush=True)
            return previous
        raise ValueError('Cache de processamento diferente: preserve e use outro --processados para regenerar.')
    counts = np.zeros((len(assigner.metadata), 12), dtype=np.int64)
    audit = Counter(rows_read=0, excluded_satellite=0, reference_rows=0, duplicate_rows=0,
                    unique_rows=0, counted_rows=0, unassigned_rows=0, source_code_disagreement=0)
    statuses = Counter()
    seen = {}
    minimum = maximum = None
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name+'.partial')
    with gzip.open(partial, 'wt', encoding='utf-8', newline='', compresslevel=6) as output:
        writer = csv.DictWriter(output, fieldnames=FIELDS)
        writer.writeheader()

        def flush(records):
            nonlocal minimum, maximum
            if not records:
                return
            indices, assignments = assigner.assign(records)
            valid = indices >= 0
            np.add.at(counts, (indices[valid], np.array([r['month']-1 for r in records])[valid]), 1)
            for record, index, assignment in zip(records, indices, assignments):
                code = assigner.metadata[int(index)]['code'] if index >= 0 else ''
                statuses[str(assignment)] += 1
                audit['unique_rows'] += 1
                audit['counted_rows' if code else 'unassigned_rows'] += 1
                if code and record['source_code'] and record['source_code'] != code:
                    audit['source_code_disagreement'] += 1
                timestamp = record['datetime_utc']
                minimum = timestamp if minimum is None else min(minimum, timestamp)
                maximum = timestamp if maximum is None else max(maximum, timestamp)
                writer.writerow(dict(zip(FIELDS, [record['id'], timestamp, record['lon'], record['lat'], code,
                    record['source_code'], record['source_name'], record['source_uf'], assignment, record['satellite']])))

        batch = []
        for row in raw_rows(spec, raw):
            audit['rows_read'] += 1
            record = normalize(row, spec)
            if record is None:
                audit['excluded_satellite'] += 1
                continue
            audit['reference_rows'] += 1
            identity = (record['datetime_utc'], record['lat'], record['lon'])
            if record['id'] in seen:
                if seen[record['id']] != identity:
                    raise ValueError('Identificador com coordenadas/datas conflitantes: '+record['id'])
                audit['duplicate_rows'] += 1
                continue
            seen[record['id']] = identity
            batch.append(record)
            if len(batch) >= 20000:
                flush(batch)
                batch = []
        flush(batch)
    if not audit['reference_rows']:
        raise ValueError('Fonte sem focos de referencia: '+spec['path'])
    if audit['unassigned_rows'] / audit['unique_rows'] > .01:
        raise ValueError('Mais de 1% dos focos sem atribuicao; revisar antes de publicar: '+spec['path'])
    partial.replace(target)
    result = {'fingerprint': fingerprint, 'source_path': spec['path'], 'normalized': str(target.relative_to(processed)),
              'audit': dict(audit), 'assignment_status': dict(statuses), 'minimum_utc': minimum, 'maximum_utc': maximum,
              'counts': counts.tolist()}
    write_json(cache, result)
    print(f"Processado {key}: {audit['unique_rows']:,} unicos; {audit['unassigned_rows']:,} sem atribuicao.", flush=True)
    return result


def comparison(annual_spec, sample_spec, raw):
    def collect(spec, month):
        found = Counter()
        ids = set()
        for row in raw_rows(spec, raw):
            item = normalize(row, spec)
            if item is None or item['month'] != month or item['id'] in ids:
                continue
            ids.add(item['id'])
            found[(item['datetime_utc'], item['lat'], item['lon'])] += 1
        return found, ids
    annual, annual_ids = collect(annual_spec, sample_spec['month'])
    monthly, monthly_ids = collect(sample_spec, sample_spec['month'])
    result = {'year': sample_spec['year'], 'month': sample_spec['month'],
              'annual_reference_rows': sum(annual.values()), 'monthly_filtered_rows': sum(monthly.values()),
              'annual_only': sum((annual-monthly).values()), 'monthly_only': sum((monthly-annual).values()),
              'id_intersection': len(annual_ids & monthly_ids), 'same_detection_multiset': annual == monthly,
              'annual_modified': annual_spec['last_modified'], 'monthly_modified': sample_spec['last_modified']}
    if not result['same_detection_multiset']:
        raise ValueError('Amostra anual x mensal diverge; investigar antes de consolidar: '+json.dumps(result))
    return result


def display_mesh(metadata, geometries, out, budget):
    for tolerance in [.01, .02, .03, .05]:
        simplified = shapely.coverage_simplify(geometries, tolerance, simplify_boundary=True)
        simplified = shapely.set_precision(simplified, .0001)
        if any(g.is_empty for g in simplified) or not all(shapely.is_valid(simplified)):
            raise ValueError('Simplificacao removeu ou invalidou uma unidade territorial.')
        features = [{'type': 'Feature', 'id': meta['code'], 'properties': {'i': i},
                     'geometry': json.loads(shapely.to_geojson(geometry))}
                    for i, (meta, geometry) in enumerate(zip(metadata, simplified))]
        size = write_gzip_json(out/'municipios.geojson.gz', {'type': 'FeatureCollection', 'features': features})
        if size['bytes'] <= budget:
            return {**size, 'path': 'municipios.geojson.gz', 'tolerance_degrees': tolerance,
                    'coordinate_grid_degrees': .0001, 'vertices': int(shapely.count_coordinates(simplified)),
                    'features': len(features), 'method': 'GEOS coverage_simplify; somente exibicao. Atribuicao usa geometria original.'}
    raise ValueError('Malha simplificada excedeu o orcamento de carregamento.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--brutos', type=Path, default=RAW)
    parser.add_argument('--processados', type=Path, default=PROCESSED)
    parser.add_argument('--saida', type=Path, default=OUT)
    args = parser.parse_args()
    try:
        collection = read_json(args.brutos/'coleta.json')
        sources = collection['sources']
        for source in sources:
            path = args.brutos/source['path']
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if path.stat().st_size != source['bytes'] or digest != source['sha256']:
                raise ValueError('Fonte bruta difere da proveniencia: '+source['path'])
        mesh_spec = next(s for s in sources if s['kind'] == 'mesh')
        print('Carregando malha original IBGE 2025...', flush=True)
        metadata, geometries, repairs = load_mesh(args.brutos)
        assigner = MunicipalAssigner(metadata, geometries)
        print(f'Malha: {len(metadata)} unidades; {repairs} geometrias reparadas.', flush=True)
        sample = next(s for s in sources if s['kind'] == 'comparison_sample')
        annual_sample = next(s for s in sources if s['kind'] == 'annual' and s['year'] == sample['year'])
        sample_check = comparison(annual_sample, sample, args.brutos)
        print('Amostra anual x mensal: '+json.dumps(sample_check), flush=True)
        per_year, audits, coverage = {}, [], {}
        for spec in sources:
            if spec['kind'] not in {'annual', 'monthly'}:
                continue
            result = process_source(spec, args.brutos, args.processados, assigner, mesh_spec['sha256'])
            matrix = np.array(result['counts'], dtype=np.int64)
            year = spec['year']
            per_year.setdefault(year, np.zeros_like(matrix))
            per_year[year] += matrix
            months = range(1, 13) if spec['kind'] == 'annual' else [spec['month']]
            for month in months:
                coverage[f'{year}-{month:02}'] = {'status': 'provisional' if spec.get('provisional') else 'complete',
                     'source': spec['path'], 'maximum_utc': result['maximum_utc']}
            audits.append({k: v for k, v in result.items() if k != 'counts'})
        args.saida.mkdir(parents=True, exist_ok=True)
        mesh = display_mesh(metadata, geometries, args.saida, 2_000_000)
        index_size = write_gzip_json(args.saida/'municipios.json.gz', {'mesh_year': 2025, 'units': metadata})
        years = {}
        operational = [i for i, m in enumerate(metadata) if m['kind'] == 'operacional']
        for year, matrix in sorted(per_year.items()):
            rows = matrix.tolist()
            annual = matrix.sum(axis=1).tolist()
            for i in operational:
                rows[i] = None
                annual[i] = None
            value = {'year': year, 'monthly': rows, 'annual': annual,
                     'months': [coverage.get(f'{year}-{m:02}', {'status': 'unavailable'})['status'] for m in range(1, 13)]}
            size = write_gzip_json(args.saida/f'contagens-{year}.json.gz', value)
            if size['bytes'] > 150_000:
                raise ValueError('Contagens excedem o orcamento de 150 KB/ano.')
            years[str(year)] = {**size, 'path': f'contagens-{year}.json.gz', 'counted': int(matrix.sum())}
        as_of = date.fromisoformat(collection['as_of'])
        end = as_of.replace(day=1)-timedelta(days=1)
        start = end.replace(year=end.year-1)+timedelta(days=1)
        manifest = {'version': 1, 'stage': '2c-1', 'as_of': collection['as_of'], 'series': 'reference',
          'reference_policy': 'Produtos anuais INPE 2003-2025; AQUA_M-T nos mensais de 2026. Nao mistura todos os satelites.',
          'default_period': {'start': start.strftime('%Y-%m'), 'end': end.strftime('%Y-%m')},
          'mesh_year': 2025, 'units': len(metadata), 'municipal_units': len(metadata)-len(operational),
          'operational_units': len(operational), 'source_geometries_repaired': repairs,
          'classes': CLASSES, 'class_colors': CLASS_COLORS, 'coverage': coverage,
          'mesh': mesh, 'index': {**index_size, 'path': 'municipios.json.gz'}, 'years': years,
          'audit': audits, 'comparison_sample': sample_check, 'sources': sources,
          'attribution': {'focos': 'INPE. Banco de Dados de Queimadas. Programa Queimadas.',
                          'mesh': 'IBGE. Malha Municipal Digital 2025.', 'accessed': collection['as_of'],
                          'license': 'Acesso livre e gratuito segundo FAQ INPE; licenca especifica de redistribuicao nao identificada.'},
          'method': {'version': METHOD_VERSION, 'assignment': 'Coordenada pontual na geometria original IBGE 2025; covers. Em divisa, codigo de origem se candidato; senao menor codigo. Uma atribuicao por foco.',
                     'coordinates': 'CSV geografico e malha SIRGAS2000 em longitude/latitude, sem transformacao geodesica. Nao usar como analise metrica de precisao.',
                     'dates': 'UTC; data_pas anual e data_hora_gmt mensal normalizadas. Equivalencia conferida na amostra.',
                     'deduplication': 'Mesmo identificador dentro da fonte; divergencia de coordenadas/data interrompe. Nao agrupa incendios.',
                     'normalization': 'CSVs normalizados e auditoria em ../dados/brasil/processados/focos/, fora do Git.'},
          'limitations': ['Focos nao sao incendios unicos, area queimada ou prova de infracao.',
                         'Sem deteccao nao comprova ausencia de fogo; nuvens e falhas de imageamento afetam a serie.',
                         'Municipios recalculados na malha fixa 2025 podem divergir da atribuicao original do INPE.',
                         'Areas operacionais, pontos fora da malha e coordenadas invalidas nao recebem municipio; totais auditados.',
                         'CAR e demais camadas ambientais mantem cobertura do Amazonas. Sem cruzamento CAR nacional.',
                         'Sem mapa de calor nem pontos nesta entrega.']}
        write_json(args.saida/'manifesto.json', manifest)
        print('OK: produtos gerados; manifesto gravado por ultimo. Malha '+str(mesh['bytes'])+' bytes gzip.', flush=True)
        return 0
    except (OSError, ValueError, KeyError, StopIteration) as error:
        parser.exit(1, 'Preparacao interrompida: '+str(error)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
