# ScentBase

ScentBase è una proof of concept NoSQL per la consultazione, la gestione e l’analisi di un catalogo di profumi.

Il progetto utilizza MongoDB per modellare profumi, brand, note olfattive, accordi e profumieri; FastAPI espone le funzionalità applicative, mentre un frontend React/Vite permette di esplorare il catalogo, applicare filtri, consultare statistiche ed eseguire le operazioni CRUD sui profumi.

## Funzionalità principali

- modellazione documentale su cinque collection MongoDB;
- pipeline ETL riproducibile dal CSV ai documenti JSON;
- caricamento e verifica automatica del dataset;
- ricerca con filtri combinabili, ordinamento e paginazione;
- JOIN multi-collection tramite `$lookup`;
- creazione, modifica ed eliminazione dei profumi;
- controllo applicativo dei duplicati nelle scritture CRUD manuali;
- ricerca di profumi simili tramite indice di Jaccard su note e accordi;
- aggregazioni statistiche per profumi, brand e note;
- gestione e benchmark degli indici MongoDB;
- interfaccia React responsive con dashboard, catalogo, dettaglio e form CRUD.

## Tecnologie

- **Database:** MongoDB
- **Backend:** Python, FastAPI, PyMongo e Pydantic
- **Frontend:** React, Vite e React Router
- **Ambiente locale:** Docker Compose
- **Test:** pytest ed ESLint

## Struttura del progetto

```text
.github/                              Template per issue e pull request
backend/                              Backend FastAPI
backend/app/duplicate_guard.py        Controllo duplicati per il CRUD manuale
backend/app/indexes.py                Definizione centralizzata degli indici
backend/app/routers/                  Endpoint REST
backend/app/services/                 Aggregazioni, similarità e servizi applicativi
benchmarks/run_benchmarks.py          Benchmark con e senza indici
benchmarks/results/                   Risultati grezzi dei benchmark
data/raw/                             Dataset sorgente
data/enrichment/                      Mapping di arricchimento e valori canonici
data/processed/                       Documenti JSON prodotti dall’ETL
db/schema/                            Schemi delle collection MongoDB
docs/modeling.md                      Scelte di modellazione documentale
docs/etl.md                           Pipeline ETL
docs/queries.md                       JOIN, aggregazioni e similarità
docs/indexes-and-benchmarks.md        Indici e risultati dei benchmark
frontend/                             Applicazione React/Vite
queries/                              Pipeline MongoDB versionate
scripts/                              Script ETL, importazione, verifica e indici
tests/                                Test automatici del backend
```

## Modello dati

Il database contiene cinque collection principali:

```text
perfumes
brands
notes
accords
perfumers
```

`perfumes` è la collection centrale e contiene riferimenti verso le altre collection attraverso identificativi condivisi:

```text
brand_id
 top_note_ids
middle_note_ids
base_note_ids
all_note_ids
accord_ids
perfumer_ids
```

Le entità collegate sono mantenute in collection separate perché brand, note, accordi e profumieri possono essere condivisi da molti profumi e interrogati autonomamente.

La modellazione completa è descritta in [docs/modeling.md](docs/modeling.md).

### Nomi leggibili e identificativi tecnici

I campi `name` conservano il valore leggibile proveniente dal dataset. La normalizzazione tecnica in forma prefissata viene applicata agli identificativi delle collection collegate, ad esempio:

```text
brand_dior
note_white_musk
accord_warm_spicy
perfumer_alberto_morillas
```

Per i profumi importati, `_id` viene generato a partire da `source_url`, perché il nome non è completamente univoco.

Alcuni nomi presenti nel CSV sorgente contengono già trattini, ad esempio `acqua-di-gio-profondo`. Questi valori vengono conservati nel database; l’interfaccia li mostra in forma leggibile e la ricerca considera equivalenti spazi, trattini e underscore.

## Dataset e pipeline ETL

