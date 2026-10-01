import sys,tempfile,unittest,json
from pathlib import Path
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch,Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from engine import *
from pipeline import publish

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.store=Store(Path(self.tmp.name)/'state.db')
        self.cfg=json.loads((ROOT/'config/editorial.json').read_text())
    def tearDown(self):self.store.db.close();self.tmp.cleanup()
    def test_quota_persists_and_stops(self):
        self.store.reserve_call('2026-10-01','article',1)
        with self.assertRaises(QuotaStop):self.store.reserve_call('2026-10-01','article',1)
        self.assertEqual(self.store.db.execute('select count(*) from calls').fetchone()[0],1)
    def test_4_cycles_have_20_distinct_slots(self):
        got=[]
        for hour in [6,10,14,18]:
            slots=slots_available(self.cfg,self.store,datetime(2026,10,1,hour,15,tzinfo=ZoneInfo('Europe/Rome')))
            self.assertEqual(len(slots),5)
            for i,s in enumerate(slots):self.store.put(str(hour)+'-'+str(i),'titolo','Curiosità e storie','PROGRAMMATO',{},s.isoformat());got.append(s)
        self.assertEqual(len(set(got)),20)
        self.assertEqual(slots_available(self.cfg,self.store,datetime(2026,10,1,18,16,tzinfo=ZoneInfo('Europe/Rome'))),[])
    def test_winter_scheduler(self):
        slots=slots_available(self.cfg,self.store,datetime(2026,12,1,5,15,tzinfo=ZoneInfo('Europe/Rome')))
        self.assertEqual(len(slots),5);self.assertEqual(slots[0].utcoffset(),timedelta(hours=1))
    def test_future_url_and_tracking(self):
        self.assertEqual(key('https://example.org/a?utm_source=fb'),key('https://example.org/a'))
        for u in ['http://example.org','https://x:y@example.org','file:///etc/passwd']:
            with self.assertRaises(ValueError):canonical(u)
    def test_evidence_gate(self):
        fixture=json.loads((ROOT/'tests/fixture.json').read_text());d=fixture['draft']
        self.assertEqual(draft_errors(d,fixture['sources']),[])
        d['claims'][0]['evidence']='Informazione assolutamente inventata e non riscontrabile'
        self.assertIn('Evidenza non riscontrata',draft_errors(d,fixture['sources']))
    def test_sensitive_gossip_blocked(self):
        fixture=json.loads((ROOT/'tests/fixture.json').read_text());d=fixture['draft'];d['title']='La presunta gravidanza: è incinta?'
        self.assertTrue(any('sensibile' in x for x in draft_errors(d,fixture['sources'])))
    def test_unknown_review_does_not_pass(self):
        fixture=json.loads((ROOT/'tests/fixture.json').read_text());d=fixture['draft'];d.pop('fact_check_notes')
        self.assertIn('Revisione richiesta',draft_errors(d,fixture['sources']))
    def test_retry_uses_existing_future_post(self):
        fixture=json.loads((ROOT/'tests/fixture.json').read_text());data={'draft':fixture['draft'],'sources':fixture['sources']}
        self.store.put('id','titolo','Attualità','INVIO',data,'2026-10-01T07:00:00+02:00')
        client=Mock();client.existing_post.return_value={'id':7,'status':'future','link':'https://example.org/storia-id'}
        publish(self.store.rows()[0],datetime.now(UTC),self.store,client,self.cfg)
        client.create_post.assert_not_called();client.upload_media.assert_not_called()
        self.assertEqual(self.store.rows()[0]['state'],'PROGRAMMATO')
    def test_publication_includes_photo_credits_and_provenance(self):
        fixture=json.loads((ROOT/'tests/fixture.json').read_text())
        data={'draft':fixture['draft'],'sources':fixture['sources']}
        self.store.put('photo-test','Titolo','Attualità','INVIO',data)
        client=Mock();client.existing_post.return_value=None
        client.get_or_create_term.return_value={'id':1};client.related_link.return_value=''
        client.upload_media.return_value={'id':22};client.create_post.return_value={'id':33,'link':'https://example.org/post'}
        meta={'type':'archive_photo','name':'Mario Esempio','license':'CC BY 4.0','author':'Autore'}
        caption='Foto di archivio — Autore — CC BY 4.0'
        with patch('pipeline.choose',return_value=(b'photo','.jpg','image/jpeg',caption,meta)):
            publish(self.store.rows()[0],datetime.now(UTC)+timedelta(hours=1),self.store,client,self.cfg)
        payload=client.create_post.call_args[0][0]
        self.assertIn(caption,payload['content']);self.assertEqual(payload['featured_media'],22)
        self.assertEqual(json.loads(self.store.rows()[0]['data'])['image']['license'],'CC BY 4.0')
    def test_cover_png(self):self.assertTrue(cover('Perché gli oggetti raccontano storie','Curiosità e storie').startswith(b'\x89PNG'))
    def test_429_stops_without_fallback_or_retry(self):
        response=Mock(status_code=429)
        with patch.dict(os.environ,{'FREE_TIER_CONFIRMED':'true','GEMINI_API_KEY':'fake'}):
            ai=Gemini(self.cfg,self.store)
            with patch('engine.requests.post',return_value=response) as send:
                with self.assertRaises(QuotaStop):ai.call('article','test')
                self.assertEqual(send.call_count,1)
        self.assertEqual(self.store.db.execute('select count(*) from calls').fetchone()[0],1)
    def test_daily_target_respected_after_restart(self):
        for i,clock in enumerate(self.cfg['slots']):
            self.store.put(str(i),'Titolo','Attualità','INVIO',{},'2026-10-01T'+clock+':00+02:00')
        self.assertEqual(slots_available(self.cfg,self.store,datetime(2026,10,1,6,0,tzinfo=ZoneInfo('Europe/Rome'))),[])
    def test_no_call_without_free_tier_confirmation(self):
        with patch.dict(os.environ,{'FREE_TIER_CONFIRMED':'false'}):
            with self.assertRaises(RuntimeError):Gemini(self.cfg,self.store)
if __name__=='__main__':unittest.main()
