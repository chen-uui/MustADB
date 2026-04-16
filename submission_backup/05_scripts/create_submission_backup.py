from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKUP_ROOT = PROJECT_ROOT / "submission_backup"
MANIFEST_DIR = BACKUP_ROOT / "09_archive_manifest"


@dataclass(frozen=True)
class ArchiveEntry:
    source_rel: Optional[str]
    dest_rel: str
    purpose: str
    paper_relation: str
    stage: str


def entry(
    source_rel: str,
    dest_rel: str,
    purpose: str,
    paper_relation: str,
    stage: str,
) -> ArchiveEntry:
    return ArchiveEntry(
        source_rel=source_rel.replace("\\", "/"),
        dest_rel=dest_rel.replace("\\", "/"),
        purpose=purpose,
        paper_relation=paper_relation,
        stage=stage,
    )


def group_entries(
    base_source: str,
    base_dest: str,
    filenames: Iterable[str],
    purpose: str,
    paper_relation: str,
    stage: str,
) -> list[ArchiveEntry]:
    entries: list[ArchiveEntry] = []
    for name in filenames:
        clean_name = name.replace("\\", "/")
        entries.append(
            entry(
                f"{base_source.rstrip('/')}/{clean_name}",
                f"{base_dest.rstrip('/')}/{clean_name}",
                purpose,
                paper_relation,
                stage,
            )
        )
    return entries


COPY_ENTRIES: list[ArchiveEntry] = [
    entry(
        "ccc/astrobiology/data/pdfs/Astrobiology Manuscript Revised.pdf",
        "00_manuscript/Astrobiology Manuscript Revised.pdf",
        "Final manuscript PDF found in the repository.",
        "Current submission manuscript.",
        "manuscript",
    ),
    entry(
        "ccc/astrobiology/backend/evaluation/queries.jsonl",
        "04_eval_benchmarks/retrieval/queries.jsonl",
        "Retrieval query set used as the base question inventory.",
        "Retrieval experiments and qrels expansion.",
        "benchmark input",
    ),
    entry(
        "ccc/astrobiology/backend/evaluation/retrieval_qrels_seed.csv",
        "04_eval_benchmarks/retrieval/retrieval_qrels_seed.csv",
        "Seed retrieval qrels before paper-support expansion.",
        "Retrieval experiments; seed benchmark.",
        "benchmark input",
    ),
    entry(
        "ccc/astrobiology/backend/runs/retrieval_qrels_expansion_paper_support_20260402/new_query_candidates.csv",
        "04_eval_benchmarks/retrieval/new_query_candidates.csv",
        "Candidate new queries for expanding the retrieval benchmark.",
        "Expanded retrieval benchmark construction.",
        "benchmark candidate set",
    ),
    entry(
        "ccc/astrobiology/backend/runs/retrieval_qrels_expansion_paper_support_20260402/new_query_candidate_docs.csv",
        "04_eval_benchmarks/retrieval/new_query_candidate_docs.csv",
        "Candidate documents for the new retrieval queries.",
        "Expanded retrieval benchmark construction.",
        "benchmark candidate set",
    ),
    entry(
        "ccc/astrobiology/backend/runs/retrieval_qrels_expansion_paper_support_20260402/qrels_annotation_guidelines.md",
        "04_eval_benchmarks/retrieval/qrels_annotation_guidelines.md",
        "Instructions used when annotating retrieval relevance labels.",
        "Expanded retrieval benchmark construction.",
        "annotation guideline",
    ),
    entry(
        "ccc/astrobiology/backend/runs/expanded_qrels_paper_support_stability_analysis_20260402/retrieval_qrels_expanded.csv",
        "04_eval_benchmarks/retrieval/retrieval_qrels_expanded.csv",
        "Expanded retrieval qrels used for paper-support robustness analysis.",
        "Retrieval robustness and paper-support tables.",
        "benchmark input",
    ),
    entry(
        "ccc/astrobiology/backend/runs/annotation_pack_paper_support_80samples_20260402_doclevel_fix/query_subset_q011_q020.csv",
        "04_eval_benchmarks/retrieval/query_subset_q011_q020.csv",
        "Query subset used to generate the 80-sample manual QA annotation pack.",
        "Manual evaluation sample construction.",
        "benchmark subset",
    ),
    entry(
        "ccc/astrobiology/backend/runs/chunk_sanity_input_qrels_20260402/manifest.tsv",
        "01_data_inventory/chunk_sanity_input_manifest.tsv",
        "Manifest linking copied sanity-input PDFs back to their canonical source paths.",
        "Chunking sanity and retrieval benchmark input provenance.",
        "data inventory",
    ),
    entry(
        "ccc/astrobiology/backend/evaluation/gold_seed.csv",
        "04_eval_benchmarks/extraction/gold_seed.csv",
        "Original extraction gold benchmark.",
        "Extraction benchmark provenance.",
        "benchmark input",
    ),
    entry(
        "ccc/astrobiology/backend/evaluation/gold_seed_v2.csv",
        "04_eval_benchmarks/extraction/gold_seed_v2.csv",
        "Gold benchmark v2 CSV.",
        "Extraction benchmark provenance and v2 evaluation.",
        "benchmark input",
    ),
    entry(
        "ccc/astrobiology/backend/evaluation/gold_seed_v2.xlsx",
        "04_eval_benchmarks/extraction/gold_seed_v2.xlsx",
        "Gold benchmark v2 XLSX.",
        "Extraction benchmark provenance and v2 evaluation.",
        "benchmark input",
    ),
    entry(
        "ccc/astrobiology/backend/evaluation/gold_seed_v3.csv",
        "04_eval_benchmarks/extraction/gold_seed_v3.csv",
        "Gold benchmark v3 CSV.",
        "Extraction benchmark provenance and v3 evaluation.",
        "benchmark input",
    ),
    entry(
        "ccc/astrobiology/backend/evaluation/gold_seed_v3.xlsx",
        "04_eval_benchmarks/extraction/gold_seed_v3.xlsx",
        "Gold benchmark v3 XLSX.",
        "Extraction benchmark provenance and v3 evaluation.",
        "benchmark input",
    ),
]

