# ScentBase

Sistema NoSQL per la gestione e l’analisi di profumi, note olfattive, accordi, profumieri e valutazioni.

## Tipologia

Progetto NoSQL classico basato su MongoDB.

## Obiettivo

Il progetto ha l’obiettivo di realizzare una proof of concept per importare, modellare e interrogare un dataset relativo a profumi e fragranze.

Il sistema prevede:

* modellazione dei dati in collection MongoDB;
* pipeline ETL per trasformare il dataset in documenti JSON e importarli in MongoDB;
* operazioni CRUD;
* query di ricerca e aggregazione;
* JOIN tra collection tramite `$lookup`;
* utilizzo di indici;
* interfaccia utente minimale.

## Struttura del progetto

```text
.github/              Template per issue e pull request
backend/              Backend FastAPI
frontend/             Interfaccia utente minimale
benchmarks/results/   Risultati dei benchmark
data/raw/             Dataset sorgente
data/enrichment/      Valori distinti e mapping di arricchimento
data/processed/       Documenti JSON generati dalla trasformazione
db/schema/            Schemi preliminari delle collection MongoDB
docs/modeling.md      Scelte di modellazione documentale
docs/etl.md           Pipeline di estrazione, trasformazione e caricamento
queries/              Query MongoDB e aggregation pipeline
scripts/              Script di estrazione, trasformazione, importazione e verifica
tests/                Test automatici di integrazione del backend
pytest.ini            Configurazione di pytest
```

## Prerequisiti

Per eseguire il progetto in locale sono necessari:

* Python 3.11 o versione compatibile;
* Docker e Docker Compose;
* un ambiente Python locale, ad esempio Conda;
* le dipendenze indicate in `requirements.txt`.

Se si usa Conda, attivare prima l’ambiente dedicato:

```bash
conda activate bd2-scentbase
```

Installare poi le dipendenze Python:

```bash
pip install -r requirements.txt
```

## Modellazione dati

La modellazione documentale è descritta nel file:

```text
docs/modeling.md
```

Il modello prevede cinque collection principali:

```text
perfumes
brands
notes
accords
perfumers
```

La collection centrale è `perfumes`, che contiene i riferimenti verso le altre collection tramite identificativi condivisi.

Gli schemi preliminari delle collection sono disponibili nella cartella:

```text
db/schema/
```

Gli schemi descrivono la struttura dei documenti MongoDB e sono usati come riferimento per trasformazione, importazione, query e sviluppo dell’applicazione.

## Dataset

Il dataset principale previsto per il progetto è:

```text
data/raw/fra_cleaned.csv
```

Il file contiene dati relativi a profumi, brand, paese del brand, genere, rating, numero di valutazioni, anno, note olfattive, profumieri e accordi principali.

## Pipeline ETL

La pipeline di estrazione, arricchimento, trasformazione e caricamento è descritta nel file:

```text
docs/etl.md
```

Gli script principali sono:

```text
scripts/extract_distinct_values.py
scripts/transform_dataset.py
scripts/import_to_mongodb.py
scripts/verify_mongodb_import.py
```

Il primo script estrae note, accordi e profumieri distinti dal dataset e salva i risultati in:

```text
data/enrichment/
```

Il secondo script valida i mapping di arricchimento, applica il mapping canonico, controlla gli identificativi generati e produce i documenti JSON finali in:

```text
data/processed/
```

Il terzo script importa in MongoDB i documenti JSON generati.

Il quarto script verifica che l’importazione in MongoDB sia coerente, controllando conteggi, identificativi e riferimenti tra collection.

File JSON generati dalla trasformazione:

```text
data/processed/perfumes.json
data/processed/brands.json
data/processed/notes.json
data/processed/accords.json
data/processed/perfumers.json
```

## Esecuzione della pipeline ETL

Dopo aver predisposto il dataset in `data/raw/fra_cleaned.csv`, eseguire l’estrazione dei valori distinti:

```bash
python scripts/extract_distinct_values.py
```

Poi eseguire la trasformazione:

```bash
python scripts/transform_dataset.py
```

La trasformazione verifica, tra le altre cose:

* corrispondenza tra valori distinti del dataset e mapping di arricchimento;
* assenza di chiavi mancanti, chiavi extra e valori non validi nei mapping;
* collisioni di `_id` dopo la normalizzazione tecnica;
* unicità degli `_id` finali;
* presenza e unicità di `source_url` per i profumi importati dal dataset;
* validità dei riferimenti verso le collection collegate.

## Avvio MongoDB con Docker

Il progetto utilizza Docker per avviare MongoDB in locale.

Creare un file `.env` a partire dal file di esempio:

```bash
cp .env.example .env
```

Su PowerShell, in alternativa:

```powershell
Copy-Item .env.example .env
```

