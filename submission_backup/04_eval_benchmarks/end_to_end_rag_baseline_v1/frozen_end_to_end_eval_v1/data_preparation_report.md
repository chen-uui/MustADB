# End-to-End Baseline Data Preparation Report

## Scope

Prepared prompt inputs and annotation scaffolding for LLM-only vs RAG end-to-end evaluation. No LLM answer generation was run, no qrels were modified, and no frozen retrieval evaluation files were overwritten.

## Existing QA Samples Located

Source:

`D:/workspace/123/submission_backup/08_manual_annotations/annotation_pack_paper_support_80samples_20260402_doclevel_fix/qa_annotation_samples_80_merged.csv`

Detected fields:

- `sample_id`
- `qid`
- `query`
- `mode`
- `alpha`
- `collection_name`
- `retrieved_doc_ids`
- `retrieved_evidence_text`
- `model_answer`
- `source_paths`
- `notes_for_annotator`
- `answer_correct`
- `evidence_support`
- `unsupported_span_note`
- `annotation_note`

Detected structure:

- total rows: 80
- unique questions: 20
- mode counts: `bm25` 20, `dense` 20, `hybrid` 20, `hybrid_rerank` 20
- `model_answer` non-empty rows: 80
- per-row manual label fields non-empty rows: 0

Interpretation:

- The 80-row sample pack is reusable as a question set and prior RAG-answer artifact.
- It does not contain per-row gold answers or answer-level support labels in the archived merged CSV.
- Existing aggregate manual summaries are available separately, but they are not per-row labels for this new five-pipeline experiment.

## Prompt Inputs Generated

Output directory:

`D:/workspace/123/submission_backup/04_eval_benchmarks/end_to_end_rag_baseline_v1/`

Generated prompt files:

| file | rows | evidence per row |
|---|---:|---:|
| `llm_only_prompts.jsonl` | 20 | 0 |
| `bm25_rag_prompts.jsonl` | 20 | 2-5 |
| `dense_rag_prompts.jsonl` | 20 | 4-5 |
| `hybrid_rag_prompts.jsonl` | 20 | 5 |
| `hybrid_rerank_rag_prompts.jsonl` | 20 | 4-5 |
| `all_pipeline_prompts.jsonl` | 100 | 0-5 |

Default evidence setting:

- `evidence_top_k`: 5
- `snippet_chars`: 1200

Completeness checks:

- missing ranked results: none
- missing metadata/snippets: none

## Evidence Sources

Ranked retrieval files:

- `D:/workspace/123/submission_backup/04_eval_benchmarks/retrieval/qrels_evaluation_run_with_rerank/bm25_results.jsonl`
- `D:/workspace/123/submission_backup/04_eval_benchmarks/retrieval/qrels_evaluation_run_with_rerank/dense_results.jsonl`
- `D:/workspace/123/submission_backup/04_eval_benchmarks/retrieval/qrels_evaluation_run_with_rerank/hybrid_results.jsonl`
- `D:/workspace/123/submission_backup/04_eval_benchmarks/retrieval/qrels_evaluation_run_with_rerank/hybrid_rerank_results.jsonl`

Snippet metadata:

- `D:/workspace/123/submission_backup/04_eval_benchmarks/retrieval/qrels_annotation/qrels_annotation_template.csv`

The qrels annotation template was used only for document metadata and indexed snippets. The `relevance` field was not used for answer-level support labels.

## Local LLM Configuration Observed

Read-only configuration search found local Ollama settings:

- `.env`: `OLLAMA_HOST=localhost`, `OLLAMA_PORT=11434`, `LLM_MODEL=llama3.1:8b`, `LLM_TEMPERATURE=0.1`, `LLM_MAX_TOKENS=4096`
- Django settings/default code references: `OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M`

No model was called during this preparation step.

After the configuration audit, the end-to-end prompt preparation was pinned to the revision freeze file:

- `generation_model`: `llama3.1:8b-instruct-q4_K_M`
- `backend`: `local/Ollama`
- `.env` `LLM_MODEL` fallback: disabled
- external API fallback: disabled
- runtime freeze: `end_to_end_runtime_config.freeze.json`
- local generation config: `local_generation_config.json`

All five prompt files now record the same pinned generation model.

## Annotation Scaffold

Generated:

`answer_level_evaluation_template.csv`

Rows: 100

Fields:

- `sample_id`
- `pipeline`
- `qid`
- `question`
- `generated_answer`
- `gold_answer`
- `support_label`
- `partial_support_subtype`
- `evidence_mismatch`
- `answer_correct`
- `evaluator_notes`

The template intentionally leaves generated answers, gold answers, and labels blank.