Il dataset principale è:

```text
data/raw/fra_cleaned.csv
```

La pipeline produce:

```text
data/processed/perfumes.json
data/processed/brands.json
data/processed/notes.json
data/processed/accords.json
data/processed/perfumers.json
```

Gli script principali sono:

```text
scripts/extract_distinct_values.py
scripts/transform_dataset.py
scripts/import_to_mongodb.py
scripts/verify_mongodb_import.py
```

La pipeline completa è documentata in [docs/etl.md](docs/etl.md).

### Conteggi attesi

Dopo l’importazione del dataset completo:

```text
perfumes: 24063
brands: 1060
notes: 1668
accords: 84
perfumers: 905
```

La verifica deve terminare con zero duplicati, riferimenti non validi o errori complessivi.

## Prerequisiti

Per eseguire il progetto in locale sono necessari:

- Python 3.10 o una versione compatibile;
- Docker e Docker Compose;
- Node.js e npm;
- le dipendenze Python elencate in `requirements.txt`.

Con Conda è possibile attivare l’ambiente dedicato:

```bash
conda activate bd2-scentbase
```

Installare le dipendenze Python dalla root del repository:

```bash
pip install -r requirements.txt
```

## Configurazione

### Variabili del progetto

Creare il file `.env` a partire dall’esempio:

```bash
cp .env.example .env
```

Su PowerShell:

```powershell
Copy-Item .env.example .env
```

Variabili principali:

```text
MONGO_PORT
MONGO_INITDB_ROOT_USERNAME
MONGO_INITDB_ROOT_PASSWORD
MONGO_INITDB_DATABASE
MONGO_DATABASE
MONGO_TEST_DATABASE
MONGO_URI
CORS_ALLOWED_ORIGINS
```

`CORS_ALLOWED_ORIGINS` contiene gli origin autorizzati a chiamare il backend. La configurazione locale predefinita consente:

```text
http://localhost:5173
http://127.0.0.1:5173
```

### Variabile del frontend

Dalla cartella `frontend/`, creare il file locale:

```bash
cp .env.example .env
```

Su PowerShell:

```powershell
Copy-Item .env.example .env
```

La variabile disponibile è:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Se `VITE_API_BASE_URL` non viene specificata, il frontend usa automaticamente `http://127.0.0.1:8000`.

I file `.env` sono locali e non devono essere versionati.

## Avvio di MongoDB

Avviare MongoDB:

```bash
docker compose up -d
```

Controllare lo stato:

```bash
docker compose ps
```

Visualizzare i log:

```bash
docker compose logs mongodb
```

Fermare i container:

```bash
docker compose down
```

Rimuovere anche il volume locale:

```bash
docker compose down -v
```

## Importazione e ripristino del dataset

Per ricostruire il database usando i JSON già generati:

```bash
python scripts/import_to_mongodb.py --reset
```

L’opzione `--reset` elimina e ricrea le collection target. L’importazione avviene nell’ordine:

```text
brands
notes
accords
perfumers
perfumes
```

Verificare il caricamento:

```bash
python scripts/verify_mongodb_import.py
```

Il reset delle collection elimina anche gli indici personalizzati. Dopo il ripristino eseguire:

```bash
python scripts/manage_indexes.py create
python scripts/manage_indexes.py list
```

Per rigenerare anche i JSON a partire dal CSV:

```bash
python scripts/extract_distinct_values.py
python scripts/transform_dataset.py
python scripts/import_to_mongodb.py --reset
python scripts/verify_mongodb_import.py
python scripts/manage_indexes.py create
```

## Avvio del backend

Assicurarsi che MongoDB sia in esecuzione e avviare FastAPI dalla root:

```bash
uvicorn backend.app.main:app --reload
```

Swagger UI è disponibile su:

```text
http://127.0.0.1:8000/docs
```

## Avvio del frontend

In un secondo terminale:

```bash
cd frontend
npm install
npm run dev
```

