import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from collections import Counter

from shapely.geometry import box
from shapely.strtree import STRtree

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.atencao_am import ROOT, complete_indices, prodes_metrics, rank, score, validate_weights, load_source


class AttentionTests(unittest.TestCase):
    def setUp(self):
        self.weights=json.loads((ROOT/'dist/data/atencao/pesos.json').read_text(encoding='utf-8'))

    def test_each_critical_lock_overrides_and_contributions_reconcile(self):
        for layers in [['ti'],['embargos'],['ti','embargos']]:
            row=score({k:{'count':1} for k in layers}, .25, {}, self.weights)
            self.assertEqual(row['nota'],100)
            self.assertEqual(set(row['travas']),set(layers))
            self.assertEqual(sum(row['contribuicoes'].values()),100)
            self.assertEqual(row['contribuicoes']['trava'],90)

    def test_weighted_example_and_cap_are_deterministic(self):
        overlaps={'deter':{'count':3},'anm':{'count':2},'focos':{'count':3}}
        row=score(overlaps,.25,{'MINERACAO':1,'CS_GEOMETRICO':1,'DESMATAMENTO_CR':1},self.weights)
        self.assertEqual(row['nota'],31)
        self.assertEqual(row['contribuicoes'],{'prodes':10.0,'deter':12,'anm':6,'focos':3,'trava':0})
        high=score({'deter':{'count':100},'anm':{'count':100},'focos':{'count':100}},1,{'MINERACAO':100},self.weights)
        self.assertEqual(high['nota'],100)
        self.assertEqual(high['travas'],[])

    def test_mining_and_selective_logging_weigh_more_than_other_alerts(self):
        values={c:score({'deter':{'count':1}},0,{c:1},self.weights)['nota'] for c in ['MINERACAO','CORTE_SELETIVO','DESMATAMENTO_CR','CICATRIZ_DE_QUEIMADA']}
        self.assertGreater(values['MINERACAO'],values['DESMATAMENTO_CR'])
        self.assertGreater(values['CORTE_SELETIVO'],values['DESMATAMENTO_CR'])

    def test_no_overlap_zero_and_invalid_or_incomplete_data_rejected(self):
        self.assertEqual(score({},0,{},self.weights)['nota'],0)
        for fraction in [-1,2,float('nan')]:
            with self.assertRaises(ValueError):score({},fraction,{},self.weights)
        with self.assertRaises(ValueError):score({'deter':{'count':2}},0,{'MINERACAO':1},self.weights)
        with self.assertRaises(ValueError):score({'deter':{'count':1}},0,{'UNKNOWN':1},self.weights)
        with self.assertRaises(ValueError):score({'focos':{'count':-1}},0,{},self.weights)
        with self.assertRaises(ValueError):score({'deter':{'count':1}},0,{'MINERACAO':2,'DEGRADACAO':-1},self.weights)

    def test_prodes_is_dissolved_clipped_and_does_not_use_whole_alert_area(self):
        car=box(-60,-3,-59.99,-2.99)
        a=box(-60.01,-3,-59.995,-2.99)
        b=box(-59.9975,-3,-59.9925,-2.99)
        total,covered,fraction=prodes_metrics(car,[a,b,a])
        self.assertAlmostEqual(fraction,.75,places=4)
        self.assertLessEqual(covered,total)

    def test_full_deter_classes_recovered_when_preview_is_truncated(self):
        geometries=[box(i,0,i+.5,1) for i in range(3)]
        source=(geometries,{'a':0,'b':1,'c':2},{0:'MINERACAO',1:'CS_GEOMETRICO',2:'DESMATAMENTO_CR'},STRtree(geometries))
        indices=complete_indices({'count':3,'records':[{'record_id':'a'}],'preview_limited':True},box(-1,-1,4,2),source,'deter')
        self.assertEqual(set(indices),{0,1,2})
        with self.assertRaises(ValueError):complete_indices({'count':4,'preview_limited':True},box(-1,-1,4,2),source,'deter')

    def test_top20_excludes_cancelled_zero_and_has_stable_ties(self):
        rows={f'AM-1302603-{i:032X}':{'nota':100 if i<25 else 0} for i in range(30)}
        records=[{'code':c,'status':'CA' if i==0 else 'AT'} for i,c in enumerate(rows)]
        result=rank(rows,records,self.weights)
        self.assertEqual(result,sorted(rows)[1:21])
        self.assertEqual(len(result),20)

    def test_malformed_weights_rejected(self):
        w=copy.deepcopy(self.weights);w['prodes']['max_points']=101
        with self.assertRaises(ValueError):validate_weights(w)

    def test_recovery_preserves_original_am_territory_filter(self):
        from shapely.geometry import mapping
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'prodes.json'
            path.write_text(json.dumps({'features':[
                {'geometry':mapping(box(0,0,1,1)),'properties':{'uuid':'inside'}},
                {'geometry':mapping(box(3,0,4,1)),'properties':{'uuid':'outside'}}
            ]}),encoding='utf-8')
            geometries,ids,_,_=load_source(path,'prodes',STRtree([box(-1,-1,2,2)]))
            self.assertEqual(len(geometries),1)
            self.assertEqual(set(ids),{'prodes_inside'})
        w=copy.deepcopy(self.weights);w['anm']['points_per_record']=float('inf')
        with self.assertRaises(ValueError):validate_weights(w)


if __name__=='__main__':unittest.main()