GENERATED_ENTRIES: list[ArchiveEntry] = [
    ArchiveEntry(None, "README.md", "Backup package overview.", "Entire submission backup.", "generated documentation"),
    ArchiveEntry(
        None,
        "01_data_inventory/asset_inventory.md",
        "Human-readable asset inventory from the scan.",
        "Inventory and curation rationale.",
        "generated documentation",
    ),
    ArchiveEntry(
        None,
        "09_archive_manifest/file_manifest.md",
        "Per-file archive manifest generated by the packaging script.",
        "Archive manifest.",
        "generated documentation",
    ),
    ArchiveEntry(
        None,
        "09_archive_manifest/missing_items.md",
        "Known gaps, ambiguities, and items needing human confirmation.",
        "Archive manifest.",
        "generated documentation",
    ),
    ArchiveEntry(
        None,
        "09_archive_manifest/paper_results_traceability.md",
        "Traceability map from paper results to archived evidence.",
        "Archive manifest.",
        "generated documentation",
    ),
    ArchiveEntry(
        None,
        "09_archive_manifest/package_summary.json",
        "Machine-readable summary of the packaging run.",
        "Archive manifest.",
        "generated log",
    ),
    ArchiveEntry(
        None,
        "09_archive_manifest/package_log.txt",
        "Text log from the packaging run.",
        "Archive manifest.",
        "generated log",
    ),
]

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_batch1_final_20260313_v1",
    "01_data_inventory/gold_batch1_final_20260313_v1",
    [
        "batch1_final_summary.md",
        "batch1_final_summary.json",
        "gold_seed_batch1_final.csv",
        "gold_seed_batch1_final.xlsx",
    ],
    "Batch 1 finalized extraction benchmark assets.",
    "Extraction benchmark provenance.",
    "benchmark curation",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_batch2_final_annotated_20260313_v1",
    "01_data_inventory/gold_batch2_final_annotated_20260313_v1",
    [
        "summary.md",
        "summary.json",
        "gold_seed_batch2_core_final.csv",
        "gold_seed_batch2_core_final.xlsx",
        "gold_seed_batch2_supporting_final.csv",
        "gold_seed_batch2_supporting_final.xlsx",
        "batch2_excluded_items.csv",
    ],
    "Batch 2 annotated extraction benchmark decisions.",
    "Extraction benchmark provenance.",
    "benchmark curation",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_v3_build_20260313_v1",
    "01_data_inventory/gold_v3_build_20260313_v1",
    [
        "summary.md",
        "summary.json",
        "gold_seed_batch2_core_final_fixed.csv",
        "gold_seed_batch2_core_final_fixed.xlsx",
    ],
    "Gold v3 build provenance from the batch 2 core additions.",
    "Extraction benchmark provenance.",
    "benchmark curation",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_batch4_core_review_20260313_v1",
    "01_data_inventory/gold_batch4_core_review_20260313_v1",
    ["summary.md"],
    "Batch 4 core-review recommendation summary for later benchmark expansion.",
    "Extraction benchmark provenance and deferred candidate review.",
    "benchmark curation",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/paper_ready_retrieval_quality_20260402_doclevel_fix",
    "02_raw_results/retrieval/paper_ready_retrieval_quality_20260402_doclevel_fix",
    [
        "bm25_dense/retrieval_quality_summary.csv",
        "bm25_dense/retrieval_quality_details.csv",
        "hybrid_alpha_0p7/retrieval_quality_summary.csv",
        "hybrid_alpha_0p7/retrieval_quality_details.csv",
        "hybrid_alpha_0p9/retrieval_quality_summary.csv",
        "hybrid_alpha_0p9/retrieval_quality_details.csv",
    ],
    "Raw retrieval outputs for the paper-ready doc-level comparison.",
    "Main retrieval comparison: bm25 vs dense vs hybrid vs hybrid_rerank.",
    "raw result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/paper_ready_retrieval_quality_20260402_doclevel_fix",
    "07_figures_tables_sources/retrieval",
    ["paper_ready_retrieval_table.csv"],
    "Table-ready retrieval summary used to present the main doc-level comparison.",
    "Main retrieval comparison table.",
    "final summary",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/expanded_qrels_paper_support_stability_analysis_20260402",
    "02_raw_results/retrieval/expanded_qrels_paper_support_stability_analysis_20260402",
    [
        "retrieval_main_bm25_dense/retrieval_quality_summary.csv",
        "retrieval_main_bm25_dense/retrieval_quality_details.csv",
        "retrieval_main_hybrid_alpha_0p7/retrieval_quality_summary.csv",
        "retrieval_main_hybrid_alpha_0p7/retrieval_quality_details.csv",
        "retrieval_alpha_hybrid_rerank_0p9/retrieval_quality_summary.csv",
        "retrieval_alpha_hybrid_rerank_0p9/retrieval_quality_details.csv",
        "chunk_500_50/retrieval_quality_summary.csv",
        "chunk_500_50/retrieval_quality_details.csv",
        "chunk_700_80/retrieval_quality_summary.csv",
        "chunk_700_80/retrieval_quality_details.csv",
        "chunk_900_100/retrieval_quality_summary.csv",
        "chunk_900_100/retrieval_quality_details.csv",
    ],
    "Raw retrieval outputs used for expanded-qrels paper-support analysis.",
    "Retrieval robustness, chunking, and alpha checks.",
    "raw result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/expanded_qrels_paper_support_stability_analysis_20260402",
    "03_processed_results/retrieval/expanded_qrels_paper_support_stability_analysis_20260402",
    [
        "expanded_qrels_analysis_summary.md",
        "retrieval_expanded_summary.csv",
        "retrieval_expanded_ci_summary.csv",
        "chunk_expanded_summary.csv",
        "chunk_expanded_paired_ci_summary.csv",
        "alpha_expanded_summary.csv",
        "alpha_expanded_paired_ci_summary.csv",
    ],
    "Processed expanded-qrels summaries and confidence intervals.",
    "Retrieval robustness, chunking, and alpha checks.",
    "processed result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/expanded_qrels_paper_support_stability_analysis_20260402",
    "07_figures_tables_sources/retrieval",
    ["retrieval_expanded_paper_table.csv"],
    "Table-ready expanded-qrels retrieval summary.",
    "Expanded retrieval comparison table or appendix table.",
    "final summary",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/retrieval_alpha_ablation_20260402_doclevel_fix",
    "02_raw_results/retrieval/retrieval_alpha_ablation_20260402_doclevel_fix",
    [
        "alpha_ablation_summary.csv",
        "alpha_ablation_details.csv",
        "alpha_0p3000/retrieval_quality_summary.csv",
        "alpha_0p3000/retrieval_quality_details.csv",
        "alpha_0p5000/retrieval_quality_summary.csv",
        "alpha_0p5000/retrieval_quality_details.csv",
        "alpha_0p7000/retrieval_quality_summary.csv",
        "alpha_0p7000/retrieval_quality_details.csv",
        "alpha_0p9000/retrieval_quality_summary.csv",
        "alpha_0p9000/retrieval_quality_details.csv",
    ],
    "Doc-level seed-qrels alpha ablation outputs.",
    "Alpha parameter sensitivity check.",
    "raw result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/chunk_ablation_full_corpus_500_50_20260402_doclevel_fix",
    "02_raw_results/retrieval/chunk_ablation_full_corpus_500_50_20260402_doclevel_fix",
    ["retrieval_quality_summary.csv", "retrieval_quality_details.csv"],
    "Doc-level chunking ablation outputs for 500/50.",
    "Chunking ablation.",
    "raw result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/chunk_ablation_full_corpus_700_80_20260402_doclevel_fix",
    "02_raw_results/retrieval/chunk_ablation_full_corpus_700_80_20260402_doclevel_fix",
    ["retrieval_quality_summary.csv", "retrieval_quality_details.csv"],
    "Doc-level chunking ablation outputs for 700/80.",
    "Chunking ablation.",
    "raw result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/chunk_ablation_full_corpus_900_100_20260402_doclevel_fix",
    "02_raw_results/retrieval/chunk_ablation_full_corpus_900_100_20260402_doclevel_fix",
    ["retrieval_quality_summary.csv", "retrieval_quality_details.csv"],
    "Doc-level chunking ablation outputs for 900/100.",
    "Chunking ablation.",
    "raw result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/stability_analysis_paper_support_doclevel_fix_20260402",
    "03_processed_results/retrieval/stability_analysis_paper_support_doclevel_fix_20260402",
    [
        "stability_analysis_summary.md",
        "retrieval_ci_summary.csv",
        "chunk_paired_ci_summary.csv",
        "alpha_paired_ci_summary.csv",
        "manual_eval_ci_overall.csv",
        "manual_eval_ci_by_mode.csv",
    ],
    "Paper-support confidence interval summaries.",
    "Retrieval robustness and manual-evaluation stability reporting.",
    "processed result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/annotation_pack_paper_support_80samples_20260402_doclevel_fix",
    "08_manual_annotations/annotation_pack_paper_support_80samples_20260402_doclevel_fix",
    [
        "qa_annotation_samples_80_merged.csv",
        "new_40/annotation_guidelines.md",
        "new_40/annotation_pack_metadata.json",
        "new_40/qa_annotation_samples.csv",
        "new_40/qa_annotation_samples_raw.jsonl",
    ],
    "Manual QA annotation pack and merged annotation sheet stored in-repo.",
    "Manual evaluation evidence chain.",
    "raw annotation",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/annotation_summary_paper_support_80_20260402",
    "08_manual_annotations/annotation_summary_paper_support_80_20260402",
    [
        "annotation_summary.csv",
        "annotation_summary.md",
        "paper_manual_eval_by_mode.csv",
        "paper_manual_eval_crosstab_answer_by_mode.csv",
        "paper_manual_eval_crosstab_support_by_mode.csv",
        "paper_manual_eval_overall.csv",
        "paper_manual_eval_tables.md",
    ],
    "Manual QA annotation summaries derived from the annotated 80-sample sheet.",
    "Manual evaluation evidence chain and paper-ready tables.",
    "processed annotation",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_rerun_mainchain_20260312_v2",
    "02_raw_results/extraction/gold_rerun_mainchain_20260312_v2",
    [
        "gold_seed_rerun.csv",
        "prediction_changes.csv",
        "raw_chunk_predictions.jsonl",
        "organic_error_summary.csv",
        "baseline_organic_error_summary.csv",
        "baseline_eval/accuracy_summary.csv",
        "rerun_eval/accuracy_summary.csv",
    ],
    "Baseline-to-rerun extraction outputs on the main gold set.",
    "Extraction benchmark and field-level extraction results.",
    "raw result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_rerun_mainchain_20260312_v2",
    "03_processed_results/extraction/gold_rerun_mainchain_20260312_v2",
    ["before_after_comparison.csv"],
    "Baseline-versus-rerun extraction comparison table.",
    "Extraction benchmark and field-level extraction results.",
    "processed result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_field_specific_narrow_20260312_v1",
    "03_processed_results/extraction/gold_field_specific_narrow_20260312_v1",
    ["comparison_metric_summary.csv", "comparison_organic_error_summary.csv"],
    "Comparison summaries for baseline vs current field-specific vs narrow-improved extraction.",
    "Field-level extraction comparison.",
    "processed result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_field_specific_narrow_20260312_v1/current_best_field_specific",
    "02_raw_results/extraction/gold_field_specific_narrow_20260312_v1/current_best_field_specific",
    [
        "gold_seed_rerun.csv",
        "prediction_changes.csv",
        "raw_chunk_predictions.jsonl",
        "organic_error_summary.csv",
        "baseline_organic_error_summary.csv",
        "baseline_eval/accuracy_summary.csv",
        "rerun_eval/accuracy_summary.csv",
    ],
    "Current field-specific extraction outputs.",
    "Field-level extraction comparison.",
    "raw result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_field_specific_narrow_20260312_v1/narrow_improved",
    "02_raw_results/extraction/gold_field_specific_narrow_20260312_v1/narrow_improved",
    [
        "gold_seed_rerun.csv",
        "prediction_changes.csv",
        "raw_chunk_predictions.jsonl",
        "organic_error_summary.csv",
        "baseline_organic_error_summary.csv",
        "baseline_eval/accuracy_summary.csv",
        "rerun_eval/accuracy_summary.csv",
    ],
    "Narrow-improved field-specific extraction outputs.",
    "Field-level extraction comparison.",
    "raw result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_class_preservation_20260312_v1",
    "03_processed_results/extraction/gold_class_preservation_20260312_v1",
    ["comparison_metric_summary.csv", "comparison_organic_error_summary.csv"],
    "Comparison summaries for baseline vs prior narrow-improved vs class-preserved extraction.",
    "Intermediate field-level extraction comparison.",
    "processed result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_class_preservation_20260312_v1/gold_class_preserved",
    "02_raw_results/extraction/gold_class_preservation_20260312_v1/gold_class_preserved",
    [
        "gold_seed_rerun.csv",
        "prediction_changes.csv",
        "raw_chunk_predictions.jsonl",
        "organic_error_summary.csv",
        "baseline_organic_error_summary.csv",
        "baseline_eval/accuracy_summary.csv",
        "rerun_eval/accuracy_summary.csv",
    ],
    "Class-preserved extraction outputs.",
    "Intermediate field-level extraction comparison.",
    "raw result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_raw_recall_20260312_v1",
    "03_processed_results/extraction/gold_raw_recall_20260312_v1",
    ["comparison_metric_summary.csv", "comparison_organic_error_summary.csv"],
    "Comparison summaries for baseline vs prior class-preservation vs raw-recall-improved extraction.",
    "Field-level extraction comparison.",
    "processed result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_raw_recall_20260312_v1/raw_recall_improved",
    "02_raw_results/extraction/gold_raw_recall_20260312_v1/raw_recall_improved",
    [
        "gold_seed_rerun.csv",
        "prediction_changes.csv",
        "raw_chunk_predictions.jsonl",
        "organic_error_summary.csv",
        "baseline_organic_error_summary.csv",
        "baseline_eval/accuracy_summary.csv",
        "rerun_eval/accuracy_summary.csv",
    ],
    "Raw-recall-improved extraction outputs.",
    "Field-level extraction comparison.",
    "raw result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_ablation_20260312_v2",
    "03_processed_results/extraction/gold_ablation_20260312_v2",
    ["ablation_metric_summary.csv", "ablation_organic_error_summary.csv"],
    "Prompt-ablation comparison summaries on the extraction benchmark.",
    "Auxiliary extraction ablation evidence.",
    "processed result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_v2_eval_20260313_v1",
    "03_processed_results/extraction/gold_v2_eval_20260313_v1",
    [
        "gold_v2_eval_summary.md",
        "gold_v2_eval_summary.json",
        "before_after_comparison.csv",
        "old_gold_fixed_eval/accuracy_summary.csv",
        "new_gold_v2_fixed_eval/accuracy_summary.csv",
    ],
    "Gold v2 evaluation summary and comparison against the original gold set.",
    "Extraction benchmark provenance and evaluation.",
    "processed result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs/gold_v3_eval_20260313_v1",
    "03_processed_results/extraction/gold_v3_eval_20260313_v1",
    [
        "summary.md",
        "summary.json",
        "before_after_comparison.csv",
        "gold_v3_eval/accuracy_summary.csv",
    ],
    "Gold v3 evaluation summary and comparison against gold v2.",
    "Extraction benchmark provenance and evaluation.",
    "processed result",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/pdf_processor/management/commands",
    "05_scripts/management_commands",
    [
        "eval_retrieval_quality.py",
        "ablate_retrieval_alpha.py",
        "ablate_retrieval_chunking.py",
        "export_retrieval_qrels_expansion_pack.py",
        "merge_retrieval_qrels_annotations.py",
        "export_qa_annotation_pack.py",
        "summarize_qa_annotations.py",
        "eval_extraction_accuracy.py",
        "rerun_gold_extraction_eval.py",
        "ablate_field_specific_narrow_eval.py",
        "compare_organic_class_preservation_eval.py",
        "compare_organic_raw_recall_eval.py",
        "run_gold_v3_eval_comparison.py",
        "finalize_gold_seed_batch1.py",
        "build_batch2_final_from_annotated_xlsx.py",
        "build_gold_v3_from_batch2_core.py",
        "build_batch4_core_review_candidates.py",
        "build_gold_expansion_candidates.py",
    ],
    "Django management commands used to create or evaluate the retained experiment assets.",
    "Reproduction support for retrieval, annotation, and extraction results.",
    "script",
)

