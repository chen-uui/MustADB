# Frozen End-to-End Evaluation v1

This archive freezes the answer-level end-to-end LLM-only vs RAG baseline evaluation for the paper revision experiment.

## Purpose

The experiment compares five answer-generation settings while holding the local generation model fixed:

- LLM-only
- BM25 + LLM
- dense + LLM
- hybrid + LLM
- hybrid + rerank + LLM

The goal is to test the contribution of retrieval evidence, not the strength of different LLMs.

## Fixed Generation Configuration

- backend: local/Ollama
- generation model: `llama3.1:8b-instruct-q4_K_M`
- temperature: `0`
- top_p: `1`
- max_tokens: `512`
- external API used: no

## Fixed Retrieval Configuration

- dense embedding model: `sentence-transformers/all-mpnet-base-v2`
- vector dimension: `768`
- Weaviate collection: `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`
- reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- rerank input candidate depth: `20`
- final evaluated top-k: `10`

## Outputs

- prompt JSONL files
- generated answer CSV/JSONL files
- manual answer-level annotation files
- paper-ready metrics tables
- evaluation reports and manuscript text draft
- runtime/config freeze files and generation report

## Interpretation

The results should not be framed as RAG outperforming LLM-only in every respect. LLM-only may produce plausible answers, but it lacks document-grounded evidence support. The same local generation model was used across all settings to isolate retrieval evidence contribution. Larger LLMs can be substituted as generation backends in future frozen experiments, while retrieval remains necessary for evidence grounding and auditability.
