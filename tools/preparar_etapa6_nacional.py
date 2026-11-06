"""Prepara embargos, CNFP e CAR tabular fora do Git; nenhuma integração em dist/."""
import argparse
from collections import Counter, defaultdict
import csv
from datetime import datetime, timezone
import gzip
import io
import json
import re
import sqlite3
import struct
import sys
from pathlib import Path
import zipfile

import requests
import shapefile
import shapely
from shapely import from_wkt
from shapely.geometry import shape

from etapa6_comum import (ROOT, BASE, UFS, GeoJSONWriter, classify_embargo,
                         clean_geometry, download, fold, sha256, utc, write_json, inventory, term_key)

IBAMA_API = 'https://dadosabertos.ibama.gov.br/api/3/action/package_show?id=fiscalizacao-termo-de-embargo'
CNFP_API = 'https://dados.florestal.gov.br/api/3/action/package_show?id=cadastro-nacional-de-florestas-publicas-cnfp'
CNFP_ITEM = 'https://mapas.florestal.gov.br/portal/sharing/rest/content/items/2b752dfbf9254920bf8990ce363918af'
CAR_BASE = 'https://data.source.coop/tristangruppwri/cadastral/brazil-car-area-imovel/'


def get_json(url, path):
    if path.exists():
        return json.loads(path.read_bytes())
    response = requests.get(url, timeout=60)
    response.raise_for_status()
    data = response.json()
    write_json(path, data)
    return data


def acquire(raw):
    ibama = get_json(IBAMA_API, raw / 'ibama/catalogo.json')['result']
    resource = next(r for r in ibama['resources'] if r['name'] == 'Termos de embargo' and r['format'] == 'CSV')
    embargo = download(resource['url'], raw / 'ibama/termo_de_embargo.csv')
    get_json(CNFP_API, raw / 'cnfp/catalogo.json')
    item = get_json(CNFP_ITEM + '?f=pjson', raw / 'cnfp/item.json')
    if item.get('type') != 'Shapefile':
        raise ValueError('Item CNFP não é Shapefile.')
    cnfp = download(CNFP_ITEM + '/data', raw / 'cnfp/CNFP_2025.zip', item['size'])
    print(json.dumps({'fontes_baixadas': True, 'embargos_bytes': embargo['bytes'], 'cnfp_bytes': cnfp['bytes']}), flush=True)


