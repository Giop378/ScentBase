# Pipeline ETL ScentBase

## Obiettivo

Questo documento descrive la pipeline ETL usata per trasformare il dataset `fra_cleaned.csv` nei documenti JSON destinati alle collection MongoDB del progetto **ScentBase**.

Il documento non contiene il log completo di ogni esecuzione, ma raccoglie le scelte operative principali, i comandi usati e i risultati sintetici delle verifiche più rilevanti per le fasi di estrazione, trasformazione e caricamento.

---

## Struttura delle cartelle

La pipeline usa la seguente struttura:

```text
data/
  raw/
    fra_cleaned.csv
  enrichment/
    distinct_notes.txt
    distinct_accords.txt
    distinct_perfumers.txt
    note_olfactory_groups.json
    accord_colors.json
    perfumer_nationalities.json
    canonical_names.json
  processed/
    perfumes.json
    brands.json
    notes.json
    accords.json
    perfumers.json

scripts/
  extract_distinct_values.py
  transform_dataset.py
  import_to_mongodb.py
  verify_mongodb_import.py
```

Ruolo delle cartelle:

| Cartella | Ruolo |
| --- | --- |
| `data/raw/` | contiene il CSV sorgente |
| `data/enrichment/` | contiene i mapping di arricchimento e il mapping canonico |
| `data/processed/` | contiene i JSON finali generati dalla trasformazione |
| `scripts/` | contiene gli script Python della pipeline |

---

## Script della pipeline

### `extract_distinct_values.py`

Lo script estrae dal CSV i valori distinti necessari per preparare i mapping di arricchimento.

Valori estratti:

* note olfattive dalle colonne `Top`, `Middle`, `Base`;
* accordi dalle colonne `mainaccord1`-`mainaccord5`;
* profumieri dalle colonne `Perfumer1`, `Perfumer2`.

Output previsti in `data/enrichment/`:

```text
distinct_notes.txt
distinct_accords.txt
distinct_perfumers.txt
```

Questi file servono come base per creare i mapping JSON di arricchimento.

---

### `transform_dataset.py`

Lo script principale legge `fra_cleaned.csv`, valida i mapping di arricchimento e genera i file JSON finali per MongoDB.

Collection generate:

```text
perfumes
brands
notes
accords
perfumers
```

Output previsti in `data/processed/`:

```text
perfumes.json
brands.json
notes.json
accords.json
perfumers.json
```

---

### `import_to_mongodb.py`

Lo script importa in MongoDB i file JSON generati dalla trasformazione.

La connessione al database viene letta dalle variabili definite in `.env`:

```text
MONGO_URI
MONGO_DATABASE
```

L'importazione avviene in ordine controllato:

```text
brands
notes
accords
perfumers
perfumes
```

La collection `perfumes` viene importata per ultima perché contiene riferimenti verso le collection collegate.

Con l'opzione `--reset`, lo script elimina prima le collection target, permettendo di ricostruire il database locale da zero durante test e demo.

---

### `verify_mongodb_import.py`

Lo script verifica che i dati importati in MongoDB siano coerenti con gli output della pipeline ETL.

Controlli effettuati:

* conteggio dei documenti importati per collection;
* unicità degli `_id`;
* presenza e unicità di `source_url` nella collection `perfumes`;
* presenza degli array di riferimenti nei documenti `perfumes`;
* validità dei riferimenti da `perfumes` verso `brands`, `notes`, `accords` e `perfumers`.

Lo script termina con errore se almeno una verifica fallisce.

---

## Comandi principali

Estrarre i valori distinti:

```bash
python scripts/extract_distinct_values.py
```

Eseguire la trasformazione completa:

```bash
python scripts/transform_dataset.py
```

Avviare MongoDB tramite Docker:

```bash
docker compose up -d
```

Importare i JSON trasformati in MongoDB:

```bash
python scripts/import_to_mongodb.py --reset
```

Verificare l'importazione in MongoDB:

