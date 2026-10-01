"""Classificazione e varietà locali: nessuna chiamata API aggiuntiva."""
import re
from collections import Counter

RULES=[
 ('Reality e TV',r'\b(grande fratello|uomini e donne|temptation island|ballando con le stelle|amici|isola dei famosi|x factor|sanremo|tale e quale|affari tuoi|che tempo che fa|domenica in|verissimo|palinsest\w*|televoto|nomination|concorrente|puntata|reality)\b'),
 ('Misteri e leggende',r'\b(fantasmi?|infestat\w*|paranormale|leggenda|leggende|misterios\w*|mistero|avvistament\w*|ufo|spettr\w*)\b'),
 ('Curiosità e storie',r'\b(mostra|museo|impero romano|archeolog\w*|ritrovamento|record|storia incredibile)\b'),
]

def classify(item):
    text=item.get('title','').casefold()
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
