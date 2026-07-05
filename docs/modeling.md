# Modellazione documentale ScentBase

## Obiettivo

Questo documento raccoglie le principali scelte di modellazione del database MongoDB del progetto **ScentBase**.

Lo scopo è mantenere traccia delle decisioni stabili sul modello dati, in particolare:

* dataset e miniworld di riferimento;
* collection previste;
* collegamenti tra collection;
* scelta tra embedding e referencing;
* gestione dei valori mancanti;
* identificativi tecnici;
* campi di arricchimento usati per filtri, aggregazioni, ricerca di profumi simili e dashboard.

I dettagli operativi della pipeline di estrazione e trasformazione sono descritti in `docs/etl.md`.

---

## Dataset di riferimento

Il progetto usa come dataset principale:

```text
fra_cleaned.csv
```

Il file contiene informazioni su profumi e fragranze, con dati relativi a nome, brand, paese del brand, genere, rating, anno, note olfattive, profumieri e accordi principali.

Colonne principali del CSV:

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

Dati rilevanti per la modellazione:

* `url` è il riferimento sorgente del record importato;
* `Perfume` non è completamente univoco e non viene usato come identificativo;
* `Brand` rappresenta un'entità autonoma;
* `Top`, `Middle` e `Base` contengono liste di note olfattive;
* `mainaccord1`-`mainaccord5` contengono gli accordi principali;
* `Perfumer1` e `Perfumer2` rappresentano i profumieri associati al profumo;
* `Year`, `Rating Value` e `Rating Count` devono essere convertiti in tipi numerici dove possibile.

---

## Miniworld operativo

ScentBase rappresenta una piattaforma di consultazione e analisi di profumi.

Ogni profumo è associato a:

* un brand;
* un paese del brand;
* un genere;
* un rating medio;
* un numero di valutazioni;
* un anno di rilascio;
* note olfattive di testa, cuore e fondo;
* accordi principali;
* zero, uno o più profumieri.

Il sistema deve supportare consultazione del catalogo, ricerca, CRUD, filtri combinati, aggregazioni, ricerca di profumi simili e una mini dashboard statistica.

---

## Collection previste

Il database MongoDB è organizzato in cinque collection principali:

```text
perfumes
brands
notes
accords
perfumers
```

La collection centrale è `perfumes`, che contiene i riferimenti verso le altre collection tramite identificativi condivisi.

---

## Collection `perfumes`

La collection `perfumes` rappresenta i profumi presenti nel catalogo.

Schema logico:

```json
{
  "_id": "string",
  "source_url": "string",
  "name": "string",
  "brand_id": "string",
  "gender": "string",
  "rating": "number|null",
  "votes": "number|null",
  "year": "number|null",
  "top_note_ids": ["string"],
  "middle_note_ids": ["string"],
  "base_note_ids": ["string"],
  "all_note_ids": ["string"],
  "accord_ids": ["string"],
  "perfumer_ids": ["string"]
}
```

Campi principali:

| Campo | Descrizione |
| --- | --- |
| `_id` | Identificativo tecnico del profumo |
| `source_url` | URL originale del record importato dal dataset |
| `name` | Nome leggibile del profumo |
| `brand_id` | Riferimento alla collection `brands` |
| `gender` | Genere del profumo |
| `rating` | Rating medio convertito in numero |
| `votes` | Numero di valutazioni |
| `year` | Anno di rilascio, se disponibile |
| `top_note_ids` | Note di testa |
| `middle_note_ids` | Note di cuore |
| `base_note_ids` | Note di fondo |
| `all_note_ids` | Unione delle note di testa, cuore e fondo |
| `accord_ids` | Accordi principali |
| `perfumer_ids` | Profumieri associati |

Il campo `all_note_ids` viene introdotto per semplificare le query basate sulle note e la ricerca di profumi simili.

Per i profumi importati dal dataset, `source_url` è obbligatorio e viene usato come riferimento stabile al record originale. L'identificativo tecnico dei profumi importati viene generato a partire da questo URL, perché il nome del profumo non è completamente univoco.

Per eventuali profumi inseriti manualmente tramite future funzionalità CRUD, `source_url` potrà invece essere opzionale. In quel caso l'identificativo del profumo sarà generato dal backend applicativo.

---

## Collection `brands`

La collection `brands` rappresenta i brand dei profumi.

Schema logico:

```json
{
  "_id": "string",
  "name": "string",
  "country": "string|null"
}
```

Il campo `Country` del CSV viene modellato come attributo del brand.

Non viene creata una collection separata per i paesi, perché nel dataset il paese è usato come attributo descrittivo del brand e non come entità centrale del miniworld.

