"""Servidor local Hibama + Google Earth Engine. Credenciais nunca são servidas."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import date,timedelta
import argparse,json
from configuracao import project_id,configure_project
ROOT=Path(__file__).resolve().parents[1]
ready=False
municipalities={}
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*a,**kw):super().__init__(*a,directory=str(ROOT/'dist'),**kw)
 def do_GET(self):
  parsed=urlparse(self.path)
  if parsed.path!='/api/earth-engine':return super().do_GET()
  try:
   if not ready:return self.reply(503,{'error':'Earth Engine não configurado. Execute configurar-earth-engine.ps1 com o ID do projeto Google Cloud.'})
   q={k:v[0] for k,v in parse_qs(parsed.query).items()}
   start=date.fromisoformat(q.get('start',''));end=date.fromisoformat(q.get('end',''))
   if start>end or (end-start).days>366:raise ValueError('Escolha um período de até 366 dias, com início anterior ao fim.')
   product=q.get('product','rgb');cloud=int(q.get('cloud','30'))
   if product not in ['rgb','ndvi'] or not 0<=cloud<=100:raise ValueError('Visualização ou limite de nuvens inválido.')
   feature=next((f for f in municipalities['features'] if f['properties']['code']==q.get('municipio')),None)
   if not feature:raise ValueError('Município inválido.')
   region=ee.Geometry(feature['geometry'])
   collection=ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED').filterBounds(region).filterDate(start.isoformat(),(end+timedelta(days=1)).isoformat()).filter(ee.Filter.lte('CLOUDY_PIXEL_PERCENTAGE',cloud))
   count=collection.size().getInfo()
   if not count:return self.reply(422,{'error':'Nenhuma cena atende ao período e ao limite de nuvens. Amplie os filtros.'})
   def mask(image):
    scl=image.select('SCL')
    valid=scl.neq(0).And(scl.neq(1)).And(scl.neq(3)).And(scl.neq(8)).And(scl.neq(9)).And(scl.neq(10)).And(scl.neq(11))
    return image.updateMask(valid).select(['B2','B3','B4','B8']).multiply(.0001)
   image=collection.map(mask).median().clip(region)
   vis={'bands':['B4','B3','B2'],'min':0,'max':.3}
   if product=='ndvi':image=image.normalizedDifference(['B8','B4']);vis={'min':-1,'max':1,'palette':['70452b','e6d9a4','277441']}
   result=image.getMapId(vis)
   self.reply(200,{'url':result['tile_fetcher'].url_format,'count':count,'start':start.isoformat(),'end':end.isoformat(),'product':product})
  except (ValueError,KeyError):self.reply(400,{'error':'Revise município, datas (até 366 dias), produto e limite de nuvens.'})
  except Exception:self.reply(502,{'error':'Google Earth Engine não concluiu a consulta. Verifique acesso ao projeto e tente novamente.'})
 def reply(self,status,data):
  body=json.dumps(data,ensure_ascii=False).encode()
  self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
def main():
 global ready,municipalities,ee
 ready=False
 parser=argparse.ArgumentParser()
 parser.add_argument('--project',default=None)
 parser.add_argument('--authenticate',action='store_true')
 parser.add_argument('--configure-project',action='store_true')
 parser.add_argument('--port',type=int,default=8766)
 parser.add_argument('--check-config',action='store_true',help='Valida configuracao sem login nem servidor.')
 args=parser.parse_args()
 try:project=configure_project(args.project) if args.configure_project and not args.check_config else project_id(args.project)
 except ValueError as error:parser.error(str(error))
 if args.check_config:
  print('Projeto configurado.' if project else 'Defina GOOGLE_CLOUD_PROJECT no ambiente ou no .env da raiz.')
  return 0 if project else 2
 try:
  municipalities=json.loads((ROOT/'dist/data/municipios.geojson').read_text(encoding='utf-8'))
  if not isinstance(municipalities.get('features'),list) or not municipalities['features']:raise ValueError()
 except (OSError,ValueError,AttributeError):
  parser.error('Malha municipal ausente, vazia ou invalida em dist/data/municipios.geojson.')
 if project:
  try:
   import ee
   if args.authenticate:ee.Authenticate()
   ee.Initialize(project=project)
   ready=True
  except Exception:
   print('Earth Engine indisponivel. Confira o acesso e execute tools/configurar-earth-engine.ps1. O site local continua disponivel.',flush=True)
 else:
  print('Earth Engine nao configurado. Defina GOOGLE_CLOUD_PROJECT no ambiente ou no .env da raiz. A API retorna 503.',flush=True)
 print(f'Hibama: http://127.0.0.1:{args.port}/mapa.html | Earth Engine: {ready}',flush=True)
 try:
  with ThreadingHTTPServer(('127.0.0.1',args.port),Handler) as server:server.serve_forever()
 except OSError:
  parser.error('Nao foi possivel abrir a porta local. Confira se ja esta em uso.')
 return 0

if __name__=='__main__':raise SystemExit(main())