```bash
python scripts/verify_mongodb_import.py
```

---

## Mapping di arricchimento

La pipeline usa tre mapping principali generati con supporto AI e controllati manualmente.

| File | Campo generato | Collection |
| --- | --- | --- |
| `note_olfactory_groups.json` | `olfactory_group` | `notes` |
| `accord_colors.json` | `color_hex` | `accords` |
| `perfumer_nationalities.json` | `nationality` | `perfumers` |

I mapping devono contenere tutti e soli i valori distinti presenti nel dataset.

Per evitare valori null nei campi di arricchimento vengono usati valori controllati:

| Caso | Valore usato |
| --- | --- |
| nota non classificabile | `other` |
| accordo senza colore specifico | `#9E9E9E` |
| nazionalità non determinabile | `Unknown` |

---

## Validazione dei mapping

Prima di generare i JSON finali, lo script verifica che i mapping siano coerenti con il dataset.

Controlli effettuati:

* nessun valore distinto del dataset deve mancare nel mapping;
* il mapping non deve contenere chiavi inventate o non presenti nel dataset;
* non devono esserci chiavi vuote o duplicate dopo normalizzazione;
* `olfactory_group` deve appartenere all'insieme dei gruppi ammessi;
* `color_hex` deve rispettare il formato `#RRGGBB`;
* `nationality` non deve essere nulla o vuota.

La trasformazione viene bloccata se una di queste condizioni non è rispettata.

---

## Mapping canonico

Il file:

```text
data/enrichment/canonical_names.json
```

serve per risolvere manualmente varianti di scrittura che generano lo stesso identificativo tecnico.

Esempi di casi gestibili:

```text
ylang ylang -> ylang-ylang
jean charles mignon -> jean-charles mignon
```

Regole applicate:

* il mapping canonico è manuale;
* non vengono applicati accorpamenti automatici per somiglianza tra stringhe;
* le chiavi devono essere valori presenti nel dataset;
* i valori canonici devono essere valori presenti nella stessa collection;
* le collisioni vengono controllate separatamente per `brands`, `notes`, `accords` e `perfumers`;
* non vengono controllate collisioni tra collection diverse, perché gli identificativi hanno prefissi diversi.

---

## Generazione degli identificativi

Gli identificativi delle collection collegate sono generati a partire dal nome normalizzato e dal prefisso della collection.

Esempi:

```text
brand_dior
note_bergamot
accord_warm_spicy
perfumer_alberto_morillas
```

Per i profumi importati dal dataset, l'identificativo viene generato a partire da `source_url`, perché il nome del profumo non è completamente univoco.

Il campo `source_url` viene conservato nel documento `perfumes` come riferimento al record originale del dataset.

---

## Controlli finali sui documenti generati

Prima di scrivere i file JSON finali, lo script verifica:

* unicità degli `_id` finali in ogni collection;
* assenza di documenti senza `_id` valido;
* presenza di `source_url` per ogni profumo importato dal dataset;
* unicità di `source_url` nella collection `perfumes`;
* validità dei campi strutturali dei profumi, in particolare `name`, `brand_id` e `gender`;
* presenza degli array di riferimenti come array, anche quando vuoti;
* assenza di valori vuoti/non validi negli array di riferimenti;
* validità dei riferimenti da `perfumes` verso `brands`, `notes`, `accords` e `perfumers`.

Il controllo su `source_url` riguarda solo i dati importati dal CSV. Per futuri profumi inseriti manualmente tramite CRUD, `source_url` potrà essere opzionale e l'identificativo sarà generato dal backend applicativo.

Gli array di riferimenti non vengono salvati come `null`: se un profumo non ha note di testa, accordi o profumieri noti, il relativo campo viene salvato come array vuoto.

---

## Trasformazioni principali

Durante la trasformazione vengono applicate le seguenti operazioni:

