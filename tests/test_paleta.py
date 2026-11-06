from pathlib import Path
import copy
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from paleta import load_palette, validate_palette


class PaletteTests(unittest.TestCase):
    def test_palette_is_independent_and_selection_is_unique(self):
        palette = load_palette()
        self.assertEqual(len(palette['layers']), 6)
        colors = {spec['color'].lower() for spec in palette['layers'].values()}
        colors.update(c['color'].lower() for c in palette['layers']['deter']['style']['categories'].values())
        self.assertNotIn(palette['municipalities']['selectedColor'].lower(), colors)
        self.assertNotEqual(palette['layers']['anm']['color'], palette['layers']['focos']['color'])
        catalog = json.loads((ROOT / 'dist/data/ambiental/catalogo.json').read_text(encoding='utf-8'))
        self.assertEqual(catalog['palette_file'], 'paleta.json')
        self.assertTrue(all('color' not in spec and 'style' not in spec for spec in catalog['layers']))

    def test_missing_corrupt_and_invalid_palette(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'paleta.json'
            with self.assertRaisesRegex(ValueError, 'ausente'):
                load_palette(path)
            for content in ['{', '[]', '{"version":1}', '\ufffd']:
                path.write_text(content, encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'invalida'):
                    load_palette(path)
        for mutation in [
            lambda p: p['layers']['ti']['style'].update(fillOpacity=.3),
            lambda p: p['municipalities'].update(selectedColor=p['layers']['ti']['color']),
            lambda p: p['layers']['focos'].update(color=p['layers']['anm']['color']),
            lambda p: p['cars']['AT'].update(color='url(invalida)'),
            lambda p: p['layers']['deter']['style']['categories'].clear(),
        ]:
            palette = copy.deepcopy(load_palette())
            mutation(palette)
            with self.assertRaisesRegex(ValueError, 'invalida'):
                validate_palette(palette)

    def test_generator_fails_before_writing_without_valid_palette(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / 'tools'
            tools.mkdir()
            for name in ['preparar_ambiental.py', 'paleta.py']:
                (tools / name).write_bytes((ROOT / 'tools' / name).read_bytes())
            command = [sys.executable, str(tools / 'preparar_ambiental.py')]
            process = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn('Paleta visual ausente', process.stderr)
            self.assertFalse((root / 'dist').exists())
            path = root / 'dist/data/ambiental/paleta.json'
            path.parent.mkdir(parents=True)
            path.write_text('{', encoding='utf-8')
            process = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn('Paleta visual invalida', process.stderr)
            self.assertFalse((path.parent / 'municipios').exists())
