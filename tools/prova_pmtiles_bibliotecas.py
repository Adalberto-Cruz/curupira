"""Baixa somente a biblioteca solicitada para a prova; não instala pacotes."""
from pathlib import Path
from urllib.request import urlopen
import hashlib,json
OUT=Path(__file__).resolve().parents[1]/'work/prova-pmtiles'
FILES={
 'protomaps-leaflet-5.1.0.js':('https://unpkg.com/protomaps-leaflet@5.1.0/dist/protomaps-leaflet.js','26af014f7b1af308ec120b791cff76657bb9c3383633b52033e6edf9e5e4cdb5'),
 'LICENSE-protomaps-leaflet.txt':('https://unpkg.com/protomaps-leaflet@5.1.0/LICENSE','a2ada548aa25012e833b71364a402d6924f2afcf5f8f146e2989a377290ab3ad')}
def main():
 OUT.mkdir(parents=True,exist_ok=True);metadata={}
 for name,(url,expected) in FILES.items():
  data=urlopen(url,timeout=30).read();digest=hashlib.sha256(data).hexdigest()
  if digest!=expected:raise ValueError('Integridade inesperada: '+name)
  (OUT/name).write_bytes(data);metadata[name]={'url':url,'sha256':digest,'bytes':len(data)}
 (OUT/'bibliotecas.json').write_bytes(json.dumps(metadata,indent=2).encode())
if __name__=='__main__':main()
