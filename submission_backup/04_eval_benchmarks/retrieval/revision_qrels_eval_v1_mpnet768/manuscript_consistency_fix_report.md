# Manuscript Consistency Fix Report

## Objective

Align the retrieval benchmark implementation with the manuscript method statement:

- Dense embedding model: `sentence-transformers/all-mpnet-base-v2`
- Reranker model: `cross-encoder/ms-marco-MiniLM-L-6-v2`

The manuscript text was not modified.

## Root Cause

The manuscript specifies `sentence-transformers/all-mpnet-base-v2`, which produces 768-dimensional embeddings. The existing Weaviate benchmark collection contained 384-dimensional vectors generated with `all-MiniLM-L6-v2`. This caused dense retrieval failures whenever the query side used mpnet embeddings.

The dense and reranker models are separate:

- Dense retrieval now uses `sentence-transformers/all-mpnet-base-v2`.
- Reranking remains `cross-encoder/ms-marco-MiniLM-L-6-v2`.

No vector truncation, padding, or synthetic document IDs were used.

## Configuration Sources Checked

| Source | Status |
|---|---|
| `.env` | Updated `EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2`; added `WEAVIATE_COLLECTION_NAME=PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`. |
| Django settings | Existing defaults in `config/settings.py` and `config/django_settings.py` already point to `sentence-transformers/all-mpnet-base-v2`. |
| Standalone candidate pool script | Default collection updated to the mpnet/768 collection; shim already resolves `EMBEDDING_MODEL_NAME`, then `EMBEDDING_MODEL`, then mpnet default. |
| Ingestion/indexing config | `WeaviateConfig.embedding_model` default updated to `sentence-transformers/all-mpnet-base-v2`. |
| Retrieval service | Uses shared `EmbeddingService`; verified query embeddings are 768-dimensional after config fix. |
| Weaviate collection creation | Uses `Vectorizer.none()` and stores explicitly generated vectors; no fixed fake dimension is configured. |
| Docker transformer default | Updated default from MiniLM to mpnet to avoid future environment drift. |

## Modified Files

- `D:\workspace\123\ccc\astrobiology\.env`
- `D:\workspace\123\ccc\astrobiology\docker-compose.yml`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\weaviate_services.py`
- `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\build_retrieval_candidate_pool_standalone.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\build_retrieval_candidate_pool.py`
- `D:\workspace\123\ccc\astrobiology\backend\pdf_processor\management\commands\export_retrieval_qrels_expansion_pack.py`

## Final State

- Dense embedding model: `sentence-transformers/all-mpnet-base-v2`
- Query embedding dimension: `768`
- Active benchmark collection: `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`
- Stored vector dimension in active collection: `768`
- Benchmark schema unchanged.
- Evaluation metrics unchanged.
