/*
 * Aggregation Pipeline della Issue 10.
 *
 * Lo script seleziona automaticamente un profumo che possiede almeno un
 * candidato simile e calcola una classifica basata su:
 *
 *   - similarità di Jaccard sulle note, peso 0.7;
 *   - similarità di Jaccard sugli accordi, peso 0.3.
 *
 * Esecuzione tramite il container MongoDB:
 *
 *   docker cp .\queries\issue-10-similar-perfumes.js \
 *     scentbase-mongodb:/tmp/issue-10-similar-perfumes.js
 *
 *   docker exec -it scentbase-mongodb mongosh \
 *     "mongodb://scentbase_admin:change_me@localhost:27017/admin" \
 *     /tmp/issue-10-similar-perfumes.js
 */

const databaseName = "scentbase";
const limit = 10;
const noteWeight = 0.7;
const accordWeight = 0.3;

const scentbaseDb = db.getSiblingDB(databaseName);


/** Rimuove i duplicati mantenendo l'ordine originale. */
function uniqueValues(values) {
    if (!Array.isArray(values)) {
        return [];
    }

    return [...new Set(values)];
}


/** Restituisce il primo documento prodotto da un lookup oppure null. */
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
 * Ricostruisce i documenti collegati rispettando l'ordine degli ID.
 */
