# Verifica della versione 0.1 — 1 ottobre 2026

## Superato
- 12 test unitari: quote persistenti, 429 senza retry/fallback, calendario quattro cicli,
  massimo giornaliero, cambio ora, URL, evidenze, temi sensibili, revisione,
  post futuri già presenti, copertine, conferma piano gratuito.
- Sintassi Python e lettura strutturale del workflow YAML.
- Pipeline offline con fixture fittizia, output HTML/CSV e copertina PNG.
- Copertina 1200x630 ispezionata visivamente: testo leggibile e non tagliato.
- Lettura reale feed senza API IA: due candidati NASA idonei nella finestra temporale.

## Risultati fonti
- ANSA cultura: HTTP 200, sommari molto brevi (alcuni inferiori a 10 parole).
- Fanpage spettacolo: primo probe HTTP 200, feed con sommari di circa 32–42 parole.
- NASA: HTTP 200, testo nel feed, campioni di 292–821 parole.
- MEDIA INAF: primo probe HTTP 200, campioni di 699–1200 parole.
- Seconda prova di raccolta: timeout INAF e Fanpage; raccolti due candidati NASA.
- Il Post: HTTP 403, non incluso. ANSA Viaggi: HTTP 404, non incluso.
- Non sono state aggirate limitazioni d'accesso o pagine a pagamento.

## Non verificato qui
- Chiamate Gemini reali, quote effettive e qualità editoriale del modello sul nuovo prompt.
- Installazione/esecuzione PHP del plugin: PHP e WordPress non presenti nell'ambiente.
- REST WordPress, persistenza GitHub live, WP-Cron e resa SEO/Open Graph del tema.
- Volume reale di 20 articoli validi al giorno; feed e quote possono limitarlo.
- Analytics e apprendimento: ancora da implementare con dati del nuovo sito.

Nessuna pubblicazione esterna, chiamata Gemini, spesa, modifica del sito AI Vision,
creazione di account o campagna pubblicitaria è stata eseguita.

## Aggiornamento 0.2 — fotografie reali
- Totale 25 test passati, inclusi 12 test del modulo foto e un test di integrazione pubblicazione/crediti.
- Verificati: omonimi, licenze NC, URL licenza incoerenti, restrizioni, immagini sintetiche/dipinti,
  host download, MIME, ripiego in assenza di rete e conservazione dei crediti nel post e nello stato.
- Prova live Wikidata: ReadTimeout. Il percorso completo di una foto reale NON è stato validato
  dal vivo in questo ambiente; i test del modulo usano risposte simulate.
- Nessuna spesa API aggiuntiva: il nome del soggetto viene estratto nella stessa risposta dell'articolo.