def output_dir(processed, name):
    result = processed / (name + '-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
    result.mkdir(parents=True, exist_ok=False)
    return result


def prepare_embargos(raw, processed, ipaam):
    source = raw / 'ibama/termo_de_embargo.csv'
    if not source.is_file():
        raise FileNotFoundError('Execute --etapa baixar primeiro.')
    result = output_dir(processed, 'embargos')
    csv.field_size_limit(64 * 1024 * 1024)
    stats = Counter()
    by_uf = defaultdict(Counter)
    domains = defaultdict(Counter)
    writers = {}
    seen = set()
    seq_seen = set()
    am = defaultdict(list)
    term_classes = defaultdict(set)
    reports = set()
    safe_fields = ['SEQ_TAD', 'NUM_TAD', 'SER_TAD', 'UF', 'DES_STATUS_FORMULARIO', 'DES_STATUS_FORMULARIO_AIE',
                   'SIT_CANCELADO', 'SIT_DESEMBARGO', 'TIPO_DESEMBARGO', 'DAT_DESEMBARGO',
                   'DAT_EMBARGO', 'DAT_ULT_ALTERACAO']
    index_path = result / 'registros_sanitizados.csv.gz'
    with gzip.open(index_path, 'wt', encoding='utf-8', newline='') as stream:
        columns = safe_fields + ['classe', 'geometria', 'invalid_before', 'repaired', 'srid_wkt']
        index = csv.DictWriter(stream, fieldnames=columns)
        index.writeheader()
        try:
            with source.open(encoding='utf-8-sig', newline='') as original:
                reader = csv.DictReader(original, delimiter=';')
                required = {'SEQ_TAD', 'UF', 'GEOM_AREA_EMBARGADA', 'DES_STATUS_FORMULARIO', 'SIT_CANCELADO', 'SIT_DESEMBARGO'}
                if not required <= set(reader.fieldnames or []):
                    raise ValueError('Esquema do CSV Ibama mudou.')
                for row in reader:
                    stats['registros'] += 1
                    seq = row['SEQ_TAD'].strip()
                    if seq:
                        key = term_key(seq, row.get('NUM_TAD'), row.get('SER_TAD'), stats['registros'])
                        stats['linhas_com_seq_tad_repetido'] += seq in seq_seen
                        seq_seen.add(seq)
                    else:
                        stats['seq_tad_vazio'] += 1
                        number, series = row.get('NUM_TAD', '').strip(), row.get('SER_TAD', '').strip()
                        key = term_key(seq, number, series, stats['registros'])
                        stats['chave_fallback_tad_serie' if number else 'sem_chave_oficial'] += 1
                    stats['linhas_com_chave_repetida'] += key in seen
                    seen.add(key)
                    uf = row['UF'].strip().upper()
                    if uf not in UFS:
                        uf = 'SEM_UF'
                    category, flags = classify_embargo(row)
                    term_classes[(uf, key)].add(category)
                    stats['classe_' + category] += 1
                    by_uf[uf][category] += 1
                    for flag, value in flags.items():
                        stats[flag] += int(value)
                    for field in ['DES_STATUS_FORMULARIO', 'DES_STATUS_FORMULARIO_AIE', 'SIT_CANCELADO', 'SIT_DESEMBARGO']:
                        domains[field][row.get(field, '').strip()] += 1
                    reports.add(row.get('ULTIMA_ATUALIZACAO_RELATORIO', ''))
                    wkt = row['GEOM_AREA_EMBARGADA'].strip()
                    srid = ''
                    if wkt.upper().startswith('SRID='):
                        srid, _, wkt = wkt.partition(';')
                    geometry = None
                    audit = {'reason': 'wkt_ausente', 'invalid_before': False, 'repaired': False}
                    if wkt:
                        try:
                            geometry, audit = clean_geometry(from_wkt(wkt))
                        except (shapely.errors.GEOSException, ValueError, TypeError):
                            audit = {'reason': 'erro_wkt_ou_reparo', 'invalid_before': False, 'repaired': False}
                    stats['geometria_' + audit['reason']] += 1
                    stats['invalidas_antes'] += audit['invalid_before']
                    stats['reparadas_structure'] += audit['repaired'] and geometry is not None
                    props = {k.lower(): row.get(k, '') for k in safe_fields}
                    props.update({'source_row': stats['registros'], 'uf': uf, 'classe_operacional': category, **flags, 'geometria_reparada': audit['repaired']})
                    if geometry is not None:
                        writer_key = uf, category
                        if writer_key not in writers:
                            writers[writer_key] = GeoJSONWriter(result / 'por_uf' / uf / (category + '.geojson'), None,
                                'Coordenadas XY preservadas do WKT; datum não declarado no CSV. CRS desconhecido (GeoJSON 2008 crs:null), sem transformação nem aceite de precisão cadastral. Classe vigente é inferida dos indicadores do snapshot, não certificação jurídica.')
                        writers[writer_key].add(geometry, props)
                        by_uf[uf]['geometrias_' + category] += 1
                    index.writerow({**{k: row.get(k, '') for k in safe_fields}, 'UF': uf,
                                    'classe': category, 'geometria': audit['reason'],
                                    'invalid_before': audit['invalid_before'], 'repaired': audit['repaired'], 'srid_wkt': srid})
                    if uf == 'AM':
                        am[key].append((category, geometry))
                    if stats['registros'] % 10000 == 0:
                        print(json.dumps({'embargos_lidos': stats['registros']}), flush=True)
        finally:
            for writer in writers.values():
                writer.close()
    global_terms = defaultdict(set)
    for (uf, key), _ in term_classes.items():
        global_terms[key].add(uf)
    comparison = compare_ipaam(am, ipaam, result, global_terms)
    stats['seq_tad_distintos'] = len(seq_seen)
    stats['termos_identificados'] = len(seen)
    stats['termos_uf_com_classes_conflitantes'] = sum(len(v) > 1 for v in term_classes.values())
    term_summary = defaultdict(Counter)
    for (uf, _), categories in term_classes.items():
        term_summary[uf][next(iter(categories)) if len(categories) == 1 else 'conflitante'] += 1
    summary = {'prepared_at_utc': utc(), 'source': str(source), 'source_sha256': sha256(source),
               'stats': dict(stats), 'por_uf': {k: dict(v) for k, v in sorted(by_uf.items())},
               'termos_distintos_por_uf_classe': {k: dict(v) for k, v in sorted(term_summary.items())},
               'dominios': {k: dict(v) for k, v in domains.items()}, 'atualizacao_relatorio': sorted(reports),
               'classificacao': 'Desembargado precede cancelado. Excluídos/substituídos separados; inconsistências ficam indeterminadas. Vigente requer Lavrado, SIT_CANCELADO=N, sem desembargo e sem AIe Excluído; não é vigência jurídica certificada.',
               'crs': 'Datum do CSV não confirmado; crs:null explícito. Não houve transformação.',
               'geometrias': 'XY; make_valid(method=structure, keep_collapsed=False); somente partes poligonais.',
               'comparacao_ipaam': comparison}
    write_json(result / 'resumo.json', summary)
    print(json.dumps({'etapa': 'embargos', 'saida': str(result), 'stats': dict(stats)}), flush=True)
    return result


def compare_ipaam(am, ipaam, result, global_terms=None):
    if not ipaam.is_file():
        return {'disponivel': False}
    features = json.loads(ipaam.read_bytes())['features']
    by_key = defaultdict(list)
    local_empty_seq = 0
    local_seq = set()
    for i, feature in enumerate(features):
        attrs = feature['properties']
        sequence = attrs.get('seq_tad')
        if sequence is None or str(sequence).strip() in {'', '0'}:
            local_empty_seq += 1
        else:
            local_seq.add(str(sequence).strip())
        key = term_key(sequence, attrs.get('num_tad'), attrs.get('serie_tad'), i)
        by_key[key].append(feature)
    counts = Counter()
    index = []
    for key, features_for_term in sorted(by_key.items()):
        if key not in am:
            counts['termos_ipaam_ausentes_nacional_am'] += 1
            other_ufs = sorted((global_terms or {}).get(key, set()))
            counts['ipaam_presente_nacional_outra_uf' if other_ufs else 'ipaam_ausente_todo_csv_nacional'] += 1
            index.append({'chave': key, 'classe_nacional': 'ausente_nacional_am', 'ufs_no_csv_nacional': other_ufs})
            continue
        categories = {c for c, _ in am[key]}
        category = next(iter(categories)) if len(categories) == 1 else 'conflitante'
        national_parts = [g for _, g in am[key] if g is not None]
        try:
            national_geometry = shapely.union_all(national_parts) if national_parts else None
        except shapely.errors.GEOSException:
            national_geometry = None
            counts['falhas_uniao_nacional'] += 1
        counts['termos_comuns'] += 1
        counts['classe_nacional_' + category] += 1
        equivalent = False
        if national_geometry is not None:
            geometries = []
            for feature in features_for_term:
                cleaned, _ = clean_geometry(shape(feature['geometry']))
                if cleaned is not None:
                    geometries.append(cleaned)
            if geometries:
                try:
                    equivalent = shapely.union_all(geometries).equals(national_geometry)
                except shapely.errors.GEOSException:
                    counts['falhas_comparacao_geometrica'] += 1
            counts['geometrias_iguais_topologicamente_xy'] += equivalent
            counts['geometrias_diferentes_xy'] += not equivalent
        else:
            counts['comuns_sem_geometria_nacional_utilizavel'] += 1
        index.append({'chave': key, 'classe_nacional': category, 'igualdade_topologica_xy': equivalent})
    counts['termos_nacionais_am_ausentes_ipaam'] = len(set(am) - set(by_key))
    write_json(result / 'comparacao_ipaam_por_termo.json', index)
    return {'disponivel': True, 'fonte': str(ipaam), 'sha256': sha256(ipaam),
            'feicoes_ipaam': len(features), 'termos_distintos_ipaam': len(by_key),
            'seq_tad_preenchidos_distintos_ipaam': len(local_seq), 'linhas_sem_seq_tad_ipaam': local_empty_seq,
            'termos_nacional_am': len(am), 'contagens': dict(counts),
            'limite': 'Comparação por SEQ_TAD preenchido ou fallback número/série; vazios não se agrupam. Igualdade geométrica numérica XY, sem transformação porque datum do WKT não está confirmado. Diferença não prova erro nem defasagem.'}


def compare_secondary_keys(source, ipaam, target):
    """Audita número/série apenas para chaves SEQ_TAD sem correspondência nacional."""
    csv.field_size_limit(64 * 1024 * 1024)
    sequences, numbers = set(), defaultdict(list)
    with source.open(encoding='utf-8-sig', newline='') as stream:
        for i, row in enumerate(csv.DictReader(stream, delimiter=';'), 1):
            sequence = row['SEQ_TAD'].strip()
            if sequence:
                sequences.add(sequence)
            key = row['NUM_TAD'].strip().upper(), row['SER_TAD'].strip().upper()
            if key[0]:
                numbers[key].append({'seq_tad': sequence, 'uf': row['UF'], 'source_row': i,
                                     'classe_operacional': classify_embargo(row)[0]})
    local = defaultdict(set)
    for feature in json.loads(ipaam.read_bytes())['features']:
        row = feature['properties']
        document = (str(row.get('num_tad') or '').strip().upper(), str(row.get('serie_tad') or '').strip().upper())
        sequence = str(row.get('seq_tad') or '').strip()
        # Zero identifica ausência de SEQ na cópia IPAAM. Auditar cada documento
        # contra TODO o CSV, inclusive termos nacionais com SEQ preenchido.
        key = sequence if sequence not in {'', '0'} else 'SEM_SEQ:' + repr(document)
        local[key].add(document)
    counts, details = Counter(), []
    for seq, keys in local.items():
        if seq in sequences:
            counts['correspondencia_por_seq_tad'] += 1
            continue
        counts['sem_correspondencia_por_seq_tad'] += 1
        candidates = [record for key in keys for record in numbers.get(key, [])]
        unique = len(keys) == 1 and len(candidates) == 1
        counts['alternativa_unica_numero_serie' if unique else 'alternativa_ambigua' if candidates else 'sem_alternativa_numero_serie'] += 1
        details.append({'seq_tad_ipaam': seq, 'alternativa_unica': unique, 'candidatos': candidates})
    report = {'source_sha256': sha256(source), 'ipaam_sha256': sha256(ipaam),
              'counts': dict(counts), 'details': details,
              'note': 'Correspondência textual exata número/série, sem remover zeros ou pontuação. Alternativa documental, não equivalência cadastral/geométrica certificada nem atualização automática de chave.'}
    write_json(target, report)
    print(json.dumps({'comparacao_secundaria': str(target), 'counts': dict(counts)}), flush=True)
    return report


def validate_cnfp_crs(prj):
    text = prj.upper()
    if 'PROJCS' in text or 'SIRGAS_2000' not in text or 'GRS_1980' not in text or 'DEGREE' not in text:
        raise ValueError('CRS CNFP não corresponde ao SIRGAS 2000 geográfico esperado.')
    return 'EPSG:4674'


def prepare_cnfp(raw, processed):
    source = raw / 'cnfp/CNFP_2025.zip'
    result = output_dir(processed, 'cnfp')
    stats = Counter()
    by_uf = defaultdict(Counter)
    declared_areas = defaultdict(float)
    types = Counter()
    writers = {}
    try:
        with zipfile.ZipFile(source) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError('Falha CRC no ZIP CNFP.')
            stem = next(name[:-4] for name in archive.namelist() if name.lower().endswith('.shp'))
            prj = archive.read(stem + '.prj').decode('utf-8-sig')
            crs = validate_cnfp_crs(prj)
            encoding = archive.read(stem + '.cpg').decode('ascii').strip()
            if encoding.upper() in {'65001', 'UTF8'}:
                encoding = 'utf-8'
            reader = shapefile.Reader(shp=archive.open(stem + '.shp'), shx=archive.open(stem + '.shx'),
                                      dbf=archive.open(stem + '.dbf'), encoding=encoding)
            if reader.shapeType != shapefile.POLYGONZ:
                raise ValueError('Tipo shapefile difere de PolygonZ verificado.')
            fields = [field[0] for field in reader.fields[1:]]
            if not {'tipo', 'uf', 'area_ha', 'geocodigo'} <= set(fields):
                raise ValueError('Esquema CNFP mudou.')
            with (result / 'auditoria_geometrias.csv').open('x', encoding='utf-8', newline='') as audit_stream:
                audit_writer = csv.DictWriter(audit_stream, fieldnames=['source_record', 'uf', 'tipo', 'reason', 'invalid_before', 'repaired'])
                audit_writer.writeheader()
                for i, record in enumerate(reader.iterShapeRecords()):
                    attrs = record.record.as_dict()
                    stats['registros'] += 1
                    uf = str(attrs.get('uf') or '').strip().upper()
                    if uf not in UFS:
                        uf = 'SEM_UF'
                    raw_type = str(attrs.get('tipo') or '').strip()
                    types[raw_type] += 1
                    normalized = fold(raw_type)
                    kind = 'B' if normalized in {'B', 'TIPO B', 'FLORESTA TIPO B'} else 'A' if normalized in {'A', 'TIPO A', 'FLORESTA TIPO A'} else 'OUTRO'
                    stats['tipo_' + kind] += 1
                    by_uf[uf]['tipo_' + kind] += 1
                    try:
                        geometry, audit = clean_geometry(shape(record.shape.__geo_interface__))
                    except (ValueError, TypeError, shapely.errors.GEOSException):
                        geometry, audit = None, {'reason': 'erro_geometria', 'invalid_before': False, 'repaired': False}
                    stats['geometria_' + audit['reason']] += 1
                    stats['invalidas_antes'] += audit['invalid_before']
                    stats['reparadas_structure'] += audit['repaired'] and geometry is not None
                    audit_writer.writerow({'source_record': i, 'uf': uf, 'tipo': kind, **audit})
                    try:
                        area = float(attrs.get('area_ha') or 0)
                        if not __import__('math').isfinite(area):
                            raise ValueError()
                        declared_areas[(uf, kind)] += area
                    except (ValueError, TypeError):
                        stats['area_declarada_invalida'] += 1
                    if kind == 'B' and geometry is not None:
                        if uf not in writers:
                            writers[uf] = GeoJSONWriter(result / 'tipo_b' / (uf + '.geojson'),
                                {'type': 'name', 'properties': {'name': crs}},
                                'GeoJSON de processamento (CRS legado EPSG:4674); XY preservado, Z descartado. Não transformado para WGS84/RFC 7946. Tipo B conforme atributo, sem inferir infração.')
                        safe = {key: attrs.get(key) for key in ['categoria', 'protecao', 'governo', 'classe', 'bioma', 'geocodigo', 'area_ha']}
                        safe.update({'source_record': i, 'uf': uf, 'tipo': 'B', 'geometria_reparada': audit['repaired']})
                        writers[uf].add(geometry, safe)
                        by_uf[uf]['tipo_B_geometrias'] += 1
    finally:
        for writer in writers.values():
            writer.close()
    areas = [{'uf': uf, 'tipo': kind, 'soma_area_ha_declarada': value} for (uf, kind), value in sorted(declared_areas.items())]
    summary = {'prepared_at_utc': utc(), 'source': str(source), 'source_sha256': sha256(source),
               'crs_validado': crs, 'prj': prj, 'source_shape_type': 'PolygonZ', 'processed_dimensions': 'XY, sem reprojeção',
               'encoding': encoding, 'fields': fields, 'stats': dict(stats), 'tipos_originais': dict(types),
               'por_uf': {k: dict(v) for k, v in sorted(by_uf.items())}, 'areas_declaradas': areas,
               'area_note': 'Soma aritmética do atributo area_ha; não dissolve sobreposições nem equivale a área territorial única.'}
    write_json(result / 'resumo.json', summary)
    print(json.dumps({'etapa': 'cnfp', 'saida': str(result), 'stats': dict(stats), 'tipos': dict(types)}), flush=True)
    return result


def load_ibge_names(path):
    with zipfile.ZipFile(path) as archive:
        dbf = next(n for n in archive.namelist() if n.endswith('.dbf'))
        reader = shapefile.Reader(dbf=archive.open(dbf), encoding='utf-8')
        entries = []
        for record in reader.iterRecords():
            attrs = record.as_dict()
            code = str(attrs['CD_MUN'])
            if code in {'4300001', '4300002'}:
                continue
            entries.append({'code': code, 'uf': attrs['SIGLA_UF'], 'name': attrs['NM_MUN']})
    if len(entries) != 5571:
        raise ValueError('Malha IBGE 2025 sem as 5.571 unidades municipais esperadas.')
    return entries


def municipality_match(uf, name, exact, normalized):
    exact_key = uf, str(name or '').strip().upper()
    choices = exact.get(exact_key, set())
    method = 'exato_sem_distinguir_caixa'
    if not choices:
        choices = normalized.get((uf, fold(name)), set())
        method = 'normalizado_acentos_espacos'
    if len(choices) == 1:
        return next(iter(choices)), method
    return '', 'ambiguo' if choices else 'sem_correspondencia'


class TabularParquetRemote(io.RawIOBase):
    """Lê footer e envelopes de colunas tabulares, sem requisitar geometry/bbox."""
    def __init__(self, url, size, directory):
        self.url, self.size, self.directory = url, size, Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.session = requests.Session()
        self.download_bytes = 0
        self.requests_count = 0
        self.pos = 0
        self.span = None
        self.etag = self.session.head(url, timeout=40).headers.get('ETag')
        version = {'url': url, 'bytes': size, 'etag': self.etag}
        marker = self.directory / 'origem_http.json'
        if marker.exists():
            if json.loads(marker.read_bytes()) != version:
                raise ValueError('Versão HTTP do CAR mudou; não misturar faixas de snapshots diferentes.')
        else:
            if any(self.directory.glob('*.bin')):
                raise ValueError('Cache anterior sem versão HTTP; preserve-o e use execução nova.')
            write_json(marker, version)
        tail = self.fetch(size - 8, size - 1)
        if tail[4:] != b'PAR1':
            raise ValueError('Footer Parquet inválido.')
        length = struct.unpack_from('<I', tail)[0]
        self.footer_start = size - 8 - length
        self.footer = self.fetch(self.footer_start, size - 1)
        self.header = self.fetch(0, 3)
        if self.header != b'PAR1':
            raise ValueError('Cabeçalho Parquet inválido.')

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, offset, whence=0):
        self.pos = offset if whence == 0 else self.pos + offset if whence == 1 else self.size + offset
        return self.pos

    def fetch(self, start, end):
        path = self.directory / f'{start}-{end}.bin'
        if path.exists():
            raw = path.read_bytes()
            if len(raw) != end - start + 1:
                raise ValueError('Faixa tabular em cache truncada.')
            return raw
        headers = {'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity'}
        if self.etag:
            headers['If-Match'] = self.etag
        response = self.session.get(self.url, headers=headers, timeout=(30, 120))
        response.raise_for_status()
        if response.status_code != 206 or response.headers.get('Content-Range') != f'bytes {start}-{end}/{self.size}' or len(response.content) != end - start + 1:
            raise ValueError('Range tabular inválido ou versão da origem alterada.')
        self.download_bytes += len(response.content)
        self.requests_count += 1
        path.write_bytes(response.content)
        return response.content

    def set_group(self, metadata, columns):
        ranges = []
        forbidden = []
        for i in range(metadata.num_columns):
            col = metadata.column(i)
            start = col.dictionary_page_offset if col.has_dictionary_page else col.data_page_offset
            interval = start, start + col.total_compressed_size - 1
            if col.path_in_schema in columns:
                ranges.append(interval)
            else:
                forbidden.append(interval)
        start, end = min(a for a, _ in ranges), max(b for _, b in ranges)
        if any(a <= end and b >= start for a, b in forbidden):
            raise ValueError('Layout intercalado: envelope tabular cruzaria coluna não autorizada.')
        self.span = start, end, self.fetch(start, end)

    def read(self, n=-1):
        end = min(self.size, self.pos + n if n >= 0 else self.size)
        if end == self.pos:
            return b''
        if self.pos >= self.footer_start:
            raw = self.footer[self.pos - self.footer_start:end - self.footer_start]
        elif self.pos == 0 and end <= 4:
            raw = self.header[:end]
        elif self.span and self.span[0] <= self.pos <= end - 1 <= self.span[1]:
            raw = self.span[2][self.pos - self.span[0]:end - self.span[0]]
        else:
            raise ValueError('Leitura fora do footer ou das colunas tabulares autorizadas.')
        self.pos = end
        return raw

    def readinto(self, buffer):
        raw = self.read(len(buffer))
        buffer[:len(raw)] = raw
        return len(raw)


