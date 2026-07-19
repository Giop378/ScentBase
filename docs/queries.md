# Query e aggregazioni MongoDB

Questo documento descrive le principali Aggregation Pipeline utilizzate dal backend di ScentBase.

## Dettaglio completo del profumo

L'endpoint:

```text
GET /perfumes/{perfume_id}/details
```

recupera un profumo e ne espande i riferimenti verso le collection `brands`, `notes`, `accords` e `perfumers`.

La pipeline utilizza:

- `$match` per selezionare il profumo;
- `$lookup` per recuperare i documenti collegati;
- `$set` per aggiungere i dati espansi;
- `$map` e `$filter` per mantenere l'ordine originale degli identificativi;
- `$project` per rimuovere i campi temporanei.

Le note restano separate in `top_notes`, `middle_notes` e `base_notes`. I riferimenti assenti vengono restituiti come array vuoti.

## Profumi meglio valutati

L'endpoint:

```text
GET /statistics/top-perfumes
```

seleziona i profumi con almeno il numero di voti indicato da `min_votes`, li ordina per rating decrescente, voti decrescenti e `_id`, quindi applica `limit`.

Il brand viene espanso tramite `$lookup`.

## Statistiche per brand

L'endpoint:

```text
GET /statistics/brands
```

raggruppa i profumi per `brand_id` e calcola:

- numero totale di profumi;
- numero di profumi dotati di rating;
- rating medio.

I rating mancanti non partecipano alla media. Il documento del brand viene aggiunto tramite `$lookup`.

## Note olfattive più frequenti

L'endpoint:

```text
GET /statistics/notes
```

usa `$unwind` per separare gli elementi di `all_note_ids`, `$group` per contarne le occorrenze e `$lookup` per espandere i dati della nota.

I risultati sono ordinati per frequenza decrescente e `_id`.

## Ricerca di profumi simili

L'endpoint:

```text
GET /perfumes/{perfume_id}/similar
```

restituisce i profumi maggiormente simili a quello indicato, confrontando le note olfattive e gli accordi principali.

Il parametro opzionale:

```text
limit
```

stabilisce il numero massimo di risultati restituiti. Il valore predefinito è `10` e sono accettati valori compresi tra `1` e `50`.

### Selezione dei candidati

Prima di calcolare la similarità completa, la pipeline seleziona soltanto i profumi che condividono almeno una nota oppure un accordo con il profumo sorgente.

Il profumo sorgente viene sempre escluso dai risultati.

Questa preselezione riduce il numero di documenti sui quali eseguire i calcoli e rende la query adatta a beneficiare dei futuri indici multikey sui campi `all_note_ids` e `accord_ids`.

### Calcolo della similarità

La similarità viene calcolata separatamente per note e accordi mediante l'indice di Jaccard:

```text
Jaccard(A, B) = |A ∩ B| / |A ∪ B|
```

Per le note:

```text
note_similarity =
    note condivise / note complessive distinte
```

Per gli accordi:

```text
accord_similarity =
    accordi condivisi / accordi complessivi distinti
```

Lo score finale assegna un peso maggiore alle note olfattive, che rappresentano una descrizione più dettagliata della composizione del profumo:

```text
similarity_score =
    0.7 × note_similarity
  + 0.3 × accord_similarity
```

Quando l'unione delle note o degli accordi è vuota, la componente corrispondente assume valore `0`, evitando divisioni per zero.

I candidati con `similarity_score` uguale a zero non vengono restituiti.

### Stage e operatori utilizzati

La pipeline utilizza principalmente:

- `$match` per escludere il profumo sorgente e preselezionare i candidati;
- `$ifNull` per gestire array assenti o nulli;
- `$setIntersection` e `$setUnion` per calcolare intersezioni e unioni;
- `$size`, `$divide`, `$multiply` e `$add` per calcolare le componenti dello score;
- `$cond` per gestire gli insiemi vuoti;
- `$sort` e `$limit` per ordinare e limitare i risultati;
- `$lookup` per espandere brand, note condivise e accordi condivisi;
- `$map` e `$filter` per conservare l'ordine degli identificativi;
- `$project` per rimuovere i campi temporanei.

### Ordinamento dei risultati

I risultati vengono ordinati in modo deterministico secondo i seguenti criteri:

1. `similarity_score` decrescente;
2. `rating` decrescente;
3. `votes` decrescente;
4. `_id` crescente.

Rating e numero di voti non partecipano al calcolo della similarità, ma vengono utilizzati soltanto per risolvere eventuali parità.

### Struttura della risposta

Per ogni profumo simile vengono restituiti:

- identificativo e dati principali del profumo;
- brand espanso;
- `shared_note_ids`;
- `shared_accord_ids`;
- documenti delle note condivise;
- documenti degli accordi condivisi;
- `note_similarity`;
- `accord_similarity`;
- `similarity_score`.

La risposta include inoltre:

- identificativo del profumo sorgente;
- pesi utilizzati;
- valore di `limit`;
- lista ordinata dei risultati.

### Limiti dell'approccio

La similarità considera esclusivamente la presenza delle note e degli accordi e non tiene conto:

- della posizione delle note nella piramide olfattiva;
- dell'intensità o della quantità delle singole componenti;
- del brand;
- del genere;
- del profumiere;
- dell'anno;
- del rating;
- della descrizione testuale del profumo.

Non vengono utilizzati embedding, modelli di machine learning o database vettoriali. La soluzione è intenzionalmente semplice, interpretabile e coerente con i dati strutturati disponibili nel database.

