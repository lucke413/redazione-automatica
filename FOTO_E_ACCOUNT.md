# Foto reali e account Google — versione 0.2

## Immagini integrate

La pipeline ora tenta di usare una foto reale quando l'articolo riguarda una persona pubblica
identificata con nome completo. `image_subject` viene prodotto insieme al testo: nessuna chiamata Gemini aggiuntiva.
Il nome deve essere presente anche nelle fonti e nell'articolo. La ricerca gratuita Wikidata richiede
un solo risultato esatto e un'entità umana (P31=Q5). La foto deriva dalla proprietà P18, non dalla prima
immagine trovata su un motore di ricerca. In caso di ambiguità si usa una grafica.

Per il file Wikimedia Commons vengono letti licenza, URL licenza, autore, credit line, data, dimensioni,
descrizione e categorie. Sono ammessi solo CC BY / CC BY-SA nelle versioni esplicitamente elencate,
CC0 e pubblico dominio con un link coerente alla dichiarazione. Licenze NC/ND/sconosciute sono escluse.
I file con restrizioni supplementari dichiarate, segnalazioni problematiche o indizi di immagini
sintetiche/dipinti vengono esclusi. Servono indizi testuali di fotografia nei metadati.
Queste euristiche sono conservative, non riconoscimento visivo né garanzia assoluta di identità o diritti.
Metadati errati o incompleti possono esistere anche negli archivi: il controllo automatico non sostituisce
una valutazione editoriale nei casi delicati. Le storie marcate REVISIONE non ricevono una foto automatica.

Il file originale è scaricato senza ritocchi o ritagli, massimo 12 MB e 40 megapixel.
WordPress e il tema possono creare versioni ridimensionate/ritagliate: verificarne la visualizzazione
prima del lancio e mantenere licenza e attribuzione visibili anche per tali versioni.
La didascalia dice esplicitamente FOTO D'ARCHIVIO e non attribuisce lo scatto all'evento narrato.
Autore, provenienza e link licenza sono inseriti sia nel media WordPress sia nel testo dell'articolo,
perché alcuni temi non mostrano la didascalia della foto in evidenza.
Provenienza e metadati vengono salvati nel database e nei report PRIMA dell'upload.

Il sistema non acquista foto, non genera foto IA, non scarica immagini dai social o dalle testate.
Non è ancora inclusa una ricerca generalista di immagini di luoghi/prodotti né una banca di press kit.
Se la persona manca, l'identità è ambigua, la licenza non è ammessa o la rete non risponde,
si usa la copertina grafica originale. Si può disabilitare Commons con `commons_photos: false`.

Non usare mai la sessione WordPress per scaricare foto esterne: il modulo usa richieste separate,
senza credenziali del CMS e con domini consentiti espliciti. Nessuna chiave richiesta da Wikimedia.

## Google: scelta consigliata

Un solo account Google, due progetti distinti:
- Progetto AI Vision: mantiene la propria chiave e configurazione.
- Progetto del nuovo sito: una chiave dedicata, piano gratuito senza fatturazione collegata.

AI Studio gestisce più progetti e ogni chiave appartiene a un progetto.
Una seconda chiave NELLO STESSO progetto non aggiunge quota: i limiti sono per progetto.
La separazione serve a gestire due applicazioni distinte e tracciarne l'uso, non a ruotare chiavi o
progetti quando la quota termina. Non serve creare un altro account Google.

Controllare in AI Studio la quota del modello prima del lancio: per venti articoli il percorso nominale
è quattro ranking + venti scritture + venti audit = 44 chiamate al giorno, oltre a eventuali scarti.
La configurazione limita a 48/giorno e 11/ciclo; gli scarti possono far pubblicare meno articoli.
La capacità effettiva non è garantita dal semplice possesso di una chiave e va collaudata.

Salvare la chiave del nuovo progetto SOLO nel Secret GitHub `EDITORIAL_GEMINI_API_KEY`.
Confermare `EDITORIAL_FREE_TIER_CONFIRMED=true` soltanto dopo la verifica del piano gratuito.
Non inviare la chiave in chat. Nessun account/progetto esterno viene creato da questo pacchetto.

Fonti tecniche consultate il 1 ottobre 2026:
- https://ai.google.dev/gemini-api/docs/rate-limits
- https://ai.google.dev/gemini-api/docs/api-key
- https://www.mediawiki.org/wiki/API:Imageinfo
- https://commons.wikimedia.org/wiki/Commons:Reusing_content_outside_Wikimedia
