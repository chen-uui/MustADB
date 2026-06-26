# Rebuilt Index Report

## Rebuild Summary

A new Weaviate collection was created for the manuscript-consistent mpnet embeddings:

- Source collection: `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix`
- Target collection: `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`
- Embedding model: `sentence-transformers/all-mpnet-base-v2`
- Query vector dimension: `768`
- Stored vector dimension sample: `{"default": 768}`

The old collection was not used for dense retrieval after the fix because it stores 384-dimensional vectors.

## Rebuild Method

The rebuild copied real chunk properties from the existing Weaviate collection:

- `content`
- `document_id`
- `title`
- `page_number`
- `chunk_index`

Each chunk was re-embedded with `sentence-transformers/all-mpnet-base-v2` before insertion into the new collection. No stored 384-dimensional vectors were reused.

## Counts

| Item | Count |
|---|---:|
| Source collection objects | 16975 |
| Target collection objects | 16975 |
| Invalid/skipped source objects | 0 |
| Existing target objects before resume | 4640 |
| Newly inserted objects during resume | 12335 |

## Validation

- Target collection exists.
- Target collection object count matches source collection object count.
- Stored vector sample dimension is 768.
- No padding or truncation was used.
- No synthetic `doc_id` values were generated.

## Metadata Artifact

Detailed rebuild metadata is stored in:

`D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\candidate_pool_run\rebuilt_index_metadata.json`
