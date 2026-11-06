"""Le a paleta independente dos produtos gerados."""
from pathlib import Path
import json
import math
import re

DEFAULT_PATH = Path(__file__).resolve().parents[1] / 'dist/data/ambiental/paleta.json'
MODES = {'ti': 'outline', 'anm': 'outline', 'embargos': 'outline', 'prodes': 'event', 'deter': 'event', 'focos': 'point'}


def validate_palette(palette):
    def fail(detail):
        raise ValueError('Paleta visual invalida em paleta.json: ' + detail)

    def color(value):
        return isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value)

    def dash(value):
        return value is None or isinstance(value, str) and re.fullmatch(r'[\d. ,]*', value) is not None

    def number(value):
        return type(value) in (int, float) and math.isfinite(value)

    if not isinstance(palette, dict) or type(palette.get('version')) is not int or palette['version'] != 1:
        fail('versao nao suportada.')
    municipalities = palette.get('municipalities')
    if not isinstance(municipalities, dict) or not all(color(municipalities.get(k)) for k in ['color', 'selectedColor', 'hoverColor']):
        fail('cores dos municipios ausentes ou invalidas.')
    scale = municipalities.get('countScale')
    if not isinstance(scale, list) or len(scale) != 6 or not all(color(c) for c in scale):
        fail('escala municipal invalida.')
    cars = palette.get('cars')
    if not isinstance(cars, dict) or set(cars) != {'AT', 'PE', 'SU', 'CA'} or not all(isinstance(s, dict) and color(s.get('color')) and dash(s.get('dashArray')) for s in cars.values()):
        fail('situacoes CAR ausentes ou invalidas.')
    if len({s['color'].lower() for s in cars.values()}) != 4:
        fail('situacoes CAR com cores repetidas.')
    selection = palette.get('carSelection')
    if not isinstance(selection, dict) or not color(selection.get('color')) or not color(selection.get('hoverColor')):
        fail('destaque CAR invalido.')
    layers = palette.get('layers')
    if not isinstance(layers, dict) or set(layers) != set(MODES):
        fail('camadas ausentes ou invalidas.')
    colors = []
    for name, mode in MODES.items():
        spec = layers[name]
        style = spec.get('style') if isinstance(spec, dict) else None
        if not isinstance(spec, dict) or not color(spec.get('color')) or not isinstance(style, dict) or style.get('mode') != mode:
            fail('estilo da camada ' + name + '.')
        if not number(style.get('weight')) or style['weight'] <= 0 or not number(style.get('fillOpacity')) or not 0 <= style['fillOpacity'] <= 1 or not dash(style.get('dashArray')):
            fail('espessura ou preenchimento da camada ' + name + '.')
        if mode == 'outline' and style['fillOpacity'] != 0 or mode != 'outline' and style['fillOpacity'] == 0 or mode == 'point' and (not number(style.get('radius')) or style['radius'] <= 0):
            fail('preenchimento ou raio da camada ' + name + '.')
        colors.append(spec['color'].lower())
        if name == 'deter':
            categories = style.get('categories')
            if not isinstance(categories, dict) or not categories:
                fail('classes DETER ausentes.')
            for category in categories.values():
                if not isinstance(category, dict) or not color(category.get('color')) or not isinstance(category.get('label'), str) or not category['label'].strip() or not dash(category.get('dashArray')) or 'weight' in category or 'fillOpacity' in category:
                    fail('classe DETER invalida.')
                colors.append(category['color'].lower())
    if len({spec['color'].lower() for spec in layers.values()}) != 6:
        fail('cada camada precisa de uma cor propria.')
    if municipalities['selectedColor'].lower() in colors:
        fail('municipio selecionado usa cor de camada ambiental.')
    if not isinstance(palette.get('method'), dict) or not isinstance(palette['method'].get('note'), str):
        fail('metodo ausente.')
    return palette


def load_palette(path=DEFAULT_PATH):
    try:
        palette = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    except FileNotFoundError:
        raise ValueError('Paleta visual ausente: restaure dist/data/ambiental/paleta.json.') from None
    except (OSError, UnicodeError, json.JSONDecodeError):
        raise ValueError('Paleta visual invalida ou ilegivel: confira dist/data/ambiental/paleta.json.') from None
    return validate_palette(palette)
