import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock
from datetime import datetime
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from engine import ROOT,UTC,Store
from recovery import assess,parse_audit,record_failure,recovery_queue
class ModelErrorTests(unittest.TestCase):
 def data(self):
  d=json.loads((ROOT/'tests/fixture.json').read_text());d['sources'][0]['published']=datetime.now(UTC).isoformat();return d
 def test_audit_format_tolerance(self):
  self.assertEqual(parse_audit({'approved':'true','issues':None}),{'approved':True,'issues':[]})
  self.assertFalse(parse_audit({'approved':'false','issues':''})['approved'])
  self.assertFalse(parse_audit({'approved':True,'issues':'Un fatto errato'})['approved'])
 def test_ambiguous_audits_never_approve(self):
  for value in ({'approved':True},{'approved':'yes','issues':[]},{'approved':1,'issues':[]},[],{'approved':True,'issues':[42]}):
   with self.assertRaises(ValueError):parse_audit(value)
 def test_invalid_repair_keeps_original_and_diagnostic(self):
  d=self.data();d['draft']['claims'][0]['evidence']='Una prova non presente nella fonte'
  old=copy.deepcopy(d['draft']);ai=Mock();ai.call.return_value={'body_markdown':None}
  try:assess(d,ai)
  except ValueError as e:record_failure(d,e)
  self.assertEqual(d['draft']['body_markdown'],old['body_markdown'])
  self.assertEqual(d.get('repair_attempts',0),0)
  self.assertIn('[repair]',d['errors'][0]);self.assertTrue(d['technical_retry'])
 def test_audit_retry_uses_existing_draft(self):
  d=self.data();ai=Mock();ai.call.return_value={'approved':'perhaps'}
  try:assess(d,ai)
  except ValueError as e:record_failure(d,e)
  self.assertTrue(d['pending_audit']);self.assertIn('Audit non valido',d['errors'][0])
  ai.reset_mock();ai.call.return_value={'approved':True,'issues':[]}
  self.assertTrue(assess(d,ai));self.assertEqual(ai.call.call_args.args[0],'audit')
  self.assertFalse(d['pending_audit']);self.assertFalse(d['technical_retry'])
 def test_network_messages_not_exported_and_retries_bounded(self):
  d=self.data();d['processing_stage']='audit'
  for _ in range(2):record_failure(d,ValueError('https://secret.example/?key=private'))
  self.assertNotIn('private',json.dumps(d));self.assertFalse(d['technical_retry']);self.assertFalse(d['pending_audit'])
  cfg=json.loads((ROOT/'config/editorial.json').read_text())
  with tempfile.TemporaryDirectory() as tmp:
   st=Store(Path(tmp)/'state.db');st.put('bad','Titolo','Attualità','REVISIONE',d)
   self.assertEqual(recovery_queue(st,cfg),[]);st.db.close()
 def test_legacy_valueerror_one_repair_allowance(self):
  d=self.data();d.update(errors=['ValueError'],repair_attempts=1)
  cfg=json.loads((ROOT/'config/editorial.json').read_text())
  with tempfile.TemporaryDirectory() as tmp:
   st=Store(Path(tmp)/'state.db');st.put('legacy','Titolo','Attualità','REVISIONE',d)
   row,queued=recovery_queue(st,cfg)[0]
   self.assertTrue(queued['legacy_valueerror_retried']);self.assertEqual(queued['repair_attempts'],0)
   queued['repair_attempts']=1
   st.put('legacy','Titolo','Attualità','REVISIONE',queued)
   self.assertEqual(recovery_queue(st,cfg)[0][1]['repair_attempts'],1)
   st.db.close()
