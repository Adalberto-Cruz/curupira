"""Leitura e atribuicao de focos nacionais, sem depender do catalogo CAR."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import csv
import gzip
import hashlib
import io
import json
import math
import unicodedata
import zipfile

import numpy as np
import shapefile
import shapely

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent / 'dados/brasil/brutos/focos'
PROCESSED = ROOT.parent / 'dados/brasil/processados/focos'
OUT = ROOT / 'dist/data/focos-brasil'
METHOD_VERSION = 2
CLASSES = [0, 10, 50, 200, 1000, 5000]
CLASS_COLORS = ['#edf0e8', '#fff3bd', '#ffd17a', '#f9a44f', '#e87737', '#bb442c', '#792b35']


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    temporary = path.with_name(path.name+'.partial')
    temporary.write_bytes(payload)
    temporary.replace(path)
    return payload


def write_gzip_json(path, value):
    payload = json.dumps(value, ensure_ascii=False, separators=(',', ':'), allow_nan=False).encode()
    data = gzip.compress(payload, compresslevel=9, mtime=0)
    temporary = path.with_name(path.name+'.partial')
    temporary.parent.mkdir(parents=True, exist_ok=True)
    temporary.write_bytes(data)
    temporary.replace(path)
    return {'bytes': len(data), 'uncompressed_bytes': len(payload), 'sha256': hashlib.sha256(data).hexdigest()}


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def fold(value):
    return ''.join(c for c in unicodedata.normalize('NFD', value.strip().upper()) if not unicodedata.combining(c))


def municipality_kind(name, uf, code=''):
    if code in {'4300001', '4300002'}:
        return 'operacional'
    if uf == 'DF':
        return 'distrito-federal'
    if fold(name) == 'FERNANDO DE NORONHA':
        return 'distrito-estadual'
    return 'municipio'


def load_mesh(raw=RAW):
    path = raw / 'ibge/BR_Municipios_2025.zip'
    target = path.parent / 'extraido'
    target.mkdir(exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            name = Path(info.filename).name
            if Path(name).suffix.lower() not in {'.shp', '.shx', '.dbf', '.prj', '.cpg'}:
                continue
            destination = target/name
            if destination.exists():
                if destination.stat().st_size != info.file_size:
                    raise ValueError('Malha extraida diverge do ZIP; preserve e confira o arquivo.')
                continue
            with archive.open(info) as source, destination.open('wb') as output:
                while block := source.read(1024*1024):
                    output.write(block)
    shp = next(target.glob('*Municipios*.shp'))
    metadata, geometries = [], []
    repaired = 0
    with shapefile.Reader(str(shp), encoding='utf-8') as reader:
        for record in reader.iterShapeRecords():
            p = record.record.as_dict()
            code, name, uf = str(p['CD_MUN']), p['NM_MUN'], p['SIGLA_UF']
            geometry = shapely.geometry.shape(record.shape.__geo_interface__)
            if not geometry.is_valid:
                geometry = shapely.make_valid(geometry)
                repaired += 1
            if geometry.is_empty or geometry.geom_type not in {'Polygon', 'MultiPolygon'}:
                raise ValueError('Geometria municipal invalida: '+code)
            metadata.append({'code': code, 'name': name, 'uf': uf,
                             'kind': municipality_kind(name, uf, code), 'area_km2': float(p['AREA_KM2'])})
            geometries.append(geometry)
    order = sorted(range(len(metadata)), key=lambda i: metadata[i]['code'])
    metadata = [metadata[i] for i in order]
    geometries = np.array([geometries[i] for i in order], dtype=object)
    if len(metadata) != 5573 or len({m['code'] for m in metadata}) != len(metadata):
        raise ValueError('Malha IBGE 2025 incompleta ou com codigos repetidos.')
    return metadata, geometries, repaired


def raw_rows(spec, raw=RAW):
    path = raw/spec['path']
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as archive:
            members = [n for n in archive.namelist() if n.lower().endswith('.csv')]
            if len(members) != 1:
                raise ValueError('ZIP deve conter um unico CSV: '+str(path))
            with archive.open(members[0]) as binary, io.TextIOWrapper(binary, encoding='utf-8-sig', newline='') as text:
                yield from csv.DictReader(text)
    else:
        with path.open(encoding='utf-8-sig', newline='') as text:
            yield from csv.DictReader(text)


def normalize(row, spec):
    monthly = spec['kind'] != 'annual'
    required = {'lat', 'lon', 'municipio', 'estado', 'pais'} | ({'id', 'data_hora_gmt', 'satelite'} if monthly else {'foco_id', 'data_pas'})
    if not required.issubset(row):
        raise ValueError('Colunas obrigatorias ausentes em '+spec['path'])
    if monthly and row['satelite'].strip() != 'AQUA_M-T':
        return None
    if fold(row['pais']) not in {'BRASIL', 'BRAZIL'}:
        raise ValueError('Registro fora do Brasil na fonte: '+spec['path'])
    ident = row['id' if monthly else 'foco_id'].strip()
    if not ident:
        raise ValueError('Foco sem identificador: '+spec['path'])
    dt = datetime.fromisoformat(row['data_hora_gmt' if monthly else 'data_pas'].strip().replace('Z', '+00:00'))
    dt = dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)
    if dt.year != spec['year'] or monthly and dt.month != spec['month']:
        raise ValueError('Data fora do periodo do arquivo: '+spec['path'])
    try:
        lat, lon = float(row['lat']), float(row['lon'])
        if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError()
    except (ValueError, TypeError):
        lat = lon = None
    return {'id': ident, 'datetime_utc': dt.strftime('%Y-%m-%dT%H:%M:%SZ'), 'month': dt.month,
            'lat': lat, 'lon': lon, 'source_code': row.get('municipio_id', '').strip(),
            'source_name': row['municipio'].strip(), 'source_uf': row['estado'].strip(),
            'satellite': row.get('satelite', '').strip() if monthly else 'produto-referencia-INPE'}


class MunicipalAssigner:
    def __init__(self, metadata, geometries):
        self.metadata = metadata
        self.geometries = geometries
        self.tree = shapely.STRtree(geometries)
        self.code_index = {m['code']: i for i, m in enumerate(metadata)}
        self.operational = np.array([m['kind'] == 'operacional' for m in metadata])
        shapely.prepare(geometries)

    def assign(self, records):
        chosen = np.full(len(records), -1, dtype=np.int32)
        status = np.array(['invalid-coordinate' if r['lat'] is None else 'outside-mesh' for r in records], dtype=object)
        valid = np.array([i for i, r in enumerate(records) if r['lat'] is not None], dtype=np.int32)
        if not len(valid):
            return chosen, status
        points = shapely.points([records[i]['lon'] for i in valid], [records[i]['lat'] for i in valid])
        pairs = self.tree.query(points)
        inside = shapely.covers(self.geometries[pairs[1]], points[pairs[0]])
        point_ids, polygon_ids = valid[pairs[0][inside]], pairs[1][inside]
        municipal = ~self.operational[polygon_ids]
        sentinel = len(self.metadata)
        best = np.full(len(records), sentinel, dtype=np.int32)
        np.minimum.at(best, point_ids[municipal], polygon_ids[municipal])
        good = best < sentinel
        chosen[good] = best[good]
        status[good] = 'assigned'
        only_operational = point_ids[~municipal]
        status[only_operational[chosen[only_operational] < 0]] = 'operational-area'
        origin = np.array([self.code_index.get(r['source_code'], -1) for r in records])
        preferred = municipal & (origin[point_ids] == polygon_ids)
        chosen[point_ids[preferred]] = polygon_ids[preferred]
        frequencies = np.bincount(point_ids[municipal], minlength=len(records))
        status[frequencies > 1] = 'boundary-lowest-code'
        status[point_ids[preferred & (frequencies[point_ids] > 1)]] = 'boundary-source-code'
        return chosen, status


def normalized_rows(path):
    with gzip.open(path, 'rt', encoding='utf-8', newline='') as stream:
        yield from csv.DictReader(stream)