* conversione del rating in numero decimale, oppure `null` se mancante o non valido;
* conversione del numero di voti in intero, oppure `null` se mancante o non valido;
* conversione dell'anno in intero, oppure `null` se mancante o non valido;
* normalizzazione del genere in minuscolo;
* estrazione delle liste di note da `Top`, `Middle`, `Base`;
* creazione di `top_note_ids`, `middle_note_ids`, `base_note_ids`;
* creazione di `all_note_ids` come unione ordinata delle note;
* creazione di `accord_ids` dagli accordi principali;
* creazione di `perfumer_ids` ignorando valori mancanti o `unknown`;
* generazione delle collection collegate senza duplicati.

---

## Output generati

La pipeline produce cinque file JSON, uno per ogni collection MongoDB:

```text
data/processed/perfumes.json
data/processed/brands.json
data/processed/notes.json
data/processed/accords.json
data/processed/perfumers.json
```

I file sono usati nella successiva fase di caricamento in MongoDB.

---

## Ultima esecuzione verificata della fase Extract/Transform

La pipeline è stata eseguita sul dataset completo `data/raw/fra_cleaned.csv` usando encoding `cp1252`.

### Estrazione valori distinti

| Elemento estratto | Valori distinti |
| --- | ---: |
| Note | 1671 |
| Accordi | 84 |
| Profumieri | 909 |

### Validazione dei mapping

| Mapping | Valori attesi | Chiavi mapping | Mancanti | Extra | Valori invalidi | Duplicati normalizzati |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Note | 1671 | 1671 | 0 | 0 | 0 | 0 |
| Accordi | 84 | 84 | 0 | 0 | 0 | 0 |
| Profumieri | 909 | 909 | 0 | 0 | 0 | 0 |

Valori di fallback controllati rilevati nei mapping:

| Campo | Valore di fallback | Occorrenze |
| --- | --- | ---: |
| `notes.olfactory_group` | `other` | 82 |
| `accords.color_hex` | `#9E9E9E` | 0 |
| `perfumers.nationality` | `Unknown` | 379 |

### Mapping canonico e collisioni

| Collection | Valori distinti dataset | Valori canonici | ID generati | Alias manuali | Collisioni non risolte |
| --- | ---: | ---: | ---: | ---: | ---: |
| `brands` | 1060 | 1060 | 1060 | 0 | 0 |
| `notes` | 1671 | 1668 | 1668 | 3 | 0 |
| `accords` | 84 | 84 | 84 | 0 | 0 |
| `perfumers` | 909 | 905 | 905 | 4 | 0 |

### Controlli finali sui documenti generati

| Collection | Documenti | ID univoci | ID duplicati | Documenti senza ID valido |
| --- | ---: | ---: | ---: | ---: |
| `perfumes` | 24063 | 24063 | 0 | 0 |
| `brands` | 1060 | 1060 | 0 | 0 |
| `notes` | 1668 | 1668 | 0 | 0 |
| `accords` | 84 | 84 | 0 | 0 |
| `perfumers` | 905 | 905 | 0 | 0 |

Per la collection `perfumes` è stato verificato anche il campo `source_url`:

| Controllo | Risultato |
| --- | ---: |
| Documenti `perfumes` | 24063 |
| `source_url` univoci | 24063 |
| `source_url` duplicati | 0 |
| Documenti senza `source_url` valido | 0 |

Sono stati inoltre verificati i campi strutturali dei profumi e i riferimenti verso le collection collegate:

| Controllo | Risultato |
| --- | ---: |
| Documenti `perfumes` controllati per campi strutturali | 24063 |
| Documenti `perfumes` con campi strutturali non validi | 0 |
| Documenti `perfumes` controllati per riferimenti | 24063 |
| Riferimenti non validi verso collection collegate | 0 |

### Conteggi finali generati

| Collection | Documenti generati |
| --- | ---: |
| `perfumes` | 24063 |
| `brands` | 1060 |
| `notes` | 1668 |
| `accords` | 84 |
| `perfumers` | 905 |

