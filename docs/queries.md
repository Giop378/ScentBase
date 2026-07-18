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
