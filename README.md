# ScentBase

Sistema NoSQL per la gestione e l’analisi di profumi, note olfattive, accordi, profumieri e valutazioni.

## Tipologia

Progetto NoSQL classico basato su MongoDB.

## Obiettivo

Il progetto ha l’obiettivo di realizzare una proof of concept per importare, modellare e interrogare un dataset pubblico relativo a profumi e fragranze.

Il sistema prevede:

* modellazione dei dati in collection MongoDB;
* operazioni CRUD;
* query di ricerca e aggregazione;
* JOIN tra collection tramite `$lookup`;
* utilizzo di indici;
* interfaccia utente minimale.

## Struttura del progetto

```text
backend/              Backend FastAPI
frontend/             Interfaccia utente minimale
db/schema/            Schemi preliminari delle collection MongoDB
scripts/              Script di pulizia, trasformazione e importazione dati
queries/              Query MongoDB e aggregation pipeline
benchmarks/results/   Risultati dei benchmark
data/raw/             Dataset originale
data/processed/       Dati trasformati dagli script
docs/modeling.md      Modellazione documentale preliminare
docs/report/          Documentazione finale del progetto
```

## Modellazione dati

La modellazione documentale preliminare è descritta nel file:

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

Gli schemi descrivono la struttura iniziale dei documenti MongoDB e saranno usati come riferimento per le successive fasi di trasformazione, importazione, query e sviluppo dell’applicazione.

## Dataset

Il dataset principale previsto per il progetto è:

```text
fra_cleaned.csv
```

Il file contiene dati relativi a profumi, brand, paese del brand, genere, rating, numero di valutazioni, anno, note olfattive, profumieri e accordi principali.

Il dataset completo può essere collocato localmente nella cartella:

```text
data/raw/
```

I dati trasformati dagli script saranno salvati in:

```text
data/processed/
```

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

La struttura base del progetto è stata predisposta e MongoDB è avviabile localmente tramite Docker.

È stata definita la modellazione documentale preliminare del database MongoDB, con le collection principali, i collegamenti tramite riferimenti, le scelte di modellazione e gli schemi preliminari in `db/schema/`.

Le prossime attività riguarderanno l’implementazione degli script di pulizia, trasformazione e importazione del dataset.