---

## Collection `notes`

La collection `notes` rappresenta le note olfattive usate nei profumi.

Schema logico:

```json
{
  "_id": "string",
  "name": "string",
  "olfactory_group": "string"
}
```

Le note derivano dalle colonne:

```text
Top
Middle
Base
```

Il campo `olfactory_group` è un campo di arricchimento. Permette di usare le note come vocabolario controllato arricchito, utile per filtri, aggregazioni, ricerca di profumi simili e dashboard.

Quando una nota non è classificabile con sufficiente sicurezza, viene usato il valore controllato:

```text
other
```

---

## Collection `accords`

La collection `accords` rappresenta gli accordi principali associati ai profumi.

Schema logico:

```json
{
  "_id": "string",
  "name": "string",
  "color_hex": "string"
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

Il campo `color_hex` è un campo di arricchimento usato per associare un colore rappresentativo agli accordi, utile soprattutto per interfaccia utente e dashboard.

Quando non è possibile assegnare un colore specifico, viene usato il valore controllato:

```text
#9E9E9E
```

---

## Collection `perfumers`

La collection `perfumers` rappresenta i profumieri associati ai profumi.

Schema logico:

```json
{
  "_id": "string",
  "name": "string",
  "nationality": "string"
}
```

I profumieri derivano dalle colonne:

```text
Perfumer1
Perfumer2
```

Il valore `unknown` presente nel CSV non viene considerato un profumiere valido e non genera un documento in `perfumers`.

Il campo `nationality` è un campo di arricchimento descrittivo. Quando la nazionalità non è determinabile con sufficiente sicurezza, viene usato il valore controllato:

```text
Unknown
```

Se un profumo non ha profumieri noti, `perfumer_ids` resta un array vuoto.

---

## Collegamenti tra collection

Le collection sono collegate tramite identificativi condivisi.

| Campo in `perfumes` | Collection collegata | Campo collegato |
| --- | --- | --- |
| `brand_id` | `brands` | `_id` |
| `top_note_ids` | `notes` | `_id` |
| `middle_note_ids` | `notes` | `_id` |
| `base_note_ids` | `notes` | `_id` |
| `all_note_ids` | `notes` | `_id` |
| `accord_ids` | `accords` | `_id` |
| `perfumer_ids` | `perfumers` | `_id` |

Questa struttura consente di mantenere separate le entità principali del miniworld e di implementare query con `$lookup` tra più collection.

---

## Mapping CSV → MongoDB

| Colonna CSV | Destinazione prevista |
| --- | --- |
| `url` | `perfumes.source_url` |
| `Perfume` | `perfumes.name` |
| `Brand` | `brands.name` e `perfumes.brand_id` |
| `Country` | `brands.country` |
| `Gender` | `perfumes.gender` |
| `Rating Value` | `perfumes.rating` |
| `Rating Count` | `perfumes.votes` |
| `Year` | `perfumes.year` |
| `Top` | `notes` e `perfumes.top_note_ids` |
| `Middle` | `notes` e `perfumes.middle_note_ids` |
| `Base` | `notes` e `perfumes.base_note_ids` |
| `Perfumer1` | `perfumers` e `perfumes.perfumer_ids` |
| `Perfumer2` | `perfumers` e `perfumes.perfumer_ids` |
| `mainaccord1`-`mainaccord5` | `accords` e `perfumes.accord_ids` |
| arricchimento note | `notes.olfactory_group` |
| arricchimento accordi | `accords.color_hex` |
| arricchimento profumieri | `perfumers.nationality` |

---

## Scelta tra embedding e referencing

Il modello usa principalmente il **referencing** per collegare profumi, brand, note, accordi e profumieri.

La scelta è motivata dal fatto che brand, note, accordi e profumieri possono comparire in molti profumi diversi e devono essere interrogabili separatamente.

Inoltre, le collection collegate possono contenere metadati propri:

* `brands.country`;
* `notes.olfactory_group`;
* `accords.color_hex`;
* `perfumers.nationality`.

L'embedding completo dei documenti collegati non viene adottato per le entità principali, perché renderebbe più difficile mantenere separati e riutilizzabili brand, note, accordi e profumieri.

### Vantaggi del referencing

* modellazione più chiara del miniworld;
* interrogabilità separata di brand, note, accordi e profumieri;
* CRUD più coerenti sulle entità collegate;
* maggiore estendibilità del modello;
* supporto a query multi-collection tramite `$lookup`;
* supporto a filtri, aggregazioni e dashboard;
* possibilità di usare alcune collection come vocabolari controllati.

### Svantaggi del referencing

* maggiore complessità nella fase di trasformazione/importazione;
* necessità di controlli applicativi sui riferimenti, perché MongoDB non impone foreign key tra collection;
* query di dettaglio più complesse, perché richiedono `$lookup`;
* possibile costo prestazionale aggiuntivo nelle query multi-collection;
* presenza di una certa ridondanza, perché gli identificativi vengono ripetuti nei documenti `perfumes`.

Nel contesto di ScentBase questi svantaggi sono considerati accettabili, perché il progetto richiede una modellazione multi-collection, query tra collection, operazioni CRUD coerenti e analisi basate su entità riutilizzabili.

---

## Gestione dei valori mancanti

| Caso | Scelta prevista |
| --- | --- |
| `Year` mancante | salvare `null` |
| `Rating Value` mancante/non valido | salvare `null` |
| `Rating Count` mancante/non valido | salvare `null` |
| `Perfumer1 = unknown` | non creare un documento in `perfumers` |
| `Perfumer2` mancante | ignorare il valore |
| accordi mancanti | non aggiungere riferimenti in `accord_ids` |
| note vuote o non valide | ignorare nella trasformazione |
| `olfactory_group` non determinabile | salvare `other` |
| `color_hex` non specifico | salvare `#9E9E9E` |
| `nationality` non determinabile | salvare `Unknown` |