Avviare MongoDB:

```bash
docker compose up -d
```

Verificare lo stato del container:

```bash
docker compose ps
```

Visualizzare i log del servizio MongoDB:

```bash
docker compose logs mongodb
```

Fermare MongoDB:

```bash
docker compose down
```

Fermare MongoDB rimuovendo anche il volume dati:

```bash
docker compose down -v
```

## Importazione dati in MongoDB

Dopo aver generato i file JSON in `data/processed/`, importare i dati in MongoDB con:

```bash
python scripts/import_to_mongodb.py --reset
```

L’opzione `--reset` elimina le collection target prima dell’importazione, permettendo di rigenerare il database locale da zero.

L’ordine di importazione è:

```text
brands
notes
accords
perfumers
perfumes
```

La collection `perfumes` viene importata per ultima perché contiene riferimenti verso le altre collection.

## Verifica importazione MongoDB

Dopo l’importazione, verificare il caricamento con:

```bash
python scripts/verify_mongodb_import.py
```

La verifica controlla:

* conteggio dei documenti importati per collection;
* unicità degli `_id`;
* presenza e unicità di `source_url` in `perfumes`;
* validità degli array di riferimenti nei documenti `perfumes`;
* validità dei riferimenti verso `brands`, `notes`, `accords` e `perfumers`.

Conteggi attesi dopo l’importazione del dataset completo:

```text
perfumes: 24063
brands: 1060
notes: 1668
accords: 84
perfumers: 905
```

L’ultima verifica eseguita ha prodotto:

```text
Duplicate _id values: 0
Duplicate source_url values: 0
Invalid perfume array fields: 0
Invalid brand references: 0
Invalid note references: 0
Invalid accord references: 0
Invalid perfumer references: 0
Total errors: 0
```

## Backend FastAPI

Il progetto include un backend sviluppato con FastAPI per consultare e modificare i dati presenti in MongoDB.

Prima di avviare il backend, assicurarsi che MongoDB sia in esecuzione e che i dati siano stati importati.

Avviare MongoDB:

```bash
docker compose up -d
```

Installare le dipendenze Python:

```bash
pip install -r requirements.txt
```

Verificare che i dati siano presenti in MongoDB:

```bash
python scripts/verify_mongodb_import.py
```

Avviare il backend FastAPI:

```bash
uvicorn backend.app.main:app --reload
```

La documentazione interattiva Swagger è disponibile all’indirizzo:

```text
http://127.0.0.1:8000/docs
```

### Endpoint disponibili

| Metodo | Endpoint | Descrizione |
| --- | --- | --- |
| GET | `/` | Restituisce un messaggio base dell’API |
| GET | `/health` | Verifica lo stato del backend e la connessione a MongoDB |
| GET | `/collections/counts` | Restituisce i conteggi delle collection principali |
| GET | `/perfumes` | Ricerca e filtra i profumi con ordinamento e paginazione |
| POST | `/perfumes` | Crea un nuovo profumo |
| GET | `/perfumes/{perfume_id}` | Restituisce un profumo tramite `_id` |
| PUT | `/perfumes/{perfume_id}` | Sostituisce i campi modificabili di un profumo esistente |
| DELETE | `/perfumes/{perfume_id}` | Elimina un profumo esistente |

### Ricerca e filtri sui profumi

L’endpoint `GET /perfumes` supporta filtri singoli e combinati. Tutti i criteri specificati nella stessa richiesta vengono applicati con logica `AND`.

Parametri disponibili:

| Parametro | Tipo | Descrizione |
| --- | --- | --- |
| `name` | stringa | Ricerca parziale e case-insensitive per nome del profumo |
| `brand` | stringa | Filtro per nome del brand |
| `gender` | `men`, `women`, `unisex` | Filtro per genere |
| `year_min` | intero | Anno minimo, incluso |
| `year_max` | intero | Anno massimo, incluso |
| `rating_min` | numero | Rating minimo, compreso tra `0` e `5` |
| `rating_max` | numero | Rating massimo, compreso tra `0` e `5` |
| `votes_min` | intero | Numero minimo di voti |
| `note` | stringa | Filtro per nome di nota olfattiva |
| `accord` | stringa | Filtro per nome di accordo |
| `perfumer` | stringa | Filtro per nome del profumiere |
| `sort_by` | `name`, `year`, `rating`, `votes` | Campo usato per l’ordinamento |
| `sort_order` | `asc`, `desc` | Direzione dell’ordinamento |
| `limit` | intero | Numero massimo di risultati, da `1` a `100` |
| `skip` | intero | Numero di risultati da saltare |

I filtri per brand, note, accordi e profumieri risolvono i nomi nelle rispettive collection e applicano poi gli identificativi ottenuti ai documenti `perfumes`.

Esempi:

