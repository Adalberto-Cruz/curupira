"""Baixa somente as fontes aprovadas para a Etapa 2c-1."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import time
import zipfile

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent / 'dados/brasil/brutos/focos'
BASE = 'https://dataserver-coids.inpe.br/queimadas/queimadas/focos/csv/'
MESH_URL = 'https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/Brasil/BR_Municipios_2025.zip'


def sha256(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sources(as_of):
    if as_of.year != 2026:
        raise ValueError('Este lote aprovado usa --ate em 2026; revise o escopo antes de ampliar.')
    files = [dict(kind='annual', year=year, path=f'anuais/focos_br_ref_{year}.zip',
                  url=BASE+f'anual/Brasil_sat_ref/focos_br_ref_{year}.zip') for year in range(2003, 2026)]
    files += [dict(kind='monthly', year=2026, month=month,
                   path=f'mensais/focos_mensal_br_2026{month:02}.csv',
                   url=BASE+f'mensal/Brasil/focos_mensal_br_2026{month:02}.csv',
                   provisional=month == as_of.month) for month in range(1, as_of.month+1)]
    files += [dict(kind='comparison_sample', year=2025, month=4,
                   path='amostra/focos_mensal_br_202504.csv',
                   url=BASE+'mensal/Brasil/focos_mensal_br_202504.csv'),
              dict(kind='mesh', year=2025, path='ibge/BR_Municipios_2025.zip', url=MESH_URL)]
    return files


def download(spec, raw):
    path = raw / spec['path']
    path.parent.mkdir(parents=True, exist_ok=True)
    sidecar = path.with_name(path.name+'.fonte.json')
    if path.exists() and sidecar.exists():
        previous = json.loads(sidecar.read_text(encoding='utf-8'))
        if previous.get('url') == spec['url'] and previous.get('sha256') == sha256(path):
            print('Reutilizado: '+spec['path'], flush=True)
            return {**previous, **spec}
        raise ValueError(f'Arquivo local diferente do manifesto: {path}. Preserve e revise antes de baixar novamente.')
    if path.exists():
        raise ValueError(f'Arquivo sem proveniencia: {path}. Nao sera sobrescrito.')
    partial = path.with_name(path.name+'.partial')
    for attempt in range(4):
        try:
            size = partial.stat().st_size if partial.exists() else 0
            headers = {'User-Agent': 'Hibama/2c-1 source-collector'}
            if size:
                headers['Range'] = f'bytes={size}-'
            with requests.get(spec['url'], headers=headers, stream=True, timeout=(20, 90)) as response:
                response.raise_for_status()
                append = size > 0 and response.status_code == 206
                if append and not response.headers.get('Content-Range', '').startswith(f'bytes {size}-'):
                    raise ValueError('Resposta Range inconsistente; nao anexar bytes.')
                expected = response.headers.get('Content-Length')
                received = 0
                with partial.open('ab' if append else 'wb') as stream:
                    for block in response.iter_content(1024*1024):
                        if block:
                            stream.write(block)
                            received += len(block)
                if expected and received != int(expected):
                    raise ValueError('Download incompleto: tamanho diferente do informado pelo servidor.')
                metadata = {**spec, 'bytes': partial.stat().st_size, 'sha256': sha256(partial),
                            'collected_at_utc': datetime.now(timezone.utc).isoformat(),
                            'last_modified': response.headers.get('Last-Modified'),
                            'etag': response.headers.get('ETag')}
            if path.suffix == '.zip':
                with zipfile.ZipFile(partial) as archive:
                    if archive.testzip():
                        raise ValueError('ZIP com erro de integridade.')
                    metadata['members'] = [{'name': info.filename, 'bytes': info.file_size} for info in archive.infolist()]
            else:
                with partial.open('rb') as stream:
                    header = stream.readline().lower()
                if not partial.stat().st_size or b'lat' not in header:
                    raise ValueError('Resposta nao parece um CSV de focos.')
            partial.rename(path)
            sidecar.write_text(json.dumps(metadata, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
            print(f"Baixado: {spec['path']} ({metadata['bytes']:,} bytes)", flush=True)
            return metadata
        except (requests.RequestException, OSError, ValueError, zipfile.BadZipFile) as error:
            if attempt == 3:
                raise RuntimeError(f"Falha em {spec['url']}: {error}") from error
            time.sleep(min(2**attempt, 8))
    raise RuntimeError('Download nao concluido.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ate', type=date.fromisoformat, required=True)
    parser.add_argument('--brutos', type=Path, default=RAW)
    parser.add_argument('--workers', type=int, choices=range(1, 5), default=3)
    args = parser.parse_args()
    try:
        specs = sources(args.ate)
        args.brutos.mkdir(parents=True, exist_ok=True)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            entries = list(pool.map(lambda spec: download(spec, args.brutos), specs))
        manifest = {'version': 1, 'as_of': args.ate.isoformat(), 'sources': entries,
                    'scope': 'Referencia 2003-2025; mensais somente 2026; uma amostra de abril/2025 para confronto; malha IBGE 2025.'}
        (args.brutos/'coleta.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
        print(f'OK: {len(entries)} fontes, {sum(e["bytes"] for e in entries):,} bytes.', flush=True)
        return 0
    except (OSError, ValueError, RuntimeError) as error:
        parser.exit(1, str(error)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
