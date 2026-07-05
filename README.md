# ScentBase

Sistema NoSQL per la gestione e l’analisi di profumi, note olfattive, accordi, profumieri e valutazioni.

## Tipologia

Progetto NoSQL classico basato su MongoDB.

## Obiettivo

Il progetto ha l’obiettivo di realizzare una proof of concept per importare, modellare e interrogare un dataset relativo a profumi e fragranze.

Il sistema prevede:

* modellazione dei dati in collection MongoDB;
* pipeline ETL per trasformare il dataset in documenti JSON;
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
docs/etl.md           Pipeline di estrazione, arricchimento e trasformazione
queries/              Query MongoDB e aggregation pipeline
scripts/              Script di estrazione e trasformazione dati
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

La pipeline di estrazione, arricchimento e trasformazione è descritta nel file:

```text
docs/etl.md
```

Gli script principali sono:

```text
scripts/extract_distinct_values.py
scripts/transform_dataset.py
```

Il primo script estrae note, accordi e profumieri distinti dal dataset e salva i risultati in:

```text
data/enrichment/
```

Il secondo script valida i mapping di arricchimento, applica il mapping canonico, controlla gli identificativi generati e produce i documenti JSON finali in:

```text
data/processed/
```

File JSON generati:

```text
data/processed/perfumes.json
data/processed/brands.json
data/processed/notes.json
data/processed/accords.json
data/processed/perfumers.json
```

## Esecuzione della pipeline ETL

Dopo aver predisposto il dataset in `data/raw/fra_cleaned.csv`, eseguire:

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
* presenza e unicità di `source_url` per i profumi importati dal dataset.

## Avvio MongoDB con Docker

Il progetto utilizza Docker per avviare MongoDB in locale.

Creare un file `.env` a partire dal file di esempio:

```bash
cp .env.example .env
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

## File di configurazione

Il file `.env.example` contiene variabili di ambiente di esempio.

Il file `.env` viene usato solo in locale e non deve essere caricato nel repository.

## Stato del progetto

Setup iniziale del repository completato.

MongoDB è avviabile localmente tramite Docker.

La modellazione documentale è stata definita in `docs/modeling.md`, con le collection principali, i collegamenti tramite riferimenti, la gestione degli identificativi, i campi di arricchimento e le scelte di modellazione.

La pipeline ETL è stata implementata con script per estrazione dei valori distinti, validazione dei mapping di arricchimento, controllo delle collisioni e generazione dei file JSON in `data/processed/`.

Le prossime attività riguarderanno l’importazione dei documenti in MongoDB, la definizione delle query, l’aggiunta degli indici, i benchmark e lo sviluppo delle funzionalità applicative.
