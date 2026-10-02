#!/usr/bin/env python3
"""Eseguire da root: python scripts/pipeline.py [--offline] [--publish]."""
import argparse, csv, html, json, os
import requests
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from engine import (ROOT,UTC,Store,Gemini,QuotaStop,collect,DRAFT_INSTRUCTION,
                    draft_errors,slots_available,cover,key,headline_errors,draft_warnings,content_errors,normalise_draft)
from wp_base import WordPressClient, markdown_to_html
from images import choose
from editorial_policy import classify, balanced, cap
from recovery import prepare, assess, remaining, recover_local, recovery_queue, fresh


def write_report(store,out,cycle=None):
    out.mkdir(parents=True,exist_ok=True)
    rows=store.rows()
    cycle=cycle or {}
    current=[r for r in rows if r['id'] in cycle.get('attempted_ids',[])]
    cycle['articles']=[{'id':r['id'],'title':r['title'],'category':r['category'],'state':r['state'],'errors':json.loads(r['data']).get('errors',[]),'warnings':json.loads(r['data']).get('warnings',[])} for r in current]
    cycle['states']=dict(Counter(r['state'] for r in current))
    (out/'ciclo.json').write_text(json.dumps(cycle,ensure_ascii=False,indent=2))
    (out/'esecuzione.json').write_text(json.dumps({'version':'0.8.6','report_generated_at':datetime.now(UTC).isoformat(),'commit':os.getenv('GITHUB_SHA'),'run_id':os.getenv('GITHUB_RUN_ID'),'states':dict(Counter(r['state'] for r in rows)),'cycle':cycle,'note':'Stati cumulativi, non conteggi degli articoli nuovi del ciclo'},ensure_ascii=False,indent=2))
    (out/'report.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
    with (out/'social-manuale.csv').open('w',newline='') as f:
        writer=csv.writer(f);writer.writerow(['Titolo','Categoria','Stato','Data','Link','Varianti titolo'])
        for r in rows:
            d=json.loads(r['data']).get('draft',{})
            writer.writerow([r['title'],r['category'],r['state'],r['slot'],r['url'],' | '.join(d.get('title_variants',[]))])
    previews=[]
    for row in rows:
        data=json.loads(row['data']); draft=data.get('draft',{})
        if not draft.get('body_markdown'): continue
        filename='articolo-'+row['id']+'.html'
        page='<html lang="it"><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>'+html.escape(row['title'])+'</title><style>body{max-width:760px;margin:30px auto;padding:20px;font:18px/1.65 system-ui}img{max-width:100%}</style><p>'+html.escape(row['category']+' · '+row['state'])+'</p><h1>'+html.escape(row['title'])+'</h1>'+markdown_to_html(draft['body_markdown'])+'</html>'
        (out/filename).write_text(page,encoding='utf-8')
        previews.append('<li><a href="'+filename+'">'+html.escape(row['title'])+'</a> — '+html.escape(row['state'])+'</li>')
    (out/'articoli.html').write_text('<html lang="it"><meta charset="utf-8"><h1>Anteprime articoli</h1><ul>'+''.join(previews)+'</ul></html>',encoding='utf-8')
    cycle_summary='<h2>Questo ciclo</h2><p>'+html.escape(str(len(current)))+' articoli elaborati. '+html.escape(str(cycle.get('stop_reason','')))+' </p><ul>'+''.join('<li>'+html.escape(r['title']+' — '+r['state'])+'</li>' for r in current)+'</ul><p>Diagnostica dettagliata in ciclo.json</p><h2>Storico</h2>'
    table=''.join('<tr>'+''.join('<td>'+html.escape(str(v or ''))+'</td>' for v in [r['title'],r['category'],r['state'],r['slot'],r['url']])+'</tr>' for r in rows)
    (out/'dashboard.html').write_text('<!doctype html><html lang="it"><meta charset="utf-8"><title>Redazione</title><style>body{font:16px system-ui;margin:35px;background:#f4f6fa}table{border-collapse:collapse;background:white}td,th{padding:12px;border-bottom:1px solid #ddd;text-align:left}h1{color:#102335}</style><h1>Redazione — stato del ciclo</h1><p><a href="articoli.html">Leggi gli articoli completi</a></p><p>Archivio cumulativo: le vecchie revisioni non indicano nuovi errori. In simulazione nessun invio a WordPress. Dettaglio raccolta in fonti.json.</p>'+cycle_summary+'<table><tr><th>Titolo</th><th>Categoria</th><th>Stato</th><th>Programmazione</th><th>Link</th></tr>'+table+'</table></html>')


def publish(row,slot,store,client,cfg,review=False):
    data=json.loads(row['data']);draft=data['draft']
    draft.setdefault('title',row['title'])
    slug='storia-'+row['id']  # identità stabile anche se il titolo cambia
    # Prima riconciliare ogni tentativo precedente: retry dopo timeout non crea doppioni.
    existing=client.existing_post(slug)
    if existing:
        status=existing.get('status')
        state={'publish':'PUBBLICATO','future':'PROGRAMMATO','draft':'REVISIONE','pending':'REVISIONE'}.get(status,'REVISIONE')
        store.put(row['id'],draft['title'],row['category'],state,data,row.get('slot'),existing['id'],existing.get('link'))
        return
    category=client.get_or_create_term('categories',row['category'])
    tags=[client.get_or_create_term('tags',str(t)[:50])['id'] for t in (draft.get('tags') if isinstance(draft.get('tags'),list) else [])[:6]]
    related=client.related_link(draft,category['id'])
    image_bytes,suffix,mime,caption,image_meta=choose(draft,data['sources'],row['category'],enabled=cfg.get('commons_photos',True) and not review)
    data['image']=image_meta
    # Conservare provenienza e licenza PRIMA di inviare il file al CMS.
    store.put(row['id'],row['title'],row['category'],'INVIO',data,slot.isoformat() if slot else None)
    alt=('Foto d’archivio di '+image_meta['name']) if image_meta['type']=='archive_photo' else draft['title']
    media=client.upload_media(image_bytes,slug+suffix,mime,alt,caption)
    source_links=''.join('<li><a href="'+html.escape(s['url'],quote=True)+'">'+html.escape(s['source_name'])+'</a></li>' for s in data['sources'])
    body=markdown_to_html(draft['body_markdown'])+related+'<h2>Fonti</h2><ul>'+source_links+'</ul><p><small>Contenuto prodotto con assistenza IA.</small></p><p class="image-credits"><small>'+caption+'</small></p>'
    seo={k:str(draft.get(k,'')) for k in ('seo_title','seo_description','focus_keyphrase')}
    payload={'title':draft['title'],'slug':slug,'content':body,'excerpt':draft.get('excerpt',''),'categories':[category['id']],'tags':tags,'featured_media':media['id'],'status':'draft' if review else 'future','editorial_seo':seo}
    if not review:
        payload.update(date=slot.strftime('%Y-%m-%dT%H:%M:%S'),date_gmt=slot.astimezone(UTC).strftime('%Y-%m-%dT%H:%M:%S'))
    # Stesso payload contiene SEO e post, il bridge è verificato prima della pipeline.
    created=client.create_post(payload)
    state='REVISIONE' if review else 'PROGRAMMATO'
    store.put(row['id'],draft['title'],row['category'],state,data,slot.isoformat() if slot else None,created['id'],created.get('link'))


def run(cfg,store,offline=False,publish_live=False,cycle=None):
    if cycle is None: cycle={}
    cycle.update(started_at=datetime.now(UTC).isoformat(),mode='publication' if publish_live else 'simulation',attempted_ids=[],skips=[],stop_reason='completed')
    slots=slots_available(cfg,store)
    if not slots and publish_live:
        cycle['stop_reason']='no_slots';return
    client=None
    if publish_live:
        base=os.environ.get('EDITORIAL_WP_URL','').rstrip('/')
        if not base.startswith('https://') or 'aivision.altervista.org' in base.lower(): raise RuntimeError('Impostare URL HTTPS del NUOVO sito, distinto da AI Vision')
        client=WordPressClient(base,os.environ['EDITORIAL_WP_USER'],os.environ['EDITORIAL_WP_PASSWORD'],False)
        bridge=client.session.get(base+'/wp-json/editorial/v1/status',timeout=20)
        bridge.raise_for_status()
        if bridge.json().get('version')!='1.0': raise RuntimeError('Installare Editorial Bridge prima di pubblicare')
        # Riprende i tentativi ambigui prima di produrre altro materiale.
        for r in store.rows():
            if r['state']=='INVIO':
                publish(r,datetime.fromisoformat(r['slot']) if r['slot'] else None,store,client,cfg,review=not bool(r['slot']))
        slots=slots_available(cfg,store)
    if not slots and publish_live:
        cycle['stop_reason']='no_slots';return
    ai=None
    if offline:
        fixture=json.loads((ROOT/'tests/fixture.json').read_text())
        candidates=fixture['sources']
        candidates=[c for c in candidates if not store.duplicate(c)]
    else:
        candidates=collect(cfg,store)
    if not candidates: cycle['stop_reason']='no_new_candidates'
    cycle['candidates']=len(candidates)
    cycle['candidate_categories']=dict(Counter(c['category'] for c in candidates))
    # Scorte valide: massimo 48 ore, nessun nuovo costo IA.
    recover_local(store,cfg,cycle)
    ready=[]
    for r in store.rows():
        if r['state']=='PRONTO':
            data=json.loads(r['data'])
            old_draft=data.get('draft',{})
            before=json.dumps(old_draft,ensure_ascii=False)
            try:
                data['draft']=prepare(old_draft,data.get('sources',[]))
                issues=draft_errors(data['draft'],data.get('sources',[]))
            except (ValueError,TypeError,KeyError):
                issues=['Bozza delle scorte non valida']
            # Mantieni coerenti titolo DB, anteprima, CSV e invio WordPress.
            r=dict(r)
            r['title']=(data['draft'].get('title') if isinstance(data.get('draft'),dict) else None) or r['title']
            if before!=json.dumps(data['draft'],ensure_ascii=False):
                store.put(r['id'],r['title'],r['category'],r['state'],data,r['slot'],r['post_id'],r['url'])
                r=dict(r);r['data']=json.dumps(data,ensure_ascii=False)
                cycle.setdefault('stock_metadata_updated',[]).append(r['id'])
                cycle.setdefault('stock_repairs',[]).append({'id':r['id'],'title':r['title']})
            if issues:
                data['errors']=list(dict.fromkeys(data.get('errors',[])+issues))
                store.put(r['id'],r['title'],r['category'],'REVISIONE',data,r['slot'],r['post_id'],r['url'])
                cycle.setdefault('stock_revalidated',[]).append({'id':r['id'],'title':r['title'],'errors':issues})
                continue
            if fresh(data.get('sources',[]),cfg): ready.append(r)
            else:store.put(r['id'],r['title'],r['category'],'ARCHIVIO',data)
    # Limita anche le scorte: la coda scientifica non deve bloccare le nuove categorie.
    ready_counts=Counter(); eligible=[]
    for row in ready:
        if ready_counts[row['category']]<cap(cfg,row['category']):
            eligible.append(row);ready_counts[row['category']]+=1
    ready=eligible
    # In simulazione gli slot non vengono consumati: elabora comunque le nuove
    # fonti anche quando esistono articoli PRONTO nello storico. In pubblicazione
    # reale il limite resta quello degli slot.
    api_stopped=False
    if not offline and remaining(cfg,store)>0:
        queue=recovery_queue(store,cfg)
        for row,data in queue:
            if publish_live and len(ready)>=len(slots): break
            if ai is None: ai=Gemini(cfg,store)
            if remaining(cfg,store,ai)<1: break
            cycle['attempted_ids'].append(row['id'])
            cycle.setdefault('recovery_attempts',[]).append(row['id'])
            data['recovery_attempted']=True
            try:
                approved=assess(data,ai)
                store.put(row['id'],data['draft']['title'],row['category'],'PRONTO' if approved else 'REVISIONE',data)
                if approved: ready.append(next(r for r in store.rows() if r['id']==row['id']))
            except QuotaStop as e:
                data['pending_audit']=True
                data['errors']=['Quota esaurita: verifica non completata']
                store.put(row['id'],data['draft']['title'],row['category'],'REVISIONE',data)
                cycle['stop_reason']=str(e);api_stopped=True;break
            except (ValueError,KeyError,TypeError,requests.RequestException,RuntimeError) as e:
                data['errors']=['Recupero non completato: '+type(e).__name__]
                store.put(row['id'],row['title'],row['category'],'REVISIONE',data)
                if isinstance(e,(requests.RequestException,RuntimeError)):
                    cycle['stop_reason']='API temporaneamente non disponibile';api_stopped=True;break
    if candidates and not api_stopped and (not publish_live or len(ready)<len(slots)):
        # Classifica locale: conserva la varietà, risparmia una chiamata per ciclo.
        selected=[{'id':x['id'],'score':min(95,65+len(x.get('text','').split())//40)} for x in candidates]
        cycle['ranking_method']='local'
        by_id={c['id']:dict(c) for c in candidates};seen=set()
        for choice in selected:
            if isinstance(choice,dict) and choice.get('id') in by_id and choice.get('category') in cfg['categories']:
                by_id[choice['id']]['category']=choice['category']
        cycle['ranked_items']=len(selected)
        cycle['ranking_rejected']=sum(1 for c in selected if not isinstance(c,dict) or c.get('id') not in by_id or not isinstance(c.get('score'),(int,float)) or c.get('score',0)<55)
        selected=balanced(selected,by_id,cfg,[r['category'] for r in ready] if publish_live else [])
        categories=Counter(r['category'] for r in ready) if publish_live else Counter()
        generated=0
        for choice in selected:
            if generated>=cfg['per_cycle']:
                cycle['stop_reason']='cycle_target_reached';break
            if publish_live and len(ready)>=len(slots):
                cycle['stop_reason']='ready_stock_fills_slots';break
            if not isinstance(choice,dict) or choice.get('id') not in by_id or choice['id'] in seen:continue
            seen.add(choice['id'])
            if not isinstance(choice.get('score'),(int,float)) or choice['score']<55:continue
            source=by_id[choice['id']]
            if categories[source['category']]>=cap(cfg,source['category']):
                cycle['skips'].append({'id':source['id'],'reason':'category_cap','category':source['category']});continue
            # Scrittura da una sola notizia: le correlate non entrano nel prompt.
            sources=[{k:v for k,v in source.items() if k!='related'}]
            cycle['attempted_ids'].append(source['id'])
            draft=None
            data={'sources':sources,'score':choice['score'],'image':{'type':'original_graphic','license':'own','author':'Sistema editoriale'}}
            try:
                if not offline:
                    # Non iniziare una bozza se non resta almeno una chiamata per verificarla.
                    if remaining(cfg,store,ai)<2:
                        raise QuotaStop('Budget residuo insufficiente per scrittura e verifica; scorte disponibili')
                    if ai is None: ai=Gemini(cfg,store)
                draft=fixture['draft'] if offline else ai.call('article',DRAFT_INSTRUCTION+'\n'+json.dumps(sources,ensure_ascii=False))
                data['draft']=draft
                approved=assess(data,ai,offline)
                draft=data['draft']
                store.put(source['id'],draft.get('title',source['title']),source['category'],'PRONTO' if approved else 'REVISIONE',data)
                if approved:
                    generated+=1
                    ready.append(next(r for r in store.rows() if r['id']==source['id']));categories[source['category']]+=1
            except QuotaStop as e:
                cycle['stop_reason']=str(e)
                if draft is None:
                    cycle['attempted_ids'].remove(source['id'])
                    cycle['skips'].append({'id':source['id'],'reason':'quota_before_generation'})
                elif isinstance(data.get('draft'),dict) and data['draft'].get('body_markdown'):
                    data['pending_audit']=True
                    data['errors']=['Quota esaurita: verifica non completata']
                    store.put(source['id'],data['draft'].get('title',source['title']),source['category'],'REVISIONE',data)
                break
            except (ValueError,KeyError,TypeError,requests.RequestException,RuntimeError) as e:
                data['errors']=[type(e).__name__]
                # Non salvare strutture non valide come bozze leggibili.
                if not isinstance(data.get('draft'),dict): data.pop('draft',None)
                store.put(source['id'],source['title'],source['category'],'REVISIONE',data)
                if isinstance(e,(requests.RequestException,RuntimeError)):
                    cycle['stop_reason']='API temporaneamente non disponibile';break
    if ai is not None: cycle['ai_calls_this_cycle']=ai.count
    cycle['ai_calls_remaining']=remaining(cfg,store,ai)
    cycle['ready_available']=len(ready)
    day=datetime.now(UTC).astimezone(__import__('zoneinfo').ZoneInfo(cfg['timezone'])).date().isoformat()
    daily_categories=Counter(r['category'] for r in store.rows() if r['slot'] and r['slot'].startswith(day) and r['state'] in ('PROGRAMMATO','PUBBLICATO','INVIO'))
    for row in ready:
        if not slots:break
        if daily_categories[row['category']]>=cap(cfg,row['category'],daily=True):continue
        if publish_live:
            slot=slots.pop(0)
            store.put(row['id'],row['title'],row['category'],'INVIO',json.loads(row['data']),slot.isoformat())
            row['slot']=slot.isoformat()
            publish(row,slot,store,client,cfg)
            daily_categories[row['category']]+=1
        else:
            # Simulazione non consuma slot reali né cambia PRONTO in pubblicato.
            path=ROOT/'output'/('copertina-'+row['id']+'.png');path.parent.mkdir(exist_ok=True)
            path.write_bytes(cover(row['title'],row['category']))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--offline',action='store_true');parser.add_argument('--publish',action='store_true');args=parser.parse_args()
    if args.offline and args.publish:parser.error('Offline non può pubblicare')
    cfg=json.loads((ROOT/'config/editorial.json').read_text())
    store=Store(ROOT/('state-demo/editorial.sqlite' if args.offline else 'state/editorial.sqlite'))
    cycle={}
    try:run(cfg,store,args.offline,args.publish,cycle)
    except QuotaStop as e:
        cycle['stop_reason']=str(e);print(str(e))
    finally:
        cycle['finished_at']=datetime.now(UTC).isoformat()
        write_report(store,ROOT/'output',cycle);store.db.close()
if __name__=='__main__':main()