Per i campi di arricchimento si evita l'uso di valori nulli, preferendo valori controllati e documentati.

---

## Identificativi

Gli identificativi sono generati durante la trasformazione del dataset.

Scelte previste:

* `Perfume` non viene usato come `_id`, perché non è univoco;
* `url` viene conservato come `source_url`, perché è il riferimento stabile al record originale;
* gli `_id` delle collection collegate sono generati tramite valori normalizzati con prefisso della collection;
* il campo `name` conserva il valore leggibile dell'entità;
* le relazioni tra collection usano gli `_id` generati durante la trasformazione.

Esempi:

```text
brand_dior
note_bergamot
accord_warm_spicy
perfumer_alberto_morillas
```

La normalizzazione tecnica degli identificativi prevede:

* conversione in minuscolo;
* rimozione di accenti e segni diacritici;
* sostituzione di spazi, trattini, apostrofi, slash, parentesi e punteggiatura con `_`;
* riduzione di più `_` consecutivi a uno solo;
* rimozione di eventuali `_` iniziali o finali.

Esempi:

```text
Jean-Claude Ellena  -> perfumer_jean_claude_ellena
François Demachy    -> perfumer_francois_demachy
warm-spicy          -> accord_warm_spicy
white musk          -> note_white_musk
```

Durante la trasformazione viene verificato che gli identificativi generati siano univoci. Eventuali collisioni all'interno della stessa collection vengono gestite tramite un mapping canonico manuale, salvato in:

```text
data/enrichment/canonical_names.json
```

Il mapping canonico non applica accorpamenti automatici basati sulla somiglianza tra stringhe. Serve solo per risolvere manualmente varianti di scrittura che generano lo stesso identificativo tecnico.

Le collisioni vengono controllate separatamente per collection. Non vengono considerate collisioni tra collection diverse, perché gli identificativi usano prefissi differenti, ad esempio `note_` e `accord_`.

---

## Supporto alle funzionalità principali

| Funzionalità | Supporto nel modello |
| --- | --- |
| Consultazione catalogo | dati principali in `perfumes` |
| Ricerca | campi `name`, `brand_id`, `gender`, `year`, `rating`, `all_note_ids`, `accord_ids` |
| CRUD | operazioni principali su `perfumes` e sulle entità collegate |
| JOIN con `$lookup` | riferimenti verso `brands`, `notes`, `accords`, `perfumers` |
| Aggregazioni | campi numerici e riferimenti verso le collection collegate |

---

## Supporto alle funzionalità avanzate

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
notes.olfactory_group
perfumers.nationality
```

### Ricerca di profumi simili

La ricerca di profumi simili sarà basata principalmente su:

```text
all_note_ids
accord_ids
notes.olfactory_group
```

Un criterio preliminare potrà considerare il numero di note e accordi condivisi tra profumi.

### Mini dashboard statistica

La dashboard potrà usare campi come:

```text
rating
votes
brand_id
year
all_note_ids
accord_ids
notes.olfactory_group
perfumers.nationality
```

Statistiche supportabili:

* profumi meglio valutati;
* profumi più votati;
* rating medio per brand;
* note più frequenti;
* accordi più frequenti;
* distribuzione dei profumi per anno;
* distribuzione delle note per gruppo olfattivo;
* distribuzione dei profumieri per nazionalità.