Aprire:

```text
http://localhost:5173
```

Comandi disponibili:

```bash
npm run dev
npm run lint
npm run build
npm run preview
```

`npm run build` genera la versione di produzione nella cartella locale `frontend/dist/`. La cartella `dist` non deve essere aggiunta al repository.

## Pagine dell’interfaccia

### Dashboard

La pagina iniziale mostra:

- conteggi di profumi, brand, note, accordi e profumieri;
- profumi meglio valutati;
- brand con rating medio più alto;
- note olfattive più frequenti;
- rappresentazioni grafiche leggere realizzate nell’interfaccia.

### Catalogo

Il catalogo offre:

- ricerca per nome;
- filtri per brand, genere, anno, rating, voti, nota, accordo e profumiere;
- combinazione dei filtri con logica `AND`;
- ordinamento per nome, anno, rating o voti;
- ordinamento crescente o decrescente;
- paginazione;
- conteggio complessivo dei risultati;
- azzeramento dei filtri;
- gestione di caricamento, errori e risultati vuoti.

### Dettaglio del profumo

La pagina di dettaglio usa una JOIN multi-collection e mostra:

- brand espanso;
- rating, voti, genere e anno;
- note di testa, cuore e fondo;
- accordi con colori associati;
- profumieri;
- profumi simili;
- pulsanti per modifica ed eliminazione.

### Creazione e modifica

Il form consente di:

- creare un nuovo profumo;
- modificare un profumo esistente;
- selezionare brand, note, accordi e profumieri tramite nomi leggibili;
- visualizzare gli errori restituiti dal backend;
- ricevere una conferma dopo il salvataggio.

L’eliminazione richiede una conferma esplicita.

## Endpoint principali

| Metodo | Endpoint | Descrizione |
| --- | --- | --- |
| GET | `/` | Informazioni di base sull’API |
| GET | `/health` | Stato del backend e di MongoDB |
| GET | `/collections/counts` | Conteggi delle collection |
| GET | `/references/catalog` | Brand, note, accordi e profumieri necessari al frontend |
| GET | `/perfumes` | Ricerca, filtri, ordinamento e paginazione |
| POST | `/perfumes` | Creazione di un profumo |
| GET | `/perfumes/{perfume_id}` | Lettura di un profumo |
| GET | `/perfumes/{perfume_id}/details` | Dettaglio con riferimenti espansi |
| GET | `/perfumes/{perfume_id}/similar` | Profumi simili |
| PUT | `/perfumes/{perfume_id}` | Modifica completa dei campi scrivibili |
| DELETE | `/perfumes/{perfume_id}` | Eliminazione di un profumo |
| GET | `/statistics/top-perfumes` | Profumi meglio valutati |
| GET | `/statistics/brands` | Conteggi e rating medio per brand |
| GET | `/statistics/notes` | Note più frequenti |

## Ricerca e filtri

`GET /perfumes` accetta:

| Parametro | Descrizione |
| --- | --- |
| `name` | Ricerca parziale per nome |
| `brand` | Nome del brand |
| `gender` | `men`, `women` oppure `unisex` |
| `year_min`, `year_max` | Intervallo di anni |
| `rating_min`, `rating_max` | Intervallo di rating |
| `votes_min` | Numero minimo di voti |
| `note` | Nome della nota |
| `accord` | Nome dell’accordo |
| `perfumer` | Nome del profumiere |
| `sort_by` | `name`, `year`, `rating` oppure `votes` |
| `sort_order` | `asc` oppure `desc` |
| `limit` | Numero di risultati, da 1 a 100 |
| `skip` | Numero di risultati da saltare |

La ricerca testuale è:

- parziale;
- case-insensitive;
- sicura rispetto ai caratteri delle espressioni regolari;
- tollerante rispetto a spazi, trattini e underscore.

Le seguenti ricerche sono quindi equivalenti:

