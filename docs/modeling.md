# Modellazione documentale ScentBase

## Obiettivo del documento

Questo documento descrive la modellazione iniziale del database MongoDB per il progetto **ScentBase**.

Lo scopo è definire una specifica tecnica preliminare del modello dati, indicando:

* dataset di riferimento;
* miniworld operativo;
* collection previste;
* collegamenti tra collection;
* scelte di embedding e referencing;
* campi necessari per query, aggregazioni, filtri avanzati, ricerca di profumi simili e dashboard.

Il documento non sostituisce la documentazione finale del progetto, ma definisce la base tecnica della modellazione dati.

---

## Dataset di riferimento

Il progetto utilizza come dataset principale il file:

```text
fra_cleaned.csv
```

Il file è un CSV già parzialmente pulito, derivato da dati relativi a profumi e fragranze. Il dataset raw potrà essere consultato solo come riferimento secondario, se necessario.

Caratteristiche principali rilevate:

| Proprietà            |              Valore |
| -------------------- | ------------------: |
| Numero di record     |               24063 |
| Numero di colonne    |                  18 |
| Separatore           |                 `;` |
| Encoding compatibile | `latin1` / `cp1252` |

Colonne presenti nel dataset:

```text
url
Perfume
Brand
Country
Gender
Rating Value
Rating Count
Year
Top
Middle
Base
Perfumer1
Perfumer2
mainaccord1
mainaccord2
mainaccord3
mainaccord4
mainaccord5
```

---

## Analisi sintetica del dataset

Il dataset contiene informazioni su profumi, brand, paese associato al brand, genere, rating, numero di valutazioni, anno di rilascio, note olfattive, profumieri e accordi principali.

Osservazioni rilevanti per la modellazione:

* `url` è valorizzato per tutti i record ed è univoco;
* `Perfume` non è completamente univoco, quindi non verrà usato come identificativo;
* `Brand` contiene valori ripetuti e rappresenta un’entità autonoma;
* `Country` è associato al brand e verrà modellato come attributo di `brands`;
* `Top`, `Middle` e `Base` contengono liste di note olfattive;
* `mainaccord1`-`mainaccord5` contengono gli accordi principali;
* `Perfumer1` contiene spesso il valore `unknown`;
* `Perfumer2` è mancante nella maggior parte dei record;
* `Rating Value` usa la virgola come separatore decimale e dovrà essere convertito in numero;
* `Year` presenta alcuni valori mancanti e sarà gestito come campo opzionale.

Statistiche principali:

| Campo       |           Osservazione |
| ----------- | ---------------------: |
| `url`       |     24063 valori unici |
| `Perfume`   |     22840 valori unici |
| `Brand`     |    1060 brand distinti |
| `Country`   |      54 paesi distinti |
| `Gender`    |      3 valori distinti |
| `Year`      |   2037 valori mancanti |
| `Perfumer1` | 12320 valori `unknown` |
| `Perfumer2` |  22727 valori mancanti |

Distribuzione del campo `Gender`:

| Valore   | Occorrenze |
| -------- | ---------: |
| `women`  |      11376 |
| `unisex` |       7698 |
| `men`    |       4989 |

---

## Miniworld operativo

Il miniworld di ScentBase rappresenta una piattaforma di esplorazione e analisi di profumi.

Ogni profumo è associato a:

* un brand;
* un paese del brand;
* un genere;
* un rating medio;
* un numero di valutazioni;
* un anno di rilascio;
* un insieme di note olfattive;
* uno o più accordi principali;
* zero, uno o più profumieri.

Le note olfattive sono suddivise in note di testa, note di cuore e note di fondo. Gli accordi principali descrivono invece il profilo generale della fragranza.

Il sistema dovrà consentire la consultazione e l’analisi del catalogo per brand, genere, anno, rating, note olfattive, accordi e profumieri.

---

## Collection previste

Il database MongoDB sarà composto da cinque collection principali:

```text
perfumes
brands
notes
accords
perfumers
```

La collection centrale sarà `perfumes`, che conterrà i riferimenti verso le altre collection.

---

## Collection `perfumes`

La collection `perfumes` rappresenta i profumi presenti nel catalogo.

Schema logico preliminare:

```json
{
  "_id": "string",
  "source_url": "string",
  "name": "string",
  "brand_id": "string",
  "gender": "string",
  "rating": "number",
  "votes": "number",
  "year": "number|null",
  "top_note_ids": ["string"],
  "middle_note_ids": ["string"],
  "base_note_ids": ["string"],
  "all_note_ids": ["string"],
  "accord_ids": ["string"],
  "perfumer_ids": ["string"]
}
```

Descrizione dei campi principali:

| Campo             | Descrizione                               |
| ----------------- | ----------------------------------------- |
| `_id`             | Identificativo interno del profumo        |
| `source_url`      | URL originale del profumo nel dataset     |
| `name`            | Nome del profumo                          |
| `brand_id`        | Riferimento alla collection `brands`      |
| `gender`          | Genere del profumo                        |
| `rating`          | Rating medio convertito in numero         |
| `votes`           | Numero di valutazioni                     |
| `year`            | Anno di rilascio, opzionale               |
| `top_note_ids`    | Riferimenti alle note di testa            |
| `middle_note_ids` | Riferimenti alle note di cuore            |
| `base_note_ids`   | Riferimenti alle note di fondo            |
| `all_note_ids`    | Unione delle note di testa, cuore e fondo |
| `accord_ids`      | Riferimenti agli accordi principali       |
| `perfumer_ids`    | Riferimenti ai profumieri                 |

Il campo `all_note_ids` viene introdotto per semplificare le query basate sulle note e la ricerca di profumi simili.

---

## Collection `brands`

La collection `brands` rappresenta i brand dei profumi.

Schema logico preliminare:

```json
{
  "_id": "string",
  "name": "string",
  "country": "string|null"
}
```

Il campo `Country` del CSV viene modellato come attributo della collection `brands`.

Non viene prevista una collection separata per i paesi, perché nel dataset il paese è un attributo descrittivo del brand e non un’entità centrale del miniworld.

---

## Collection `notes`

La collection `notes` rappresenta le note olfattive presenti nei profumi.

Schema logico preliminare:

```json
{
  "_id": "string",
  "name": "string"
}
```

Le note derivano dalle colonne:

```text
Top
Middle
Base
```

Dall’analisi sono state rilevate 1671 note distinte considerando insieme note di testa, cuore e fondo.

---

## Collection `accords`

La collection `accords` rappresenta gli accordi principali associati ai profumi.

Schema logico preliminare:

```json
{
  "_id": "string",
  "name": "string"
}
```

Gli accordi derivano dalle colonne:

```text
mainaccord1
mainaccord2
mainaccord3
mainaccord4
mainaccord5
```

Dall’analisi sono stati rilevati 84 accordi distinti.

---

## Collection `perfumers`

La collection `perfumers` rappresenta i profumieri associati ai profumi.

Schema logico preliminare:

```json
{
  "_id": "string",
  "name": "string"
}
```

I profumieri derivano dalle colonne:

```text
Perfumer1
Perfumer2
```

Il valore `unknown` non verrà considerato un profumiere valido e non genererà un documento nella collection `perfumers`.

Se un profumo non ha profumieri noti, il campo `perfumer_ids` nella collection `perfumes` sarà un array vuoto.

---

## Collegamenti tra collection

Le collection saranno collegate tramite identificativi condivisi.

| Campo in `perfumes` | Collection collegata | Campo collegato |
| ------------------- | -------------------- | --------------- |
| `brand_id`          | `brands`             | `_id`           |
| `top_note_ids`      | `notes`              | `_id`           |
| `middle_note_ids`   | `notes`              | `_id`           |
| `base_note_ids`     | `notes`              | `_id`           |
| `all_note_ids`      | `notes`              | `_id`           |
| `accord_ids`        | `accords`            | `_id`           |
| `perfumer_ids`      | `perfumers`          | `_id`           |

Questa struttura consente di mantenere separate le entità principali del miniworld e di implementare query con `$lookup` tra più collection.

---

## Mapping CSV → MongoDB

