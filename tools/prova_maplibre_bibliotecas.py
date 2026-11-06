"""Bibliotecas fixas da prova MapLibre; baixa assets, não instala pacotes."""
from pathlib import Path
from urllib.request import urlopen
import json,hashlib,gzip
OUT=Path(__file__).resolve().parents[1]/'work/prova-maplibre'
FILES={'maplibre-gl-6.16.0/maplibre-gl.mjs': {'url': 'https://unpkg.com/maplibre-gl@6.16.0/dist/maplibre-gl.mjs', 'bytes': 1108049, 'gzip6_bytes': 295254, 'sha256': 'fbbdf8ddd9a48e49059a4be6795a4f214a711314bb5809f72d3730b48e7897e3'}, 'maplibre-gl-6.16.0/maplibre-gl-shared.mjs': {'url': 'https://unpkg.com/maplibre-gl@6.16.0/dist/maplibre-gl-shared.mjs', 'bytes': 0, 'gzip6_bytes': 20, 'sha256': 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'}, 'maplibre-gl-6.16.0/maplibre-gl-worker.mjs': {'url': 'https://unpkg.com/maplibre-gl@6.16.0/dist/maplibre-gl-worker.mjs', 'bytes': 519372, 'gzip6_bytes': 147628, 'sha256': '0bf06492bdb7ba3d4132b78e435621bfba60d5250967991c02b1a73affea8cd5'}, 'maplibre-gl-6.16.0/maplibre-gl.css': {'url': 'https://unpkg.com/maplibre-gl@6.16.0/dist/maplibre-gl.css', 'bytes': 71596, 'gzip6_bytes': 10261, 'sha256': 'a90798a1953017790e590f7e1bd35ff103a8a4263972cb47290b78adf86f8c20'}, 'maplibre-gl-6.16.0/LICENSE.txt': {'url': 'https://unpkg.com/maplibre-gl@6.16.0/LICENSE.txt', 'bytes': 5984, 'gzip6_bytes': 1531, 'sha256': 'ee5fc05a0677eaf69601d2c7db0d9ecd6cc27c3abc1d0733bc9ed34707cf8ef2'}, 'pmtiles-4.5.0.js': {'url': 'https://unpkg.com/pmtiles@4.5.0/dist/pmtiles.js', 'bytes': 20229, 'gzip6_bytes': 7950, 'sha256': 'caf981bc46f6327ee7e65d5dc964d89d38a69f60edca2bd4c5c890c21b554c6c'}, 'LICENSE-pmtiles.txt': {'url': 'https://raw.githubusercontent.com/protomaps/PMTiles/main/LICENSE', 'bytes': 1713, 'gzip6_bytes': 898, 'sha256': '0371c38f338835f7fc13ed71176f3d92144e22c8b736a31cced57adbbeb647b3'}}
def main():
 OUT.mkdir(parents=True,exist_ok=True);result={}
 for name,spec in FILES.items():
  data=urlopen(spec['url'],timeout=30).read()
  if hashlib.sha256(data).hexdigest()!=spec['sha256']:raise ValueError('Integridade inválida: '+name)
  path=OUT/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
  result[name]={**spec,'bytes':len(data),'gzip6_bytes':len(gzip.compress(data,compresslevel=6,mtime=0))}
 (OUT/'bibliotecas.json').write_bytes(json.dumps(result,indent=2).encode())
if __name__=='__main__':main()
