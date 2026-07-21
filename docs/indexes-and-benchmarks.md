# Indici MongoDB e benchmark

## Obiettivo

Confrontare query rappresentative di ScentBase prima e dopo la creazione degli indici gestiti. Le misurazioni sono eseguite direttamente tramite PyMongo.

## Ambiente

- Data UTC: `2026-07-20T23:40:19.402030+00:00`
- Database: `scentbase`
- MongoDB: `7.0.37`
- Python: `3.10.20`
- Piattaforma: `Windows-10-10.0.26200-SP0`
- Profumi: **24063**
- Warm-up: **3**
- Esecuzioni misurate: **20**

## Indici gestiti

| Nome | Chiavi | Unique | Filtro parziale |
|---|---|---:|---|
| `uq_perfumes_source_url` | `source_url ASC` | Sì | `{"source_url": {"$type": "string"}}` |
| `idx_perfumes_brand_rating` | `brand_id ASC`, `rating DESC`, `_id ASC` | No | — |
| `idx_perfumes_gender_rating_votes` | `gender ASC`, `rating DESC`, `votes DESC`, `_id ASC` | No | — |
| `idx_perfumes_rating_votes` | `rating DESC`, `votes DESC`, `_id ASC` | No | — |
| `idx_perfumes_all_note_ids` | `all_note_ids ASC`, `_id ASC` | No | — |
| `idx_perfumes_accord_ids` | `accord_ids ASC`, `_id ASC` | No | — |

## Metodologia

Per ogni scenario vengono eseguite iterazioni di warm-up e successivamente le misurazioni con `perf_counter`. Lo script verifica che gli identificativi restituiti siano identici nelle due configurazioni e raccoglie `executionStats` tramite `explain`.

## Risultati

| Scenario | Configurazione | Media ms | Mediana ms | Docs esaminati | Keys esaminate | nReturned | Piano | Indici |
|---|---|---:|---:|---:|---:|---:|---|---|
| Ricerca per nota olfattiva | Senza indici gestiti | 4.827 | 3.364 | 63 | 63 | 20 | LIMIT, FETCH, IXSCAN | _id_ |
| Ricerca per nota olfattiva | Con indici gestiti | 3.147 | 2.847 | 20 | 20 | 20 | LIMIT, FETCH, IXSCAN | idx_perfumes_all_note_ids |
| Ricerca per accordo principale | Senza indici gestiti | 5.139 | 3.932 | 32 | 32 | 20 | LIMIT, FETCH, IXSCAN | _id_ |
| Ricerca per accordo principale | Con indici gestiti | 2.956 | 2.768 | 20 | 20 | 20 | LIMIT, FETCH, IXSCAN | idx_perfumes_accord_ids |
| Brand ordinato per rating | Senza indici gestiti | 25.212 | 21.070 | 24063 | 0 | 20 | SORT, COLLSCAN | Nessuno |
| Brand ordinato per rating | Con indici gestiti | 2.727 | 2.696 | 20 | 20 | 20 | LIMIT, FETCH, IXSCAN | idx_perfumes_brand_rating |
| Filtri combinati | Senza indici gestiti | 35.032 | 28.756 | 24063 | 0 | 20 | SORT, COLLSCAN | Nessuno |
| Filtri combinati | Con indici gestiti | 3.046 | 2.990 | 20 | 37 | 20 | LIMIT, FETCH, IXSCAN | idx_perfumes_gender_rating_votes |
| Profumi meglio valutati | Senza indici gestiti | 49.100 | 44.540 | 24063 | 0 | 20 | SORT, COLLSCAN | Nessuno |
| Profumi meglio valutati | Con indici gestiti | 4.746 | 4.687 | 20 | 39 | 20 | LIMIT, FETCH, IXSCAN | idx_perfumes_rating_votes |
| Profumi simili | Senza indici gestiti | 1499.935 | 1523.540 | 24062 | 24063 | 23986 | FETCH, IXSCAN | _id_ |
| Profumi simili | Con indici gestiti | 1540.798 | 1528.598 | 23986 | 159055 | 23986 | FETCH, OR, IXSCAN | idx_perfumes_all_note_ids, idx_perfumes_accord_ids |
| Ricerca esatta per source_url | Senza indici gestiti | 11.263 | 10.641 | 14977 | 0 | 1 | LIMIT, COLLSCAN | Nessuno |
| Ricerca esatta per source_url | Con indici gestiti | 9.201 | 9.347 | 14977 | 0 | 1 | LIMIT, COLLSCAN | Nessuno |

## Confronto

