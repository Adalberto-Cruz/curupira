"""Contratos da preparação: classificação, reparo, privacidade e casamento por UF."""
from collections import defaultdict
import csv
import gzip
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

import shapefile
from shapely.geometry import GeometryCollection, LineString, Point, Polygon, shape

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from etapa6_comum import classify_embargo, clean_geometry, fold, term_key
import preparar_etapa6_nacional as prepare


class ClassificationTests(unittest.TestCase):
    def test_ipaam_zero_sequence_joins_each_document_independently(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'ipaam.json'
            source.write_text(json.dumps({'features': [
                {'properties': {'seq_tad': 0, 'num_tad': number, 'serie_tad': None}}
                for number in ['A', 'B']]}), encoding='utf-8')
            national = {term_key('', number, '', 1): [('indeterminado', None)]
                        for number in ['A', 'B']}
            result = prepare.compare_ipaam(national, source, root, national)
            self.assertEqual(result['termos_distintos_ipaam'], 2)
            self.assertEqual(result['seq_tad_preenchidos_distintos_ipaam'], 0)
            self.assertEqual(result['linhas_sem_seq_tad_ipaam'], 2)
            self.assertEqual(result['contagens']['termos_comuns'], 2)

    def test_empty_identifiers_in_both_sources_use_document_or_row(self):
        self.assertEqual(term_key(None, 'abc', None, 1), term_key('', 'ABC', '', 999))
        self.assertEqual(term_key(0, 'abc', None, 1), term_key('', 'ABC', '', 999))
        self.assertNotEqual(term_key(None, '', '', 1), term_key(None, '', '', 2))
        self.assertNotEqual(term_key('ABC', '', '', 1), term_key(None, 'ABC', '', 1))

    def base(self, **changes):
        return {'DES_STATUS_FORMULARIO': 'Lavrado', 'DES_STATUS_FORMULARIO_AIE': '',
                'SIT_CANCELADO': 'N', 'SIT_DESEMBARGO': '', **changes}

    def test_release_and_cancellation_overlap_preserved(self):
        category, flags = classify_embargo(self.base(SIT_CANCELADO='S', SIT_DESEMBARGO='S'))
        self.assertEqual(category, 'desembargado')
        self.assertTrue(flags['cancelado_indicado'])
        self.assertTrue(flags['sobreposicao_cancelado_desembargado'])

    def test_cancel_status_wins_over_negative_cancel_flag(self):
        self.assertEqual(classify_embargo(self.base(DES_STATUS_FORMULARIO='Cancelado'))[0], 'cancelado')

    def test_incomplete_or_inconsistent_not_active(self):
        for row in [self.base(SIT_CANCELADO=''), self.base(DAT_DESEMBARGO='2020-01-01'),
                    self.base(TIPO_DESEMBARGO='Judicial')]:
            self.assertEqual(classify_embargo(row)[0], 'indeterminado')

    def test_excluded_and_replaced_not_active(self):
        self.assertEqual(classify_embargo(self.base(DES_STATUS_FORMULARIO_AIE='Excluído'))[0], 'excluido')
        self.assertEqual(classify_embargo(self.base(DES_STATUS_FORMULARIO='Substituído por outro'))[0], 'substituido')
        self.assertEqual(classify_embargo(self.base())[0], 'vigente')


class GeometryTests(unittest.TestCase):
    def test_structure_repairs_bowtie(self):
        bowtie = Polygon([(0, 0), (2, 2), (0, 2), (2, 0), (0, 0)])
        geometry, audit = clean_geometry(bowtie)
        self.assertTrue(geometry.is_valid)
        self.assertAlmostEqual(geometry.area, 2)
        self.assertTrue(audit['invalid_before'])
        self.assertTrue(audit['repaired'])

    def test_preserves_only_polygonal_surface(self):
        surface = Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])
        geometry, _ = clean_geometry(GeometryCollection([surface, LineString([(0, 0), (4, 4)])]))
        self.assertEqual(geometry.area, surface.area)
        self.assertEqual(clean_geometry(Point(0, 0))[1]['reason'], 'sem_parte_poligonal')

    def test_out_of_bounds_and_empty_quarantined(self):
        self.assertIsNone(clean_geometry(Polygon())[0])
        geometry = Polygon([(200, 0), (201, 0), (201, 1), (200, 0)])
        self.assertEqual(clean_geometry(geometry)[1]['reason'], 'fora_coordenadas_geograficas')


class MunicipalityTests(unittest.TestCase):
    def test_match_uses_uf_and_normalization_without_fuzzy(self):
        exact = {('MA', 'SÃO LUÍS'): {'2111300'}, ('RR', 'BOA VISTA'): {'1400100'}}
        normalized = {(uf, fold(name)): codes for (uf, name), codes in exact.items()}
        self.assertEqual(prepare.municipality_match('MA', 'Sao Luis', exact, normalized), ('2111300', 'normalizado_acentos_espacos'))
        self.assertEqual(prepare.municipality_match('RR', 'Sao Luis', exact, normalized)[1], 'sem_correspondencia')
        self.assertEqual(prepare.municipality_match('RR', 'Boa Vistaa', exact, normalized)[1], 'sem_correspondencia')

    def test_normalized_collision_never_chosen(self):
        self.assertEqual(prepare.municipality_match('XX', 'Sao Luis', {}, {('XX', 'SAO LUIS'): {'1', '2'}}), ('', 'ambiguo'))