COPY_ENTRIES += group_entries(
    "ccc/astrobiology/backend/runs",
    "05_scripts",
    ["chunk_sanity_prepare.py"],
    "Helper script associated with chunk-sanity benchmark preparation.",
    "Retrieval benchmark preparation support.",
    "script",
)

COPY_ENTRIES += [
    entry(
        "scripts/create_submission_backup.py",
        "05_scripts/create_submission_backup.py",
        "Repeatable packaging script for this submission backup.",
        "Submission backup generation.",
        "script",
    ),
    entry(
        "ccc/astrobiology/.env.template",
        "06_env/.env.template",
        "Environment template used by the project.",
        "Runtime configuration snapshot.",
        "environment/config",
    ),
    entry(
        "ccc/astrobiology/docker-compose.yml",
        "06_env/docker-compose.yml",
        "Service orchestration file for Weaviate and transformer inference.",
        "Runtime configuration snapshot.",
        "environment/config",
    ),
    entry(
        "ccc/astrobiology/start_astrobiology_system.py",
        "06_env/start_astrobiology_system.py",
        "Project startup helper.",
        "Runtime configuration snapshot.",
        "environment/config",
    ),
    entry(
        "ccc/astrobiology/backend/requirements.txt",
        "06_env/backend_requirements.txt",
        "Python dependency snapshot.",
        "Runtime configuration snapshot.",
        "environment/config",
    ),
    entry(
        "ccc/astrobiology/backend/manage.py",
        "06_env/manage.py",
        "Django command runner used by the archived management commands.",
        "Runtime configuration snapshot.",
        "environment/config",
    ),
    entry(
        "ccc/astrobiology/backend/config/settings.py",
        "06_env/config_snapshots/settings.py",
        "Django settings snapshot.",
        "Runtime configuration snapshot.",
        "environment/config",
    ),
    entry(
        "ccc/astrobiology/backend/pdf_processor/weaviate_config.py",
        "06_env/config_snapshots/weaviate_config.py",
        "Weaviate configuration snapshot.",
        "Runtime configuration snapshot.",
        "environment/config",
    ),
    entry(
        "ccc/astrobiology/backend/pdf_processor/llama_config.py",
        "06_env/config_snapshots/llama_config.py",
        "LLM-related configuration snapshot.",
        "Runtime configuration snapshot.",
        "environment/config",
    ),
]


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def copy_sources(entries: list[ArchiveEntry]) -> tuple[list[dict[str, str]], list[str]]:
    copied_rows: list[dict[str, str]] = []
    warnings: list[str] = []

    for archive_entry in entries:
        if archive_entry.source_rel is None:
            continue

        source_path = (PROJECT_ROOT / archive_entry.source_rel).resolve()
        dest_path = (BACKUP_ROOT / archive_entry.dest_rel).resolve()
        ensure_parent(dest_path)

        status = "copied"
        if not source_path.exists():
            status = "missing_source"
            warnings.append(f"MISSING: {source_path}")
        else:
            shutil.copy2(source_path, dest_path)

        copied_rows.append(
            {
                "archive_path": archive_entry.dest_rel,
                "source_path": str(source_path),
                "purpose": archive_entry.purpose,
                "paper_relation": archive_entry.paper_relation,
                "stage": archive_entry.stage,
                "status": status,
            }
        )

    return copied_rows, warnings


