# Candidate Pool Validation Report

## Run Configuration

- Queries: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\expanded_query_set.jsonl`
- Output directory: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\candidate_pool_run`
- Methods: `bm25`, `dense`, `hybrid`
- Top K per method: `20`
- Collection: `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`
- Dense embedding model: `sentence-transformers/all-mpnet-base-v2`
- Reranker model: `cross-encoder/ms-marco-MiniLM-L-6-v2`

## Vector Validation

| Check | Result |
|---|---:|
| Query vector dimension | 768 |
| Stored vector dimension sample | 768 |
| Target collection objects | 16975 |
| Core retrieval loaded | yes |

## Candidate Pool Outputs

- Candidate pool: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\candidate_pool_run\candidate_pool.jsonl`
- Stats report: `D:\workspace\123\submission_backup\04_eval_benchmarks\retrieval\candidate_pool_run\stats_report.md`

## Candidate Counts

| Metric | Value |
|---|---:|
| Total queries | 45 |
| Total merged candidates | 683 |
| Average candidates/query | 15.178 |
| Minimum candidates/query | 4 |
| Maximum candidates/query | 26 |
| Zero-candidate queries | 0 |

## Method Coverage

| Method | Queries with >=1 candidate | Avg unique docs/query | Corpus-wide unique docs |
|---|---:|---:|---:|
| `bm25` | 45/45 | 6.089 | 123 |
| `dense` | 45/45 | 10.778 | 129 |
| `hybrid` | 45/45 | 9.200 | 143 |

## Merged Candidate Method Distribution

| Method | Candidates |
|---|---:|
| `bm25` | 274 |
| `dense` | 285 |
| `hybrid` | 124 |

## Method Overlap

| Method pair | Avg intersection docs/query | Avg Jaccard/query |
|---|---:|---:|
| `bm25 / dense` | 1.689 | 0.126 |
| `bm25 / hybrid` | 3.933 | 0.378 |
| `dense / hybrid` | 6.844 | 0.541 |

## Conclusion

Dense retrieval has been restored under the manuscript-consistent mpnet model. Hybrid retrieval is not identical to BM25: the average `bm25 / hybrid` Jaccard overlap is `0.378`, and the merged candidate pool contains candidates selected by all three methods.