class ParquetReadBoundaryTests(unittest.TestCase):
    def test_http_version_change_cannot_mix_cached_ranges(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / 'origem_http.json').write_text(json.dumps({'url': 'https://example.test/data', 'bytes': 1000, 'etag': 'old'}))
            session = SimpleNamespace(head=lambda *a, **kw: SimpleNamespace(headers={'ETag': 'new'}))
            with patch.object(prepare.requests, 'Session', return_value=session):
                with self.assertRaisesRegex(ValueError, 'Versão HTTP'):
                    prepare.TabularParquetRemote('https://example.test/data', 1000, path)

    def test_envelope_cannot_cross_geometry_column(self):
        from types import SimpleNamespace
        columns = [SimpleNamespace(path_in_schema='cod_imovel', has_dictionary_page=False, data_page_offset=4, total_compressed_size=20),
                   SimpleNamespace(path_in_schema='geometry', has_dictionary_page=False, data_page_offset=24, total_compressed_size=100),
                   SimpleNamespace(path_in_schema='ind_status', has_dictionary_page=False, data_page_offset=124, total_compressed_size=10)]
        group = SimpleNamespace(num_columns=len(columns), column=lambda i: columns[i])
        remote = prepare.TabularParquetRemote.__new__(prepare.TabularParquetRemote)
        remote.fetch = lambda start, end: self.fail('Não deve requisitar envelope com geometria')
        with self.assertRaisesRegex(ValueError, 'coluna não autorizada'):
            remote.set_group(group, ['cod_imovel', 'ind_status'])

    def test_read_outside_authorized_span_is_blocked(self):
        remote = prepare.TabularParquetRemote.__new__(prepare.TabularParquetRemote)
        remote.size, remote.footer_start, remote.footer = 1000, 900, bytes(100)
        remote.span, remote.header = (10, 19, b'0123456789'), b'PAR1'
        remote.seek(10)
        self.assertEqual(remote.read(3), b'012')
        remote.seek(50)
        with self.assertRaisesRegex(ValueError, 'colunas tabulares'):
            remote.read(10)


class SmallPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.raw = self.base / 'raw'
        self.processed = self.base / 'processed'

    def test_embargos_preserves_duplicate_terms_and_sanitizes(self):
        path = self.raw / 'ibama/termo_de_embargo.csv'
        path.parent.mkdir(parents=True)
        fields = ['SEQ_TAD', 'UF', 'GEOM_AREA_EMBARGADA', 'DES_STATUS_FORMULARIO',
                  'SIT_CANCELADO', 'SIT_DESEMBARGO', 'NOME_EMBARGADO', 'CPF_CNPJ_EMBARGADO']
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter=';')
            writer.writeheader()
            base = {'SEQ_TAD': '1', 'UF': 'AM', 'GEOM_AREA_EMBARGADA': 'POLYGON ((0 0,1 0,1 1,0 0))',
                    'DES_STATUS_FORMULARIO': 'Lavrado', 'SIT_CANCELADO': 'N', 'SIT_DESEMBARGO': '',
                    'NOME_EMBARGADO': 'RESTRITO', 'CPF_CNPJ_EMBARGADO': 'RESTRITO'}
            writer.writerow(base)
            writer.writerow({**base, 'SIT_CANCELADO': 'S', 'DES_STATUS_FORMULARIO': 'Cancelado'})
            writer.writerow({**base, 'SEQ_TAD': '2', 'GEOM_AREA_EMBARGADA': ''})
        result = prepare.prepare_embargos(self.raw, self.processed, self.base / 'missing.geojson')
        summary = json.loads((result / 'resumo.json').read_bytes())
        self.assertEqual(summary['stats']['registros'], 3)
        self.assertEqual(summary['stats']['seq_tad_distintos'], 2)
        self.assertEqual(summary['stats']['termos_uf_com_classes_conflitantes'], 1)
        features = json.loads((result / 'por_uf/AM/vigente.geojson').read_bytes())
        self.assertIsNone(features['crs'])
        self.assertEqual(len(features['features']), 1)
        self.assertNotIn('nome_embargado', features['features'][0]['properties'])
        with gzip.open(result / 'registros_sanitizados.csv.gz', 'rt', encoding='utf-8') as stream:
            self.assertNotIn('RESTRITO', stream.read())

    def test_secondary_key_records_unique_candidate_without_changing_identifier(self):
        source = self.base / 'terms.csv'
        fields = ['SEQ_TAD', 'NUM_TAD', 'SER_TAD', 'UF', 'DES_STATUS_FORMULARIO', 'SIT_CANCELADO', 'SIT_DESEMBARGO']
        with source.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter=';')
            writer.writeheader()
            writer.writerow({'SEQ_TAD': '', 'NUM_TAD': 'ABC', 'SER_TAD': '', 'UF': 'AM', 'DES_STATUS_FORMULARIO': '', 'SIT_CANCELADO': 'N', 'SIT_DESEMBARGO': ''})
            writer.writerow({'SEQ_TAD': '123', 'NUM_TAD': 'DEF', 'SER_TAD': '', 'UF': 'AM', 'DES_STATUS_FORMULARIO': '', 'SIT_CANCELADO': 'N', 'SIT_DESEMBARGO': ''})
        local = self.base / 'ipaam.geojson'
        local.write_text(json.dumps({'features': [
            {'properties': {'seq_tad': 'OLD', 'num_tad': 'ABC', 'serie_tad': ''}},
            {'properties': {'seq_tad': 0, 'num_tad': 'DEF', 'serie_tad': None}}]}))
        before = local.read_bytes()
        report = prepare.compare_secondary_keys(source, local, self.base / 'comparison.json')
        self.assertEqual(report['counts']['alternativa_unica_numero_serie'], 2)
        self.assertEqual(report['details'][0]['candidatos'][0]['seq_tad'], '')
        self.assertEqual(local.read_bytes(), before)

    def test_cnfp_crs_polygonz_and_type_b_only(self):
        stem = self.base / 'CNFP_2025'
        writer = shapefile.Writer(str(stem), shapeType=shapefile.POLYGONZ, encoding='utf-8')
        for key, kind in [('tipo', 'C'), ('uf', 'C'), ('geocodigo', 'C'), ('area_ha', 'N'), ('nome', 'C')]:
            writer.field(key, kind)
        for kind in ['TIPO A', 'TIPO B']:
            writer.polyz([[[0, 0, 0], [0, 1, 0], [1, 1, 0], [0, 0, 0]]])
            writer.record(kind, 'AM', '1302603', 1, 'RESTRITO')
        writer.close()
        stem.with_suffix('.prj').write_text('GEOGCS["GCS_SIRGAS_2000",DATUM["D_SIRGAS_2000",SPHEROID["GRS_1980",6378137,298.257]],UNIT["Degree",0.01745]]')
        stem.with_suffix('.cpg').write_text('UTF-8')
        target = self.raw / 'cnfp/CNFP_2025.zip'
        target.parent.mkdir(parents=True)
        with zipfile.ZipFile(target, 'w') as archive:
            for path in stem.parent.glob('CNFP_2025.*'):
                archive.write(path, path.name)
        result = prepare.prepare_cnfp(self.raw, self.processed)
        summary = json.loads((result / 'resumo.json').read_bytes())
        self.assertEqual(summary['stats']['tipo_B'], 1)
        features = json.loads((result / 'tipo_b/AM.geojson').read_bytes())
        self.assertEqual(len(features['features']), 1)
        self.assertEqual(features['crs']['properties']['name'], 'EPSG:4674')
        self.assertNotIn('nome', features['features'][0]['properties'])
        self.assertTrue(shape(features['features'][0]['geometry']).is_valid)
        with self.assertRaises(ValueError):
            prepare.validate_cnfp_crs('PROJCS["SIRGAS_2000", "GRS_1980", UNIT["Degree",1]]')

    def test_blank_seq_tad_never_merges_distinct_electronic_terms(self):
        path = self.raw / 'ibama/termo_de_embargo.csv'
        path.parent.mkdir(parents=True)
        fields = ['SEQ_TAD', 'NUM_TAD', 'SER_TAD', 'UF', 'GEOM_AREA_EMBARGADA',
                  'DES_STATUS_FORMULARIO', 'SIT_CANCELADO', 'SIT_DESEMBARGO']
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=fields, delimiter=';')
            writer.writeheader()
            for number, cancel in [('AAA', 'N'), ('BBB', 'S')]:
                writer.writerow({'SEQ_TAD': '', 'NUM_TAD': number, 'SER_TAD': '', 'UF': 'AM',
                                 'GEOM_AREA_EMBARGADA': '', 'DES_STATUS_FORMULARIO': 'Lavrado',
                                 'SIT_CANCELADO': cancel, 'SIT_DESEMBARGO': ''})
        result = prepare.prepare_embargos(self.raw, self.processed, self.base / 'missing.geojson')
        stats = json.loads((result / 'resumo.json').read_bytes())['stats']
        self.assertEqual(stats['termos_identificados'], 2)
        self.assertEqual(stats['seq_tad_distintos'], 0)
        self.assertEqual(stats['seq_tad_vazio'], 2)
        self.assertEqual(stats['termos_uf_com_classes_conflitantes'], 0)


if __name__ == '__main__':
    unittest.main()