```bash
curl "http://127.0.0.1:8000/perfumes?name=vanilla"
```

```bash
curl "http://127.0.0.1:8000/perfumes?brand=Dior&gender=unisex"
```

```bash
curl "http://127.0.0.1:8000/perfumes?note=Vanilla&rating_min=4&votes_min=100"
```

```bash
curl "http://127.0.0.1:8000/perfumes?accord=woody&year_min=2000&year_max=2020&sort_by=rating&sort_order=desc&limit=20&skip=0"
```

La risposta mantiene la struttura paginata:

```json
{
  "items": [],
  "limit": 20,
  "skip": 0,
  "total": 0
}
```

Il campo `total` rappresenta il numero complessivo di documenti che soddisfano i filtri prima dell’applicazione di `limit` e `skip`.

Gli intervalli incoerenti, come `year_min` maggiore di `year_max`, restituiscono `400 Bad Request`. I valori non ammessi o fuori intervallo restituiscono `422`.

La ricerca di un brand, una nota, un accordo o un profumiere non presente restituisce una lista vuota con stato `200 OK`.

Gli endpoint restituiscono per ora i riferimenti verso le collection collegate come identificativi, ad esempio `brand_id`, `all_note_ids`, `accord_ids` e `perfumer_ids`.

L’espansione dei dati collegati tramite `$lookup` sarà implementata in una issue successiva dedicata alle query multi-collection.

### Operazioni CRUD sui profumi

I payload ricevuti dagli endpoint `POST` e `PUT` vengono validati tramite modelli Pydantic.

Per i profumi creati tramite API:

* `_id` viene generato automaticamente dal backend con prefisso `manual_perfume_`;
* `all_note_ids` viene calcolato automaticamente unendo `top_note_ids`, `middle_note_ids` e `base_note_ids`;
* i riferimenti verso `brands`, `notes`, `accords` e `perfumers` devono puntare a documenti già esistenti;
* gli identificativi duplicati negli array vengono rimossi mantenendo l’ordine;
* `source_url` è opzionale, ma quando presente deve essere un URL valido e univoco;
* `_id`, `all_note_ids` e i campi non previsti non possono essere impostati direttamente dal client.

Per i profumi importati tramite ETL, `source_url` resta obbligatorio e non può essere rimosso o modificato tramite `PUT`, perché identifica la sorgente originale del record.

L’endpoint `PUT` richiede il payload completo dei campi modificabili e non crea automaticamente un nuovo documento quando il profumo non esiste.

L’eliminazione di un profumo non elimina brand, note, accordi o profumieri collegati, poiché tali documenti possono essere condivisi da più profumi.

Esempio di payload valido:

```json
{
  "name": "ScentBase CRUD Test",
  "brand_id": "brand_example",
  "gender": "unisex",
  "rating": 4.2,
  "votes": 10,
  "year": 2026,
  "top_note_ids": ["note_example"],
  "middle_note_ids": [],
  "base_note_ids": [],
  "accord_ids": ["accord_example"],
  "perfumer_ids": [],
  "source_url": "https://example.com/scentbase-crud-test"
}
```

Gli identificativi dell’esempio devono essere sostituiti con valori realmente presenti nelle rispettive collection.

Principali codici di risposta:

| Codice | Significato |
| --- | --- |
| `200` | Profumo letto o modificato correttamente |
| `201` | Profumo creato correttamente |
| `204` | Profumo eliminato correttamente |
| `400` | Riferimenti inesistenti, intervalli incoerenti o dati non modificabili |
| `404` | Profumo non trovato |
| `409` | Conflitto di unicità, ad esempio `source_url` duplicato |
| `422` | Payload o parametro della query non valido |

### Test automatici di integrazione

Il backend dispone di test automatici eseguiti con `pytest` e `TestClient`.

I test utilizzano un database MongoDB separato:

```text
scentbase_test
```

La configurazione dei test:

* seleziona `scentbase_test` prima di importare l’applicazione FastAPI;
* verifica che il nome del database termini con `_test`;
* elimina un eventuale database di test precedente;
* popola automaticamente le collection `brands`, `notes`, `accords`, `perfumers` e `perfumes` con dati sintetici;
* esegue i test senza leggere o modificare il database principale `scentbase`;
* elimina `scentbase_test` al termine della suite.

Prima di eseguire i test, assicurarsi che MongoDB sia attivo:

```bash
docker compose up -d
```

Nel file `.env` devono essere presenti:

```dotenv
MONGO_DATABASE=scentbase
MONGO_TEST_DATABASE=scentbase_test
```

`MONGO_DATABASE` deve rimanere impostata su `scentbase`: la suite seleziona autonomamente il database di test.

Eseguire tutti i test dalla root del repository:

```bash
python -m pytest -v
```

La suite verifica:

