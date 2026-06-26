# Candidate Pool Statistics

- generated_at: `2026-06-24T13:23:11`
- queries_path: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\expanded_query_set.jsonl`
- candidate_pool_path: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\candidate_pool_run\candidate_pool.jsonl`
- methods: `bm25, dense, hybrid`
- top_k_per_method: `20`
- collection_name: `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`
- core_retrieval_loaded: `yes`
- fallback_mode: `auto`

## Candidate Size

- total_queries: `45`
- avg_candidate_size_per_query: `15.178`
- median_candidate_size_per_query: `16.000`
- min_candidate_size: `4`
- max_candidate_size: `26`
- avg_pool_fill_ratio_vs_60_max: `0.253`
- zero_candidate_queries: `0`

## Overlap Between Methods

| Method pair | Avg intersection docs/query | Avg Jaccard/query |
|---|---:|---:|
| `bm25 / dense` | 1.689 | 0.126 |
| `bm25 / hybrid` | 3.933 | 0.378 |
| `dense / hybrid` | 6.844 | 0.541 |

## Coverage Analysis

| Method | Queries with >=1 candidate | Avg unique docs/query | Corpus-wide unique docs |
|---|---:|---:|---:|
| `bm25` | 45/45 | 6.089 | 123 |
| `dense` | 45/45 | 10.778 | 129 |
| `hybrid` | 45/45 | 9.200 | 143 |

- corpus_wide_unique_candidate_docs: `185`
- queries_with_any_candidate: `45/45`

## Warnings

- none
