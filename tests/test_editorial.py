import unittest,sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from engine import headline_errors,promotional_source,draft_errors,ROOT,evidence_matches,draft_warnings
class EditorialTests(unittest.TestCase):
 def test_explicit_ad(self):
  self.assertTrue(promotional_source({'text':'Contenuto sponsorizzato: potremmo ricevere una commissione.'}))
 def test_news_about_prices_allowed(self):
  self.assertFalse(promotional_source({'text':'I prezzi aumentano del 20% secondo i dati diffusi oggi.'}))
 def test_false_quote_blocked(self):
  self.assertTrue(headline_errors({'title':'Totti: “Non parlava, ecco perché aveva paura”'},[{'text':'All’inizio era scioccato, non parlava. Poi mi ha spiegato che era preoccupato.'}]))
 def test_literal_quote_allowed(self):
  self.assertEqual(headline_errors({'title':'La confessione: “All’inizio era scioccato, non parlava”'},[{'text':"All'inizio era scioccato, non parlava."}]),[])
 def test_lively_indirect_headline_allowed(self):
  self.assertEqual(headline_errors({'title':'Noemi a Ballando, Totti resta senza parole: il motivo raccontato da lei'},[{'text':'All’inizio era scioccato, non parlava.'}]),[])
 def test_variants_checked(self):
  self.assertTrue(headline_errors({'title':'Titolo','title_variants':['Lei: «Questa frase non è stata mai pronunciata»']},[{'text':'Un altro testo.'}]))
 def test_two_claims_with_audit_allowed(self):
  f=json.loads((ROOT/'tests/fixture.json').read_text());d=f['draft']
  d['claims']=d['claims'][:2];d['body_markdown']+='\n\nVoi che cosa ne pensate?'
  self.assertNotIn('Evidenze insufficienti',draft_errors(d,f['sources']))
  d['claims']=d['claims'][:1]
  self.assertIn('Evidenze insufficienti',draft_errors(d,f['sources']))

 def test_brief_lengths_and_question_not_blocking(self):
  f=json.loads((ROOT/'tests/fixture.json').read_text());d=f['draft']
  for length in (180,208,238):
   d['body_markdown']=' '.join('parola'+str(i) for i in range(length))
   self.assertNotIn('Lunghezza non valida',draft_errors(d,f['sources']))
   self.assertNotIn('Finale senza domanda ai lettori',draft_errors(d,f['sources']))
   self.assertEqual(draft_warnings(d),['Finale senza domanda ai lettori'])
  d['body_markdown']='breve '*179
  self.assertIn('Lunghezza non valida',draft_errors(d,f['sources']))
 def test_evidence_typography_not_changed_facts(self):
  self.assertTrue(evidence_matches('La banda K (18–26 GHz)', 'La banda K, 18-26 GHz.'))
  self.assertFalse(evidence_matches('La banda K 18-28 GHz', 'La banda K 18-26 GHz'))
  self.assertFalse(evidence_matches('La visita non è confermata', 'La visita è confermata'))
