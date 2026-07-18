/*
 * Aggregation Pipeline della Issue 9.
 *
 * Lo script esegue:
 *   1. dettaglio completo di un profumo;
 *   2. classifica dei profumi meglio valutati;
 *   3. statistiche aggregate per brand;
 *   4. classifica delle note olfattive più frequenti.
 *
 * Il profumo usato nella prima pipeline viene selezionato automaticamente
 * tra i documenti presenti nella collection perfumes.
 *
 * Esecuzione tramite il container MongoDB:
 *
 *   docker cp .\queries\issue-09-aggregations.js \
 *     scentbase-mongodb:/tmp/issue-09-aggregations.js
 *
 *   docker exec -it scentbase-mongodb mongosh \
 *     "mongodb://scentbase_admin:change_me@localhost:27017/admin" \
 *     /tmp/issue-09-aggregations.js
 */

const databaseName = "scentbase";
const limit = 10;
const minVotes = 100;

const scentbaseDb = db.getSiblingDB(databaseName);

const samplePerfume = scentbaseDb.perfumes.findOne(
    {},
    {
        _id: 1
    }
);

if (samplePerfume === null) {
    throw new Error(
        `Nessun profumo presente nel database '${databaseName}'`
    );
}

const perfumeId = samplePerfume._id;


/**
 * Restituisce il primo documento prodotto da un lookup.
 *
 * Se il lookup non ha trovato documenti, restituisce null.
 */
function firstDocumentOrNull(lookupResultField) {
    return {
        $ifNull: [
            {
                $arrayElemAt: [
                    `$${lookupResultField}`,
                    0
                ]
            },
            null
        ]
    };
}


/**
 * Ricostruisce un array di documenti collegati conservando l'ordine
 * degli identificativi presenti nel documento perfume.
 *
 * MongoDB non garantisce che l'array prodotto da $lookup mantenga
 * l'ordine dell'array locale. Per questo vengono usati $map e $filter.
 */
function orderedDocuments(
    idArrayField,
    lookupResultField
) {
    return {
        $filter: {
            input: {
                $map: {
                    input: {
                        $ifNull: [
                            `$${idArrayField}`,
                            []
                        ]
                    },
                    as: "reference_id",
                    in: {
                        $arrayElemAt: [
                            {
                                $filter: {
                                    input: {
                                        $ifNull: [
                                            `$${lookupResultField}`,
                                            []
                                        ]
                                    },
                                    as: "linked_document",
                                    cond: {
                                        $eq: [
                                            "$$linked_document._id",
                                            "$$reference_id"
                                        ]
                                    }
                                }
                            },
                            0
                        ]
                    }
                }
            },
            as: "linked_document",
            cond: {
                $ne: [
                    "$$linked_document",
                    null
                ]
            }
        }
    };
}


print(
    "\n============================================================"
);

print(
    "1. DETTAGLIO COMPLETO DEL PROFUMO"
);

print(
    `Database: ${databaseName}`
);

print(
    `Profumo selezionato: ${perfumeId}`
);

print(
    "============================================================\n"
);

printjson(
    scentbaseDb.perfumes.aggregate(
        [
            {
                $match: {
                    _id: perfumeId
                }
            },
            {
                $lookup: {
                    from: "brands",
                    localField: "brand_id",
                    foreignField: "_id",
                    as: "_brand_documents"
                }
            },
            {
                $lookup: {
                    from: "notes",
                    localField: "all_note_ids",
                    foreignField: "_id",
                    as: "_note_documents"
                }
            },
            {
                $lookup: {
                    from: "accords",
                    localField: "accord_ids",
                    foreignField: "_id",
                    as: "_accord_documents"
                }
            },
            {
                $lookup: {
                    from: "perfumers",
                    localField: "perfumer_ids",
                    foreignField: "_id",
                    as: "_perfumer_documents"
                }
            },
            {
                $set: {
                    brand: firstDocumentOrNull(
                        "_brand_documents"
                    ),
                    top_notes: orderedDocuments(
                        "top_note_ids",
                        "_note_documents"
                    ),
                    middle_notes: orderedDocuments(
                        "middle_note_ids",
                        "_note_documents"
                    ),
                    base_notes: orderedDocuments(
                        "base_note_ids",
                        "_note_documents"
                    ),
                    accords: orderedDocuments(
                        "accord_ids",
                        "_accord_documents"
                    ),
                    perfumers: orderedDocuments(
                        "perfumer_ids",
                        "_perfumer_documents"
                    )
                }
            },
            {
                $project: {
                    _brand_documents: 0,
                    _note_documents: 0,
                    _accord_documents: 0,
                    _perfumer_documents: 0
                }
            }
        ]
    ).toArray()
);


