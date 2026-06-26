# Frozen Results Summary

- archive: `D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\frozen_end_to_end_eval_v1`
- annotated rows: `100`
- pipeline row counts: `{'llm_only': 20, 'bm25_rag': 20, 'dense_rag': 20, 'hybrid_rag': 20, 'hybrid_rerank_rag': 20}`
- generation model: `llama3.1:8b-instruct-q4_K_M`
- backend: `local/Ollama`
- external API used: `no`
- identical generator settings across pipelines: `true`

## Metrics By Pipeline

| pipeline | n | fully supported | partially supported | unsupported | answer correct | evidence mismatch | hallucination flag |
|---|---:|---:|---:|---:|---:|---:|---:|
| `llm_only` | 20 | 0 (0.0%) | 0 (0.0%) | 20 (100.0%) | 18 (90.0%) | 0 (0.0%) | 20 (100.0%) |
| `bm25_rag` | 20 | 7 (35.0%) | 11 (55.0%) | 2 (10.0%) | 11 (55.0%) | 2 (10.0%) | 2 (10.0%) |
| `dense_rag` | 20 | 4 (20.0%) | 15 (75.0%) | 1 (5.0%) | 16 (80.0%) | 3 (15.0%) | 2 (10.0%) |
| `hybrid_rag` | 20 | 5 (25.0%) | 14 (70.0%) | 1 (5.0%) | 10 (50.0%) | 5 (25.0%) | 3 (15.0%) |
| `hybrid_rerank_rag` | 20 | 7 (35.0%) | 11 (55.0%) | 2 (10.0%) | 11 (55.0%) | 1 (5.0%) | 1 (5.0%) |

## Notes

- LLM-only answers were evaluated for factual correctness but have no document-grounded evidence by design.
- Retrieval-augmented settings allow explicit evidence-support assessment.
- Retrieval qrels were not used as answer-level support labels.