* filtri singoli e combinati;
* ricerca parziale e case-insensitive;
* trattamento sicuro dei caratteri usati nelle espressioni regolari;
* ordinamento crescente e decrescente;
* paginazione e calcolo di `total`;
* riferimenti non presenti nelle collection collegate;
* intervalli incoerenti e parametri non validi;
* regressione minima degli endpoint di lettura e health check.

I file principali sono:

```text
pytest.ini
tests/conftest.py
tests/test_perfume_filters.py
```

### Verifica manuale degli endpoint

Gli endpoint possono essere verificati tramite Swagger UI oppure con `curl`.

Dopo la suite automatica è sufficiente eseguire uno smoke test rappresentativo sul database completo:

```bash
curl "http://127.0.0.1:8000/perfumes?note=Vanilla&rating_min=4&sort_by=rating&sort_order=desc&limit=5"
```

Su PowerShell è preferibile usare:

```powershell
curl.exe "http://127.0.0.1:8000/perfumes?note=Vanilla&rating_min=4&sort_by=rating&sort_order=desc&limit=5"
```

Esempi aggiuntivi di lettura:

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/collections/counts
curl "http://127.0.0.1:8000/perfumes?limit=5&skip=0"
curl "http://127.0.0.1:8000/perfumes/<ID_REALE>"
curl "http://127.0.0.1:8000/perfumes/not_existing_perfume"
```

Per verificare la CRUD completa:

1. creare un profumo sintetico con `POST /perfumes`, usando riferimenti reali;
2. recuperarlo con `GET /perfumes/{perfume_id}`;
3. modificarlo con `PUT /perfumes/{perfume_id}`;
4. eliminarlo con `DELETE /perfumes/{perfume_id}`;
5. verificare che una successiva lettura restituisca `404 Not Found`.

Sono stati verificati anche i principali casi negativi: riferimento inesistente, genere o rating non valido, campo non previsto, profumo inesistente e `source_url` duplicato.

Lo script `verify_mongodb_import.py` controlla i conteggi esatti del dataset ETL. Dopo i test CRUD è quindi necessario eliminare tutti i documenti sintetici prima di rieseguirlo.

## Esecuzione completa da zero

Per rigenerare i dati, caricarli in MongoDB e avviare il backend da zero:

```bash
docker compose up -d
pip install -r requirements.txt
python scripts/extract_distinct_values.py
python scripts/transform_dataset.py
python scripts/import_to_mongodb.py --reset
python scripts/verify_mongodb_import.py
python -m pytest -v
uvicorn backend.app.main:app --reload
```

## File di configurazione

Il file `.env.example` contiene variabili di ambiente di esempio.

Il file `.env` viene usato solo in locale e non deve essere caricato nel repository.

Variabili principali:

```text
MONGO_PORT
MONGO_INITDB_ROOT_USERNAME
MONGO_INITDB_ROOT_PASSWORD
MONGO_INITDB_DATABASE
MONGO_DATABASE
MONGO_TEST_DATABASE
MONGO_URI
```

## Stato del progetto

Setup iniziale del repository completato.

MongoDB è avviabile localmente tramite Docker.

La modellazione documentale è stata definita in `docs/modeling.md`, con le collection principali, i collegamenti tramite riferimenti, la gestione degli identificativi, i campi di arricchimento e le scelte di modellazione.

La pipeline ETL è stata implementata con script per estrazione dei valori distinti, validazione dei mapping di arricchimento, controllo delle collisioni e generazione dei file JSON in `data/processed/`.

La fase di caricamento in MongoDB è stata implementata tramite script di importazione e verifica. I dati trasformati possono essere importati nel database locale e controllati tramite conteggi, unicità degli identificativi e validità dei riferimenti tra collection.

Il backend FastAPI è stato implementato e collegato al database MongoDB. L’applicazione espone endpoint per verificare lo stato della connessione, consultare i conteggi delle collection e leggere i profumi importati tramite API.

Le operazioni CRUD principali sulla collection `perfumes` sono state completate. Il backend consente la creazione, la modifica e l’eliminazione dei profumi, applicando validazione Pydantic, controllo dei riferimenti verso le collection collegate, generazione automatica di `_id` e `all_note_ids`, controllo di unicità di `source_url` e gestione degli errori HTTP principali.

La ricerca del catalogo supporta filtri singoli e combinati per nome, brand, genere, anno, rating, voti, note, accordi e profumieri, oltre a ordinamento e paginazione. La funzionalità è verificata tramite test automatici di integrazione eseguiti su un database MongoDB separato denominato `scentbase_test`.

Le prossime attività riguarderanno le query di aggregazione, la JOIN tramite `$lookup`, la ricerca di profumi simili, gli indici, i benchmark e lo sviluppo dell’interfaccia utente.