```text
acqua di
acqua-di
acqua_di
```

Esempi:

```bash
curl "http://127.0.0.1:8000/perfumes?name=acqua%20di"
curl "http://127.0.0.1:8000/perfumes?brand=Dior&gender=unisex"
curl "http://127.0.0.1:8000/perfumes?note=Vanilla&rating_min=4&votes_min=100"
```

## Endpoint dei riferimenti

Il frontend usa:

```text
GET /references/catalog
```

La risposta contiene quattro elenchi ordinati:

```json
{
  "brands": [],
  "notes": [],
  "accords": [],
  "perfumers": []
}
```

L’endpoint è di sola lettura. Permette di visualizzare nomi comprensibili nei form e inviare al backend gli identificativi MongoDB corretti senza richiedere all’utente di digitarli manualmente.

## Operazioni CRUD e normalizzazione

I payload di `POST /perfumes` e `PUT /perfumes/{perfume_id}` sono validati tramite Pydantic.

Il backend:

- genera automaticamente `_id` per i profumi manuali con prefisso `manual_perfume_`;
- ricostruisce `all_note_ids` a partire dalle tre categorie di note;
- rimuove i riferimenti duplicati mantenendo il loro ordine;
- verifica che brand, note, accordi e profumieri esistano;
- controlla l’unicità di `source_url` quando presente;
- impedisce la modifica o rimozione di `source_url` per i profumi importati dall’ETL.

La pulizia del nome è allineata a quella della pipeline ETL:

- sostituzione degli spazi non separabili;
- rimozione di spazi esterni;
- rimozione di virgolette o apici che racchiudono l’intero valore;
- riduzione delle sequenze di spazi a un solo spazio;
- conservazione della capitalizzazione originale.

### Controllo dei duplicati applicativi

Il middleware applicativo controlla esclusivamente:

```text
POST /perfumes
PUT /perfumes/{perfume_id}
```

Un profumo viene considerato duplicato quando coincidono:

- nome, senza distinguere maiuscole e minuscole;
- brand;
- genere;
- anno;
- note di testa, cuore e fondo;
- accordi;
- profumieri.

L’ordine dei riferimenti non modifica il risultato del confronto.

Rating, voti e `source_url` non fanno parte della firma applicativa, perché possono cambiare senza identificare una fragranza diversa. `source_url` mantiene inoltre il proprio controllo di unicità separato.

In caso di duplicato il backend restituisce:

```text
409 Conflict
```

Il controllo riguarda soltanto le richieste CRUD ricevute dall’API. Gli script ETL e di importazione non attraversano il middleware e mantengono il comportamento definito nelle issue dedicate al caricamento del CSV.

## JOIN, statistiche e profumi simili

Il dettaglio completo usa `$lookup` verso:

```text
brands
notes
accords
perfumers
```

Le pipeline e le relative scelte sono documentate in [docs/queries.md](docs/queries.md).

La ricerca di profumi simili confronta note e accordi tramite indice di Jaccard:

```text
similarity_score = 0.7 × note_similarity + 0.3 × accord_similarity
```

Rating e voti non partecipano al calcolo, ma vengono usati per risolvere eventuali parità.

## Indici MongoDB

Gli indici sono definiti in:

```text
backend/app/indexes.py
```

Gestione:

```bash
python scripts/manage_indexes.py create
python scripts/manage_indexes.py list
python scripts/manage_indexes.py drop
```

Il comando `create` è idempotente. `drop` rimuove soltanto gli indici gestiti dal progetto e conserva `_id_`.

Il progetto include indici per:

- unicità parziale di `source_url`;
- brand e rating;
- genere, rating e voti;
- classifica per rating e voti;
- note olfattive;
- accordi.

## Benchmark

Il benchmark replicabile si esegue con:

```bash
python benchmarks/run_benchmarks.py --warmup 3 --runs 20
```

Confronta sette scenari prima e dopo la creazione degli indici e salva i risultati in:

