# ScentBase

Sistema NoSQL per la gestione e l’analisi di profumi, note olfattive e valutazioni.

## Tipologia

Progetto NoSQL classico basato su MongoDB.

## Obiettivo

Il progetto ha l’obiettivo di realizzare una proof of concept per importare, modellare e interrogare un dataset pubblico relativo a profumi e fragranze.

Il sistema prevede:

- modellazione dei dati in collection MongoDB;
- operazioni CRUD;
- query di ricerca e aggregazione;
- JOIN tra collection tramite `$lookup`;
- utilizzo di indici;
- interfaccia utente minimale.

## Struttura del progetto

```text
backend/              Backend FastAPI
frontend/             Interfaccia utente minimale
db/schema/            Schema, validator e indici MongoDB
scripts/              Script di pulizia, trasformazione e importazione dati
queries/              Query MongoDB e aggregation pipeline
benchmarks/results/   Risultati dei benchmark
data/raw/             Dataset originale
data/processed/       Dati trasformati dagli script
docs/report/          Documentazione finale del progetto
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

Le prossime attività riguarderanno l’analisi del dataset, la progettazione del modello documentale MongoDB e gli script di trasformazione/importazione dei dati.