| Scenario | Risultati equivalenti | Riduzione media tempo | Riduzione mediana tempo | Riduzione docs esaminati |
|---|---:|---:|---:|---:|
| Ricerca per nota olfattiva | Sì | 34.802% | 15.357% | 68.254% |
| Ricerca per accordo principale | Sì | 42.483% | 29.624% | 37.500% |
| Brand ordinato per rating | Sì | 89.184% | 87.203% | 99.917% |
| Filtri combinati | Sì | 91.305% | 89.601% | 99.917% |
| Profumi meglio valutati | Sì | 90.334% | 89.477% | 99.917% |
| Profumi simili | Sì | -2.724% | -0.332% | 0.316% |
| Ricerca esatta per source_url | Sì | 18.309% | 12.163% | 0.000% |

## Osservazioni automatiche

- **Ricerca per nota olfattiva**: MongoDB ha usato `idx_perfumes_all_note_ids`; il tempo medio è ridotto del 34.802%; i documenti esaminati sono ridotti del 68.254%.
- **Ricerca per accordo principale**: MongoDB ha usato `idx_perfumes_accord_ids`; il tempo medio è ridotto del 42.483%; i documenti esaminati sono ridotti del 37.500%.
- **Brand ordinato per rating**: MongoDB ha usato `idx_perfumes_brand_rating`; il tempo medio è ridotto del 89.184%; i documenti esaminati sono ridotti del 99.917%.
- **Filtri combinati**: MongoDB ha usato `idx_perfumes_gender_rating_votes`; il tempo medio è ridotto del 91.305%; i documenti esaminati sono ridotti del 99.917%.
- **Profumi meglio valutati**: MongoDB ha usato `idx_perfumes_rating_votes`; il tempo medio è ridotto del 90.334%; i documenti esaminati sono ridotti del 99.917%.
- **Profumi simili**: MongoDB ha usato `idx_perfumes_all_note_ids`, `idx_perfumes_accord_ids`; il tempo medio è aumentato del 2.724%; i documenti esaminati sono ridotti del 0.316%.
- **Ricerca esatta per source_url**: Il piano vincente non mostra un indice gestito; il tempo medio è ridotto del 18.309%; i documenti esaminati sono ridotti del 0.000%.

## Interpretazione dei risultati

### Ricerca per nota olfattiva

Con gli indici gestiti MongoDB utilizza `idx_perfumes_all_note_ids`.

I documenti esaminati passano da 63 a 20 e le chiavi esaminate da 63 a 20. Il tempo medio si riduce da 4.827 ms a 3.147 ms, con un miglioramento del 34.802%.

L'indice è quindi utile sia dal punto di vista del piano di esecuzione sia dal punto di vista temporale. Poiché `all_note_ids` è un array, MongoDB crea automaticamente un indice multikey, indicizzando separatamente ogni nota contenuta nel documento.

### Ricerca per accordo principale

MongoDB utilizza correttamente `idx_perfumes_accord_ids`.

I documenti esaminati passano da 32 a 20 e le chiavi esaminate da 32 a 20. Il tempo medio si riduce da 5.139 ms a 2.956 ms, con un miglioramento del 42.483%.

Questo benchmark dimostra che l'indice sugli accordi è utile quando viene valutato isolatamente su una normale query di filtro del catalogo. Come per le note, `accord_ids` è un array e l'indice viene quindi gestito come multikey.

Il risultato conferma che l'indice deve essere mantenuto.

### Brand ordinato per rating

`idx_perfumes_brand_rating` produce uno dei risultati più significativi.

Senza l'indice MongoDB deve esaminare tutti i 24.063 profumi, filtrare quelli del brand richiesto e ordinarli per rating. Con l'indice vengono esaminati soltanto 20 documenti e 20 chiavi.

Il tempo medio passa da 25.212 ms a 2.727 ms, con un miglioramento dell'89.184%.

L'ordine dei campi è adatto alla query:

- `brand_id ASC` permette di raggiungere direttamente i profumi del brand;
- `rating DESC` supporta l'ordinamento dal rating più alto;
- `_id ASC` rende stabile l'ordine in caso di parità.

Questo indice deve essere mantenuto.

### Filtri combinati

`idx_perfumes_gender_rating_votes` riduce i documenti esaminati da 24.063 a 20 e utilizza 37 chiavi per restituire 20 risultati.

Il tempo medio passa da 35.032 ms a 3.046 ms, con un miglioramento del 91.305%.

