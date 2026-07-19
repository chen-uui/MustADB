# Submission Backup Package

This package is a curated reproducibility archive supporting the revised manuscript submitted to *Applied Computing and Geosciences*. Its goal is not to snapshot the whole repository, but to preserve a traceable evidence chain for the manuscript, the benchmark definitions behind the reported experiments, the retained result files, and the scripts/configuration needed to inspect or reproduce the reported analyses.

## What This Package Is For

- Quickly answer editor or reviewer questions about where a reported result came from.
- Reduce risk from version drift across retrieval runs, qrels revisions, and extraction benchmark revisions.
- Preserve enough inputs, outputs, and command snapshots to support targeted reruns or audits later.
- Keep original project files in place: this package only copies selected files.

## Directory Guide

- `00_manuscript/`: optional local-only manuscript staging area. It is excluded from the default public git-tracked release and from the default generated archive.
- `01_data_inventory/`: benchmark provenance and inventory notes.
- `02_raw_results/`: selected raw or near-raw result files from retrieval and extraction runs.
- `03_processed_results/`: summaries, comparison tables, and CI outputs.
- `04_eval_benchmarks/`: retained qrels, queries, and gold benchmark files.
- `05_scripts/`: management commands and the backup-packaging script.
- `06_env/`: environment and runtime configuration snapshots.
- `07_figures_tables_sources/`: table-ready CSVs retained as likely paper-facing sources.
- `08_manual_annotations/`: QA annotation pack and manual-evaluation summaries.
- `09_archive_manifest/`: manifest, missing-items log, traceability notes, and packaging logs.

## Experiment Modules Covered

- Retrieval main comparison:
  `07_figures_tables_sources/retrieval/paper_ready_retrieval_table.csv`
  backed by raw files under `02_raw_results/retrieval/paper_ready_retrieval_quality_20260402_doclevel_fix/`.
- Retrieval robustness, doc-level evaluation, chunking, and alpha checks:
  `03_processed_results/retrieval/expanded_qrels_paper_support_stability_analysis_20260402/`
  and
  `03_processed_results/retrieval/stability_analysis_paper_support_doclevel_fix_20260402/`
  backed by raw files in the matching `02_raw_results/retrieval/` run folders.
- Manual evaluation:
  `08_manual_annotations/annotation_pack_paper_support_80samples_20260402_doclevel_fix/`
  plus
  `08_manual_annotations/annotation_summary_paper_support_80_20260402/`.
- Revised end-to-end LLM-only and RAG comparison:
  `04_eval_benchmarks/end_to_end_rag_baseline_v1/frozen_end_to_end_eval_v1/`,
  including the frozen generation configuration, generated outputs, answer-level annotations, and paper-ready metrics.
- Expanded 45-query retrieval benchmark:
  `04_eval_benchmarks/retrieval/expanded_query_set.jsonl`,
  `04_eval_benchmarks/retrieval/retrieval_qrels_expanded.csv`,
  and
  `04_eval_benchmarks/retrieval/qrels_evaluation_run_with_rerank/`.
- Extraction benchmark provenance:
  `04_eval_benchmarks/extraction/`
  plus the benchmark-build records in `01_data_inventory/`.
- Extraction evaluation and field-level comparison:
  `03_processed_results/extraction/`
  backed by the rerun outputs in `02_raw_results/extraction/`.
- Reviewer-requested scope and error analyses:
  `04_eval_benchmarks/contamination_controls_error_analysis_v1/`,
  `04_eval_benchmarks/ocr_robustness_check_v1/`,
  and
  `04_eval_benchmarks/table_figure_text_layer_audit_v1/`.

## Current Completeness

- Present in the public git-tracked release:
  the expanded retrieval query set and qrels, per-method ranked outputs and metrics, the frozen five-pipeline end-to-end evaluation, answer-support annotations, manual-evaluation assets, gold benchmark v1/v2/v3 assets, extraction comparisons, contamination-control error analysis, OCR checks, table/figure text-layer audit, management commands, and environment snapshots.
- Intentionally not redistributed:
  copyrighted literature PDFs, local vector-store data, model weights, uploaded files, runtime logs, machine-specific assets, and journal submission files. These exclusions match the manuscript's Data Availability statement and are not missing benchmark evidence.
- Manuscript-facing result locations are mapped in the repository-root `PAPER_RESULTS_MAP.md`.
- Historical seed-qrels and intermediate run lineages are retained for provenance. The revised manuscript's alpha statement is supported by the expanded-qrels reranked-hybrid analysis in `03_processed_results/retrieval/expanded_qrels_paper_support_stability_analysis_20260402/`, where alpha 0.7 and 0.9 have identical saved query-level results.

## Regeneration

Run the packaging script from the project root:

```bash
python scripts/create_submission_backup.py
```

The script refreshes copied files, regenerates `09_archive_manifest/file_manifest.md`, writes packaging logs, and rebuilds `submission_backup/submission_backup.zip`. The default archive excludes `00_manuscript/`.
