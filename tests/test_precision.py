import json,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from engine import ROOT,Store
from editorial_policy import classify
from recovery import quota_status,budget_stop_reason,prepare
class PrecisionTests(unittest.TestCase):
 def test_judicial_interview_not_entertainment(self):
  self.assertEqual(classify({'title':'Intervista a Quarto Grado','text':'La procura ha comunicato la chiusura delle indagini a suo carico per omicidio.','category':'Reality e TV'}),'Attualità')
 def test_fiction_and_casual_metaphor_not_crime(self):
  for text in ('La fiction segue una procura e una inchiesta per omicidio.','Processo ai concorrenti: il televoto premia la concorrente.'):
   self.assertEqual(classify({'title':'La puntata di ieri','text':text,'category':'Reality e TV'}),'Reality e TV')
 def test_cycle_and_daily_quota_are_distinct(self):
  cfg=json.loads((ROOT/'config/editorial.json').read_text())
  with tempfile.TemporaryDirectory() as tmp:
   st=Store(Path(tmp)/'state.db')
   day=datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
   for _ in range(11):st.reserve_call(day,'article',48)
   ai=SimpleNamespace(count=11);q=quota_status(cfg,st,ai)
   self.assertEqual((q['cycle_remaining'],q['daily_remaining']),(0,37))
   self.assertIn('Budget del ciclo',budget_stop_reason(cfg,st,ai))
   for _ in range(37):st.reserve_call(day,'article',48)
   self.assertIn('Budget giornaliero',budget_stop_reason(cfg,st))
   st.db.close()
 def test_lunar_correction_is_scoped_and_idempotent(self):
  sentence="Senza la luce lunare, il buio sarebbe totale e costringerebbe a un forte aumento dell'illuminazione artificiale."
  src={'id':'e1f2d3562ba6618bebbc6b8b','text':'sotto la sola fioca luce delle stelle; verosimilmente un maggior uso di illuminazione artificiale'}
  d={'title':'Una Luna diversa','body_markdown':sentence}
  fixed=prepare(d,[src]);self.assertNotIn('buio sarebbe totale',fixed['body_markdown'])
  self.assertIn('si potrebbe',fixed['body_markdown'])
  self.assertEqual(prepare(fixed,[src]),fixed)
  self.assertEqual(prepare(d,[dict(src,id='other')])['body_markdown'],sentence)
