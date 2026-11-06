"""Contrato HTTP da prova, sem navegador, dados reais ou serviços externos."""
import json
import hashlib
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import prova_maplibre_servidor as server
import prova_maplibre_estado as state
from unittest.mock import patch


class ProofHTTPTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = server.DATA, server.PMDATA
        cls.temp = tempfile.TemporaryDirectory()
        server.DATA = Path(cls.temp.name) / 'libs'
        server.PMDATA = Path(cls.temp.name) / 'pm'
        server.DATA.mkdir()
        server.PMDATA.mkdir()
        (server.PMDATA / 'car-am.pmtiles').write_bytes(bytes(range(256)) * 8)
        (server.DATA / 'test.mjs').write_text('export const n=1;', encoding='utf-8')
        (server.DATA / 'bibliotecas.json').write_text(json.dumps({'test.mjs': {}}), encoding='utf-8')
        cls.http = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        threading.Thread(target=cls.http.serve_forever, daemon=True).start()
        cls.url = f'http://127.0.0.1:{cls.http.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown()
        cls.http.server_close()
        server.DATA, server.PMDATA = cls.original
        cls.temp.cleanup()

    def test_ranges(self):
        for value, expected, size in [('bytes=0-126', 'bytes 0-126/2048', 127), ('bytes=2000-', 'bytes 2000-2047/2048', 48)]:
            with urlopen(Request(self.url + '/prova-data/car-am.pmtiles', headers={'Range': value})) as response:
                self.assertEqual(response.status, 206)
                self.assertEqual(response.headers['Content-Range'], expected)
                self.assertEqual(len(response.read()), size)
        for value in ['bytes=2048-', 'bytes=100-50', 'bytes=0-1,5-6']:
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(self.url + '/prova-data/car-am.pmtiles', headers={'Range': value}))
            self.assertEqual(error.exception.code, 416)

    def test_head_and_module_mime(self):
        with urlopen(Request(self.url + '/prova-data/car-am.pmtiles', method='HEAD')) as response:
            self.assertEqual(response.headers['Content-Length'], '2048')
            self.assertEqual(response.read(), b'')
        with urlopen(self.url + '/prova-maplibre-data/test.mjs') as response:
            self.assertEqual(response.headers['Content-Type'], 'text/javascript')

    def test_whitelist(self):
        for path in ['/mapa.html', '/.env', '/prova-data/acesso-local.txt', '/prova-maplibre-data/../.env']:
            with self.assertRaises(HTTPError) as error:
                urlopen(self.url + path)
            self.assertEqual(error.exception.code, 404)

    def test_save_results(self):
        payload = {'rows': [], 'selection': ''}
        with urlopen(Request(self.url + '/prova-maplibre-medidas', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})) as response:
            self.assertEqual(response.status, 204)
        self.assertEqual(json.loads((server.DATA / 'medidas.jsonl').read_text(encoding='utf-8')), payload)

    def test_invalid_results(self):
        for payload in [b'no-json', b'[]', b'']:
            with self.assertRaises(HTTPError) as error:
                urlopen(Request(self.url + '/prova-maplibre-medidas', data=payload))
            self.assertEqual(error.exception.code, 400)


class StatePreparationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'input.geojson'
        self.feature = {'type': 'Feature', 'properties': {'cod_imovel': 'MT-5103403-' + 'A' * 32, 'ind_status': 'AT', 'campo_descartado': 'não publicar'},
                        'geometry': {'type': 'Polygon', 'coordinates': [[[-56, -12], [-55.99, -12], [-55.99, -11.99], [-56, -12]]]}}

    def write(self, features):
        self.source.write_text(json.dumps({'type': 'FeatureCollection', 'features': features}), encoding='utf-8')

    def test_sanitizes_without_overwriting(self):
        self.write([self.feature])
        with patch.object(state, 'OUT', self.root / 'out'):
            state.prepare(self.source, 'MT', 'fixture local')
            output = json.loads((state.OUT / 'car-mt.geojson').read_bytes())
            self.assertEqual(set(output['features'][0]['properties']), {'code', 'status'})
            with self.assertRaises(FileExistsError):
                state.prepare(self.source, 'MT', 'fixture local')

    def test_rejects_duplicate_codes(self):
        self.write([self.feature, self.feature])
        with patch.object(state, 'OUT', self.root / 'out'):
            with self.assertRaisesRegex(ValueError, 'duplicado'):
                state.prepare(self.source, 'MT', 'fixture local')
            self.assertFalse(state.OUT.exists())

    def test_rejects_wrong_uf_and_unknown_status(self):
        self.write([self.feature])
        with self.assertRaisesRegex(ValueError, 'UF'):
            state.prepare(self.source, 'PA', 'fixture local')
        self.feature['properties']['ind_status'] = 'XX'
        self.write([self.feature])
        with self.assertRaisesRegex(ValueError, 'Situação'):
            state.prepare(self.source, 'MT', 'fixture local')

    def test_duplicate_audit_is_bound_to_input_and_preserves_rows(self):
        self.write([self.feature, self.feature])
        audit = self.root / 'audit.json'
        report = {'source_sha256': hashlib.sha256(self.source.read_bytes()).hexdigest(),
                  'rows_extracted_mt': 2, 'unique_codes_mt': 1}
        audit.write_text(json.dumps(report), encoding='utf-8')
        with patch.object(state, 'OUT', self.root / 'out'):
            state.prepare(self.source, 'MT', 'fixture local', audit)
            output = json.loads((state.OUT / 'car-mt.geojson').read_bytes())
            self.assertEqual(len(output['features']), 2)
            self.feature['properties']['ind_status'] = 'PE'
            self.write([self.feature, self.feature])
            with self.assertRaisesRegex(ValueError, 'Auditoria'):
                state.prepare(self.source, 'MT', 'fixture local', audit)


if __name__ == '__main__':
    unittest.main()
