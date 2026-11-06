"""Prepara MT/PA para a prova; exige GeoJSON local e não baixa nem publica dados.

O arquivo de entrada deve vir de extração documentada em EPSG:4326.
Por padrão, falha em códigos duplicados. Uma auditoria vinculada por hash
pode autorizar preservar todas as linhas; nunca escolhe uma geometria em silêncio.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import gzip
import math
import struct
import subprocess
import sys
import io
import zipfile
from urllib.request import urlopen

from shapely.geometry import shape, mapping

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'work/prova-maplibre'


def extract_sourcecoop_mt():
    """Extrai todas as linhas MT por Range, sem instalar pacote no sistema.

    PyArrow fica descompactado em work/. Não deduplica nem escolhe situações.
    O hash nacional é declarado pelo catálogo; não é recalculado integralmente.
    """
    import requests
    from shapely import from_wkb
    arrow = OUT / 'arrow-isolado'
    if not (arrow / 'pyarrow').is_dir():
        package = json.load(urlopen('https://pypi.org/pypi/pyarrow/22.0.0/json', timeout=30))
        tag = f'cp{sys.version_info.major}{sys.version_info.minor}'
        asset = next(a for a in package['urls'] if tag in a['filename'] and a['filename'].endswith('win_amd64.whl') and 'cp313t' not in a['filename'])
        raw = urlopen(asset['url'], timeout=90).read()
        if hashlib.sha256(raw).hexdigest() != asset['digests']['sha256']:
            raise ValueError('Hash da biblioteca PyArrow divergente.')
        arrow.mkdir(parents=True, exist_ok=True)
        (arrow / asset['filename']).write_bytes(raw)
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            for entry in archive.infolist():
                target = (arrow / entry.filename).resolve()
                if not target.is_relative_to(arrow.resolve()):
                    raise ValueError('Caminho inválido no pacote.')
                if entry.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(archive.read(entry))
        (arrow / 'origem.json').write_text(json.dumps({'url': asset['url'], 'sha256': asset['digests']['sha256']}, indent=2), encoding='utf-8')
    sys.path.insert(0, str(arrow))
    import pyarrow
    import pyarrow.parquet as pq
    if pyarrow.__version__ != '22.0.0':
        raise ValueError('PyArrow 22.0.0 exigido para esta reprodução.')
    base = 'https://data.source.coop/tristangruppwri/cadastral/brazil-car-area-imovel/'
    catalog_raw = urlopen(base + 'collection.json', timeout=30).read()
    catalog = json.loads(catalog_raw)
    size = catalog['assets']['data']['file:size']
    checksum = catalog['assets']['data']['file:checksum']
    cache = OUT / 'parquet-range-cache'
    cache.mkdir(parents=True, exist_ok=True)
    marker = cache / 'source.json'
    if marker.exists() and json.loads(marker.read_bytes())['checksum'] != checksum:
        raise ValueError('A origem mudou; preserve o cache existente e use diretório de prova novo.')
    marker.write_bytes(json.dumps({'checksum': checksum, 'size': size}).encode())
    sources = OUT / 'fontes'
    sources.mkdir(exist_ok=True)
    (sources / 'collection-extracao.json').write_bytes(catalog_raw)

    class Remote(io.RawIOBase):
        def __init__(self):
            self.pos = 0
            self.session = requests.Session()
            self.download_bytes = 0

        def readable(self): return True
        def seekable(self): return True
        def tell(self): return self.pos

        def seek(self, offset, whence=0):
            self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else size + offset
            return self.pos

        def read(self, n=-1):
            end = min(size, self.pos + n if n >= 0 else size)
            parts = []
            while self.pos < end:
                block = self.pos // 1048576
                start, stop = block * 1048576, min(size - 1, (block + 1) * 1048576 - 1)
                target = cache / f'{block}.bin'
                if not target.exists():
                    response = self.session.get(base + 'brazil_car_area_imovel.parquet', headers={'Range': f'bytes={start}-{stop}'}, timeout=90)
                    response.raise_for_status()
                    if response.status_code != 206 or response.headers.get('Content-Range') != f'bytes {start}-{stop}/{size}' or len(response.content) != stop - start + 1:
                        raise ValueError('Resposta Range inválida.')
                    target.write_bytes(response.content)
                    self.download_bytes += len(response.content)
                raw = target.read_bytes()
                if len(raw) != stop - start + 1:
                    raise ValueError('Bloco em cache truncado.')
                a, b = self.pos - start, min(end - start, len(raw))
                parts.append(raw[a:b])
                self.pos = start + b
            return b''.join(parts)

        def readinto(self, buffer):
            raw = self.read(len(buffer))
            buffer[:len(raw)] = raw
            return len(raw)

    source = OUT / 'entrada/mt-todas-linhas.geojson'
    temporary = source.with_suffix('.geojson.partial')
    if source.exists() or temporary.exists():
        raise FileExistsError('Extração já existe ou está incompleta; preserve-a e audite antes de continuar.')
    source.parent.mkdir(exist_ok=True)
    remote = Remote()
    parquet = pq.ParquetFile(remote)
    seen, duplicates, statuses = {}, [], Counter()
    count, invalid, groups = 0, 0, []
    with temporary.open('w', encoding='utf-8', newline='\n') as output:
        output.write('{"type":"FeatureCollection","features":[')
        for i in range(parquet.num_row_groups):
            group = parquet.metadata.row_group(i)
            column = next(group.column(j) for j in range(group.num_columns) if group.column(j).path_in_schema == 'cod_estado')
            stats = column.statistics
            if stats and stats.has_min_max and not stats.min <= 'MT' <= stats.max:
                continue
            if 'MT' not in parquet.read_row_group(i, columns=['cod_estado']).column(0).to_pylist():
                continue
            groups.append(i)
            for row in parquet.read_row_group(i, columns=['cod_imovel', 'ind_status', 'cod_estado', 'geometry']).to_pylist():
                if row['cod_estado'] != 'MT':
                    continue
                code, status, raw = row['cod_imovel'], row['ind_status'], row['geometry']
                digest = hashlib.sha256(raw).hexdigest()
                geometry = from_wkb(raw)
                if code in seen:
                    old_status, old_hash, old_wkb = seen[code]
                    duplicates.append({'code': code, 'same_status': old_status == status,
                                       'identical_wkb': old_hash == digest,
                                       'topologically_equal': from_wkb(old_wkb).equals(geometry)})
                seen[code] = status, digest, raw
                invalid += not geometry.is_valid
                if count:
                    output.write(',')
                output.write(json.dumps({'type': 'Feature', 'properties': {'code': code, 'status': status}, 'geometry': mapping(geometry)}, separators=(',', ':'), allow_nan=False))
                count += 1
                statuses[status] += 1
            print(json.dumps({'group': i, 'rows_mt': count, 'unique_codes_mt': len(seen), 'duplicate_rows': len(duplicates)}), flush=True)
        output.write(']}')
    temporary.rename(source)
    with source.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = {'url': base + 'brazil_car_area_imovel.parquet', 'catalog_updated': catalog['updated'],
              'national_checksum_declared': checksum, 'national_checksum_verified': False,
              'rows_extracted_mt': count, 'unique_codes_mt': len(seen), 'groups': groups,
              'national_rows': parquet.metadata.num_rows, 'invalid_geometry': invalid,
              'statuses': dict(statuses), 'duplicate_rows_audited': duplicates,
              'source_sha256': digest, 'download_bytes_this_run': remote.download_bytes,
              'method': 'Todas as linhas MT preservadas; grupos excluídos somente por estatísticas de UF ou leitura da coluna UF. Só code/status/geometria exportados.'}
    (sources / 'mt-extracao.json').write_bytes(json.dumps(report, indent=2).encode())
    print('Extração e auditoria locais: ' + str(source), flush=True)


def prepare(source, uf, origin, duplicate_audit=None):
    payload = source.read_bytes()
    data = json.loads(payload)
    if data.get('type') != 'FeatureCollection' or not data.get('features'):
        raise ValueError('Entrada deve ser FeatureCollection não vazia em EPSG:4326.')
    if data.get('crs'):
        raise ValueError('Remova/reprojete o CRS explicitamente antes da prova; espera-se GeoJSON RFC 7946.')
    audit = json.loads(duplicate_audit.read_bytes()) if duplicate_audit else None
    if audit and (audit.get('source_sha256') != hashlib.sha256(payload).hexdigest()
                  or audit.get('rows_extracted_mt') != len(data['features'])):
        raise ValueError('Auditoria não corresponde ao arquivo de entrada.')
    features, small, seen, statuses = [], [], set(), Counter()
    for feature in data['features']:
        props = feature['properties']
        code = props.get('code', props.get('cod_imovel'))
        status = props.get('status', props.get('status_imovel', props.get('ind_status')))
        if not isinstance(code, str) or not re.fullmatch(uf + r'-\d{7}-[A-Fa-f0-9]{32}', code):
            raise ValueError('Código ausente ou incompatível com a UF solicitada.')
        if code in seen and not audit:
            raise ValueError('Código duplicado: ' + code + '; audite a origem antes de continuar.')
        if status not in {'AT', 'PE', 'SU', 'CA'}:
            raise ValueError('Situação desconhecida para ' + code)
        geometry = shape(feature['geometry'])
        if geometry.is_empty or geometry.geom_type not in {'Polygon', 'MultiPolygon'}:
            raise ValueError('Geometria não poligonal/vazia: ' + code)
        west, south, east, north = geometry.bounds
        if not (-74 <= west <= east <= -34 and -34 <= south <= north <= 6):
            raise ValueError('Coordenadas fora do envelope brasileiro: ' + code)
        # Mesma tolerância do preparador do site; não recupera precisão da origem.
        display = geometry.simplify(.00012, preserve_topology=True)
        seen.add(code)
        statuses[status] += 1
        features.append({'type': 'Feature', 'properties': {'code': code, 'status': status}, 'geometry': mapping(display)})
        if display.is_valid and display.area > 0:
            point = display.representative_point()
            small.append({'code': code, 'status': status, 'lng': point.x, 'lat': point.y, 'area_degrees2': display.area})
    if audit and audit.get('unique_codes_mt') != len(seen):
        raise ValueError('Contagem de códigos diverge da auditoria.')
    output = json.dumps({'type': 'FeatureCollection', 'features': features}, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / f'car-{uf.lower()}.geojson'
    if target.exists():
        raise FileExistsError('Saída já existe; preserve-a e revise antes de gerar novamente: ' + str(target))
    target.write_bytes(output)
    report = {'uf': uf, 'origin': origin, 'source_sha256': hashlib.sha256(payload).hexdigest(),
              'source_bytes': len(payload), 'count': len(features), 'unique_codes': len(seen), 'statuses': dict(statuses),
              'duplicate_policy': 'Todas as linhas preservadas após auditoria vinculada por hash; código não é chave única na origem.' if audit else 'Códigos duplicados bloqueados.',
              'geojson_bytes': len(output), 'geojson_sha256': hashlib.sha256(output).hexdigest(),
              'small': sorted(small, key=lambda f: f['area_degrees2'])[:5],
              'note': 'Somente code/status/geometria; situação não atesta regularidade. Validar cobertura completa da UF na origem.'}
    (OUT / f'manifesto-{uf.lower()}.json').write_bytes(json.dumps(report, ensure_ascii=False, indent=2).encode())
    print(json.dumps({k: report[k] for k in ['uf', 'count', 'geojson_bytes', 'geojson_sha256']}, ensure_ascii=False))


def verify(uf):
    """Audita cabeçalho/atributos e os cinco pequenos; não audita todos os tiles."""
    file = OUT / f'car-{uf.lower()}.pmtiles'
    manifest = json.loads((OUT / f'manifesto-{uf.lower()}.json').read_bytes())
    with file.open('rb') as stream:
        header = stream.read(127)
        if header[:8] != b'PMTiles\x03':
            raise ValueError('Cabeçalho PMTiles v3 ausente.')
        offset, size = struct.unpack_from('<QQ', header, 24)
        stream.seek(offset)
        raw = stream.read(size)
    metadata = json.loads(gzip.decompress(raw) if header[97] == 2 else raw)
    if set(metadata['vector_layers'][0]['fields']) != {'code', 'status'}:
        raise ValueError('Campos inesperados nos metadados vetoriais.')
    path = file.resolve().as_posix()
    linux_file = '/mnt/' + path[0].lower() + path[2:]
    binary = '/tmp/hibama-prova-pmtiles-20261106/tippecanoe/tippecanoe-decode'
    cases = []
    for case in manifest['small']:
        presence = {}
        for zoom in [4, header[101]]:
            n = 2 ** zoom
            x = int((case['lng'] + 180) / 360 * n)
            y = int((1 - math.asinh(math.tan(math.radians(case['lat']))) / math.pi) / 2 * n)
            tile = json.loads(subprocess.check_output(['wsl', '-d', 'Ubuntu', '--', binary, linux_file, str(zoom), str(x), str(y)]))
            features = [f for layer in tile['features'] for f in layer['features']]
            if any(set(f['properties']) != {'code', 'status'} for f in features):
                raise ValueError('Campos inesperados no tile.')
            matches = [f for f in features if f['properties']['code'] == case['code']]
            if any(f['properties']['status'] != case['status'] for f in matches):
                raise ValueError('Situação divergente: ' + case['code'])
            presence[str(zoom)] = bool(matches)
        if not presence[str(header[101])]:
            raise ValueError('Pequeno ausente no nível máximo: ' + case['code'])
        cases.append({'code': case['code'], 'present_by_zoom': presence})
    with file.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = {'uf': uf, 'bytes': file.stat().st_size, 'sha256': digest,
              'min_zoom': header[100], 'max_zoom': header[101], 'source_count': manifest['count'],
              'small_features': cases, 'scope': 'Amostra de cinco pequenos e atributos; não auditoria exaustiva de códigos em todos os tiles.'}
    (OUT / f'verificacao-{uf.lower()}.json').write_bytes(json.dumps(report, ensure_ascii=False, indent=2).encode())
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--entrada', type=Path)
    mode.add_argument('--verificar', action='store_true')
    mode.add_argument('--extrair-sourcecoop', action='store_true')
    parser.add_argument('--uf', choices=['MT', 'PA'], required=True)
    parser.add_argument('--origem', help='URL/data/versão da extração, sem dados pessoais.')
    parser.add_argument('--auditoria-duplicados', type=Path, help='Auditoria vinculada por SHA-256; preserva todas as linhas, sem deduplicação.')
    args = parser.parse_args()
    if args.extrair_sourcecoop:
        if args.uf != 'MT':
            parser.error('A extração auditada desta prova está implementada somente para MT.')
        extract_sourcecoop_mt()
    elif args.verificar:
        verify(args.uf)
    else:
        if not args.origem:
            parser.error('--origem é obrigatório com --entrada.')
        prepare(args.entrada, args.uf, args.origem, args.auditoria_duplicados)
