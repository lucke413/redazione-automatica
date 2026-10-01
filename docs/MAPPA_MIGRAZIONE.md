# Mappa AI Vision → nuovo progetto

| Esistente | Decisione | Nuova implementazione |
|---|---|---|
| Client REST WordPress | Tenere e correggere | wp_base.py: ricerca anche post futuri/bozze, niente entrypoint legacy |
| Parser articolo HTML | Tenere | source_base.py; estrazione vincolata da lista domini e robots |
| Filtro AI per singola notizia tech | Sostituire | ranking in gruppo, categorie generaliste |
| Selettore 5 al giorno | Sostituire | 5 per ciclo, massimo 20 sul giorno locale |
| Generatore testi/SEO | Adattare | prompt generalista + tre titoli + evidenze + audit |
| Storico negli artifact | Sostituire | SQLite e branch dedicato, slug deterministico |
| Download foto RSS/Open Graph | Eliminare | Wikidata/Commons con controlli licenza + copertina grafica gratuita |
| Telegram | Escludere | nessun invio social automatico, export CSV |
| Workflow recupero SEO vecchi post | Eliminare | bridge nuovo, metadata salvati con il post |
| Dashboard | Aggiungere | pannello WP e report HTML del ciclo |
| Analytics/Learning | Rimandare all'integrazione con dati reali | nessuna metrica simulata |

Nessun framework web separato, database/cloud a pagamento o scheduler aggiuntivo.
Nessun segreto incluso. Nome provvisorio configurabile, nessun nuovo sito creato automaticamente.
