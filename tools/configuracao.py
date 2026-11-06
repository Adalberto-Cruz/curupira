"""Configuracao local, fora do diretorio publico."""
import os
import re
from pathlib import Path

from dotenv.parser import parse_stream
from dotenv import set_key

ROOT = Path(__file__).resolve().parents[1]


def project_id(explicit=None, root=ROOT, environ=None):
    environ = os.environ if environ is None else environ
    value = explicit if explicit is not None else environ.get('GOOGLE_CLOUD_PROJECT')
    if value is None:
        path = root / '.env'
        try:
            with path.open(encoding='utf-8-sig') as stream:
                values = {}
                for binding in parse_stream(stream):
                    if binding.error:
                        raise ValueError('Arquivo .env invalido. Use GOOGLE_CLOUD_PROJECT=ID_DO_PROJETO.')
                    if binding.key:
                        values[binding.key] = binding.value
            value = values.get('GOOGLE_CLOUD_PROJECT')
        except FileNotFoundError:
            value = None
        except (OSError, UnicodeError):
            raise ValueError('Nao foi possivel ler o .env do projeto.') from None
    value = (value or '').strip()
    if value and not re.fullmatch(r'[a-z][a-z0-9-]{4,28}[a-z0-9]', value):
        raise ValueError('GOOGLE_CLOUD_PROJECT invalido. Informe o ID do projeto, nao uma chave de API.')
    return value


def configure_project(explicit=None, root=ROOT, environ=None):
    value = project_id(explicit, root, environ)
    if value:
        return value
    try:
        value = project_id(input('ID do projeto Google Cloud: '), root, {})
        if not value:
            raise ValueError('Informe um ID de projeto para configurar o Earth Engine.')
        save = input('Gravar GOOGLE_CLOUD_PROJECT no .env local? [s/N]: ').strip().lower()
    except (EOFError, KeyboardInterrupt):
        raise ValueError('Configuracao cancelada. Defina GOOGLE_CLOUD_PROJECT no ambiente ou no .env.') from None
    if save in {'s', 'sim'}:
        try:
            set_key(root / '.env', 'GOOGLE_CLOUD_PROJECT', value, quote_mode='never', encoding='utf-8-sig')
        except (OSError, UnicodeError):
            raise ValueError('Nao foi possivel gravar o .env local.') from None
    return value
