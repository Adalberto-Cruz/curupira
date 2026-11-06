"""Valida os lotes oficiais do SICAR AM e produz GeoJSON e inventario."""

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'dados/amazonas/brutos/sicar'
OUTPUT = ROOT / 'dados/amazonas/processados'


def coordinates_valid(value):
    if not isinstance(value, list) or not value:
        return False
    if isinstance(value[0], (int, float)):
        return (
            len(value) >= 2
            and all(isinstance(v, (int, float)) and math.isfinite(v) for v in value)
            and -180 <= value[0] <= 180
            and -90 <= value[1] <= 90
        )
    return all(coordinates_valid(part) for part in value)


def main():
    manifest_path = SOURCE / 'extracao.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig'))
    expected = manifest['contagem_inicial']
    if manifest.get('contagem_final') != expected:
        raise ValueError('Contagens inicial e final ausentes ou divergentes.')
    OUTPUT.mkdir(parents=True, exist_ok=True)
    destination = OUTPUT / 'AM_CAR_publico.geojson'
    temporary = destination.with_suffix('.geojson.partial')
    seen_codes, seen_ids = set(), set()
    statuses, conditions, municipalities, types = Counter(), Counter(), Counter(), Counter()
    names = {}
    null_geometry = 0
    invalid_coordinates = 0
    previous_code = ''
    count = 0
    with temporary.open('w', encoding='utf-8', newline='\n') as out:
        out.write('{"type":"FeatureCollection","features":[\n')
        for batch in manifest['lotes']:
            path = SOURCE / batch['arquivo']
            payload = path.read_bytes()
            if hashlib.sha256(payload).hexdigest() != batch['sha256']:
                raise ValueError(f'Hash divergente: {path.name}')
            page = json.loads(payload.decode('utf-8-sig'))
            if len(page['features']) != batch['registros']:
                raise ValueError(f'Contagem divergente: {path.name}')
            for feature in page['features']:
                p = feature['properties']
                code = p['cod_imovel']
                feature_id = feature['id']
                if p.get('uf') != 'AM' or not code.startswith('AM-'):
                    raise ValueError('Registro de outra UF.')
                if code in seen_codes or feature_id in seen_ids:
                    raise ValueError(f'Registro duplicado: {code}')
                if code < previous_code:
                    raise ValueError('Ordenacao instavel entre lotes.')
                seen_codes.add(code)
                seen_ids.add(feature_id)
                previous_code = code
                geometry = feature.get('geometry')
                if not geometry:
                    null_geometry += 1
                elif not coordinates_valid(geometry.get('coordinates')):
                    invalid_coordinates += 1
                municipality = str(p['cod_municipio_ibge'])
                if not municipality.startswith('13'):
                    raise ValueError('Codigo municipal fora do Amazonas.')
                municipalities[municipality] += 1
                names[municipality] = p['municipio']
                statuses[p.get('status_imovel') or 'nao_informado'] += 1
                conditions[p.get('condicao') or 'nao_informado'] += 1
                types[p.get('tipo_imovel') or 'nao_informado'] += 1
                if count:
                    out.write(',\n')
                json.dump(feature, out, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
                count += 1
        out.write('\n]}\n')
    if count != expected:
        raise ValueError(f'Esperados {expected}, encontrados {count}.')
    if null_geometry or invalid_coordinates:
        raise ValueError(f'Geometrias ausentes: {null_geometry}; coordenadas invalidas: {invalid_coordinates}.')
    temporary.replace(destination)
    summary = {
        'status': 'validado',
        'registros': count,
        'codigos_unicos': len(seen_codes),
        'ids_unicos': len(seen_ids),
        'municipios_com_registros': len(municipalities),
        'geometrias_ausentes': null_geometry,
        'coordenadas_invalidas': invalid_coordinates,
        'validacao_topologica': 'nao_executada',
        'status_cadastrais_como_publicados': dict(statuses),
        'condicoes_como_publicadas': dict(conditions),
        'tipos_como_publicados': dict(types),
        'municipios': [
            {'codigo_ibge': code, 'nome': names[code], 'registros': amount}
            for code, amount in sorted(municipalities.items())
        ],
        'geojson': str(destination.relative_to(ROOT)),
        'bytes_geojson': destination.stat().st_size,
        'sha256_geojson': hashlib.file_digest(destination.open('rb'), 'sha256').hexdigest(),
        'validado_utc': datetime.now(timezone.utc).isoformat(),
        'observacoes': [
            'Nao ha validacao topologica ou atestado de regularidade ambiental nesta extracao.',
            'Registros podem se sobrepor: suas areas nao devem ser somadas como cobertura territorial.',
            'As camadas internas de APP, Reserva Legal e vegetacao declarada nao estao neste produto WFS.',
        ],
    }
    (OUTPUT / 'AM_CAR_publico.resumo.json').write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    manifest['status'] = 'validado'
    manifest['validacao'] = str((OUTPUT / 'AM_CAR_publico.resumo.json').relative_to(ROOT))
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k: summary[k] for k in (
        'status', 'registros', 'municipios_com_registros', 'geometrias_ausentes',
        'coordenadas_invalidas', 'bytes_geojson', 'sha256_geojson'
    )}, ensure_ascii=False))


if __name__ == '__main__':
    main()