def collect_generated_rows(entries: list[ArchiveEntry]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for archive_entry in entries:
        target = BACKUP_ROOT / archive_entry.dest_rel
        status = "generated" if target.exists() else "missing_generated"
        rows.append(
            {
                "archive_path": archive_entry.dest_rel,
                "source_path": "generated inside submission_backup",
                "purpose": archive_entry.purpose,
                "paper_relation": archive_entry.paper_relation,
                "stage": archive_entry.stage,
                "status": status,
            }
        )
    return rows


def write_manifest(rows: list[dict[str, str]]) -> None:
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# File Manifest",
        "",
        "| Archive path | Original source | Purpose | Paper relation | Stage | Status |",
        "|---|---|---|---|---|---|",
    ]
    for row in sorted(rows, key=lambda item: item["archive_path"]):
        lines.append(
            "| `{archive_path}` | `{source_path}` | {purpose} | {paper_relation} | {stage} | {status} |".format(
                **row
            )
        )
    (MANIFEST_DIR / "file_manifest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_logs(
    copied_rows: list[dict[str, str]],
    generated_rows: list[dict[str, str]],
    warnings: list[str],
    zip_path: Optional[Path],
) -> None:
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "project_root": str(PROJECT_ROOT),
        "backup_root": str(BACKUP_ROOT),
        "copied_file_count": sum(1 for row in copied_rows if row["status"] == "copied"),
        "missing_source_count": sum(1 for row in copied_rows if row["status"] == "missing_source"),
        "generated_entry_count": len(generated_rows),
        "zip_path": str(zip_path) if zip_path else None,
        "warnings": warnings,
    }
    (MANIFEST_DIR / "package_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    log_lines = [
        f"generated_at_utc={summary['generated_at_utc']}",
        f"project_root={PROJECT_ROOT}",
        f"backup_root={BACKUP_ROOT}",
        f"copied_file_count={summary['copied_file_count']}",
        f"missing_source_count={summary['missing_source_count']}",
        f"generated_entry_count={summary['generated_entry_count']}",
        f"zip_path={summary['zip_path']}",
        "",
        "[warnings]",
    ]
    log_lines.extend(warnings or ["none"])
    (MANIFEST_DIR / "package_log.txt").write_text("\n".join(log_lines) + "\n", encoding="utf-8")


