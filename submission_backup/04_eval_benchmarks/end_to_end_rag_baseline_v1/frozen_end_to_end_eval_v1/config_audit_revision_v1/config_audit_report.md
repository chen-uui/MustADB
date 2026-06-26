# Configuration Audit Report

Audit date: 2026-06-24

Scope: `.env`, Django/settings defaults, retrieval services, standalone benchmark scripts, Docker/Weaviate/Ollama configuration, and local manuscript `.tex` files. This audit did not run retrieval, rebuild indexes, call an LLM, edit the manuscript, or modify frozen qrels results.

## Confirmed Frozen Experiment Configuration

| Item | Frozen value |
|---|---|
| Dense embedding model | `sentence-transformers/all-mpnet-base-v2` |
| Dense vector dimension | `768` |
| Weaviate collection | `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Rerank input candidate depth | `20` |
| Final evaluated top-k | `10` |
| End-to-end generation backend | local/Ollama |
| Intended end-to-end generation model | `llama3.1:8b-instruct-q4_K_M` |

## Source Files Checked

- `D:/workspace/123/ccc/astrobiology/.env`
- `D:/workspace/123/ccc/astrobiology/.env.template`
- `D:/workspace/123/submission_backup/06_env/.env.template`
- `D:/workspace/123/ccc/astrobiology/docker-compose.yml`
- `D:/workspace/123/submission_backup/06_env/docker-compose.yml`
- `D:/workspace/123/ccc/astrobiology/backend/config/settings.py`
- `D:/workspace/123/ccc/astrobiology/backend/config/django_settings.py`
- `D:/workspace/123/ccc/astrobiology/backend/pdf_processor/pdf_utils.py`
- `D:/workspace/123/ccc/astrobiology/backend/pdf_processor/weaviate_services.py`
- `D:/workspace/123/ccc/astrobiology/backend/pdf_processor/embedding_service.py`
- `D:/workspace/123/ccc/astrobiology/backend/pdf_processor/unified_rag_service.py`
- `D:/workspace/123/ccc/astrobiology/backend/pdf_processor/rag_service.py`
- `D:/workspace/123/ccc/astrobiology/backend/pdf_processor/llama_config.py`
- `D:/workspace/123/submission_backup/04_eval_benchmarks/retrieval/build_retrieval_candidate_pool_standalone.py`
- `D:/workspace/123/submission_backup/04_eval_benchmarks/retrieval/run_qrels_evaluation.py`
- `D:/workspace/123/submission_backup/04_eval_benchmarks/retrieval/evaluation_framework.py`
- `D:/workspace/123/submission_backup/04_eval_benchmarks/end_to_end_rag_baseline_v1/run_end_to_end_baseline_eval.py`
- `D:/workspace/123/supplementary_material.tex`
- `D:/workspace/123/submission_backups/supplementary_material_final/supplementary_material.tex`

Note: only supplementary `.tex` files were visible in the current workspace. They include result tables and examples but do not state the dense embedding model. The method value for `sentence-transformers/all-mpnet-base-v2` is therefore taken from the user-confirmed manuscript statement and the existing local `manuscript_consistency_fix_report.md`.

## Audit Table

| Config item | Current `.env` value | Code/default value | Manuscript/method value | Frozen experiment value | Consistent? | Risk | Recommendation |
|---|---|---|---|---|---|---|---|
| Dense embedding model | `sentence-transformers/all-mpnet-base-v2` | `settings.py`, `django_settings.py`, `pdf_utils.py`, standalone script default to `sentence-transformers/all-mpnet-base-v2` | `sentence-transformers/all-mpnet-base-v2` | `sentence-transformers/all-mpnet-base-v2` | Yes | Low | Keep unchanged. |
| Dense vector dimension | not explicit | `pdf_utils.GlobalConfig.EMBEDDING_DIMENSION = 768`; validated rebuilt index report says query/stored vectors are 768 | 768 implied by mpnet | 768 | Yes | Low | Keep as frozen metadata; no index rebuild. |
| Active Weaviate collection | `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768` | standalone retrieval script default is mpnet768; `weaviate_services.py` and `unified_rag_service.py` fallback to `PDFDocument` if env/argument missing | mpnet768 collection required for 768 vectors | `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768` | Partially | High | Do not change now. For future experimental scripts, require explicit `--collection-name` or freeze-file loading; do not rely on service fallback. |
| Weaviate host/port | `localhost:8080` | settings defaults `localhost:8080`; Docker maps `${WEAVIATE_PORT:-8080}:8080` | local Weaviate | `localhost:8080` | Yes | Low | Keep. |
| Weaviate vectorizer | not in `.env` | code creates collection with `Vectorizer.none()`; Docker enables `text2vec-transformers` module | explicit vectors from mpnet rebuild | `none` for benchmark collection | Partially | Medium | Avoid creating benchmark collections through Docker module auto-vectorization; keep explicit-vector collection creation for experiments. |
| Docker transformer image default | not direct; `.env` sets full `sentence-transformers/all-mpnet-base-v2` | active `ccc/astrobiology/docker-compose.yml` uses `sentence-transformers-${EMBEDDING_MODEL:-all-mpnet-base-v2}`; backup `submission_backup/06_env/docker-compose.yml` still defaults to `all-MiniLM-L6-v2` | mpnet | mpnet | Partially | Medium | Do not edit during audit. Later align backup/template Docker defaults to mpnet or document them as historical snapshots. |
| `.env.template` embedding model | not applicable | both `ccc/astrobiology/.env.template` and `submission_backup/06_env/.env.template` still use `EMBEDDING_MODEL=all-MiniLM-L6-v2` and chunk `1600/400` | mpnet; chunk `700/80` for rebuilt collection | mpnet; chunk `700/80` | No | High | Must not affect current frozen run, but future users copying templates could reproduce the wrong setup. Update templates only after approval. |
| Chunk size / overlap | `700` / `80` | `pdf_utils.py`, `django_settings.py` defaults `700` / `80`; templates still `1600` / `400` | collection name and reports indicate `700_80` | `700` / `80` | Partially | Medium | Runtime is aligned; templates should be corrected later or marked historical. |
| Reranker model | not set as `RERANKER_MODEL` in `.env` | settings and standalone defaults use `cross-encoder/ms-marco-MiniLM-L-6-v2` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Yes by default | Low | Optional: add explicit `RERANKER_MODEL` to experimental environment/freeze wrapper for clarity. |
| Hybrid alpha | not set | `UnifiedRAGService.DEFAULT_HYBRID_ALPHA = 0.7` | hybrid alpha 0.7 in prior experiments/supplement table | 0.7 | Yes by default | Low | Keep. Record explicitly in freeze file. |
| Candidate pool top-k | not set | `build_retrieval_candidate_pool_standalone.py` default `20` | BM25/dense/hybrid top-20 candidate pool | 20 | Yes | Low | Keep. |
| Rerank candidate depth | not set | `UnifiedRAGService` default rerank_k is `top_k * 2`; rerank export metadata says depth 20 | 20 | 20 | Yes for top_k=10 | Medium | Future rerank export should pass or record `rerank_k=20` explicitly; otherwise changes to final top-k alter depth. |
| Final evaluated top-k | not in `.env` | evaluation metrics use cutoffs `1,3,5,10`; rerank metadata `final_top_k=10` | 10 | 10 | Yes | Low | Keep. |
| Retrieval evaluation cutoffs | not in `.env` | `evaluation_framework.DEFAULT_KS = (1,3,5,10)` | Recall/nDCG at 1,3,5,10; MRR@10 | 1,3,5,10 | Yes | Low | Keep. |
| Local LLM backend | `OLLAMA_HOST=localhost`, `OLLAMA_PORT=11434` | settings default `OLLAMA_BASE_URL=http://localhost:11434`; code calls Ollama API | local/Ollama | local/Ollama | Yes | Low | Keep backend local. |
| Local generation model | `.env` has `LLM_MODEL=llama3.1:8b`; no `OLLAMA_MODEL` | settings default `OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M`; `rag_service.py`, `unified_rag_service.py`, startup checks hardcode/use `llama3.1:8b-instruct-q4_K_M`; end-to-end prompt prep records only `local LLM configured externally` | `llama3.1:8b-instruct-q4_K_M` | `llama3.1:8b-instruct-q4_K_M` | No | High | Do not edit `.env` in this audit. Before running end-to-end generation, explicitly set/pass the intended model and record it in outputs. Prefer adding an experiment-only runner option rather than relying on `LLM_MODEL`. |
| LLM temperature | `0.1` | `.env` has `LLM_TEMPERATURE=0.1`; OpenAI fallback temperature is 0.7; Ollama generation code appears hardcoded in service calls | not specified except local baseline needs same settings | 0.1 intended | Partially | Medium | For end-to-end baseline, set temperature explicitly in the generation runner and manifest. |
| LLM max tokens | `4096` | `.env` `LLM_MAX_TOKENS=4096`; service code may have hardcoded request options; `pdf_utils.MAX_ANSWER_LENGTH=4000` | not specified | 4096 intended | Partially | Medium | Record exact generation limit in end-to-end manifest before answer generation. |
| OpenAI fallback | placeholder key; `OPENAI_MODEL=gpt-3.5-turbo` | settings include OpenAI fallback config | not used; local/Ollama required | disabled/not used | Partially | Medium | Ensure end-to-end script never falls back to OpenAI; keep `external_api_allowed=false` in freeze file. |
| End-to-end prompt evidence top-k | not set | prompt prep script default `--evidence-top-k 5` | not a retrieval qrels metric; generation design choice | 5 in prepared prompts | Yes for current prepared prompts | Low | Keep for prepared prompts; if changed later, regenerate prompt files in a new versioned directory. |

