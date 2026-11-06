"""Utilidades exclusivas da preparação nacional; não importa nem escreve em dist/."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import unicodedata

import requests
import shapely
from shapely.geometry import GeometryCollection, MultiPolygon, Polygon

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'dados/brasil'
UFS = set('AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO'.split())


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False).encode()
    if path.exists():
        if path.read_bytes() == raw:
            return
        raise FileExistsError('Saída existente preservada: ' + str(path))
    partial = path.with_name(path.name + '.partial')
    with partial.open('xb') as stream:
        stream.write(raw)
    partial.rename(path)


def download(url, path, expected_bytes=None):
    """Download verificável; não substitui snapshots nem apaga tentativas parciais."""
    path = Path(path)
    meta_path = path.with_name(path.name + '.fonte.json')
    if path.exists():
        meta = json.loads(meta_path.read_bytes())
        if sha256(path) != meta['sha256'] or path.stat().st_size != meta['bytes']:
            raise ValueError('Snapshot local diverge do manifesto: ' + str(path))
        return meta
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + '.partial')
    size = 0
    with requests.get(url, timeout=(30, 120), stream=True, headers={'Accept-Encoding': 'identity'}) as response:
        response.raise_for_status()
        with partial.open('xb') as stream:
            for block in response.iter_content(1048576):
                if block:
                    stream.write(block)
                    size += len(block)
        length = response.headers.get('Content-Length')
        if length and not response.headers.get('Content-Encoding') and size != int(length):
            raise ValueError('Download truncado; parcial preservado.')
        if expected_bytes is not None and size != expected_bytes:
            raise ValueError('Tamanho diverge do catálogo; parcial preservado.')
        meta = {'url': url, 'downloaded_at_utc': utc(), 'bytes': size,
                'last_modified_http': response.headers.get('Last-Modified'),
                'etag': response.headers.get('ETag'), 'sha256': sha256(partial)}
    partial.rename(path)
    write_json(meta_path, meta)
    print(json.dumps({'download': path.name, 'bytes': size, 'sha256': meta['sha256']}), flush=True)
    return meta


def fold(value):
    value = unicodedata.normalize('NFKD', str(value or '').strip().upper())
    return ' '.join(''.join(c for c in value if not unicodedata.combining(c)).split())


def term_key(sequence, number, series, row_number):
    sequence = '' if sequence is None else str(sequence).strip()
    number = '' if number is None else str(number).strip().upper()
    series = '' if series is None else str(series).strip().upper()
    # A cópia IPAAM representa SEQ_TAD não atribuído pelo sentinela 0.
    if sequence and sequence != '0':
        return 'SEQ:' + sequence
    if number:
        return 'TAD:' + number + '|SER:' + series
    return 'ROW:' + str(row_number)


def classify_embargo(row):
    """Classe operacional do snapshot; não certifica vigência jurídica.

    Desembargo tem precedência sobre cancelamento para classes disjuntas;
    ambos os indicadores são preservados e suas interseções contabilizadas.
    """
    status = fold(row.get('DES_STATUS_FORMULARIO'))
    aie = fold(row.get('DES_STATUS_FORMULARIO_AIE'))
    cancel = fold(row.get('SIT_CANCELADO'))
    release = fold(row.get('SIT_DESEMBARGO'))
    cancelled = cancel == 'S' or status == 'CANCELADO'
    released = release == 'S'
    flags = {'cancelado_indicado': cancelled, 'desembargado_indicado': released,
             'sobreposicao_cancelado_desembargado': cancelled and released}
    if released:
        return 'desembargado', flags
    if cancelled:
        return 'cancelado', flags
    if 'SUBSTITUIDO' in status:
        return 'substituido', flags
    if status == 'EXCLUIDO' or aie == 'EXCLUIDO':
        return 'excluido', flags
    # Não ignora uma data/tipo de desembargo preenchida com indicador inconsistente.
    release_details = any(str(row.get(k) or '').strip() for k in ['DAT_DESEMBARGO', 'TIPO_DESEMBARGO'])
    if status == 'LAVRADO' and cancel == 'N' and release in {'', 'N'} and not release_details:
        return 'vigente', flags
    return 'indeterminado', flags


def polygonal(geometry):
    if isinstance(geometry, (Polygon, MultiPolygon)):
        return geometry
    if isinstance(geometry, GeometryCollection):
        parts = []
        for part in geometry.geoms:
            result = polygonal(part)
            if isinstance(result, Polygon) and not result.is_empty:
                parts.append(result)
            elif isinstance(result, MultiPolygon):
                parts.extend(result.geoms)
        return MultiPolygon(parts) if parts else None
    return None


def clean_geometry(geometry):
    """Valida XY; make_valid structure só na cópia. Retém apenas partes poligonais."""
    if geometry is None or geometry.is_empty:
        return None, {'reason': 'vazia', 'invalid_before': False, 'repaired': False}
    geometry = shapely.force_2d(geometry)
    coords = shapely.get_coordinates(geometry)
    if not all(math.isfinite(float(v)) for pair in coords for v in pair):
        return None, {'reason': 'coordenada_nao_finita', 'invalid_before': not geometry.is_valid, 'repaired': False}
    west, south, east, north = geometry.bounds
    if not (-180 <= west <= east <= 180 and -90 <= south <= north <= 90):
        return None, {'reason': 'fora_coordenadas_geograficas', 'invalid_before': not geometry.is_valid, 'repaired': False}
    invalid = not geometry.is_valid
    if invalid:
        geometry = shapely.make_valid(geometry, method='structure', keep_collapsed=False)
    result = polygonal(geometry)
    if result is None or result.is_empty or result.area <= 0:
        return None, {'reason': 'sem_parte_poligonal', 'invalid_before': invalid, 'repaired': invalid}
    if not result.is_valid:
        return None, {'reason': 'invalida_apos_reparo', 'invalid_before': invalid, 'repaired': invalid}
    return result, {'reason': 'ok', 'invalid_before': invalid, 'repaired': invalid}


class GeoJSONWriter:
    """GeoJSON de processamento com CRS explícito (modelo 2008), sem prometer RFC 7946."""
    def __init__(self, path, crs, note):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.stream = self.path.open('x', encoding='utf-8', newline='\n')
        self.count = 0
        metadata = {'type': 'FeatureCollection', 'crs': crs, 'preparation_note': note}
        self.stream.write(json.dumps(metadata, ensure_ascii=False)[:-1] + ',"features":[')

    def add(self, geometry, properties):
        if self.count:
            self.stream.write(',')
        feature = {'type': 'Feature', 'properties': properties, 'geometry': shapely.geometry.mapping(geometry)}
        self.stream.write(json.dumps(feature, ensure_ascii=False, separators=(',', ':'), allow_nan=False))
        self.count += 1

    def close(self):
        self.stream.write(']}\n')
        self.stream.close()


def inventory(directory):
    directory = Path(directory)
    return [{'path': p.relative_to(directory).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha256(p)}
            for p in sorted(directory.rglob('*')) if p.is_file() and not p.name.endswith('.partial')]
