# ScentBase Frontend

Interfaccia React/Vite per esplorare il catalogo, usare i filtri, visualizzare il dettaglio ottenuto tramite `$lookup`, eseguire le operazioni CRUD e consultare la dashboard statistica.

## Prerequisiti

- Node.js 20 o versione compatibile;
- MongoDB e backend FastAPI già avviati.

## Configurazione

Creare il file locale `.env` partendo dall'esempio:

```bash
cp .env.example .env
```

Su PowerShell:

```powershell
Copy-Item .env.example .env
```

La variabile predefinita è:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Installazione e avvio

```bash
npm install
npm run dev
```

L'interfaccia viene avviata normalmente su:

```text
http://127.0.0.1:5173
```

## Verifiche

```bash
npm run lint
npm run build
```

Per verificare che le modifiche CORS non abbiano introdotto regressioni nel backend, dalla radice del repository eseguire anche:

```bash
python -m pytest -v
```

## Pagine

- `/` — dashboard statistica;
- `/catalogo` — catalogo con ricerca, filtri, ordinamento e paginazione;
- `/profumi/:id` — dettaglio con brand, note, accordi e profumieri espansi;
- `/profumi/:id/modifica` — modifica di un profumo;
- `/profumi/nuovo` — creazione di un profumo.

## Avvio completo

Dalla radice del repository:

```bash
docker compose up -d
python scripts/verify_mongodb_import.py
uvicorn backend.app.main:app --reload
```

In un secondo terminale:

```bash
cd frontend
npm install
npm run dev
```

Il backend accetta per impostazione predefinita richieste da `localhost:5173` e `127.0.0.1:5173`. Gli origin possono essere modificati tramite la variabile backend `CORS_ALLOWED_ORIGINS`, usando valori separati da virgola.
