import contextlib
import functools
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from configuracao import project_id, configure_project
import servidor_earth_engine as server
from verificar_commit import forbidden


class ConfigurationTests(unittest.TestCase):
    def test_interactive_save_preserves_other_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / '.env'
            path.write_text('# local\nOUTRA=valor\nGOOGLE_CLOUD_PROJECT=\n', encoding='utf-8')
            with patch('builtins.input', side_effect=['teste-projeto', 's']):
                self.assertEqual(configure_project(root=root, environ={}), 'teste-projeto')
            self.assertEqual(project_id(root=root, environ={}), 'teste-projeto')
            self.assertIn('OUTRA=valor', path.read_text(encoding='utf-8-sig'))

    def test_interactive_without_save_and_invalid_input(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch('builtins.input', side_effect=['teste-projeto', 'n']):
                self.assertEqual(configure_project(root=root, environ={}), 'teste-projeto')
            self.assertFalse((root / '.env').exists())
            for value in ['', 'ID_INVALIDO']:
                with patch('builtins.input', return_value=value), self.assertRaises(ValueError):
                    configure_project(root=root, environ={})
            with patch('builtins.input', side_effect=EOFError), self.assertRaises(ValueError):
                configure_project(root=root, environ={})
            with patch('builtins.input') as prompt:
                self.assertEqual(configure_project('teste-projeto', root, {}), 'teste-projeto')
                prompt.assert_not_called()

    def test_missing_mesh_and_busy_port(self):
        with patch.object(sys, 'argv', ['servidor', '--project', '']), \
             patch.object(Path, 'read_text', side_effect=FileNotFoundError), \
             contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised:
            server.main()
        self.assertEqual(raised.exception.code, 2)
        with patch.object(sys, 'argv', ['servidor', '--project', '']), \
             patch.object(server, 'ThreadingHTTPServer', side_effect=OSError), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()), \
             self.assertRaises(SystemExit) as raised:
            server.main()
        self.assertEqual(raised.exception.code, 2)

    def test_sources_and_precedence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(project_id(root=root, environ={}), '')
            path = root / '.env'
            path.write_text('\ufeff# comentario\nGOOGLE_CLOUD_PROJECT="teste-arquivo"\n', encoding='utf-8')
            self.assertEqual(project_id(root=root, environ={}), 'teste-arquivo')
            self.assertEqual(project_id(root=root, environ={'GOOGLE_CLOUD_PROJECT': 'teste-ambiente'}), 'teste-ambiente')
            self.assertEqual(project_id('teste-explicito', root, {'GOOGLE_CLOUD_PROJECT': 'teste-ambiente'}), 'teste-explicito')
            self.assertEqual(project_id(root=root, environ={'GOOGLE_CLOUD_PROJECT': ''}), '')
            path.write_text('GOOGLE_CLOUD_PROJECT="sem-fechar\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                project_id(root=root, environ={})
            path.write_bytes(b'\xff')
            with self.assertRaises(ValueError):
                project_id(root=root, environ={})

    def test_invalid_id_does_not_leak(self):
        for value in ['CHAVE_SECRETA', '$(executar)', 'x', 'a' * 31]:
            with self.assertRaises(ValueError) as raised:
                project_id(value)
            self.assertNotIn(value, str(raised.exception))

    def test_google_failure_keeps_static_server(self):
        with patch.object(sys, 'argv', ['servidor', '--project', 'teste-projeto']), \
             patch.dict(sys.modules, {'ee': unittest.mock.Mock()}), \
             patch.object(server, 'ThreadingHTTPServer') as http_server, \
             contextlib.redirect_stdout(io.StringIO()):
            sys.modules['ee'].Initialize.side_effect = RuntimeError('segredo de teste')
            self.assertEqual(server.main(), 0)
            self.assertFalse(server.ready)
            http_server.return_value.__enter__.return_value.serve_forever.assert_called_once()


class LocalServerTests(unittest.TestCase):
    def test_static_api_validation_and_private_file(self):
        class QuietHandler(server.Handler):
            def log_message(self, *args):
                pass
        server.ready = False
        with server.ThreadingHTTPServer(('127.0.0.1', 0), QuietHandler) as http_server:
            thread = threading.Thread(target=http_server.serve_forever, daemon=True)
            thread.start()
            connection = http.client.HTTPConnection(*http_server.server_address, timeout=5)
            try:
                connection.request('GET', '/mapa.html')
                response = connection.getresponse()
                self.assertEqual(response.status, 200)
                response.read()
                connection.request('GET', '/api/earth-engine')
                response = connection.getresponse()
                self.assertEqual(response.status, 503)
                self.assertIn('error', json.loads(response.read()))
                connection.request('GET', '/../.env')
                response = connection.getresponse()
                self.assertEqual(response.status, 404)
                response.read()
                server.ready = True
                connection.request('GET', '/api/earth-engine?start=invalida&end=2025-01-01')
                response = connection.getresponse()
                self.assertEqual(response.status, 400)
                response.read()
            finally:
                server.ready = False
                connection.close()
                http_server.shutdown()
                thread.join(timeout=5)


class PipelineTests(unittest.TestCase):
    def test_pdf_success_missing_and_corrupt(self):
        import pymupdf
        spec = importlib.util.spec_from_file_location('extrair', ROOT / 'scripts/extrair_pdfs_pesquisa.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            document = pymupdf.open()
            document.new_page().insert_text((50, 50), 'PDF de teste')
            document.save(root / 'valido.pdf')
            document.close()
            (root / 'corrompido.pdf').write_text('isto nao e PDF', encoding='utf-8')
            with patch.object(module, 'NAMES', ['valido.pdf', 'ausente.pdf', 'corrompido.pdf']), \
                 patch.object(sys, 'argv', ['extrair', '--entrada', str(root), '--saida', str(root / 'saida')]), \
                 contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(module.main(), 1)
            self.assertEqual(len(json.loads((root / 'saida/manifest.json').read_text(encoding='utf-8'))), 1)
            self.assertEqual(len(json.loads((root / 'saida/erros.json').read_text(encoding='utf-8'))), 2)

    def test_missing_input_has_no_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            process = subprocess.run([sys.executable, str(ROOT / 'scripts/extrair_pdfs_pesquisa.py'), '--entrada', str(root / 'ausente'), '--saida', str(root / 'saida')], capture_output=True)
            self.assertEqual(process.returncode, 2)
            self.assertFalse((root / 'saida').exists())

    def test_index_guard_real_blobs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            safe = root / 'seguro.txt'
            safe.write_text('ok', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', 'seguro.txt'], check=True)
            command = [sys.executable, str(ROOT / 'tools/verificar_commit.py')]
            self.assertEqual(subprocess.run(command, cwd=root, capture_output=True).returncode, 0)
            secret = root / '.env'
            secret.write_text('GOOGLE_CLOUD_PROJECT=teste-projeto', encoding='utf-8')
            subprocess.run(['git', '-C', str(root), 'add', '.env'], check=True)
            self.assertEqual(subprocess.run(command, cwd=root, capture_output=True).returncode, 1)
            subprocess.run(['git', '-C', str(root), 'rm', '--cached', '-q', '.env'], check=True)
            with safe.open('wb') as stream:
                stream.truncate(50_000_001)
            subprocess.run(['git', '-C', str(root), 'add', 'seguro.txt'], check=True)
            self.assertEqual(subprocess.run(command, cwd=root, capture_output=True).returncode, 1)
        self.assertTrue(forbidden('dist/data/ambiental/municipios/1302405.geojson'))
        self.assertFalse(forbidden('.env.example'))
        self.assertFalse(forbidden('dist/data/ambiental/catalogo.json'))


if __name__ == '__main__':
    unittest.main()