def prepare_car(raw, processed, arrow_dir, ibge_zip):
    if arrow_dir:
        if not (arrow_dir / 'pyarrow').is_dir():
            raise FileNotFoundError('Diretório PyArrow existente não localizado; nenhuma instalação será feita.')
        sys.path.insert(0, str(arrow_dir.resolve()))
    try:
        import pyarrow
        import pyarrow.parquet as pq
    except ImportError as error:
        raise RuntimeError('PyArrow ausente. Informe biblioteca já existente em --pyarrow-dir; não instala automaticamente.') from error
    catalog = get_json(CAR_BASE + 'collection.json', raw / 'car/collection.json')
    result = output_dir(processed, 'car-tabular')
    remote = TabularParquetRemote(CAR_BASE + 'brazil_car_area_imovel.parquet', catalog['assets']['data']['file:size'], raw / 'car/faixas_tabulares')
    parquet = pq.ParquetFile(remote, pre_buffer=False)
    allowed = {'cod_tema', 'nom_tema', 'cod_imovel', 'mod_fiscal', 'num_area', 'ind_status',
               'ind_tipo', 'des_condic', 'municipio', 'cod_estado', 'dat_criaca', 'dat_atuali'}
    columns = [name for name in parquet.schema_arrow.names if name in allowed]
    required = {'cod_imovel', 'cod_estado', 'ind_status', 'municipio'}
    if not required <= set(columns):
        raise ValueError('Esquema CAR mudou.')
    ibge = load_ibge_names(ibge_zip)
    exact, normalized = defaultdict(set), defaultdict(set)
    for item in ibge:
        exact[(item['uf'], item['name'].strip().upper())].add(item['code'])
        normalized[(item['uf'], fold(item['name']))].add(item['code'])
    current_codes = {item['code'] for item in ibge}
    stats, by_status, matches, municipality_groups = Counter(), Counter(), Counter(), Counter()
    conditions = Counter()
    connection = sqlite3.connect(result / 'auditoria_codigos.sqlite')
    connection.execute('PRAGMA journal_mode=DELETE')
    connection.execute('PRAGMA temp_store=MEMORY')
    connection.execute('PRAGMA cache_size=-131072')
    connection.execute('CREATE TABLE linhas(codigo TEXT, uf TEXT, situacao TEXT)')
    writer = None
    code_pattern = re.compile(r'([A-Z]{2})-(\d{7})-[A-Fa-f0-9]{32}')
    try:
        for i in range(parquet.num_row_groups):
            remote.set_group(parquet.metadata.row_group(i), columns)
            table = parquet.read_row_group(i, columns=columns, use_threads=False)
            table = table.replace_schema_metadata(None)
            if writer is None:
                if any(name in table.schema.names for name in ['geometry', 'bbox']):
                    raise ValueError('Coluna geométrica não permitida.')
                writer = pq.ParquetWriter(result / 'car_tabular_sem_geometria.parquet', table.schema, compression='zstd')
            writer.write_table(table)
            inserts = []
            for row in table.select(['cod_imovel', 'cod_estado', 'ind_status', 'municipio', 'des_condic']).to_pylist():
                code, uf, status = str(row['cod_imovel'] or ''), str(row['cod_estado'] or ''), str(row['ind_status'] or '')
                name = str(row['municipio'] or '')
                stats['registros'] += 1
                by_status[(uf, status)] += 1
                stats['cancelados'] += status == 'CA'
                condition = str(row['des_condic'] or '')
                conditions[(status, condition)] += 1
                condition_cancelled = fold(condition).startswith('CANCELADO')
                stats['condicao_cancelado'] += condition_cancelled
                stats['condicao_cancelado_status_diferente_CA'] += condition_cancelled and status != 'CA'
                stats['status_CA_sem_condicao_cancelado'] += status == 'CA' and not condition_cancelled
                stats['uf_desconhecida'] += uf not in UFS
                parsed = code_pattern.fullmatch(code)
                stats['codigo_formato_invalido'] += parsed is None
                if parsed:
                    stats['uf_codigo_diverge_coluna_uf'] += parsed[1] != uf
                    stats['codigo_municipal_embutido_fora_ibge2025'] += parsed[2] not in current_codes
                matched_code, method = municipality_match(uf, name, exact, normalized)
                matches[method] += 1
                municipality_groups[(uf, name, matched_code, method)] += 1
                if matched_code and parsed:
                    stats['municipio_nome_diverge_codigo_car'] += matched_code != parsed[2]
                inserts.append((code, uf, status))
            connection.executemany('INSERT INTO linhas VALUES(?,?,?)', inserts)
            connection.commit()
            if i % 10 == 0:
                print(json.dumps({'car_group': i, 'registros': stats['registros'], 'novos_bytes_tabulares': remote.download_bytes}), flush=True)
    finally:
        if writer:
            writer.close()
    if stats['registros'] != parquet.metadata.num_rows:
        raise ValueError('Contagem projetada diverge do footer Parquet.')
    print('CAR: construindo índice de códigos, sem geometria.', flush=True)
    connection.execute('CREATE INDEX codigo_idx ON linhas(codigo)')
    connection.commit()
    stats['codigos_distintos'] = connection.execute("SELECT count(DISTINCT codigo) FROM linhas WHERE codigo<>''").fetchone()[0]
    stats['linhas_excedentes_por_codigo'] = stats['registros'] - stats['codigos_distintos']
    print('CAR: auditando duplicações.', flush=True)
    with gzip.open(result / 'codigos_duplicados.csv.gz', 'wt', encoding='utf-8', newline='') as stream:
        duplicate_writer = csv.writer(stream)
        duplicate_writer.writerow(['cod_imovel', 'linhas', 'ufs', 'situacoes'])
        query = "SELECT codigo,count(*),group_concat(DISTINCT uf),group_concat(DISTINCT situacao) FROM linhas WHERE codigo<>'' GROUP BY codigo HAVING count(*)>1"
        for code, count, ufs, statuses in connection.execute(query):
            duplicate_writer.writerow([code, count, ufs, statuses])
            stats['codigos_repetidos'] += 1
            stats['codigos_repetidos_situacao_conflitante'] += ',' in statuses
            stats['codigos_em_mais_de_uma_uf'] += ',' in ufs
    unique_by_uf = dict(connection.execute("SELECT uf,count(DISTINCT codigo) FROM linhas WHERE codigo<>'' GROUP BY uf"))
    unique_by_status = [{'uf': uf, 'situacao': status, 'codigos_distintos_na_situacao': count}
                        for uf, status, count in connection.execute("SELECT uf,situacao,count(DISTINCT codigo) FROM linhas WHERE codigo<>'' GROUP BY uf,situacao")]
    connection.close()
    with (result / 'condicao_administrativa_por_situacao.csv').open('x', encoding='utf-8', newline='') as stream:
        condition_writer = csv.writer(stream)
        condition_writer.writerow(['situacao', 'condicao_administrativa', 'registros'])
        condition_writer.writerows((status, condition, count) for (status, condition), count in sorted(conditions.items()))
    with (result / 'casamento_municipios_ibge2025.csv').open('x', encoding='utf-8', newline='') as stream:
        match_writer = csv.writer(stream)
        match_writer.writerow(['uf', 'municipio_origem', 'codigo_ibge_2025', 'metodo', 'registros'])
        for (uf, name, code, method), count in sorted(municipality_groups.items()):
            match_writer.writerow([uf, name, code, method, count])
    summary = {'prepared_at_utc': utc(), 'source_url': remote.url, 'source_etag': remote.etag,
               'source_bytes_total': remote.size, 'source_checksum_declared': catalog['assets']['data']['file:checksum'],
               'source_full_checksum_verified': False, 'catalog_updated': catalog['updated'],
               'source_license': catalog['license'], 'columns_read': columns, 'pyarrow_version': pyarrow.__version__,
               'new_range_bytes': remote.download_bytes, 'new_range_requests': remote.requests_count,
               'geometry_downloaded': False, 'stats': dict(stats),
               'registros_por_uf_situacao': [{'uf': uf, 'situacao': status, 'registros': count} for (uf, status), count in sorted(by_status.items())],
               'codigos_distintos_por_uf': unique_by_uf, 'codigos_distintos_por_uf_situacao': unique_by_status,
               'casamento_municipios': dict(matches), 'ibge_zip': str(ibge_zip), 'ibge_zip_sha256': sha256(ibge_zip),
               'ibge_unidades_municipais': len(ibge),
               'method': 'Casamento por UF+nome exato sem caixa; depois acentos/espaços normalizados, apenas se único. Sem fuzzy, aliases presumidos ou escolha entre duplicatas. Confronto adicional com código municipal embutido no CAR; nomes casados não sobrescrevem a origem. Contagens por situação podem sobrepor códigos com status conflitantes.'}
    write_json(result / 'resumo.json', summary)
    print(json.dumps({'etapa': 'car', 'saida': str(result), 'stats': dict(stats), 'casamentos': dict(matches)}), flush=True)
    return result


