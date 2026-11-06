"""Audita o artefato da prova e a recuperação dos cinco menores CARs de Manaus."""
from pathlib import Path
import struct,gzip,json,math,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'work/prova-pmtiles'
BIN='/tmp/hibama-prova-pmtiles-20261106/tippecanoe/tippecanoe-decode'
def tile(lng,lat,z):
 n=2**z;return int((lng+180)/360*n),int((1-math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
def decode(z,x,y):
 file='/mnt/c/Users/user/Downloads/ibama/Hibama/site-hibama/work/prova-pmtiles/car-am.pmtiles'
 return json.loads(subprocess.check_output(['wsl','-d','Ubuntu','--',BIN,file,str(z),str(x),str(y)]))
def main():
 p=DATA/'car-am.pmtiles'
 with p.open('rb') as f:
  header=f.read(127);assert header[:8]==b'PMTiles\x03'
  offset,size=struct.unpack_from('<QQ',header,24);f.seek(offset);raw=f.read(size)
  metadata=json.loads(gzip.decompress(raw) if header[97]==2 else raw)
 assert set(metadata['vector_layers'][0]['fields'])=={'code','status'},metadata
 source=json.loads((DATA/'car-am.geojson').read_bytes())
 assert len(source['features'])==98982
 assert all(set(f)=={'type','properties','geometry'} and set(f['properties'])=={'code','status'} for f in source['features'])
 cases=json.loads((DATA/'manifesto.json').read_bytes())['small_manaus'];results=[]
 def features(decoded):
  return [f for layer in decoded['features'] for f in layer['features']]
 for case in cases:
  highs=features(decode(header[101],*tile(case['lng'],case['lat'],header[101])));lows=features(decode(4,*tile(case['lng'],case['lat'],4)))
  found=[f for f in highs if f['properties']['code']==case['code']];assert found,case['code']
  assert all(set(f['properties'])=={'code','status'} for f in highs+lows)
  assert all(f['properties']['status']==case['status'] for f in found)
  results.append({'code':case['code'],'low_zoom_present':any(f['properties']['code']==case['code'] for f in lows),'high_zoom_present':True})
 report={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'header_min_zoom':header[100],'header_max_zoom':header[101],'metadata':metadata,'small_features':results}
 (DATA/'verificacao.json').write_bytes(json.dumps(report,ensure_ascii=False,indent=2).encode())
 print(json.dumps({k:v for k,v in report.items() if k!='metadata'},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
