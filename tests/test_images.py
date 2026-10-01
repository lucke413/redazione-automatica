import sys,unittest,io
from pathlib import Path
from unittest.mock import patch,Mock
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import images

def payload(license='CC BY-SA 4.0',license_url='https://creativecommons.org/licenses/by-sa/4.0/',restrictions='',description='Photograph of Mario Esempio'):
    return {'query':{'pages':{'1':{'categories':[{'title':'Category:Photographs of Mario Esempio'}], 'imageinfo':[{
        'url':'https://upload.wikimedia.org/wikipedia/commons/a/a1/Example.jpg','descriptionurl':'https://commons.wikimedia.org/wiki/File:Example.jpg',
        'mime':'image/jpeg','width':1000,'height':800,'size':90000,
        'extmetadata':{k:{'value':v} for k,v in {'LicenseShortName':license,'LicenseUrl':license_url,'Artist':'<a href="bad">Autore &amp; Co</a>','Restrictions':restrictions,'ImageDescription':description,'DateTimeOriginal':'2020'}.items()}}]}}}}
PERSON={'entity_id':'Q123','name':'Mario Esempio','filename':'Example.jpg'}
class Tests(unittest.TestCase):
    def test_license_author_and_credit(self):
        with patch('images.api',return_value=payload()):meta=images.metadata(PERSON)
        self.assertEqual(meta['author'],'Autore & Co')
        caption=images.credits(meta)
        self.assertIn('Foto d’archivio',caption);self.assertIn('CC BY-SA 4.0',caption);self.assertNotIn('href="bad"',caption)
    def test_nc_license_rejected(self):
        with patch('images.api',return_value=payload('CC BY-NC 4.0')):self.assertIsNone(images.metadata(PERSON))
    def test_missing_or_mismatched_license_url_rejected(self):
        for url in ('','https://evil.test/by-sa/4.0/'):
            with patch('images.api',return_value=payload(license_url=url)):self.assertIsNone(images.metadata(PERSON))
    def test_restrictions_block(self):
        with patch('images.api',return_value=payload(restrictions='personality rights')):self.assertIsNone(images.metadata(PERSON))
    def test_painting_or_ai_block(self):
        for desc in ['Painting of Mario Esempio','AI-generated photograph']:
            with patch('images.api',return_value=payload(description=desc)):self.assertIsNone(images.metadata(PERSON))
    def test_ambiguous_identity_blocked(self):
        with patch('images.api',return_value={'search':[{'id':'Q1','label':'Mario Esempio'},{'id':'Q2','label':'Mario Esempio'}]}) as api:
            self.assertIsNone(images.resolve_person('Mario Esempio'));self.assertEqual(api.call_count,1)
    def test_human_p18_selected(self):
        claims={'P31':[{'mainsnak':{'datavalue':{'value':{'id':'Q5'}}}}],'P18':[{'mainsnak':{'datavalue':{'value':'Example.jpg'}}}]}
        with patch('images.api',side_effect=[{'search':[{'id':'Q123','label':'Mario Esempio'}]},{'entities':{'Q123':{'claims':claims}}}]):
            self.assertEqual(images.resolve_person('Mario Esempio')['filename'],'Example.jpg')
    def test_unmentioned_name_never_searched(self):
        with patch('images.api') as api:
            result=images.choose({'title':'Una storia','body_markdown':'Storia pubblica','image_subject':'Mario Esempio'},[{'text':'Altra persona'}],'Storie')
            api.assert_not_called();self.assertEqual(result[4]['type'],'original_graphic')
    def test_network_failure_fallback(self):
        with patch('images.resolve_person',side_effect=images.requests.Timeout):
            result=images.choose({'title':'Mario Esempio racconta','image_subject':'Mario Esempio'},[{'text':'Mario Esempio racconta'}],'Spettacolo')
            self.assertEqual(result[4]['type'],'original_graphic')
    def test_image_bytes_checked(self):
        out=io.BytesIO();Image.new('RGB',(800,600)).save(out,format='JPEG')
        response=Mock();response.is_redirect=False;response.iter_content.return_value=[out.getvalue()];response.__enter__=Mock(return_value=response);response.__exit__=Mock(return_value=False)
        with patch('images.requests.get',return_value=response):
            raw,suffix=images.download({'file_url':'https://upload.wikimedia.org/example.jpg','mime':'image/jpeg'})
            self.assertEqual(raw,out.getvalue());self.assertEqual(suffix,'.jpg')
    def test_untrusted_download_host(self):
        with patch('images.requests.get') as get:
            with self.assertRaises(ValueError):images.download({'file_url':'https://evil.test/img.jpg'})
            get.assert_not_called()
    def test_real_photo_path(self):
        with patch('images.resolve_person',return_value=PERSON),patch('images.metadata',return_value={**PERSON,'type':'archive_photo','license':'CC BY 4.0','license_url':images.LICENSES['CC BY 4.0'],'author':'Autore','source_url':'https://commons.wikimedia.org/wiki/File:Example.jpg','mime':'image/jpeg'}),patch('images.download',return_value=(b'jpeg','.jpg')):
            result=images.choose({'title':'Mario Esempio racconta','image_subject':'Mario Esempio'},[{'text':'Mario Esempio racconta'}],'Spettacolo')
            self.assertEqual(result[0],b'jpeg');self.assertEqual(result[4]['type'],'archive_photo')
if __name__=='__main__':unittest.main()
