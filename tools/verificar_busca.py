"""Confere o indice da busca contra os produtos nacionais locais da malha 2025."""
import json
from focos_brasil import ROOT
from preparar_busca import build

path=ROOT/'dist/data/busca-municipios.json'
data=json.loads(path.read_text(encoding='utf-8'))
assert data==build(), 'Indice local da busca diverge das fontes. Execute tools/preparar_busca.py.'
rows=data['municipalities']
assert len({m[0] for m in rows})==5571
assert len({m[2] for m in rows})==27
catalog=json.loads((ROOT/'dist/data/catalogo.json').read_text(encoding='utf-8'))
covered_codes={m['code'] for m in catalog['municipalities'] if m['count']}
covered=[m for m in rows if m[0] in covered_codes]
assert {m[0] for m in covered}==covered_codes
assert catalog['car_ufs']==sorted({m[2] for m in covered})
assert all(m[0] not in {'4300001','4300002'} for m in rows)
assert any(m[0]=='3137304' and m[1]=='Lagoa dos Patos' for m in rows)
print(f"OK busca: 5.571 unidades, 27 UFs, {len(covered)} municipios com CAR; UFs {', '.join(catalog['car_ufs'])}; {path.stat().st_size:,} bytes; fontes/hashes locais conferidos.")
