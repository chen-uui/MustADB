# Configuration Alignment Plan

This plan is advisory only. No runtime configuration, frozen retrieval results, qrels, Weaviate index, or manuscript text was changed during the audit.

## Must Change Before End-to-End Generation

1. Pin the local generation model for the end-to-end baseline.

   Current conflict:

   - `.env`: `LLM_MODEL=llama3.1:8b`
   - settings/code default and intended experiment: `llama3.1:8b-instruct-q4_K_M`

   Recommended handling:

   - Do not rely on ambiguous `.env` keys.
   - Add or use an experiment-only parameter such as `--generation-model llama3.1:8b-instruct-q4_K_M`.
   - Write the selected model into the end-to-end generation manifest.
   - Use the exact same model and decoding settings for all five pipelines.

2. Ensure no external API fallback is available during generation.

   Recommended handling:

   - Keep the end-to-end runner local/Ollama-only.
   - Fail closed if Ollama or the intended model is unavailable.
   - Do not fall back to OpenAI or any remote API.

3. Explicitly pass or load the mpnet768 collection for any future retrieval export.

   Required value:

   - `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`

   Recommended handling:

   - Use `--collection-name` in experiment scripts.
   - Or read `revision_experiment_config.freeze.json`.
   - Do not rely on generic service fallback `PDFDocument`.

## Should Change For Reproducibility, After Approval

1. Update environment templates.

   Files:

   - `D:/workspace/123/ccc/astrobiology/.env.template`
   - `D:/workspace/123/submission_backup/06_env/.env.template`

   Current template values:

   - `EMBEDDING_MODEL=all-MiniLM-L6-v2`
   - `CHUNK_SIZE=1600`
   - `CHUNK_OVERLAP=400`
   - `LLM_MODEL=llama3.1:8b`

   Revision experiment values:

   - `EMBEDDING_MODEL=sentence-transformers/all-mpnet-base-v2`
   - `WEAVIATE_COLLECTION_NAME=PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`
   - `CHUNK_SIZE=700`
   - `CHUNK_OVERLAP=80`
   - `LLM_MODEL` or `OLLAMA_MODEL=llama3.1:8b-instruct-q4_K_M`

2. Align backup Docker compose default.

   File:

   - `D:/workspace/123/submission_backup/06_env/docker-compose.yml`

   Current risky default:

   - `semitechnologies/transformers-inference:sentence-transformers-${EMBEDDING_MODEL:-all-MiniLM-L6-v2}`

   Active workspace compose is already aligned to:

   - `sentence-transformers-${EMBEDDING_MODEL:-all-mpnet-base-v2}`

   Recommended handling:

   - Either update the backup default to mpnet or mark it as historical/non-revision.

3. Add explicit rerank depth metadata to any future rerank export script.

   Current experiment value:

   - `rerank_input_candidate_depth=20`
   - `final_top_k=10`

   Recommended handling:

   - Make future scripts pass `rerank_k=20` explicitly.
   - Continue writing `rerank_input_candidate_depth` and `final_top_k` to output metadata.

## Can Be Overridden In Experiment Scripts Only

1. Collection name.

   Use the freeze file or command-line override. Do not necessarily change generic production service fallback defaults if they are used by other parts of the application.

2. End-to-end evidence top-k.

   Current prepared prompts use `evidence_top_k=5`. If the value changes, create a new versioned end-to-end directory instead of overwriting `end_to_end_rag_baseline_v1`.

3. Generation model and decoding settings.

   Prefer experiment-runner arguments and manifests over global `.env` edits if the production app needs different defaults.

## Do Not Touch

1. Frozen retrieval evaluation archive:

   - `D:/workspace/123/submission_backup/04_eval_benchmarks/retrieval/revision_qrels_eval_v1_mpnet768/`

2. Existing qrels:

   - `qrels_relevance_only.csv`
   - `qrels_annotated_manual_style.csv`

3. Frozen retrieval result files and metrics.

4. Weaviate index/collection.

   Do not rebuild or mutate:

   - `PDFDocument_chunk_full_corpus_700_80_20260402_doclevel_fix_mpnet768`

5. Manuscript `.tex` files.

6. Retrieval metric definitions.

## Recommended Next Step

Before running end-to-end LLM generation, create a small generation-run manifest that records:

- freeze file path;
- local Ollama URL;
- exact generation model;
- temperature;
- max tokens;
- prompt input file hashes;
- output directory;
- failure policy if Ollama/model is unavailable.

Then run generation into a new versioned directory without changing prepared prompt inputs or frozen retrieval results.