| Colonna CSV    | Destinazione prevista                 |
| -------------- | ------------------------------------- |
| `url`          | `perfumes.source_url`                 |
| `Perfume`      | `perfumes.name`                       |
| `Brand`        | `brands.name` e `perfumes.brand_id`   |
| `Country`      | `brands.country`                      |
| `Gender`       | `perfumes.gender`                     |
| `Rating Value` | `perfumes.rating`                     |
| `Rating Count` | `perfumes.votes`                      |
| `Year`         | `perfumes.year`                       |
| `Top`          | `notes` e `perfumes.top_note_ids`     |
| `Middle`       | `notes` e `perfumes.middle_note_ids`  |
| `Base`         | `notes` e `perfumes.base_note_ids`    |
| `Perfumer1`    | `perfumers` e `perfumes.perfumer_ids` |
| `Perfumer2`    | `perfumers` e `perfumes.perfumer_ids` |
| `mainaccord1`  | `accords` e `perfumes.accord_ids`     |
| `mainaccord2`  | `accords` e `perfumes.accord_ids`     |
| `mainaccord3`  | `accords` e `perfumes.accord_ids`     |
| `mainaccord4`  | `accords` e `perfumes.accord_ids`     |
| `mainaccord5`  | `accords` e `perfumes.accord_ids`     |

---

## Scelta tra embedding e referencing

Il modello utilizzerà principalmente il **referencing** per collegare profumi, brand, note, accordi e profumieri.

La scelta è motivata dal fatto che brand, note, accordi e profumieri possono comparire in molti profumi diversi e devono essere interrogabili separatamente.

La collection `perfumes` manterrà array di identificativi per rappresentare le relazioni molti-a-molti con note, accordi e profumieri.

Questa soluzione riduce duplicazioni, mantiene chiari i collegamenti tra le collection e consente query con `$lookup`.

---

## Gestione dei valori mancanti

A livello di modellazione si prevedono le seguenti scelte:

| Caso                                | Scelta prevista                            |
| ----------------------------------- | ------------------------------------------ |
| `Year` mancante                     | salvare `null`                             |
| `Perfumer1 = unknown`               | non creare un documento in `perfumers`     |
| `Perfumer2` mancante                | ignorare il valore                         |
| accordi mancanti                    | non aggiungere riferimenti in `accord_ids` |
| `Rating Value` con virgola decimale | convertire in numero float                 |
| `Rating Count`                      | convertire o mantenere come numero intero  |
| note vuote o non valide             | ignorare nella trasformazione              |

---

## Supporto alle funzionalità principali

La modellazione proposta supporta le funzionalità principali del progetto.

| Funzionalità           | Supporto nel modello                                                               |
| ---------------------- | ---------------------------------------------------------------------------------- |
| Consultazione catalogo | dati principali in `perfumes`                                                      |
| Ricerca                | campi `name`, `brand_id`, `gender`, `year`, `rating`, `all_note_ids`, `accord_ids` |
| CRUD                   | operazioni principali sulla collection `perfumes`                                  |
| JOIN con `$lookup`     | riferimenti verso `brands`, `notes`, `accords`, `perfumers`                        |
| Aggregazioni           | campi `rating`, `votes`, `brand_id`, `all_note_ids`, `accord_ids`, `year`          |

---

## Supporto alle funzionalità avanzate

Il modello supporta anche le funzionalità avanzate selezionate per il progetto.

### Filtri combinati avanzati

I filtri combinati potranno usare campi come:

```text
brand_id
gender
year
rating
votes
all_note_ids
accord_ids
perfumer_ids
```

Esempi di interrogazioni supportabili:

```text
profumi con una specifica nota e rating minimo
profumi di un certo brand con uno specifico accordo
profumi unisex ordinati per rating
profumi pubblicati dopo un certo anno
```

### Ricerca di profumi simili

La ricerca di profumi simili sarà basata principalmente su:

```text
all_note_ids
accord_ids
```

Un criterio preliminare di similarità potrà essere:

```text
similarity_score = numero_note_condivise * 2 + numero_accordi_condivisi
```

### Mini dashboard statistica

La dashboard potrà usare campi come:

```text
rating
votes
brand_id
year
all_note_ids
accord_ids
```

Statistiche supportabili:

```text
profumi meglio valutati
profumi più votati
rating medio per brand
note più frequenti
accordi più frequenti
distribuzione dei profumi per anno
```

---

## Identificativi

Gli identificativi definitivi saranno generati durante la trasformazione del dataset.

Scelte previste:

* `Perfume` non verrà usato come `_id`, perché non è univoco;
* `url` verrà conservato come `source_url`, perché è un riferimento stabile al record originale;
* gli `_id` delle collection potranno essere generati a partire da valori normalizzati o tramite identificativi sintetici;
* le relazioni tra collection useranno gli `_id` generati durante la trasformazione.