function orderedDocuments(idArrayField, lookupResultField) {
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


/**
 * Ordina gli ID condivisi secondo l'ordine del profumo sorgente.
 */
function orderedSharedIds(sourceIds, intersectionField) {
    return {
        $filter: {
            input: sourceIds,
            as: "reference_id",
            cond: {
                $in: [
                    "$$reference_id",
                    `$${intersectionField}`
                ]
            }
        }
    };
}


/** Calcola Jaccard, restituendo zero quando l'unione è vuota. */
function jaccardSimilarity(sharedIdsField, unionIdsField) {
    return {
        $cond: [
            {
                $gt: [
                    {
                        $size: `$${unionIdsField}`
                    },
                    0
                ]
            },
            {
                $divide: [
                    {
                        $size: `$${sharedIdsField}`
                    },
                    {
                        $size: `$${unionIdsField}`
                    }
                ]
            },
            0
        ]
    };
}


/**
 * Cerca un profumo con almeno un altro documento che condivida una nota
 * oppure un accordo, così lo script produce un output significativo.
 */
function findSourcePerfume() {
    const possibleSources = scentbaseDb.perfumes.find(
        {
            $or: [
                {
                    "all_note_ids.0": {
                        $exists: true
                    }
                },
                {
                    "accord_ids.0": {
                        $exists: true
                    }
                }
            ]
        },
        {
            _id: 1,
            name: 1,
            all_note_ids: 1,
            accord_ids: 1
        }
    ).limit(500).toArray();

    for (const possibleSource of possibleSources) {
        const sourceNoteIds = uniqueValues(
            possibleSource.all_note_ids
        );
        const sourceAccordIds = uniqueValues(
            possibleSource.accord_ids
        );

        const overlapConditions = [];

        if (sourceNoteIds.length > 0) {
            overlapConditions.push(
                {
                    all_note_ids: {
                        $in: sourceNoteIds
                    }
                }
            );
        }

        if (sourceAccordIds.length > 0) {
            overlapConditions.push(
                {
                    accord_ids: {
                        $in: sourceAccordIds
                    }
                }
            );
        }

        const similarCandidate = scentbaseDb.perfumes.findOne(
            {
                _id: {
                    $ne: possibleSource._id
                },
                $or: overlapConditions
            },
            {
                _id: 1
            }
        );

        if (similarCandidate !== null) {
            return {
                ...possibleSource,
                all_note_ids: sourceNoteIds,
                accord_ids: sourceAccordIds
            };
        }
    }

    return null;
}


const sourcePerfume = findSourcePerfume();

if (sourcePerfume === null) {
    throw new Error(
        `Nessun profumo con candidati simili nel database '${databaseName}'`
    );
}

const sourcePerfumeId = sourcePerfume._id;
const sourceNoteIds = sourcePerfume.all_note_ids;
const sourceAccordIds = sourcePerfume.accord_ids;

const similarityPipeline = [
    {
        $match: {
            _id: {
                $ne: sourcePerfumeId
            },
            $or: [
                {
                    all_note_ids: {
                        $in: sourceNoteIds
                    }
                },
                {
                    accord_ids: {
                        $in: sourceAccordIds
                    }
                }
            ]
        }
    },
    {
        $set: {
            _candidate_note_ids: {
                $ifNull: [
                    "$all_note_ids",
                    []
                ]
            },
            _candidate_accord_ids: {
                $ifNull: [
                    "$accord_ids",
                    []
                ]
            }
        }
    },
    {
        $set: {
            _shared_note_id_set: {
                $setIntersection: [
                    sourceNoteIds,
                    "$_candidate_note_ids"
                ]
            },
            _shared_accord_id_set: {
                $setIntersection: [
                    sourceAccordIds,
                    "$_candidate_accord_ids"
                ]
            },
            _note_union_ids: {
                $setUnion: [
                    sourceNoteIds,
                    "$_candidate_note_ids"
                ]
            },
            _accord_union_ids: {
                $setUnion: [
                    sourceAccordIds,
                    "$_candidate_accord_ids"
                ]
            }
        }
    },
    {
        $set: {
            shared_note_ids: orderedSharedIds(
                sourceNoteIds,
                "_shared_note_id_set"
            ),
            shared_accord_ids: orderedSharedIds(
                sourceAccordIds,
                "_shared_accord_id_set"
            )
        }
    },
    {
        $set: {
            _note_similarity: jaccardSimilarity(
                "shared_note_ids",
                "_note_union_ids"
            ),
            _accord_similarity: jaccardSimilarity(
                "shared_accord_ids",
                "_accord_union_ids"
            )
        }
    },
    {
        $set: {
            _similarity_score: {
                $add: [
                    {
                        $multiply: [
                            "$_note_similarity",
                            noteWeight
                        ]
                    },
                    {
                        $multiply: [
                            "$_accord_similarity",
                            accordWeight
                        ]
                    }
                ]
            }
        }
    },
    {
        $match: {
            _similarity_score: {
                $gt: 0
            }
        }
    },
    {
        $sort: {
            _similarity_score: -1,
            rating: -1,
            votes: -1,
            _id: 1
        }
    },
    {
        $limit: limit
    },
    {
        $set: {
            note_similarity: {
                $round: [
                    "$_note_similarity",
                    6
                ]
            },
            accord_similarity: {
                $round: [
                    "$_accord_similarity",
                    6
                ]
            },
            similarity_score: {
                $round: [
                    "$_similarity_score",
                    6
                ]
            }
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
            localField: "shared_note_ids",
            foreignField: "_id",
            as: "_shared_note_documents"
        }
    },
    {
        $lookup: {
            from: "accords",
            localField: "shared_accord_ids",
            foreignField: "_id",
            as: "_shared_accord_documents"
        }
    },
    {
        $set: {
            brand: firstDocumentOrNull(
                "_brand_documents"
            ),
            shared_notes: orderedDocuments(
                "shared_note_ids",
                "_shared_note_documents"
            ),
            shared_accords: orderedDocuments(
                "shared_accord_ids",
                "_shared_accord_documents"
            )
        }
    },
    {
        $project: {
            _candidate_note_ids: 0,
            _candidate_accord_ids: 0,
            _shared_note_id_set: 0,
            _shared_accord_id_set: 0,
            _note_union_ids: 0,
            _accord_union_ids: 0,
            _note_similarity: 0,
            _accord_similarity: 0,
            _similarity_score: 0,
            _brand_documents: 0,
            _shared_note_documents: 0,
            _shared_accord_documents: 0
        }
    }
];

print(
    "\n============================================================"
);
print(
    "RICERCA DI PROFUMI SIMILI"
);
print(
    `Database: ${databaseName}`
);
print(
    `Profumo sorgente: ${sourcePerfumeId} - ${sourcePerfume.name}`
);
print(
    `Pesi: note ${noteWeight}, accordi ${accordWeight}`
);
print(
    `Limite: ${limit}`
);
print(
    "============================================================\n"
);

const results = scentbaseDb.perfumes.aggregate(
    similarityPipeline
).toArray();

printjson(results);

print(
    "\n============================================================"
);
print(
    `RISULTATI RESTITUITI: ${results.length}`
);
print(
    "ESECUZIONE COMPLETATA"
);
print(
    "============================================================\n"
);