print(
    "\n============================================================"
);

print(
    "2. PROFUMI MEGLIO VALUTATI"
);

print(
    `Limite: ${limit} - Voti minimi: ${minVotes}`
);

print(
    "============================================================\n"
);

printjson(
    scentbaseDb.perfumes.aggregate(
        [
            {
                $match: {
                    rating: {
                        $ne: null
                    },
                    votes: {
                        $gte: minVotes
                    }
                }
            },
            {
                $sort: {
                    rating: -1,
                    votes: -1,
                    _id: 1
                }
            },
            {
                $limit: limit
            },
            {
                $lookup: {
                    from: "brands",
                    localField: "brand_id",
                    foreignField: "_id",
                    as: "_brand_documents"
                }
            },
            {
                $set: {
                    brand: firstDocumentOrNull(
                        "_brand_documents"
                    )
                }
            },
            {
                $project: {
                    _brand_documents: 0
                }
            }
        ]
    ).toArray()
);


print(
    "\n============================================================"
);

print(
    "3. STATISTICHE PER BRAND"
);

print(
    `Numero massimo di brand restituiti: ${limit}`
);

print(
    "============================================================\n"
);

printjson(
    scentbaseDb.perfumes.aggregate(
        [
            {
                $group: {
                    _id: "$brand_id",
                    perfume_count: {
                        $sum: 1
                    },
                    rated_perfume_count: {
                        $sum: {
                            $cond: [
                                {
                                    $ne: [
                                        {
                                            $ifNull: [
                                                "$rating",
                                                null
                                            ]
                                        },
                                        null
                                    ]
                                },
                                1,
                                0
                            ]
                        }
                    },
                    average_rating: {
                        $avg: "$rating"
                    }
                }
            },
            {
                $lookup: {
                    from: "brands",
                    localField: "_id",
                    foreignField: "_id",
                    as: "_brand_documents"
                }
            },
            {
                $set: {
                    brand: firstDocumentOrNull(
                        "_brand_documents"
                    )
                }
            },
            {
                $sort: {
                    average_rating: -1,
                    perfume_count: -1,
                    _id: 1
                }
            },
            {
                $limit: limit
            },
            {
                $project: {
                    _id: 0,
                    _brand_documents: 0
                }
            }
        ]
    ).toArray()
);


print(
    "\n============================================================"
);

print(
    "4. NOTE OLFATTIVE PIÙ FREQUENTI"
);

print(
    `Numero massimo di note restituite: ${limit}`
);

print(
    "============================================================\n"
);

printjson(
    scentbaseDb.perfumes.aggregate(
        [
            {
                $project: {
                    all_note_ids: {
                        $ifNull: [
                            "$all_note_ids",
                            []
                        ]
                    }
                }
            },
            {
                $unwind: "$all_note_ids"
            },
            {
                $group: {
                    _id: "$all_note_ids",
                    perfume_count: {
                        $sum: 1
                    }
                }
            },
            {
                $lookup: {
                    from: "notes",
                    localField: "_id",
                    foreignField: "_id",
                    as: "_note_documents"
                }
            },
            {
                $set: {
                    note: firstDocumentOrNull(
                        "_note_documents"
                    )
                }
            },
            {
                $sort: {
                    perfume_count: -1,
                    _id: 1
                }
            },
            {
                $limit: limit
            },
            {
                $project: {
                    _id: 0,
                    _note_documents: 0
                }
            }
        ]
    ).toArray()
);


print(
    "\n============================================================"
);

print(
    "ESECUZIONE COMPLETATA"
);

print(
    "============================================================\n"
);