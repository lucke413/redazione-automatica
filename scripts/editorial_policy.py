"""Classificazione e varietà locali: nessuna chiamata API aggiuntiva."""
import re
from collections import Counter

RULES=[
 ('Reality e TV',r'\b(grande fratello|uomini e donne|temptation island|ballando con le stelle|amici|isola dei famosi|x factor|sanremo|tale e quale|affari tuoi|che tempo che fa|domenica in|verissimo|palinsest\w*|televoto|nomination|concorrente|puntata|reality)\b'),
 ('Misteri e leggende',r'\b(fantasmi?|infestat\w*|paranormale|leggenda|leggende|misterios\w*|mistero|avvistament\w*|ufo|spettr\w*)\b'),
 ('Curiosità e storie',r'\b(mostra|museo|impero romano|archeolog\w*|ritrovamento|record|storia incredibile)\b'),
]

EVENT_STOPWORDS={
    'oggi','ieri','domani','notizie','news','video','diretta','ultime',
    'nuovo','nuova','nuovi','nuove','tutto','tutta','tutti','tutte',
    'annuncio','annunciato','racconta','racconto','svelato','svelata',
    'parla','parole','arriva','arrivano','scopriamo','scoperta','caso',
    'dopo','prima','ancora','proprio','potrebbe','secondo','quanto',
}

def event_words(text):
    """Token distintivi utili a riconoscere lo stesso fatto tra fonti."""
    words=set(re.findall(r"[a-zàèéìòù]{4,}",str(text).casefold()))
    return words-EVENT_STOPWORDS

def same_event(a,b):
    """Match conservativo: stesso tema TV o stessi nomi non bastano."""
    def terms(title):
        title=re.sub(r"grande fratello(?: vip)?|ballando con le stelle|uomini e donne|temptation island", "", str(title), flags=re.I)
        return event_words(title)
    left,right=terms(a.get('title','')),terms(b.get('title',''))
    overlap=left & right
    if len(overlap)<2 or len(overlap)/max(1,min(len(left),len(right)))<.6:
        return False
    body_left,body_right=event_words(a.get('text','')),event_words(b.get('text',''))
    if not body_left or not body_right:
        return left==right and len(left)>=3
    # Anche la descrizione dell'evento deve coincidere, non solo il programma.
    return len(body_left & body_right)/max(1,min(len(body_left),len(body_right)))>=.55

def classify(item):
    text=item.get('title','').casefold()
    lead=text+' '+str(item.get('text',''))[:1600].casefold()
    # La vicenda prevale sul programma che ospita l'intervista.
    judicial=re.search(r'\b(?:procura|rinvio a giudizio|udienza preliminare|indagini a (?:suo|sua|loro) carico)\b',lead)
    crime=re.search(r'\b(?:omicidio|indagat\w*|imputat\w*|processo|inchiesta|condanna)\b',lead)
    fiction=re.search(r'\b(?:fiction|serie tv|serie televisiva|trama|personaggio immaginario)\b',lead)
    if judicial and crime and not fiction: return 'Attualità'
    for category,pattern in RULES:
        if re.search(pattern,text): return category
    return item.get('category','Curiosità e storie')

def cap(cfg,category,daily=False):
    field='category_daily_caps' if daily else 'category_cycle_caps'
    return cfg.get(field,{}).get(category,cfg.get('max_per_category_daily',8) if daily else 2)

def balanced(choices,by_id,cfg,existing=()):
    """Ordina tutte le idee valide con turni fra categorie; non aggiunge idee bocciate."""
    counts=Counter(existing); buckets={}; seen=set()
    for choice in choices:
        if not isinstance(choice,dict) or choice.get('id') not in by_id or choice['id'] in seen:continue
        score=choice.get('score')
        if not isinstance(score,(int,float)) or isinstance(score,bool) or score<55:continue
        seen.add(choice['id']); cat=by_id[choice['id']]['category']
        buckets.setdefault(cat,[]).append(choice)
    for bucket in buckets.values():bucket.sort(key=lambda c:c['score'],reverse=True)
    result=[]; order=cfg['categories']
    while any(buckets.values()):
        cats=[c for c,b in buckets.items() if b]
        cat=min(cats,key=lambda c:(counts[c],order.index(c) if c in order else len(order)))
        result.append(buckets[cat].pop(0));counts[cat]+=1
    return result
