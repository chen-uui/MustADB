# revision_qrels_eval_v1_mpnet768

This directory freezes the manuscript-revision retrieval qrels evaluation artifacts for the EOM literature retrieval benchmark.

## Purpose

The archive preserves the mpnet768 retrieval experiment state used for the paper revision. It is intended as a fixed record of the benchmark queries, candidate pool, manual qrels annotation inputs, ranked retrieval outputs, evaluation metrics, and reporting artifacts.

## Frozen Configuration

- Dense embedding model: `sentence-transformers/all-mpnet-base-v2`
- Reranker: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Weaviate collection: `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`
- Query vector dimension: `768`
- Stored vector dimension: `768`

## Inputs

- `expanded_query_set.jsonl`: 45 benchmark queries.
- `candidate_pool.jsonl`: manuscript-consistent candidate pool generated from BM25, dense, and hybrid retrieval.
- `qrels_annotation_template.csv`: qrels annotation template.
- `qrels_relevance_only.csv` and `qrels_annotated_manual_style.csv`: qrels files are now included in this archive.

## Ranked Outputs

- `bm25_results.jsonl`
- `dense_results.jsonl`
- `hybrid_results.jsonl`

These files are the per-method ranked retrieval outputs used for qrels-based evaluation.

## Evaluation Outputs

- `metrics_by_method.csv`
- `per_query_scores.csv`
- `paper_ready_metrics_table.csv`
- `retrieval_evaluation_report.md`

## Key Results

- Benchmark queries: 45
- Qrels total: 683
- Relevant documents (`relevance > 0`): 292
- Highly relevant documents (`relevance = 2`): 144
- Evaluated queries: 45
- Queries without relevant documents: 0

At Recall@10, Hybrid retrieval scored `0.663082`, Dense retrieval scored `0.647050`, and BM25 scored `0.456652`. At nDCG@10, Dense retrieval scored `0.598760`, Hybrid retrieval scored `0.594183`, and BM25 scored `0.490940`.

## Notes

This archive was created by copying and checksumming existing artifacts only. No retrieval experiment, qrels annotation, index build, or metric computation was rerun during archival.
