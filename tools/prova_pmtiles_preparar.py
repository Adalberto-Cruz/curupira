"""Prova isolada: prepara apenas código CAR, situação e geometria; não altera o site."""
from pathlib import Path
import json,hashlib,collections
from shapely.geometry import shape
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'work/prova-pmtiles'
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 seen=set();features=[];small=[];inputs=[];statuses=collections.Counter()
 for file in sorted((ROOT/'dist/data/mapa').glob('*.geojson')):
  inputs.append({'file':file.name,'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
  for f in json.loads(file.read_bytes())['features']:
   code=f['properties']['code'];status=f['properties']['status']
   if code in seen:raise ValueError('CAR duplicado: '+code)
   seen.add(code);statuses[status]+=1
   clean={'type':'Feature','properties':{'code':code,'status':status},'geometry':f['geometry']};features.append(clean)
   if file.stem=='1302603':
    g=shape(f['geometry'])
    if not g.is_empty and g.area>0 and g.is_valid:
     pt=g.representative_point();small.append({'code':code,'status':status,'lng':pt.x,'lat':pt.y,'area_degrees2':g.area,'bounds':list(g.bounds)})
 # Manaus já faz parte dos 62 arquivos; não concatenar novamente.
 (OUT/'car-am.geojson').write_bytes(json.dumps({'type':'FeatureCollection','features':features},ensure_ascii=False,separators=(',',':')).encode())
 for source in ['1302603']:(OUT/('car-'+source+'.geojson')).write_bytes((ROOT/'dist/data/mapa'/ (source+'.geojson')).read_bytes())
 manifest={'count':len(features),'statuses':dict(statuses),'inputs':inputs,'source_bytes':sum(f['bytes'] for f in inputs),'privacy':['code','status','geometry'],'small_manaus':sorted(small,key=lambda f:f['area_degrees2'])[:5]}
 (OUT/'manifesto.json').write_bytes(json.dumps(manifest,ensure_ascii=False,indent=2).encode())
 print(len(features),'CARs;',manifest['source_bytes'],'bytes de origem; menor imóvel:',manifest['small_manaus'][0])
if __name__=='__main__':main()