```text
benchmarks/results/benchmark-results.json
```

Metodologia, risultati e limiti sono descritti in [docs/indexes-and-benchmarks.md](docs/indexes-and-benchmarks.md).

## Test automatici

Dalla root del repository:

```bash
python -m pytest -v
```

Ultimo risultato verificato:

```text
92 passed in 3.48s
```

Per eseguire gruppi specifici:

```bash
python -m pytest tests/test_perfume_filters.py -v
python -m pytest tests/test_search_normalization.py -v
python -m pytest tests/test_aggregations.py -v
python -m pytest tests/test_similarity.py -v
python -m pytest tests/test_indexes.py -v
```

La suite copre, tra le altre cose:

- filtri singoli e combinati;
- ricerca parziale e case-insensitive;
- equivalenza tra spazi, trattini e underscore;
- trattamento letterale dei caratteri speciali;
- ordinamento e paginazione;
- JOIN e aggregazioni;
- similarità di Jaccard;
- gestione degli indici;
- vincolo univoco parziale su `source_url`;
- regressione degli endpoint principali.

## Verifica del frontend

Dalla cartella `frontend/`:

```bash
npm run lint
npm run build
```

Ultima verifica locale:

```text
ESLint completato senza errori
Vite build completata senza errori
0 vulnerabilità rilevate da npm audit durante npm install
```

Verifica manuale minima:

1. caricare dashboard e statistiche;
2. usare catalogo, filtri, ordinamento e paginazione;
3. cercare lo stesso profumo con spazio, trattino e underscore;
4. aprire un dettaglio con note, accordi, profumieri e simili;
5. creare, modificare ed eliminare un profumo sintetico;
6. verificare errori e stati vuoti;
7. controllare desktop, tablet e smartphone;
8. verificare l’assenza di errori rilevanti nella console del browser.

Dopo test CRUD sul database completo, ripristinare i dati originali con:

```bash
python scripts/import_to_mongodb.py --reset
python scripts/manage_indexes.py create
python scripts/verify_mongodb_import.py
```

## Esecuzione completa da zero

Terminale principale:

```bash
pip install -r requirements.txt
docker compose up -d
python scripts/import_to_mongodb.py --reset
python scripts/verify_mongodb_import.py
python scripts/manage_indexes.py create
python -m pytest -v
uvicorn backend.app.main:app --reload
```

Secondo terminale:

```bash
cd frontend
npm install
npm run lint
npm run build
npm run dev
```

Applicazione:

```text
Frontend: http://localhost:5173
Backend:  http://127.0.0.1:8000
Swagger:  http://127.0.0.1:8000/docs
```

## Teorema CAP

Il teorema CAP viene discusso esclusivamente dal punto di vista teorico nella documentazione finale. Il progetto non implementa replica set, sharding, partizioni di rete o una rete distribuita simulata.

## Documentazione

- [Modellazione documentale](docs/modeling.md)
- [Pipeline ETL](docs/etl.md)
- [Query, JOIN, aggregazioni e similarità](docs/queries.md)
- [Indici e benchmark](docs/indexes-and-benchmarks.md)

## Stato del progetto

Sono stati completati:

- setup MongoDB tramite Docker;
- modellazione documentale;
- pipeline ETL e importazione verificata;
- backend FastAPI;
- CRUD sui profumi;
- ricerca, filtri, ordinamento e paginazione;
- JOIN multi-collection;
- aggregazioni statistiche;
- ricerca di profumi simili;
- progettazione e benchmark degli indici;
- frontend React responsive;
- dashboard, catalogo, dettaglio e form CRUD;
- configurazione CORS;
- controlli applicativi sui duplicati;
- test automatici e verifiche frontend.

Restano da completare la revisione finale della Pull Request, l’eventuale revisione esterna richiesta dal flusso del corso e la preparazione della documentazione e della demo conclusiva.