def iter_prepared_features(path):
    """Itera os GeoJSONs deste preparador sem carregar a coleção inteira."""
    decoder = json.JSONDecoder()
    with Path(path).open(encoding='utf-8') as stream:
        buffer = ''
        while '"features":[' not in buffer:
            chunk = stream.read(65536)
            if not chunk:
                raise ValueError('Coleção preparada sem array features.')
            buffer += chunk
        buffer = buffer.split('"features":[', 1)[1]
        while True:
            buffer = buffer.lstrip(' \n\r\t,')
            if buffer.startswith(']'):
                return
            try:
                feature, end = decoder.raw_decode(buffer)
            except json.JSONDecodeError:
                chunk = stream.read(65536)
                if not chunk:
                    raise ValueError('GeoJSON preparado truncado.')
                buffer += chunk
                continue
            yield feature
            buffer = buffer[end:]


def latest_result(processed, name):
    return next(p for p in sorted(processed.glob(name + '-*'), reverse=True) if (p / 'resumo.json').is_file())


def validate_outputs(processed, arrow_dir):
    if arrow_dir:
        sys.path.insert(0, str(arrow_dir.resolve()))
    import pyarrow.parquet as pq
    results = {}
    for kind, folder_name in [('embargos', 'por_uf'), ('cnfp', 'tipo_b')]:
        folder = latest_result(processed, kind)
        summary = json.loads((folder / 'resumo.json').read_bytes())
        counts = Counter()
        files = 0
        for path in sorted((folder / folder_name).rglob('*.geojson')):
            files += 1
            for feature in iter_prepared_features(path):
                geometry = shape(feature['geometry'])
                if geometry.is_empty or not geometry.is_valid or geometry.geom_type not in {'Polygon', 'MultiPolygon'}:
                    raise ValueError('Saída vetorial inválida: ' + str(path))
                properties = feature['properties']
                if any('cpf' in key.lower() or 'cnpj' in key.lower() or key.lower() in {'nome', 'nome_embargado'} for key in properties):
                    raise ValueError('Campo pessoal inesperado em saída vetorial.')
                if kind == 'embargos':
                    category = classify_embargo({key.upper(): value for key, value in properties.items()})[0]
                    if category != properties['classe_operacional'] or category != path.stem:
                        raise ValueError('Classe vetorial diverge dos indicadores.')
                    counts[(properties['uf'], category)] += 1
                else:
                    if properties['tipo'] != 'B':
                        raise ValueError('Feição não-B na saída Tipo B.')
                    counts[(properties['uf'], 'B')] += 1
        if kind == 'embargos':
            expected = {(uf, category.removeprefix('geometrias_')): count
                        for uf, values in summary['por_uf'].items() for category, count in values.items()
                        if category.startswith('geometrias_')}
        else:
            expected = {(uf, 'B'): values['tipo_B_geometrias'] for uf, values in summary['por_uf'].items() if values.get('tipo_B_geometrias')}
        if dict(counts) != expected:
            raise ValueError('Contagens vetoriais divergem do resumo.')
        results[kind] = {'folder': str(folder), 'geojson_files': files, 'valid_polygon_features': sum(counts.values()), 'counts_match_summary': True, 'no_personal_columns': True}
    folder = latest_result(processed, 'car-tabular')
    summary = json.loads((folder / 'resumo.json').read_bytes())
    parquet = pq.ParquetFile(folder / 'car_tabular_sem_geometria.parquet')
    if any(c in parquet.schema_arrow.names for c in ['geometry', 'bbox']) or b'geo' in (parquet.schema_arrow.metadata or {}):
        raise ValueError('Saída CAR contém coluna ou metadado espacial indevido.')
    if parquet.metadata.num_rows != summary['stats']['registros']:
        raise ValueError('Contagem do Parquet projetado diverge.')
    connection = sqlite3.connect(folder / 'auditoria_codigos.sqlite')
    quick = connection.execute('PRAGMA quick_check').fetchone()[0]
    count = connection.execute('SELECT count(*) FROM linhas').fetchone()[0]
    connection.close()
    if quick != 'ok' or count != parquet.metadata.num_rows:
        raise ValueError('Auditoria SQLite falhou.')
    if sum(summary['casamento_municipios'].values()) != count:
        raise ValueError('Contagem de casamento municipal diverge.')
    results['car'] = {'folder': str(folder), 'rows': count, 'columns': parquet.schema_arrow.names,
                      'no_geometry_or_spatial_metadata': True, 'sqlite_quick_check': quick,
                      'municipality_counts_match': True}
    target = processed / ('validacao-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
    write_json(target, {'validated_at_utc': utc(), 'results': results})
    print(json.dumps({'validacao': str(target), 'results': results}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--etapa', choices=['baixar', 'embargos', 'cnfp', 'car', 'validar', 'comparar', 'inventario'], required=True)
    parser.add_argument('--execucao', required=True, help='Identificador do snapshot; apenas letras, dígitos, hífen e sublinhado.')
    parser.add_argument('--base', type=Path, default=BASE)
    parser.add_argument('--ipaam', type=Path, default=ROOT.parent / 'dados/amazonas/brutos/ambiental/embargos_ipaam.geojson')
    parser.add_argument('--pyarrow-dir', type=Path)
    parser.add_argument('--ibge-zip', type=Path, default=BASE / 'brutos/focos/ibge/BR_Municipios_2025.zip')
    args = parser.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_-]+', args.execucao):
        parser.error('Identificador de execução inválido.')
    base = args.base.resolve()
    if base == ROOT or base.is_relative_to(ROOT):
        parser.error('As saídas devem ficar fora do repositório do site.')
    raw, processed = base / 'brutos/etapa6' / args.execucao, base / 'processados/etapa6' / args.execucao
    if args.etapa == 'baixar':
        acquire(raw)
    elif args.etapa == 'embargos':
        prepare_embargos(raw, processed, args.ipaam)
    elif args.etapa == 'cnfp':
        prepare_cnfp(raw, processed)
    elif args.etapa == 'validar':
        validate_outputs(processed, args.pyarrow_dir)
    elif args.etapa == 'comparar':
        target = latest_result(processed, 'embargos') / ('comparacao_secundaria-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        compare_secondary_keys(raw / 'ibama/termo_de_embargo.csv', args.ipaam, target)
    elif args.etapa == 'inventario':
        files = []
        for directory in [raw, processed]:
            for entry in inventory(directory):
                entry['path'] = (directory / entry['path']).relative_to(base).as_posix()
                files.append(entry)
        target = processed / ('inventario-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '.json')
        write_json(target, {'created_at_utc': utc(), 'base': str(base), 'files': files,
                            'python': sys.version, 'shapely': shapely.__version__, 'geos': shapely.geos_version_string})
        print(json.dumps({'inventario': str(target), 'files': len(files), 'bytes': sum(f['bytes'] for f in files)}), flush=True)
    else:
        prepare_car(raw, processed, args.pyarrow_dir, args.ibge_zip)


if __name__ == '__main__':
    main()