L'indice è efficace perché il primo campo, `gender`, viene usato come filtro di uguaglianza. I campi successivi, `rating` e `votes`, permettono al query planner di restringere e ordinare i risultati senza eseguire una scansione completa della collection.

Questo indice deve essere mantenuto.

### Profumi meglio valutati

`idx_perfumes_rating_votes` riduce i documenti esaminati da 24.063 a 20 e utilizza 39 chiavi.

Il tempo medio passa da 49.100 ms a 4.746 ms, con un miglioramento del 90.334%.

L'indice evita sia la scansione completa sia l'ordinamento in memoria dell'intera collection. Il costo residuo dipende anche dalle operazioni successive della pipeline, incluso il `$lookup` del brand.

Questo indice deve essere mantenuto.

### Profumi simili

La ricerca di profumi simili è lo scenario più costoso.

Il profumo sorgente selezionato condivide almeno una nota o un accordo con 23.986 profumi su 24.063. La condizione iniziale è quindi molto poco selettiva.

Con gli indici MongoDB utilizza un piano `OR` basato su:

- `idx_perfumes_all_note_ids`;
- `idx_perfumes_accord_ids`.

I documenti esaminati diminuiscono soltanto dello 0.316%, mentre le chiavi esaminate salgono a 159.055. Questo accade perché gli indici multikey generano più chiavi per documento e uno stesso profumo può essere individuato sia tramite le note sia tramite gli accordi.

Il tempo medio aumenta da 1499.935 ms a 1540.798 ms. In questo caso il costo di attraversamento e deduplicazione delle chiavi supera il piccolo beneficio ottenuto dalla riduzione dei documenti esaminati.

Questo risultato non rende inutili i due indici: i benchmark isolati per nota e accordo mostrano che sono efficaci nei normali filtri del catalogo. Semplicemente, non migliorano la pipeline di similarità quando quasi tutta la collection viene selezionata come insieme dei candidati.

### Ricerca esatta per `source_url`

L'indice `uq_perfumes_source_url` viene creato correttamente, ma il query planner non lo utilizza nella query benchmarkata. Il piano rimane `COLLSCAN` sia prima sia dopo la creazione degli indici.

I documenti esaminati restano 14.977 e non c'è quindi una riduzione del lavoro svolto dal database. Il tempo medio passa da 11.263 ms a 9.201 ms, ma questo miglioramento non può essere attribuito all'indice, perché il piano di esecuzione non cambia.

La differenza temporale è quindi riconducibile principalmente a cache, carico della macchina e normale variabilità delle misurazioni locali.

L'indice deve comunque essere mantenuto perché svolge soprattutto una funzione di integrità:

- impedisce URL stringa duplicati;
- permette più documenti senza `source_url`;
- permette più documenti con `source_url: null`.

## Valutazione finale degli indici

### Indici con beneficio prestazionale dimostrato

I benchmark giustificano direttamente:

- `idx_perfumes_all_note_ids`;
- `idx_perfumes_accord_ids`;
- `idx_perfumes_brand_rating`;
- `idx_perfumes_gender_rating_votes`;
- `idx_perfumes_rating_votes`.

Tutti questi indici vengono scelti dal query planner negli scenari isolati per cui sono stati progettati.

I vantaggi maggiori riguardano gli indici composti:

- `idx_perfumes_brand_rating`: riduzione media del tempo dell'89.184%;
- `idx_perfumes_gender_rating_votes`: riduzione media del 91.305%;
- `idx_perfumes_rating_votes`: riduzione media del 90.334%.

Gli indici multikey su note e accordi producono miglioramenti più contenuti ma comunque misurabili:

- `idx_perfumes_all_note_ids`: riduzione media del 34.802%;
- `idx_perfumes_accord_ids`: riduzione media del 42.483%.

### Indice con funzione principale di integrità

`uq_perfumes_source_url` non viene utilizzato dal piano della query benchmarkata. La sua presenza è comunque giustificata dal vincolo di unicità parziale che applica a livello di database.

## Considerazioni sul costo degli indici

Gli indici migliorano le letture, ma introducono anche costi:

- occupano spazio aggiuntivo;
- devono essere aggiornati durante inserimenti, modifiche ed eliminazioni;
- gli indici multikey possono generare più chiavi per ogni documento;
- un numero eccessivo di indici aumenta il costo delle scritture e la complessità del query planner.

Per questo motivo gli indici sono stati scelti in base alle query realmente implementate in ScentBase e non sono stati aggiunti indiscriminatamente a tutti i campi.

Non è stato aggiunto un normale indice su `name`, perché la ricerca attuale utilizza espressioni regolari parziali e case-insensitive. Un indice B-tree tradizionale non garantirebbe un vantaggio per ricerche che possono trovare una sottostringa in qualunque posizione.

