"""Verifica apenas o servidor e o isolamento da prova."""
import unittest,threading,tempfile,json
from pathlib import Path
from urllib.request import urlopen,Request
from urllib.error import HTTPError
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import prova_pmtiles_servidor as server
class RangeTest(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.original=server.DATA;cls.temp=tempfile.TemporaryDirectory();server.DATA=Path(cls.temp.name);(server.DATA/'car-am.pmtiles').write_bytes(bytes(range(256))*8)
  cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);threading.Thread(target=cls.http.serve_forever,daemon=True).start();cls.url='http://127.0.0.1:'+str(cls.http.server_port)
 @classmethod
 def tearDownClass(cls):cls.http.shutdown();cls.http.server_close();server.DATA=cls.original;cls.temp.cleanup()
 def test_range(self):
  with urlopen(Request(self.url+'/prova-data/car-am.pmtiles',headers={'Range':'bytes=0-126'})) as r:
   self.assertEqual(r.status,206);self.assertEqual(r.headers['Content-Range'],'bytes 0-126/2048');self.assertEqual(r.read(),bytes(range(127)))
 def test_full_and_head(self):
  with urlopen(self.url+'/prova-data/car-am.pmtiles') as r:self.assertEqual(r.status,200);self.assertEqual(len(r.read()),2048)
  with urlopen(Request(self.url+'/prova-data/car-am.pmtiles',method='HEAD')) as r:self.assertEqual(r.headers['Content-Length'],'2048');self.assertEqual(r.read(),b'')
 def test_invalid_range(self):
  with self.assertRaises(HTTPError) as error:urlopen(Request(self.url+'/prova-data/car-am.pmtiles',headers={'Range':'bytes=9999-'}))
  self.assertEqual(error.exception.code,416)
 def test_unrelated_file_not_served(self):
  for path in ['/mapa.html','/../.env','/prova-data/acesso-local.txt']:
   with self.assertRaises(HTTPError) as error:urlopen(self.url+path)
   self.assertEqual(error.exception.code,404)
 def test_no_site_scripts(self):
  root=Path(__file__).resolve().parents[1];html=(root/'dist/prova-pmtiles.html').read_text(encoding='utf-8')
  self.assertNotIn('assets/app.js',html);self.assertNotIn('assets/map-tools.js',html);self.assertIn('protomaps-leaflet-5.1.0.js',html)
if __name__=='__main__':unittest.main()
