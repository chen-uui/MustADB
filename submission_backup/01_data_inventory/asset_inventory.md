# Asset Inventory

This inventory records the main experiment assets found during the scan and the curation decisions used for this backup.

## A. Manuscript Assets

- Found:
  `ccc/astrobiology/data/pdfs/Astrobiology Manuscript Revised.pdf`
- Not found during the scan:
  `.tex`, `.bib`, `.docx`, `.doc`, or a clearly named supplementary-material source package tied to the current submission.

## B. Retrieval Result Assets

- Core benchmark inputs:
  `ccc/astrobiology/backend/evaluation/queries.jsonl`
  `ccc/astrobiology/backend/evaluation/retrieval_qrels_seed.csv`
- Paper-support retrieval runs:
  `ccc/astrobiology/backend/runs/paper_ready_retrieval_quality_20260402_doclevel_fix/`
  `ccc/astrobiology/backend/runs/expanded_qrels_paper_support_stability_analysis_20260402/`
  `ccc/astrobiology/backend/runs/stability_analysis_paper_support_doclevel_fix_20260402/`
  `ccc/astrobiology/backend/runs/retrieval_alpha_ablation_20260402_doclevel_fix/`
  `ccc/astrobiology/backend/runs/chunk_ablation_full_corpus_*_20260402_doclevel_fix/`
- Table-ready retrieval summaries found:
  `paper_ready_retrieval_table.csv`
  `retrieval_expanded_paper_table.csv`

## C. Manual Annotation Assets

- Annotation-pack runs found:
  `ccc/astrobiology/backend/runs/annotation_pack_paper_support_80samples_20260402_doclevel_fix/`
  `ccc/astrobiology/backend/runs/annotation_summary_paper_support_80_20260402/`
- Important note:
  `annotation_summary.md` points to an annotated CSV in `C:\Users\19404\Downloads\qa_annotation_samples_80_annotated.csv`, which is not stored inside the repository.

## D. Extraction Benchmark and Evaluation Assets

- Gold benchmark versions found:
  `gold_seed.csv`
  `gold_seed_v2.csv/.xlsx`
  `gold_seed_v3.csv/.xlsx`
- Benchmark-build and review runs found:
  `gold_batch1_final_20260313_v1/`
  `gold_batch2_final_annotated_20260313_v1/`
  `gold_v3_build_20260313_v1/`
  `gold_batch4_core_review_20260313_v1/`
- Extraction evaluation and comparison runs found:
  `gold_v2_eval_20260313_v1/`
  `gold_v3_eval_20260313_v1/`
  `gold_rerun_mainchain_20260312_v2/`
  `gold_field_specific_narrow_20260312_v1/`
  `gold_class_preservation_20260312_v1/`
  `gold_raw_recall_20260312_v1/`
  `gold_ablation_20260312_v2/`

## E. Scripts and Configuration Assets

- Retrieval and extraction evaluation logic is concentrated in:
  `ccc/astrobiology/backend/pdf_processor/management/commands/`
- Environment/runtime snapshots found:
  `ccc/astrobiology/.env.template`
  `ccc/astrobiology/docker-compose.yml`
  `ccc/astrobiology/backend/requirements.txt`
  `ccc/astrobiology/backend/config/settings.py`
  `ccc/astrobiology/backend/pdf_processor/weaviate_config.py`
  `ccc/astrobiology/backend/pdf_processor/llama_config.py`

## F. Large or Irrelevant Assets Intentionally Excluded

- `.venv/`
- `astro_frontend/node_modules/`
- `astro_frontend/dist/`
- `ccc/astrobiology/backend/models/`
- `ccc/astrobiology/data/weaviate_data/`
- `ccc/astrobiology/backend/media/uploads/`
- `tmp_*`, smoke files, compiled caches, and unrelated runtime logs

## G. Curation Rule Used For This Backup

- Kept:
  files that directly support the current manuscript, benchmark lineage, paper-support evaluation runs, manual annotation summaries, or extraction comparison evidence.
- Not kept by default:
  full corpora, vector-store payloads, model weights, runtime caches, frontend build outputs, and generic temporary artifacts.
- Escalated for human confirmation instead of guessing:
  manuscript source availability, exact final table/figure numbering, external annotation files, and competing retrieval-result versions.
