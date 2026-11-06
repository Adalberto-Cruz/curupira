import sys
import unittest
import tempfile
import subprocess
import json
from pathlib import Path
import numpy as np
import shapely
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from focos_brasil import normalize, MunicipalAssigner, municipality_kind
from coletar_focos_brasil import sources
from datetime import date
from verificar_commit import forbidden


class FocosTests(unittest.TestCase):
    def setUp(self):
        self.spec={'kind':'monthly','year':2026,'month':11,'path':'test.csv'}
        self.row={'id':'a','lat':'-3','lon':'-60','data_hora_gmt':'2026-11-02 15:00:00',
                  'satelite':'AQUA_M-T','municipio':'Manaus','estado':'AM','pais':'Brasil'}

    def test_reference_filter_and_utc(self):
        self.assertEqual(normalize(self.row,self.spec)['datetime_utc'],'2026-11-02T15:00:00Z')
        self.assertIsNone(normalize({**self.row,'satelite':'NOAA-20'},self.spec))

    def test_missing_columns_stop_even_nonreference(self):
        with self.assertRaisesRegex(ValueError,'Colunas'):
            normalize({'lat':'0'},self.spec)

    def test_wrong_month_stops(self):
        with self.assertRaisesRegex(ValueError,'Data fora'):
            normalize({**self.row,'data_hora_gmt':'2026-10-31'},self.spec)

    def test_bad_coordinate_audited(self):
        for value in ['nan','inf','999','']:
            self.assertIsNone(normalize({**self.row,'lat':value},self.spec)['lat'])

    def test_boundary_once_and_operational_excluded(self):
        metadata=[{'code':'1','kind':'municipio'},{'code':'2','kind':'municipio'},{'code':'3','kind':'operacional'}]
        geometries=np.array([shapely.box(0,0,1,1),shapely.box(1,0,2,1),shapely.box(3,0,4,1)],dtype=object)
        assigner=MunicipalAssigner(metadata,geometries)
        rows=[{'lon':1,'lat':.5,'source_code':''},{'lon':1,'lat':.5,'source_code':'2'},
              {'lon':3.5,'lat':.5,'source_code':'3'},{'lon':9,'lat':9,'source_code':'1'},
              {'lon':None,'lat':None,'source_code':''}]
        indices,statuses=assigner.assign(rows)
        self.assertEqual(indices.tolist(),[0,1,-1,-1,-1])
        self.assertEqual(statuses.tolist(),['boundary-lowest-code','boundary-source-code','operational-area','outside-mesh','invalid-coordinate'])

    def test_approved_download_scope(self):
        files=sources(date(2026,11,6))
        self.assertEqual(len(files),36)
        self.assertEqual([s['year'] for s in files if s['kind']=='annual'],list(range(2003,2026)))
        self.assertEqual([(s['year'],s['month']) for s in files if s['kind']=='comparison_sample'],[(2025,4)])
        with self.assertRaises(ValueError): sources(date(2027,1,1))

    def test_operational_geocodes_do_not_exclude_homonymous_municipality(self):
        self.assertEqual(municipality_kind('Lagoa dos Patos','MG','3137304'),'municipio')
        self.assertEqual(municipality_kind('Área Operacional "Lagoa Mirim"','RS','4300001'),'operacional')
        self.assertEqual(municipality_kind('Área Operacional "Lagoa dos Patos"','RS','4300002'),'operacional')

    def test_generated_products_cannot_enter_index(self):
        self.assertFalse(forbidden('dist/data/focos-brasil/manifesto.json'))
        self.assertTrue(forbidden('dist/data/focos-brasil/contagens-2003.json.gz'))
        self.assertTrue(forbidden('dist/data/focos-brasil/municipios.geojson.gz'))

    def test_preparer_rejects_modified_raw_before_output(self):
        with tempfile.TemporaryDirectory() as folder:
            raw=Path(folder); (raw/'test.csv').write_text('changed')
            (raw/'coleta.json').write_text(json.dumps({'sources':[{'path':'test.csv','bytes':7,'sha256':'0'*64}]}))
            result=subprocess.run([sys.executable,str(Path(__file__).resolve().parents[1]/'tools/preparar_focos_brasil.py'),
                                   '--brutos',folder,'--saida',str(raw/'out')],capture_output=True,text=True)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('Fonte bruta difere',result.stderr)
            self.assertFalse((raw/'out').exists())
