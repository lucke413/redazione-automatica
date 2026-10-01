"""Fotografie Wikimedia gratuite: identità esatta, P18, licenza, crediti; fallback locale.
Non cerca foto nelle testate. Non riconosce volti e non genera immagini IA.
"""
import html, io, re, unicodedata
from urllib.parse import urlsplit
from datetime import datetime, timezone
import requests
from PIL import Image
from engine import cover, plain

UA='EditorialPhotoBot/0.2 (Wikimedia licensed image reader; no face recognition)'
API_WD='https://www.wikidata.org/w/api.php'
API_COMMONS='https://commons.wikimedia.org/w/api.php'
LICENSES={
    'CC BY 4.0':'https://creativecommons.org/licenses/by/4.0/',
    'CC BY 3.0':'https://creativecommons.org/licenses/by/3.0/',
    'CC BY 2.0':'https://creativecommons.org/licenses/by/2.0/',
    'CC BY-SA 4.0':'https://creativecommons.org/licenses/by-sa/4.0/',
    'CC BY-SA 3.0':'https://creativecommons.org/licenses/by-sa/3.0/',
    'CC BY-SA 2.0':'https://creativecommons.org/licenses/by-sa/2.0/',
    'CC0':'https://creativecommons.org/publicdomain/zero/1.0/',
    'Public domain':'https://creativecommons.org/publicdomain/mark/1.0/',
}

def norm(value):
    return ' '.join(re.findall(r'\w+',unicodedata.normalize('NFKC',str(value)).casefold()))

def api(url,params):
    r=requests.get(url,params={'format':'json',**params},headers={'User-Agent':UA},timeout=(5,12))
    r.raise_for_status();payload=r.json()
    if 'error' in payload:raise ValueError('Errore Wikimedia')
    return payload

def resolve_person(name):
    if not 3<=len(name)<=100 or len(name.split())<2:return None
    results=api(API_WD,{'action':'wbsearchentities','search':name,'language':'it','uselang':'it','type':'item','limit':10}).get('search',[])
    # Non scegliere "il primo risultato": tutti gli esatti devono convergere su un solo umano.
    candidates=[]
    for item in results:
        values=[item.get('label',''),item.get('match',{}).get('text','')]+item.get('aliases',[])
        if any(norm(v)==norm(name) for v in values) and re.fullmatch(r'Q[1-9]\d*',item.get('id','')):candidates.append(item['id'])
    candidates=list(dict.fromkeys(candidates))
    if len(candidates)!=1:return None
    id=candidates[0]
    entity=api(API_WD,{'action':'wbgetentities','ids':id,'props':'claims|labels|aliases','languages':'it|en'}).get('entities',{}).get(id,{})
    claims=entity.get('claims',{})
    humans=[c.get('mainsnak',{}).get('datavalue',{}).get('value',{}).get('id') for c in claims.get('P31',[]) if c.get('rank')!='deprecated']
    if 'Q5' not in humans:return None
    photos=[c.get('mainsnak',{}).get('datavalue',{}).get('value') for c in claims.get('P18',[]) if c.get('rank')!='deprecated']
    photos=[p for p in photos if isinstance(p,str) and p.lower().endswith(('.jpg','.jpeg','.png'))]
    if not photos:return None
    return {'entity_id':id,'name':name,'filename':photos[0]}

def metadata(person):
    payload=api(API_COMMONS,{'action':'query','titles':'File:'+person['filename'],'prop':'imageinfo|categories','cllimit':50,'iiprop':'url|extmetadata|mime|size','iiextmetadatalanguage':'en'})
    pages=payload.get('query',{}).get('pages',{})
    for page in pages.values():
        if 'missing' in page:continue
        info=(page.get('imageinfo') or [{}])[0]
        meta=info.get('extmetadata',{})
        val=lambda k:plain(meta.get(k,{}).get('value','')).strip()
        license=val('LicenseShortName');url=val('LicenseUrl')
        if license not in LICENSES:return None
        expected=LICENSES[license]
        if url.replace('http://','https://').rstrip('/')!=expected.rstrip('/'):return None
        if val('Restrictions'):return None  # segnalazioni supplementari: revisione, non autopubblicazione
        author=val('Artist')
        if not author or len(author)>600:return None
        if info.get('mime') not in ('image/jpeg','image/png'):return None
        if info.get('width',0)<600 or info.get('height',0)<400 or info.get('size',0)>12_000_000:return None
        fileurl=info.get('url','');pageurl=info.get('descriptionurl','')
        if not safe_url(fileurl,'upload.wikimedia.org') or not safe_url(pageurl,'commons.wikimedia.org'):return None
        description=val('ImageDescription')
        credit=val('Credit')[:1200]
        attribution=val('Attribution')[:1200]
        categories=' '.join(c.get('title','') for c in page.get('categories',[]))
        signals=(description+' '+categories+' '+person['filename']).casefold()
        # P18 può essere anche un dipinto o un'immagine sintetica: non basta da solo.
        if re.search(r'painting|drawing|illustration|sculpture|ai.generated|ai-generated|synthetic|caricatur|dipinto|disegno|deletion requests|copyright violations|disputed',signals):return None
        if not re.search(r'photograph|photographic|photo\b|fotograf|fotografia',signals):return None
        return {**person,'type':'archive_photo','provider':'Wikimedia Commons','license':license,'license_url':expected,'author':author,'source_url':pageurl,'file_url':fileurl,'credit':credit,'attribution':attribution,'description':description[:1500],'date':val('DateTimeOriginal')[:200],'mime':info['mime'],'size':info.get('size'),'checked_at':datetime.now(timezone.utc).isoformat(),'modifications':'Nessuna modifica al file originale'}
    return None

