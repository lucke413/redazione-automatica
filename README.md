# Nuovo progetto editoriale — versione 0.2

Adattamento del repository AI Vision. Obiettivo 20 articoli/giorno, costo operativo zero,
Facebook manuale, monetizzazione AlterVista + AdSense. Non modifica il progetto AI Vision.

## Cosa è pronto

- Quattro esecuzioni GitHub Actions al giorno, cinque slot per ciclo, venti slot tra le 07 e le 22 (Europe/Rome).
- Filtro RSS locale, scadenza delle notizie, deduplicazione URL/titoli, raggruppamento fonti simili.
- Una selezione IA in gruppo; testo, tre titoli e SEO in un'unica chiamata; verifica IA separata.
- Controlli deterministici su evidenze testuali, lunghezza, metadata, copia letterale e temi sensibili.
- Bozze problematiche in REVISIONE; soltanto articoli approvati in programmazione.
- Contatori API persistenti: massimo 48 richieste/giorno Pacific time e 11/ciclo, nessun retry automatico su quota.
- Scorte PRONTO, riutilizzate entro 48 ore dalla data delle fonti.
- Foto reali da Wikimedia Commons per persone identificate: licenza, crediti e didascalia di archivio. Ripiego su copertine originali 1200x630. Dettagli in `docs/FOTO_E_ACCOUNT.md`.
- Stato SQLite su branch `editorial-state`, riconciliazione WordPress mediante slug stabile.
- Bridge WordPress per SEO, Open Graph, schema Article e riepilogo redazione.
- Report HTML e CSV per scegliere manualmente i link da condividere.

## Limiti da conoscere PRIMA dell'attivazione

Questa è una prima versione collaudata offline, non un servizio già attivo.
Venti pubblicazioni sono un OBIETTIVO: quote Google, fonti sufficienti e controlli possono ridurle.
Le 48 chiamate locali NON sono una quota concessa da Google. Adeguarle alla quota reale in AI Studio,
sottraendo l'uso di AI Vision se condivide lo stesso progetto. Cambiare orari non aumenta la quota giornaliera.
Il software non può certificare il piano di fatturazione della chiave: usare un progetto Google SENZA
fatturazione collegata. Non c'è alcun passaggio a un altro provider/modello e non vengono abilitate spese.

Fonti iniziali: NASA, MEDIA INAF, Fanpage spettacolo e RSS ANSA documentati nella pagina https://www.ansa.it/sito/static/ansa_rss.html .
Le pagine ANSA non vengono scaricate automaticamente: accesso soggetto a condizioni/limiti.
Gli RSS non concedono una licenza generale di ripubblicazione. Se il testo è insufficiente il candidato viene scartato.
Ampliare la selezione a fonti primarie e feed utilizzabili per coprire le sei aree prima di mirare a 20/giorno.
Ogni feed consente `fetch_pages`; abilitarlo solo per fonti utilizzabili senza autenticazione/paywall.
Il lettore rispetta robots.txt e si ferma se non riesce a leggerlo. Non aggira accessi limitati.

La verifica IA confronta testo e fonti, NON è una verifica indipendente del mondo reale.
Le evidenze sono controllate come citazioni esatte, ma non provano che una fonte dica il vero.
I temi sensibili vengono rinviati a revisione; il filtro non può identificare ogni rischio.
Non sono ancora implementati: analytics/ricavi automatici, learning engine, test A/B titoli,
ricerca foto generalista di luoghi/prodotti e press kit, aggiornamento autonomo delle notizie o ricerca evergreen autonoma.
La dashboard mostra stato editoriale, non inventa statistiche. Usare AlterVista/AdSense per i risultati.

## Installazione: NUOVO repository consigliato

1. Creare il nuovo sito WordPress e scegliere nome/URL. Non usare l'URL di AI Vision.
2. Caricare la cartella di questo pacchetto in un nuovo repository (i file `.github` sono inclusi).
   Non sovrascrivere il repository originale: i suoi vecchi workflow continuerebbero a funzionare.
3. Installare `wordpress/editorial-bridge.zip` come plugin e attivarlo.
4. Configurare questi **Secrets** GitHub, mai nel codice:
   - `EDITORIAL_GEMINI_API_KEY`: chiave di un progetto gratuito senza billing.
   - `EDITORIAL_WP_USER`: utente WordPress con capacità di modificare/pubblicare articoli.
   - `EDITORIAL_WP_PASSWORD`: Application Password WordPress.
5. Configurare queste **Variables**:
   - `EDITORIAL_WP_URL`: URL HTTPS del nuovo sito, senza `/wp-json`.
   - `EDITORIAL_FREE_TIER_CONFIRMED`: `true` SOLO dopo controllo del piano Google.
   - `EDITORIAL_ENABLED`: `true` per consentire l'esecuzione del workflow.
6. Prima di impostare `EDITORIAL_ENABLED`, disabilitare temporaneamente il workflow programmato in GitHub
   oppure rimuovere `schedule` dal file; eseguire manualmente con `publish=false` per il primo controllo.
   Questo usa l'IA gratuita ma NON invia post/immagini al sito.
7. Esaminare il report scaricabile dagli artifact. Poi eseguire con `publish=true` per il collaudo WordPress.
8. Ripristinare `schedule` solo dopo esito positivo. Il cron è in UTC: 04:15, 08:15, 12:15, 16:15;
   in Italia varia con l'ora legale. Gli slot di pubblicazione rimangono in Europe/Rome.

Per rendere più semplice e sicuro il primo avvio, la versione distribuita richiede anche
`EDITORIAL_SCHEDULE_ENABLED=true` per le sole esecuzioni pianificate. Lasciarla assente durante i test.

Il piano gratuito GitHub offre runner standard gratis sui repository pubblici; per repository privati
controllare minuti e spazio disponibili a livello account. Questo pacchetto non crea abbonamenti.
Il branch di stato contiene materiale editoriale e fonti: in un repository pubblico è pubblico anch'esso.
Non includere dati riservati; archiviazione privata richiede verifica delle quote GitHub.
Stato con commit dopo il ciclo: uno spegnimento brusco del runner può perdere gli ultimi contatori;
lo slug stabile protegge i post duplicati, non garantisce una transazione distribuita con WordPress.
Se il salvataggio del branch fallisce, risolvere prima di riavviare.

WordPress deve eseguire regolarmente WP-Cron: GitHub pianifica, ma la pubblicazione effettiva degli
articoli futuri dipende dal cron del sito. Verificare due slot reali su AlterVista.
Se presenti altri plugin SEO o meta generati dal tema, controllare duplicazioni/mapping prima del lancio.

## Verifica locale senza chiavi né rete

```bash
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
python scripts/pipeline.py --offline
```

La fixture è fittizia, chiaramente etichettata e usa `example.org`.
`--offline --publish` è vietato. Lo stato demo è separato in `state-demo/`.
Gli output demo non vanno importati in WordPress.

## Regole editoriali adottate

Titoli ad alta curiosità, specifici e sostenuti dal testo; apertura che dà informazioni.
Gossip: fatti pubblici documentati, nessuna invenzione su salute, relazioni o litigi.
Articoli leggibili, 250–650 parole indicative, nessuna espansione con fatti inventati.
Nessuna attribuzione fittizia a una redazione umana o prova non effettuata.
Le foto sono dichiarate di archivio; le grafiche sono illustrative e mai presentate come fotografie di un evento.
