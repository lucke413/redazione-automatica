import copy,json,sys,tempfile,unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from engine import ROOT,UTC,Store,metadata_complete
from recovery import prepare
from pipeline import run,write_report
OLD='La casa degli specchi cosmica del James Webb: il dettaglio che cancella il vecchio telescopio Hubble'
class StockTests(unittest.TestCase):
 def test_incomplete_prepositions(self):
  for word in ('nello','nelle','sugli','dalle','nei','dell’'):
   self.assertFalse(metadata_complete('La scoperta '+word))
 def test_targeted_repair_requires_source_evidence(self):
  d={'title':OLD,'seo_title':'Una scoperta nello','title_variants':[]}
  src={'id':'ae33f41dd66446b4d7dd64c5','text':'la nuova immagine di Webb rivela centinaia di galassie assenti nella precedente'}
  fixed=prepare(d,[src]);self.assertNotIn('cancella',fixed['title'])
  self.assertEqual(prepare(fixed,[src]),fixed)
  self.assertEqual(prepare(d,[dict(src,id='other')])['title'],OLD)
  self.assertEqual(prepare(d,[dict(src,text='Altro contenuto')])['title'],OLD)
 def test_stock_checks_evidence_not_only_metadata(self):
  cfg=json.loads((ROOT/'config/editorial.json').read_text())
  f=json.loads((ROOT/'tests/fixture.json').read_text())
  f['sources'][0]['published']=datetime.now(UTC).isoformat()
  f['draft']['claims'][0]['evidence']='Una frase inventata mai presente nella fonte'
  with tempfile.TemporaryDirectory() as tmp:
   store=Store(Path(tmp)/'state.db');store.put('bad',f['draft']['title'],'Curiosità e storie','PRONTO',f)
   with patch('pipeline.collect',return_value=[]),patch('pipeline.remaining',return_value=0):
    c={};run(cfg,store,cycle=c)
   self.assertEqual(store.rows()[0]['state'],'REVISIONE')
   self.assertIn('Evidenza non riscontrata',c['stock_revalidated'][0]['errors'])
   store.db.close()
