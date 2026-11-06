from pathlib import Path
import pymupdf as fitz
import json, hashlib

NAMES = ['Garimpo.pdf','Vista do Monitoramento de áreas embargadas por desmatamento ilegal.pdf','Queimadas e Ações.pdf','Credito-de-carbono-no-Brasil-Desafios-e-Perspectivas.-Revista-Meio-Ambiente-Brasil-v.7-n.3-269-284-2025.pdf','isprs-archives-XLVIII-3-2024-121-2024.pdf','isprs-archives-XLVIII-3-2024-583-2024.pdf','isprs-archives-XLVIII-3-2024-127-2024.pdf','isprs-archives-XLVIII-3-2024-357-2024.pdf','isprs-annals-X-1-W1-2023-835-2023.pdf','isprs-annals-X-1-W1-2023-999-2023.pdf','Vista do Prodes e o direito ambiental_ impactos técnicos e jurídicos na proteção da Amazônia.pdf','Vista do Drones, inteligência artificial e monitoramento remoto_ perspectivas tecnológicas para a atuação da PMPA na Amazônia. _ Revista ft.pdf','metodologia_DETER_format_020708.pdf','Vista do EVOLUÇÃO TEMPORAL DO SENSORIAMENTO REMOTO NO CONTEXTO DA DETECÇÃO DE ÁREAS DEGRADADAS NA AMAZÔNIA_ UMA REVISÃO SISTEMÁTICA.pdf','Vista do MAPEAMENTO ALÉM DAS FLORESTAS.pdf']
def main():
    import argparse
    parser = argparse.ArgumentParser(description='Extrai os PDFs de pesquisa de uma pasta informada.')
    parser.add_argument('--entrada', type=Path, required=True, help='Pasta dos PDFs de pesquisa.')
    parser.add_argument('--saida', type=Path, default=Path(__file__).resolve().parents[2] / 'pesquisa/2026-11-05/pdf')
    args = parser.parse_args()
    if not args.entrada.is_dir():
        parser.error('A pasta de entrada nao existe ou nao e um diretorio.')
    try:
        args.saida.mkdir(parents=True, exist_ok=True)
    except OSError:
        parser.error('Nao foi possivel criar a pasta de saida.')
    manifest, errors = [], []
    for i, name in enumerate(NAMES, 1):
        path = args.entrada / name
        try:
            with fitz.open(path) as doc:
                if doc.needs_pass or not len(doc):
                    raise ValueError('PDF protegido ou sem paginas.')
                pages = [{'page': j + 1, 'text': pg.get_text(sort=True)} for j, pg in enumerate(doc)]
                metadata = doc.metadata
                pixmap = doc[0].get_pixmap(matrix=fitz.Matrix(1, 1))
            ident = f'{i:02d}'
            (args.saida / f'{ident}.json').write_text(json.dumps({'path': str(path), 'metadata': metadata, 'pages': pages}, ensure_ascii=False, indent=2), encoding='utf-8')
            (args.saida / f'{ident}.txt').write_text('\n\n'.join(f"=== PAGINA {x['page']} ===\n{x['text']}" for x in pages), encoding='utf-8')
            pixmap.save(str(args.saida / f'{ident}-p1.png'))
            entry = {'id': ident, 'path': str(path), 'name': name, 'pages': len(pages), 'chars': sum(len(x['text']) for x in pages), 'metadata': metadata, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            manifest.append(entry)
            print(json.dumps({'id': ident, 'pages': len(pages), 'chars': entry['chars']}, ensure_ascii=True), flush=True)
        except (OSError, RuntimeError, ValueError) as error:
            errors.append({'name': name, 'error': type(error).__name__})
            print(f'Nao foi possivel extrair: {name}', flush=True)
    (args.saida / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (args.saida / 'erros.json').write_text(json.dumps(errors, ensure_ascii=False, indent=2), encoding='utf-8')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
