"""Confere os blobs que estao no indice antes do commit."""
from pathlib import PurePosixPath
import subprocess

LIMIT = 50_000_000


def forbidden(name):
    parts = PurePosixPath(name).parts
    base = parts[-1].lower()
    return (
        any(p in {'.venv', 'acesso-local', '__pycache__', 'dados'} for p in parts)
        or (base == '.env' or base.startswith('.env.')) and base != '.env.example'
        or base.endswith(('.pem', '.key', '.rar', '.zip', '.tar.gz', '.pyc'))
        or base.startswith('credentials') and base.endswith('.json')
        or 'service-account' in base and base.endswith('.json')
        or name.startswith(('dist/data/ambiental/municipios/', 'dist/data/ambiental/intersecoes/', 'data/raw/', 'dist/data/brutos/'))
        or name.startswith('dist/data/focos-brasil/') and name != 'dist/data/focos-brasil/manifesto.json'
    )


def main():
    result = subprocess.run(['git', 'ls-files', '--stage', '-z'], check=True, capture_output=True)
    errors = []
    for entry in result.stdout.split(b'\0'):
        if not entry:
            continue
        metadata, raw_name = entry.split(b'\t', 1)
        mode, oid, stage = metadata.decode('ascii').split()
        name = raw_name.decode('utf-8')
        if stage != '0' or mode == '160000':
            errors.append(f'{name}: conflito ou repositorio aninhado')
            continue
        size = int(subprocess.check_output(['git', 'cat-file', '-s', oid]))
        if size > LIMIT or forbidden(name):
            errors.append(f'{name}: caminho proibido ou tamanho acima de 50 MB')
    if errors:
        print('\n'.join(errors))
        return 1
    print('OK: indice sem caminhos proibidos nem arquivos acima de 50 MB.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
