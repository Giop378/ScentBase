# Pipeline ETL ScentBase

## Obiettivo

Questo documento descrive la pipeline ETL usata per trasformare il dataset `fra_cleaned.csv` nei documenti JSON destinati alle collection MongoDB del progetto **ScentBase**.

Il documento non contiene il log completo dell'esecuzione, ma raccoglie le scelte operative principali della fase di estrazione, arricchimento, validazione e trasformazione.

---

## Struttura delle cartelle

La pipeline usa la seguente struttura:

```text
data/
  raw/
    fra_cleaned.csv
  enrichment/
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

## Comandi principali

Estrarre i valori distinti:

```bash
python scripts/extract_distinct_values.py
```

Eseguire la trasformazione completa:

```bash
python scripts/transform_dataset.py
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

## Controlli su identificativi e URL sorgente

Prima di scrivere i file JSON finali, lo script verifica:

* unicità degli `_id` finali in ogni collection;
* assenza di documenti senza `_id` valido;
* presenza di `source_url` per ogni profumo importato dal dataset;
* unicità di `source_url` nella collection `perfumes`.

Il controllo su `source_url` riguarda solo i dati importati dal CSV. Per futuri profumi inseriti manualmente tramite CRUD, `source_url` potrà essere opzionale e l'identificativo sarà generato dal backend applicativo.

---

## Trasformazioni principali

Durante la trasformazione vengono applicate le seguenti operazioni:

* conversione del rating in numero decimale;
* conversione del numero di voti in intero;
* conversione dell'anno in intero quando disponibile;
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

I file sono pensati per essere usati nella successiva fase di importazione in MongoDB.

---

## Conteggi sintetici attesi

Dopo la trasformazione, i conteggi attesi sono indicativamente:

| Collection | Documenti generati |
| --- | ---: |
| `perfumes` | 24063 |
| `brands` | 1060 |
| `notes` | 1668 |
| `accords` | 84 |
| `perfumers` | 905 |

I conteggi possono cambiare solo se vengono modificati dataset sorgente, mapping canonico o regole di trasformazione.

---

## Uso dell'AI

L'AI è stata usata come supporto per costruire i mapping di arricchimento:

* classificazione delle note in gruppi olfattivi;
* assegnazione dei colori rappresentativi agli accordi;
* imputazione della nazionalità descrittiva dei profumieri.

I risultati generati con supporto AI non vengono accettati automaticamente: lo script verifica la coerenza dei mapping rispetto ai valori distinti del dataset e blocca la trasformazione in caso di valori mancanti, extra, nulli o non validi.

---

## Relazione con `modeling.md`

`docs/modeling.md` descrive il modello dati e le scelte progettuali stabili.

`docs/etl.md` descrive invece la pipeline con cui il dataset viene trasformato nei documenti coerenti con quel modello.