## Verifica funzionale

La gestione degli indici è stata verificata manualmente:

- database completo con 24.063 profumi;
- creazione dei sei indici gestiti;
- creazione ripetuta senza errori;
- elenco delle chiavi e delle opzioni;
- rimozione dei soli indici gestiti;
- conservazione dell'indice `_id_`;
- ricreazione finale degli indici.

Sono stati inoltre eseguiti otto test automatici dedicati agli indici:

- creazione degli indici attesi;
- idempotenza;
- serializzazione stabile dell'elenco;
- conservazione di `_id_` e degli indici non gestiti;
- rifiuto di `source_url` stringa duplicati;
- accettazione dei campi mancanti;
- accettazione dei valori `null`;
- equivalenza logica delle query prima e dopo la creazione degli indici.

Esito della suite dedicata:

```text
8 passed
```

Esito dell'intera suite del progetto:

```text
84 passed in 3.48s
```

Non sono state rilevate regressioni.

## Conclusioni

Il benchmark dimostra che gli indici progettati in base ai filtri e agli ordinamenti reali possono ridurre in modo significativo il lavoro svolto da MongoDB.

I risultati migliori riguardano:

- ricerca per brand ordinata per rating;
- filtri combinati;
- classifica dei profumi meglio valutati.

In questi tre scenari i documenti esaminati passano da 24.063 a 20 e il tempo medio si riduce di circa il 90%.

Anche gli indici multikey su note e accordi risultano giustificati quando vengono valutati isolatamente:

- la ricerca per nota migliora del 34.802%;
- la ricerca per accordo migliora del 42.483%.

La ricerca di similarità mostra invece che un indice non garantisce automaticamente un miglioramento. Quando la query seleziona quasi tutta la collection, il costo di attraversamento e deduplicazione delle numerose chiavi può superare il beneficio ottenuto.

L'indice parziale e univoco su `source_url` viene mantenuto principalmente per garantire l'integrità dei dati. Il benchmark non dimostra un vantaggio prestazionale, perché il query planner non lo utilizza nella query eseguita.

La valutazione finale considera quindi non soltanto i tempi, ma anche:

- selettività della query;
- documenti esaminati;
- chiavi esaminate;
- piano di esecuzione;
- funzione progettuale dell'indice.

La configurazione definitiva mantiene tutti e sei gli indici gestiti.

## Limiti

- Il benchmark è locale e dipende da hardware, cache e carico.
- È stata utilizzata una singola macchina Windows con un'istanza MongoDB locale.
- Le misurazioni non includono rete HTTP, FastAPI o serializzazione JSON.
- La configurazione senza indici rimuove soltanto gli indici gestiti; `_id_` rimane sempre presente.
- Gli indici `_id_` delle collection collegate rimangono disponibili nei `$lookup`.
- Su circa 24.000 documenti differenze temporali piccole possono essere sensibili al rumore; vanno osservati anche piano, documenti e chiavi esaminati.
- Il benchmark utilizza parametri selezionati automaticamente dal dataset.
- I risultati potrebbero cambiare scegliendo note, accordi, brand o soglie con selettività diversa.
- La ricerca di similarità è stata valutata con un profumo che produce 23.986 candidati, quindi rappresenta un caso molto poco selettivo.
- Non sono stati misurati lo spazio occupato dagli indici e il costo aggiuntivo delle operazioni di scrittura.
- La query su `source_url` non forza l'utilizzo dell'indice parziale.
- Le misurazioni riguardano una proof of concept single-node e non valutano replica, sharding o comportamento distribuito.

## Riproduzione

Avviare MongoDB e verificare l'importazione:

```bash
docker compose up -d
python scripts/verify_mongodb_import.py
```

Creare ed elencare gli indici:

```bash
python scripts/manage_indexes.py create
python scripts/manage_indexes.py list
```

Eseguire i test dedicati e l'intera suite:

```bash
python -m pytest tests/test_indexes.py -v
python -m pytest -v
```

Eseguire il benchmark:

```bash
python benchmarks/run_benchmarks.py --warmup 3 --runs 20
```

I dati grezzi sono salvati in:

```text
benchmarks/results/benchmark-results.json
```

Dopo un'importazione eseguita con `--reset`, le collection vengono ricreate e gli indici devono essere nuovamente applicati:

```bash
python scripts/import_to_mongodb.py --reset
python scripts/verify_mongodb_import.py
python scripts/manage_indexes.py create
```
