import copy,json,os,sys,tempfile,unittest
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from engine import ROOT,UTC,Store,QuotaStop,content_errors,draft_errors
from recovery import assess,recover_local,recovery_queue,prepare,remaining
from pipeline import run,write_report

class RecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'state.db')
  self.cfg=json.loads((ROOT/'config/editorial.json').read_text())
  self.f=json.loads((ROOT/'tests/fixture.json').read_text())
  self.f['sources'][0]['published']=datetime.now(UTC).isoformat()
 def tearDown(self):self.store.db.close();self.tmp.cleanup()
 def data(self):return copy.deepcopy(self.f)
 def test_incidental_health_allowed_but_advice_blocked(self):
  for title,body in [('Le strade romane','Le strade favorivano il diffondersi delle malattie.'),('Megan racconta la sua famiglia','Sua madre lavorava nelle cliniche.')]:
   self.assertEqual(content_errors({'title':title,'body_markdown':body},[]),[])
  self.assertTrue(content_errors({'title':'La tua salute','body_markdown':'Sospendi il farmaco da domani.'},[]))
 def test_restore_only_previously_ready_false_positive(self):
  d=self.data();d['errors']=['Contenuto sanitario: revisione richiesta']
  self.store.put('restore',d['draft']['title'],'Curiosità e storie','REVISIONE',d)
  other=copy.deepcopy(d);other['errors']+=['Evidenza non riscontrata']
  self.store.put('keep','Altro','Curiosità e storie','REVISIONE',other)
  cycle={};recover_local(self.store,self.cfg,cycle)
  self.assertEqual(cycle['recovered_without_ai'],['restore'])
  self.assertEqual({r['id']:r['state'] for r in self.store.rows()},{'restore':'PRONTO','keep':'REVISIONE'})
 def test_stale_false_positive_not_restored(self):
  d=self.data();d['sources'][0]['published']=(datetime.now(UTC)-timedelta(days=5)).isoformat()
  d['errors']=['Contenuto sanitario: revisione richiesta']
  self.store.put('old','Old','Curiosità e storie','REVISIONE',d)
  c={};recover_local(self.store,self.cfg,c);self.assertEqual(c['recovered_without_ai'],[])
 def test_repair_then_audit(self):
  d=self.data();d['draft']['claims'][0]['evidence']='Una frase non presente in alcuna fonte'
  ai=Mock();ai.call.side_effect=[copy.deepcopy(self.f['draft']),{'approved':True,'issues':[]}]
  self.assertTrue(assess(d,ai));self.assertEqual([c.args[0] for c in ai.call.call_args_list],['repair','audit'])
 def test_audit_rejection_repaired_only_once(self):
  d=self.data();ai=Mock()
  ai.call.side_effect=[{'approved':False,'issues':['Gancio troppo forte']},copy.deepcopy(self.f['draft']),{'approved':False,'issues':['Ancora errato']}]
  self.assertFalse(assess(d,ai));self.assertEqual(ai.call.call_count,3)
  self.assertEqual(d['repair_attempts'],1);self.assertTrue(d['recovery_attempted'])
 def test_inconsistent_audit_cannot_loop(self):
  d=self.data();ai=Mock()
  ai.call.side_effect=[{'approved':True,'issues':['Errore fattuale']},copy.deepcopy(self.f['draft']),{'approved':True,'issues':[]}]
  self.assertTrue(assess(d,ai));self.assertEqual(ai.call.call_count,3)
 def test_quota_during_audit_keeps_repaired_draft(self):
  d=self.data();d['draft']['claims'][0]['evidence']='Una prova che non esiste nella fonte'
  ai=Mock();ai.call.side_effect=[copy.deepcopy(self.f['draft']),QuotaStop('quota')]
  with self.assertRaises(QuotaStop):assess(d,ai)
  self.assertEqual(d['repair_attempts'],1)
  self.assertEqual(d['draft']['claims'],self.f['draft']['claims'])
 def test_bad_variant_removed_main_quote_still_blocked(self):
  d=self.data();d['draft']['title_variants']=['Lei: «Queste parole non sono mai state dette»']
  clean=prepare(d['draft'],d['sources']);self.assertEqual(clean['title_variants'],[])
  self.assertEqual(draft_errors(clean,d['sources']),[])
  clean['title']='Lei: «Queste parole non sono mai state dette»'
  self.assertIn('Citazione nel titolo non letterale: usare discorso indiretto',draft_errors(clean,d['sources']))
 def test_short_complete_article_allowed(self):
  d=self.data()['draft'];d['body_markdown']=' '.join(d['body_markdown'].split()[:140])
  self.assertNotIn('Lunghezza non valida',draft_errors(d,self.f['sources']))
 def test_invalid_types_are_handled(self):
  for value in (None,[],{'body_markdown':None},{'title':42}):
   with self.assertRaises(ValueError):prepare(value,self.f['sources'])
 def test_quota_exhausted_still_publishes_ready(self):
  d=self.data();self.store.put('stock',d['draft']['title'],'Curiosità e storie','PRONTO',d)
  day=datetime.now(ZoneInfo('America/Los_Angeles')).date().isoformat()
  for _ in range(self.cfg['max_ai_calls_per_day']):self.store.reserve_call(day,'article',self.cfg['max_ai_calls_per_day'])
  slots=[datetime.now(UTC)+timedelta(hours=i+1) for i in range(2)]
  client=Mock();client.session.get.return_value.json.return_value={'version':'1.0'}
  ai=Mock();ai.count=0
  with patch.dict(os.environ,{'EDITORIAL_WP_URL':'https://example.org','EDITORIAL_WP_USER':'test','EDITORIAL_WP_PASSWORD':'test'}),patch('pipeline.WordPressClient',return_value=client),patch('pipeline.slots_available',return_value=slots),patch('pipeline.collect',return_value=self.f['sources']),patch('pipeline.Gemini',return_value=ai),patch('pipeline.publish') as send:
   cycle={};run(self.cfg,self.store,publish_live=True,cycle=cycle)
  self.assertEqual(send.call_count,1);ai.call.assert_not_called()
  self.assertEqual(cycle['ai_calls_remaining'],0)
 def test_pending_audit_resumes_without_regeneration(self):
  d=self.data();d['errors']=['Quota esaurita: verifica non completata'];d['pending_audit']=True;d['recovery_attempted']=True
  self.store.put('pending',d['draft']['title'],'Curiosità e storie','REVISIONE',d)
  ai=Mock();ai.count=0;ai.call.return_value={'approved':True,'issues':[]}
  with patch('pipeline.collect',return_value=[]),patch('pipeline.slots_available',return_value=[]),patch('pipeline.Gemini',return_value=ai):
   c={};run(self.cfg,self.store,cycle=c)
  self.assertEqual([x.args[0] for x in ai.call.call_args_list],['audit'])
  self.assertEqual(self.store.rows()[0]['state'],'PRONTO')
 def test_service_error_still_uses_stock(self):
  d=self.data();self.store.put('stock',d['draft']['title'],'Curiosità e storie','PRONTO',d)
  ai=Mock();ai.count=0;ai.call.side_effect=RuntimeError('HTTP 503')
  slots=[datetime.now(UTC)+timedelta(hours=1)]
  with patch('pipeline.collect',return_value=self.f['sources']),patch('pipeline.slots_available',return_value=slots),patch('pipeline.Gemini',return_value=ai),patch('pipeline.cover',return_value=b'png') as cover:
   c={};run(self.cfg,self.store,cycle=c)
  self.assertEqual(c['stop_reason'],'API temporaneamente non disponibile');cover.assert_called_once()
