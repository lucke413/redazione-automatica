import unittest,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from editorial_policy import classify,balanced,cap
class PolicyTests(unittest.TestCase):
 def test_museum_is_not_gossip(self):
  self.assertEqual(classify({'title':'La mostra a Torino','category':'Spettacolo e gossip'}),'Curiosità e storie')
 def test_reality_and_legend(self):
  self.assertEqual(classify({'title':'Grande Fratello: il nuovo concorrente','category':'Spettacolo e gossip'}),'Reality e TV')
  self.assertEqual(classify({'title':'La leggenda del fantasma','category':'Attualità'}),'Misteri e leggende')
 def test_balance_and_rejected_scores(self):
  cfg={'categories':['Spettacolo e gossip','Scienza e tecnologia']}
  items={'a':{'category':'Scienza e tecnologia'},'b':{'category':'Spettacolo e gossip'},'c':{'category':'Spettacolo e gossip'}}
  ordered=balanced([{'id':'a','score':99},{'id':'b','score':80},{'id':'c','score':10}],items,cfg)
  self.assertEqual([x['id'] for x in ordered],['b','a'])
 def test_science_cap(self):
  cfg=json.loads((Path(__file__).resolve().parents[1]/'config/editorial.json').read_text())
  self.assertEqual(cap(cfg,'Scienza e tecnologia'),1)
  self.assertEqual(cap(cfg,'Scienza e tecnologia',True),2)

class TransportTests(unittest.TestCase):
 def test_timeout_retries_once_http_denied_does_not(self):
  import requests
  from unittest.mock import patch
  from engine import bounded_get
  with patch('engine._bounded_get_once',side_effect=[requests.Timeout(),b'feed']) as get:
   self.assertEqual(bounded_get('https://example.org',{'example.org'}),b'feed')
   self.assertEqual(get.call_count,2)
  with patch('engine._bounded_get_once',side_effect=requests.HTTPError()) as get:
   with self.assertRaises(requests.HTTPError):bounded_get('https://example.org',{'example.org'})
   self.assertEqual(get.call_count,1)