def build_zip(zip_name: str) -> Path:
    zip_path = BACKUP_ROOT / zip_name
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as handle:
        for path in sorted(BACKUP_ROOT.rglob("*")):
            if path.is_dir() or path == zip_path:
                continue
            handle.write(path, arcname=path.relative_to(BACKUP_ROOT))
    return zip_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create the submission backup package.")
    parser.add_argument("--skip-zip", action="store_true", help="Refresh files and manifests only.")
    parser.add_argument(
        "--zip-name",
        default="submission_backup.zip",
        help="Name of the zip archive written inside submission_backup/.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)

    copied_rows, warnings = copy_sources(COPY_ENTRIES)
    generated_rows = collect_generated_rows(GENERATED_ENTRIES)
    write_manifest(copied_rows + generated_rows)

    zip_path: Optional[Path] = None
    if not args.skip_zip:
        zip_path = build_zip(args.zip_name)

    generated_rows = collect_generated_rows(GENERATED_ENTRIES)
    write_manifest(copied_rows + generated_rows)
    write_logs(copied_rows, generated_rows, warnings, zip_path)

    copied_count = sum(1 for row in copied_rows if row["status"] == "copied")
    missing_count = sum(1 for row in copied_rows if row["status"] == "missing_source")
    print(f"[submission_backup] copied={copied_count} missing={missing_count}")
    if zip_path is not None:
        print(f"[submission_backup] zip={zip_path}")
    if warnings:
        print("[submission_backup] warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
