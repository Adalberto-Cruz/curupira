"""Servidor exclusivo da parte 2: serve ambas as provas e o mesmo PMTiles, sem alterar a parte 1."""
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlsplit,unquote
import re,json,time,threading,argparse
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/'work/prova-maplibre';PMDATA=ROOT/'work/prova-pmtiles';LOCK=threading.Lock()
ALLOWED={'car-am.pmtiles','car-am.geojson','car-1302603.geojson','manifesto.json','protomaps-leaflet-5.1.0.js','LICENSE-protomaps-leaflet.txt'}
STATE_FILES={f'{prefix}-{uf}.{ext}' for uf in ('mt','pa') for prefix,ext in [('car','pmtiles'),('car','geojson'),('manifesto','json')]}
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_HEAD(self):self.serve(False)
 def do_GET(self):self.serve(True)
 def do_POST(self):
  try:
   size=int(self.headers.get('Content-Length','0'))
   if self.path not in ['/prova-medidas','/prova-maplibre-medidas'] or not 0<size<=1000000:raise ValueError('Tamanho/rota inválidos')
   data=json.loads(self.rfile.read(size))
   if not isinstance(data,dict):raise ValueError('Esperado objeto JSON')
  except (ValueError,UnicodeDecodeError):self.send_error(400);return
  with LOCK, (DATA/('medidas.jsonl' if self.path=='/prova-maplibre-medidas' else 'leaflet-medidas.jsonl')).open('a',encoding='utf-8') as log:log.write(json.dumps(data,ensure_ascii=False)+'\n')
  self.send_response(204);self.end_headers()
 def serve(self,body):
  started=time.perf_counter();path=unquote(urlsplit(self.path).path)
  if path.startswith('/prova-data/') and path.split('/')[-1] in ALLOWED:target=PMDATA/path.split('/')[-1]
  elif path in ['/prova-pmtiles.html','/prova-maplibre.html']:target=ROOT/'dist'/path.lstrip('/')
  elif path.startswith('/prova-maplibre-data/') and path.removeprefix('/prova-maplibre-data/') in (set(json.loads((DATA/'bibliotecas.json').read_text(encoding='utf-8'))) | STATE_FILES):target=DATA/path.removeprefix('/prova-maplibre-data/')
  elif path in ['/assets/vendor/leaflet.js','/assets/vendor/leaflet.css','/assets/prova-pmtiles.js','/assets/prova-pmtiles.css','/assets/prova-maplibre.js','/assets/prova-maplibre-model.js','/data/ambiental/paleta.json']:target=ROOT/'dist'/path.lstrip('/')
  else:self.send_error(404);return
  if not target.is_file():self.send_error(404);return
  size=target.stat().st_size;start=0;end=size-1;status=200
  if self.headers.get('Range'):
   m=re.fullmatch(r'bytes=(\d+)-(\d*)',self.headers['Range'])
   if not m or int(m[1])>=size:
    self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.end_headers();return
   start=int(m[1]);end=min(int(m[2]) if m[2] else size-1,size-1)
   if end<start:self.send_error(416);return
   status=206
  mime={'.mjs':'text/javascript','.js':'text/javascript','.css':'text/css','.html':'text/html','.json':'application/json','.geojson':'application/geo+json','.pmtiles':'application/vnd.pmtiles'}.get(target.suffix,'text/plain')
  self.send_response(status);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(end-start+1));self.send_header('Accept-Ranges','bytes');self.send_header('Cache-Control','no-store');self.send_header('ETag',f'"{size:x}-{target.stat().st_mtime_ns:x}"')
  if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
  self.end_headers();sent=0
  if body:
   try:
    with target.open('rb') as f:
     f.seek(start);remaining=end-start+1
     while remaining:
      chunk=f.read(min(65536,remaining))
      if not chunk:break
      self.wfile.write(chunk);sent+=len(chunk);remaining-=len(chunk)
   except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
  with LOCK, (DATA/'requisicoes.jsonl').open('a',encoding='utf-8') as log:log.write(json.dumps({'at':time.time(),'path':path,'status':status,'range':self.headers.get('Range'),'bytes':sent,'seconds':time.perf_counter()-started})+'\n')
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8775);args=parser.parse_args();DATA.mkdir(parents=True,exist_ok=True)
 print(f'Prova isolada: http://127.0.0.1:{args.port}/prova-maplibre.html',flush=True);ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
