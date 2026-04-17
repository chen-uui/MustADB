# Submission Backup Package

This package is a curated backup for the PNAS Nexus submission materials in this workspace. Its goal is not to snapshot the whole repository, but to preserve a traceable evidence chain for the current manuscript, the benchmark definitions behind the reported experiments, the retained result files, and the scripts/configuration needed to inspect or repackage them later.

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
- Extraction benchmark provenance:
  `04_eval_benchmarks/extraction/`
  plus the benchmark-build records in `01_data_inventory/`.
- Extraction evaluation and field-level comparison:
  `03_processed_results/extraction/`
  backed by the rerun outputs in `02_raw_results/extraction/`.

## Current Completeness

- Present in the default public git-tracked release:
  retrieval benchmark files, expanded qrels artifacts, manual-eval pack and summaries, gold benchmark v1/v2/v3 assets, major extraction comparison runs, management commands, and environment snapshots.
- Retained only in the live local workspace, not in the default public release archive:
  manuscript PDF and raw literature PDFs.
- Missing or still requiring author confirmation:
  LaTeX/Word manuscript source, `.bib`, the original annotated 80-sample CSV in `Downloads`, the original annotated batch-2 XLSX in `Downloads`, and an explicit author-written mapping from manuscript table/figure numbers to result files.
- Version-risk items requiring care:
  retrieval results exist in multiple lineages, and alpha conclusions differ between the seed-qrels ablation and the expanded-qrels paper-support analysis. See `09_archive_manifest/missing_items.md`.

## Regeneration

Run the packaging script from the project root:

```bash
python scripts/create_submission_backup.py
```

The script refreshes copied files, regenerates `09_archive_manifest/file_manifest.md`, writes packaging logs, and rebuilds `submission_backup/submission_backup.zip`. The default archive excludes `00_manuscript/`.
