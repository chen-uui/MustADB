# Answer-Level Evaluation Template Statistics

- source_answers_csv: `D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\generated_answers_run\generated_answers_by_pipeline.csv`
- output_template_csv: `D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\answer_level_evaluation\answer_level_evaluation_template.csv`
- total answer rows: `100`
- missing generated answer rows: `0`
- missing evidence rows: `20`
- LLM-only missing evidence rows: `20`
- RAG missing evidence rows: `0`

## Rows By Pipeline

| pipeline | rows |
|---|---:|
| `bm25_rag` | 20 |
| `dense_rag` | 20 |
| `hybrid_rag` | 20 |
| `hybrid_rerank_rag` | 20 |
| `llm_only` | 20 |

## Evidence Count Distribution

| evidence_count | rows |
|---:|---:|
| 0 | 20 |
| 2 | 1 |
| 4 | 8 |
| 5 | 71 |

## Notes

- Label columns are intentionally blank.
- `evidence_text` is extracted from each generated prompt for annotation convenience.
- LLM-only rows intentionally have empty evidence text and should still be evaluated for factual correctness and verifiability.
- Retrieval qrels were not used to fill any answer-level label.
