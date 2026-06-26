# End-to-End Answer-Level Evaluation Report

## Inputs

- annotated_file: `D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\answer_level_evaluation\answer_level_evaluation_annotated_manual_style.csv`
- total rows: `100`
- required fields missing: `[]`

## Validation

- expected rows: `100`
- observed rows: `100`
- pipelines observed: `{'llm_only': 20, 'bm25_rag': 20, 'dense_rag': 20, 'hybrid_rag': 20, 'hybrid_rerank_rag': 20}`
- each pipeline has 20 rows: `True`
- label columns complete and legal after binary normalization: `true`
- empty label cells: `0`
- illegal label cells: `0`
- binary labels normalized for metrics: `0.0/1.0 -> 0/1`
- missing generated answers: `0`
- missing evidence rows: `20`
- RAG missing evidence rows: `0`

## Metrics By Pipeline

| pipeline | n | fully supported | partially supported | unsupported | answer correct | evidence mismatch | hallucination flag |
|---|---:|---:|---:|---:|---:|---:|---:|
| `llm_only` | 20 | 0 (0.0%) | 0 (0.0%) | 20 (100.0%) | 18 (90.0%) | 0 (0.0%) | 20 (100.0%) |
| `bm25_rag` | 20 | 7 (35.0%) | 11 (55.0%) | 2 (10.0%) | 11 (55.0%) | 2 (10.0%) | 2 (10.0%) |
| `dense_rag` | 20 | 4 (20.0%) | 15 (75.0%) | 1 (5.0%) | 16 (80.0%) | 3 (15.0%) | 2 (10.0%) |
| `hybrid_rag` | 20 | 5 (25.0%) | 14 (70.0%) | 1 (5.0%) | 10 (50.0%) | 5 (25.0%) | 3 (15.0%) |
| `hybrid_rerank_rag` | 20 | 7 (35.0%) | 11 (55.0%) | 2 (10.0%) | 11 (55.0%) | 1 (5.0%) | 1 (5.0%) |

## Partially Supported Subtype Distribution

| pipeline | subtype | count | pct of pipeline | pct of partial |
|---|---|---:|---:|---:|
| `bm25_rag` | `missing_detail` | 4 | 20.0% | 36.4% |
| `bm25_rag` | `weak_evidence_match` | 6 | 30.0% | 54.5% |
| `bm25_rag` | `mixed` | 1 | 5.0% | 9.1% |
| `dense_rag` | `missing_detail` | 5 | 25.0% | 33.3% |
| `dense_rag` | `weak_evidence_match` | 5 | 25.0% | 33.3% |
| `dense_rag` | `over_generalization` | 2 | 10.0% | 13.3% |
| `dense_rag` | `mixed` | 3 | 15.0% | 20.0% |
| `hybrid_rag` | `missing_detail` | 2 | 10.0% | 14.3% |
| `hybrid_rag` | `weak_evidence_match` | 6 | 30.0% | 42.9% |
| `hybrid_rag` | `over_generalization` | 2 | 10.0% | 14.3% |
| `hybrid_rag` | `mixed` | 4 | 20.0% | 28.6% |
| `hybrid_rerank_rag` | `missing_detail` | 3 | 15.0% | 27.3% |
| `hybrid_rerank_rag` | `weak_evidence_match` | 5 | 25.0% | 45.5% |
| `hybrid_rerank_rag` | `over_generalization` | 1 | 5.0% | 9.1% |
| `hybrid_rerank_rag` | `mixed` | 2 | 10.0% | 18.2% |

## Interpretation Notes

- Do not describe these results as RAG being better than LLM-only in all respects.
- LLM-only may produce plausible or factually correct answers, but it lacks document-grounded evidence support because no retrieved evidence was provided.
- The same local generation model and decoding settings were used across all settings to isolate retrieval evidence contribution.
- Larger LLMs can be substituted as the generation backend in future experiments, but retrieval remains necessary for evidence grounding and auditability.
