# Paper Results Map

This file maps the revised *Applied Computing and Geosciences* manuscript claims to the retained public artifacts in this repository. Manuscript numbering below refers to the current revised version.

## Main Retrieval Comparison

- Retained table-ready summary:
  `submission_backup/07_figures_tables_sources/retrieval/paper_ready_retrieval_table.csv`
- Raw result chain:
  `submission_backup/02_raw_results/retrieval/paper_ready_retrieval_quality_20260402_doclevel_fix/`
- Benchmark inputs:
  `submission_backup/04_eval_benchmarks/retrieval/expanded_query_set.jsonl`
  `submission_backup/04_eval_benchmarks/retrieval/retrieval_qrels_expanded.csv`
- Revised 45-query/683-judgment evaluation, including reranking:
  `submission_backup/04_eval_benchmarks/retrieval/qrels_evaluation_run_with_rerank/`
- Manuscript mapping:
  Figure 2(a), Table 2, and the retrieval portion of the Results section.

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
- Manuscript mapping:
  Figure 2(d), Table 3, and the alpha/chunking sensitivity discussion.
- Final alpha interpretation:
  for the retained 700/80 reranked-hybrid setting, alpha 0.7 and alpha 0.9 are identical in the saved query-level expanded-qrels results. Seed-qrels runs are retained as historical provenance and are not the basis of the revised manuscript statement.

## End-to-End LLM-Only And RAG Evaluation

- Frozen experiment design, configuration, prompts, and generated outputs:
  `submission_backup/04_eval_benchmarks/end_to_end_rag_baseline_v1/frozen_end_to_end_eval_v1/`
- Paper-ready answer-level metrics and support-label decomposition:
  `submission_backup/04_eval_benchmarks/end_to_end_rag_baseline_v1/frozen_end_to_end_eval_v1/answer_level_evaluation/paper_ready_end_to_end_metrics_table.csv`
  `submission_backup/04_eval_benchmarks/end_to_end_rag_baseline_v1/frozen_end_to_end_eval_v1/answer_level_evaluation/paper_ready_partially_supported_subtype_table.csv`
- Manuscript mapping:
  Figure 2(b)--(c), Table 4, and the discussion separating content correctness from document-grounded evidence support.

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
- Contamination-control error analysis:
  `submission_backup/04_eval_benchmarks/contamination_controls_error_analysis_v1/contamination_controls_error_analysis_v1/`
- Manuscript mapping:
  Table 6 and the contamination-control error discussion.

## OCR And Table/Figure Scope Audits

- OCR robustness and six-file fallback smoke test:
  `submission_backup/04_eval_benchmarks/ocr_robustness_check_v1/ocr_robustness_check_v1/`
- Table/figure text-layer audit:
  `submission_backup/04_eval_benchmarks/table_figure_text_layer_audit_v1/table_figure_text_layer_audit_v1/`
- Manuscript mapping:
  the OCR and table/figure scope statements in Materials and Methods, Discussion, and Supplementary Sections S5--S7.

## Reproducibility Boundary

- Copyrighted source PDFs, local vector stores, model weights, uploaded files, runtime logs, and machine-specific assets are intentionally excluded.
- Journal submission files are maintained separately from this public reproducibility repository.
- The software citation metadata in `CITATION.cff` points to the public GitHub repository; a Zenodo DOI can be added after an archival release is created.