def safe_url(url,host):
    p=urlsplit(url)
    return p.scheme=='https' and p.hostname==host and not p.username and not p.password and p.port in (None,443)

def download(meta):
    if not safe_url(meta['file_url'],'upload.wikimedia.org'):raise ValueError('Host immagine non valido')
    with requests.get(meta['file_url'],headers={'User-Agent':UA},timeout=(5,20),stream=True,allow_redirects=False) as r:
        r.raise_for_status()
        if r.is_redirect:raise ValueError('Redirect non accettato')
        data=bytearray()
        for chunk in r.iter_content(32768):
            data.extend(chunk)
            if len(data)>12_000_000:raise ValueError('Immagine troppo grande')
    raw=bytes(data)
    with Image.open(io.BytesIO(raw)) as im:
        if im.format not in ('JPEG','PNG') or im.width<600 or im.height<400 or im.width*im.height>40_000_000:raise ValueError('Formato o dimensioni immagine non validi')
        fmt=im.format;im.verify()
    actual='image/jpeg' if fmt=='JPEG' else 'image/png'
    if actual!=meta['mime']:raise ValueError('MIME incoerente')
    return raw,'.jpg' if fmt=='JPEG' else '.png'

def credits(meta):
    esc=lambda s:html.escape(str(s),quote=True)
    date=(' Data indicata nell’archivio: '+esc(meta['date'])+'.') if meta.get('date') else ''
    extra=(' Crediti aggiuntivi: '+esc(meta.get('attribution') or meta.get('credit'))+'.') if (meta.get('attribution') or meta.get('credit')) else ''
    return ('Foto d’archivio di '+esc(meta['name'])+'; non documenta necessariamente l’evento raccontato.'+date+
            ' Autore: '+esc(meta['author'])+'.'+extra+' <a href="'+esc(meta['source_url'])+'">Wikimedia Commons — file originale</a>.'+
            ' Licenza: <a href="'+esc(meta['license_url'])+'">'+esc(meta['license'])+'</a>. File originale, non modificato.')

def choose(draft,sources,category,enabled=True):
    name=str(draft.get('image_subject') or '').strip()
    # Il nome proposto dal modello deve comparire sia nell'articolo sia nelle fonti.
    article=norm(draft.get('title','')+' '+draft.get('body_markdown',''))
    source=' '.join(norm(x.get('title','')+' '+x.get('text','')) for x in sources)
    reason='Nessun soggetto fotografico identificato con sufficiente certezza'
    if enabled and name and re.search(r'(?<!\w)'+re.escape(norm(name))+r'(?!\w)',article) and re.search(r'(?<!\w)'+re.escape(norm(name))+r'(?!\w)',source):
        try:
            person=resolve_person(name)
            meta=metadata(person) if person else None
            if meta:
                raw,suffix=download(meta)
                return raw,suffix,meta['mime'],credits(meta),meta
            reason='Identità, natura fotografica, licenza o condizioni non sufficientemente certe'
        except (requests.RequestException,ValueError,KeyError,TypeError,OSError,Image.DecompressionBombError):
            reason='Ricerca o download foto non disponibile: ripiego gratuito'
    return cover(draft['title'],category),'.png','image/png','Copertina grafica originale: immagine illustrativa, non fotografia dell’evento.',{'type':'original_graphic','license':'own','author':'Sistema editoriale','fallback_reason':reason}