Il conteggio `Unknown` dei profumieri è pari a 379 nella validazione del mapping sui valori distinti originali e pari a 378 nei documenti finali generati. La differenza dipende dall'applicazione del mapping canonico, che riduce i profumieri distinti da 909 a 905 tramite alias manuali.

I conteggi possono cambiare solo se vengono modificati dataset sorgente, mapping canonico o regole di trasformazione.

---

## Load: importazione in MongoDB

La fase di caricamento importa in MongoDB i file JSON generati in `data/processed/`.

### File di input

```text
data/processed/brands.json
data/processed/notes.json
data/processed/accords.json
data/processed/perfumers.json
data/processed/perfumes.json
```

### Script utilizzati

```text
scripts/import_to_mongodb.py
scripts/verify_mongodb_import.py
```

### Variabili di ambiente usate

```text
MONGO_URI
MONGO_DATABASE
```

### Ordine di importazione

| Ordine | Collection |
| ---: | --- |
| 1 | `brands` |
| 2 | `notes` |
| 3 | `accords` |
| 4 | `perfumers` |
| 5 | `perfumes` |

La collection `perfumes` viene importata per ultima perché contiene riferimenti verso `brands`, `notes`, `accords` e `perfumers`.

### Comandi principali

Avviare MongoDB:

```bash
docker compose up -d
```

Importare i dati trasformati, resettando le collection target:

```bash
python scripts/import_to_mongodb.py --reset
```

Verificare l'importazione:

```bash
python scripts/verify_mongodb_import.py
```

### Controlli post-importazione

Dopo il caricamento vengono verificati:

* conteggio dei documenti importati;
* unicità degli `_id`;
* presenza e unicità di `source_url` in `perfumes`;
* correttezza degli array di riferimenti nei documenti `perfumes`;
* validità dei riferimenti da `perfumes` verso `brands`, `notes`, `accords` e `perfumers`.

### Ultima esecuzione verificata della fase Load

L'importazione è stata eseguita sul database MongoDB locale `scentbase`.

Conteggi importati:

| Collection | Documenti importati |
| --- | ---: |
| `perfumes` | 24063 |
| `brands` | 1060 |
| `notes` | 1668 |
| `accords` | 84 |
| `perfumers` | 905 |

Controlli di verifica:

| Controllo | Risultato |
| --- | ---: |
| `_id` duplicati in `perfumes` | 0 |
| `_id` duplicati in `brands` | 0 |
| `_id` duplicati in `notes` | 0 |
| `_id` duplicati in `accords` | 0 |
| `_id` duplicati in `perfumers` | 0 |
| Documenti senza `_id` valido | 0 |
| `source_url` duplicati in `perfumes` | 0 |
| Documenti `perfumes` senza `source_url` valido | 0 |
| Campi array non validi in `perfumes` | 0 |
| Riferimenti non validi verso `brands` | 0 |
| Riferimenti non validi verso `notes` | 0 |
| Riferimenti non validi verso `accords` | 0 |
| Riferimenti non validi verso `perfumers` | 0 |
| Errori totali rilevati | 0 |

La verifica è stata eseguita tramite `scripts/verify_mongodb_import.py` e si è conclusa con esito positivo.


## Uso dell'AI

L'AI è stata usata come supporto per costruire i mapping di arricchimento:

* classificazione delle note in gruppi olfattivi;
* assegnazione dei colori rappresentativi agli accordi;
* imputazione della nazionalità descrittiva dei profumieri.

I risultati generati con supporto AI non vengono accettati automaticamente: lo script verifica la coerenza dei mapping rispetto ai valori distinti del dataset e blocca la trasformazione in caso di valori mancanti, extra, nulli o non validi.

---

## Relazione con `modeling.md`

`docs/modeling.md` descrive il modello dati e le scelte progettuali stabili.

`docs/etl.md` descrive invece la pipeline con cui il dataset viene trasformato nei documenti coerenti con quel modello e successivamente caricato nel database MongoDB locale.