## Findings

1. High risk: the runtime `.env` has `LLM_MODEL=llama3.1:8b`, while the intended end-to-end baseline generation model is `llama3.1:8b-instruct-q4_K_M`. Existing service code often uses `OLLAMA_MODEL` or hardcoded `llama3.1:8b-instruct-q4_K_M`, so the actual effect depends on the runner. This must be pinned before generation.

2. High risk: service fallback collection names remain generic (`PDFDocument`) when no collection argument or `WEAVIATE_COLLECTION_NAME` is present. Current `.env` and standalone scripts are aligned, but future runs without env loading could silently use the wrong collection.

3. High risk: `.env.template` files still contain `EMBEDDING_MODEL=all-MiniLM-L6-v2` and chunking `1600/400`, inconsistent with the mpnet768 `700/80` experiment. These are templates, not the current runtime `.env`, but they are risky for reproducibility.

4. Medium risk: `submission_backup/06_env/docker-compose.yml` still defaults the transformer image to `all-MiniLM-L6-v2`, while the active `ccc/astrobiology/docker-compose.yml` defaults to `all-mpnet-base-v2`. If the backup compose file is used to reproduce the revision experiment, it can recreate the earlier mismatch.

5. Medium risk: rerank candidate depth is correct in the generated metadata (`20`), but one service default computes rerank depth as `top_k * 2`. This is consistent for final top-k 10, but should be explicitly pinned in any future rerank export script.

6. Low risk: retrieval metrics defaults are aligned with the paper revision evaluation: Recall/nDCG at K = 1,3,5,10 and MRR@10.

7. Low risk: embedding model, vector dimension, active mpnet768 collection, chunk size/overlap, reranker, hybrid alpha, and candidate pool top-k are aligned in the current runtime `.env`, current settings defaults, and frozen experiment artifacts.

## Manuscript Cross-Check

Visible local `.tex` files:

- `D:/workspace/123/supplementary_material.tex`
- `D:/workspace/123/submission_backups/supplementary_material_final/supplementary_material.tex`

These files include retrieval/manual-evaluation tables and examples but do not include the dense embedding model statement. The audit therefore uses:

- user-confirmed method statement: dense embeddings generated with `sentence-transformers/all-mpnet-base-v2`;
- local `manuscript_consistency_fix_report.md`, which records the same method statement and the mpnet768 rebuild.

No manuscript files were edited.
