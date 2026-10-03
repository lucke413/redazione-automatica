import sys,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from engine import Store,ROOT
from pipeline import run,write_report

class CycleTests(unittest.TestCase):
 def test_simulation_ignores_old_stock_and_no_slots(self):
  cfg=json.loads((ROOT/'config/editorial.json').read_text())
  fixture=json.loads((ROOT/'tests/fixture.json').read_text())
  source=dict(fixture['sources'][0]);source['id']='fresh';source['related']=[{'title':'Un altro evento','text':'Altro contenuto'}]
  draft=dict(fixture['draft']);draft['body_markdown']+='\n\nVoi cosa ne pensate?'
  class FakeAI:
   count=0
   def __init__(self,*a):pass
   def call(self,kind,prompt):
    self.count+=1
    if kind=='ranking':return {'items':[{'id':'fresh','score':90}]}
    if kind=='article':
     payload=json.loads(prompt.split('\n')[-1])
     assert len(payload)==1 and 'related' not in payload[0]
     return draft
    return {'approved':True,'issues':[]}
  with tempfile.TemporaryDirectory() as tmp:
   store=Store(Path(tmp)/'state.db')
   for i in range(2):store.put('old'+str(i),'old',source['category'],'PRONTO',{'sources':[source],'draft':draft})
   with patch('pipeline.slots_available',return_value=[]),patch('pipeline.collect',return_value=[source]),patch('pipeline.Gemini',FakeAI),patch('pipeline.cover',return_value=b'png'):
    cycle={};run(cfg,store,cycle=cycle)
   self.assertEqual(cycle['attempted_ids'],['fresh'])
   self.assertEqual(next(r['state'] for r in store.rows() if r['id']=='fresh'),'PRONTO')
   write_report(store,Path(tmp)/'out',cycle)
   report=json.loads((Path(tmp)/'out/esecuzione.json').read_text())
   self.assertEqual(report['version'],'0.8.8')
   self.assertEqual(len(report['cycle']['articles']),1)
   self.assertEqual(report['cycle']['states'],{'PRONTO':1})
   store.db.close()
