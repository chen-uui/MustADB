# Paper Results Map

This file maps the current manuscript-support claims to the retained public artifacts in this repository. The mappings are topic-based because the repository does not encode final manuscript table or figure numbers.

## Main Retrieval Comparison

- Retained table-ready summary:
  `submission_backup/07_figures_tables_sources/retrieval/paper_ready_retrieval_table.csv`
- Raw result chain:
  `submission_backup/02_raw_results/retrieval/paper_ready_retrieval_quality_20260402_doclevel_fix/`
- Benchmark inputs:
  `submission_backup/04_eval_benchmarks/retrieval/queries.jsonl`
  `submission_backup/04_eval_benchmarks/retrieval/retrieval_qrels_seed.csv`

## Retrieval Robustness, Chunking, And Alpha Checks

- Processed summaries:
  `submission_backup/03_processed_results/retrieval/expanded_qrels_paper_support_stability_analysis_20260402/`
  `submission_backup/03_processed_results/retrieval/stability_analysis_paper_support_doclevel_fix_20260402/`
- Expanded-qrels table-ready summary:
  `submission_backup/07_figures_tables_sources/retrieval/retrieval_expanded_paper_table.csv`
- Raw ablation outputs:
  `submission_backup/02_raw_results/retrieval/retrieval_alpha_ablation_20260402_doclevel_fix/`
  `submission_backup/02_raw_results/retrieval/chunk_ablation_full_corpus_500_50_20260402_doclevel_fix/`
  `submission_backup/02_raw_results/retrieval/chunk_ablation_full_corpus_700_80_20260402_doclevel_fix/`
  `submission_backup/02_raw_results/retrieval/chunk_ablation_full_corpus_900_100_20260402_doclevel_fix/`

## Manual Evaluation

- Annotation pack:
  `submission_backup/08_manual_annotations/annotation_pack_paper_support_80samples_20260402_doclevel_fix/`
- Derived summaries:
  `submission_backup/08_manual_annotations/annotation_summary_paper_support_80_20260402/`
- Confidence interval summaries:
  `submission_backup/03_processed_results/retrieval/stability_analysis_paper_support_doclevel_fix_20260402/manual_eval_ci_overall.csv`
  `submission_backup/03_processed_results/retrieval/stability_analysis_paper_support_doclevel_fix_20260402/manual_eval_ci_by_mode.csv`

## Extraction Benchmark Construction

- Benchmark inputs:
  `submission_backup/04_eval_benchmarks/extraction/`
- Build lineage:
  `submission_backup/01_data_inventory/gold_batch1_final_20260313_v1/`
  `submission_backup/01_data_inventory/gold_batch2_final_annotated_20260313_v1/`
  `submission_backup/01_data_inventory/gold_v3_build_20260313_v1/`

## Extraction Evaluation

- Gold v2 summary:
  `submission_backup/03_processed_results/extraction/gold_v2_eval_20260313_v1/`
- Gold v3 summary:
  `submission_backup/03_processed_results/extraction/gold_v3_eval_20260313_v1/`
- Baseline vs rerun comparison:
  `submission_backup/03_processed_results/extraction/gold_rerun_mainchain_20260312_v2/before_after_comparison.csv`
- Field-level comparisons:
  `submission_backup/03_processed_results/extraction/gold_field_specific_narrow_20260312_v1/`
  `submission_backup/03_processed_results/extraction/gold_class_preservation_20260312_v1/`
  `submission_backup/03_processed_results/extraction/gold_raw_recall_20260312_v1/`

## Important Gaps Requiring Author Confirmation

- The final manuscript table and figure numbering is not encoded in the repository.
- Some original annotation inputs lived outside the repository and are listed in `submission_backup/09_archive_manifest/missing_items.md`.
- The manuscript wording around alpha sensitivity should be checked against the retained seed-qrels and expanded-qrels analyses before publication.
- The software citation metadata in `CITATION.cff` now points to the public GitHub repository; the Zenodo DOI can be added after archival release.
