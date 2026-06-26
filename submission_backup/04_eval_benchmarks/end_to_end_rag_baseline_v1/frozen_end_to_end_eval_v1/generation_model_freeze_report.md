# Generation Model Freeze Report

## Scope

This report pins the configuration for the future end-to-end LLM-only vs RAG baseline generation step. No LLM generation was run by this script invocation.

## Frozen Generation Configuration

- backend: `local/Ollama`
- generation_model: `llama3.1:8b-instruct-q4_K_M`
- temperature: `0.1`
- max_tokens: `4096`
- external_api_allowed: `false`
- `.env` LLM fallback allowed: `false`

All five pipelines use the same generation model:

- `llm_only`
- `bm25_rag`
- `dense_rag`
- `hybrid_rag`
- `hybrid_rerank_rag`

Using the same local generation model isolates the contribution of retrieval evidence: any observed answer-level difference is attributable to whether evidence is provided and which retrieval method supplies it, not to a different LLM backend.

## Frozen Retrieval/Index Configuration

- dense_embedding_model: `sentence-transformers/all-mpnet-base-v2`
- dense_vector_dimension: `768`
- weaviate_collection: `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`
- reranker_model: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- rerank_input_candidate_depth: `20`
- final_evaluated_top_k: `10`
- prompt_evidence_top_k: `5`

The script fails fast if the freeze config is missing, if the generation model does not match the freeze file, if the collection is generic, or if rerank metadata does not match the frozen mpnet768 configuration.

## Model-Agnostic System Statement

The system remains model-agnostic: a different generation backend can be used in a separately frozen experiment. This experiment intentionally fixes the local Ollama model so that the comparison tests retrieval/evidence grounding rather than LLM model strength.

## Command To Regenerate Pinned Prompt Inputs

```powershell
C:\Users\19404\AppData\Local\Programs\Python\Python311\python.exe D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\run_end_to_end_baseline_eval.py prepare-prompts ^
  --config D:\workspace\123\submission_backup\04_eval_benchmarks\config_audit_revision_v1\revision_experiment_config.freeze.json ^
  --generation-model llama3.1:8b-instruct-q4_K_M ^
  --out-dir D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1
```

## Future Answer Generation Command

No answer generation was executed during pinning. The project does not currently include a standalone `run_local_ollama_batch_generation.py`; the commands below define the required formal entry point for the next step. That runner must read `end_to_end_runtime_config.freeze.json`, use local Ollama only, refuse external API fallback, and fail if `llama3.1:8b-instruct-q4_K_M` is unavailable.

```powershell
C:\Users\19404\AppData\Local\Programs\Python\Python311\python.exe D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\run_local_ollama_batch_generation.py ^
  --runtime-config D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\end_to_end_runtime_config.freeze.json ^
  --pipeline llm_only ^
  --input D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\llm_only_prompts.jsonl ^
  --output D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\generated_answers_llm_only.jsonl

C:\Users\19404\AppData\Local\Programs\Python\Python311\python.exe D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\run_local_ollama_batch_generation.py ^
  --runtime-config D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\end_to_end_runtime_config.freeze.json ^
  --pipeline bm25_rag ^
  --input D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\bm25_rag_prompts.jsonl ^
  --output D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\generated_answers_bm25_rag.jsonl

C:\Users\19404\AppData\Local\Programs\Python\Python311\python.exe D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\run_local_ollama_batch_generation.py ^
  --runtime-config D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\end_to_end_runtime_config.freeze.json ^
  --pipeline dense_rag ^
  --input D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\dense_rag_prompts.jsonl ^
  --output D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\generated_answers_dense_rag.jsonl

C:\Users\19404\AppData\Local\Programs\Python\Python311\python.exe D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\run_local_ollama_batch_generation.py ^
  --runtime-config D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\end_to_end_runtime_config.freeze.json ^
  --pipeline hybrid_rag ^
  --input D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\hybrid_rag_prompts.jsonl ^
  --output D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\generated_answers_hybrid_rag.jsonl

C:\Users\19404\AppData\Local\Programs\Python\Python311\python.exe D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\run_local_ollama_batch_generation.py ^
  --runtime-config D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\end_to_end_runtime_config.freeze.json ^
  --pipeline hybrid_rerank_rag ^
  --input D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\hybrid_rerank_rag_prompts.jsonl ^
  --output D:\workspace\123\submission_backup\04_eval_benchmarks\end_to_end_rag_baseline_v1\generated_answers_hybrid_rerank_rag.jsonl

```
