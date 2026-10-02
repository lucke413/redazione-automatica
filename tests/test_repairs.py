import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from engine import content_errors,normalise_draft,metadata_complete
class RepairTests(unittest.TestCase):
 def test_health_cannot_self_approve(self):
  self.assertIn('Contenuto sanitario: revisione richiesta',content_errors({'title':'Obesità e disturbi alimentari','risk':'low'},[]))
 def test_folklore_claim_and_qualification(self):
  src=[{'text':'Questi amuleti erano portafortuna secondo una credenza.'}]
  self.assertTrue(content_errors({'title':'I bambolotti che proteggevano dalle bombe'},src))
  self.assertEqual(content_errors({'title':'La leggenda dei bambolotti che proteggevano dalle bombe'},src),[])
 def test_punchy_nonclinical_story_allowed(self):
  self.assertEqual(content_errors({'title':'Ballando, la risposta che riapre la sfida','body_markdown':'Il concorrente risponde al giudice.'},[]),[])
 def test_truncated_seo_replaced_with_complete_variant(self):
  d={'title':'Titolo '+('troppo lungo '*10),'seo_title':'Quando il pregiudizio blocca le','seo_description':'Scopri tutte le novità di','title_variants':['Il pregiudizio ostacola le cure'],'focus_keyphrase':'pregiudizio','excerpt':'Un testo completo e breve.'}
  d=normalise_draft(d)
  self.assertEqual(d['seo_title'],'Il pregiudizio ostacola le cure')
  self.assertEqual(d['seo_description'],'Un testo completo e breve.')
  self.assertEqual(normalise_draft(dict(d)),d)
 def test_long_metadata_never_blindly_sliced(self):
  d=normalise_draft({'title':'a '*100,'seo_title':'b '*100,'seo_description':'c '*200,'focus_keyphrase':'Un tema concreto','title_variants':[]})
  self.assertEqual(d['seo_title'],'Un tema concreto')
  self.assertTrue(metadata_complete(d['seo_description']))
  self.assertLessEqual(len(d['seo_description']),160)
 def test_good_metadata_preserved(self):
  d={'seo_title':'Un titolo completo','seo_description':'Una descrizione completa.'}
  self.assertEqual(normalise_draft(dict(d)),d)
