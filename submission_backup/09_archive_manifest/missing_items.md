# Archive Exclusions And Version Notes

This file records the reproducibility boundary and retained historical lineages for the revised *Applied Computing and Geosciences* manuscript. The items below are documented exclusions or provenance notes, not unresolved manuscript-result checks.

## Intentionally Excluded Materials

- Journal submission files, including the manuscript source, bibliography, response letter, and submission PDFs, are maintained separately from this public reproducibility repository.
- Copyrighted literature PDFs, local vector-store data, model weights, uploaded files, runtime logs, and machine-specific assets are not redistributed.
- Some legacy annotation summaries refer to original working copies outside the repository. The frozen public benchmark and annotation artifacts used for the reported analyses are retained under `04_eval_benchmarks/` and `08_manual_annotations/`.

These exclusions match the revised manuscript's Data Availability statement.

## Retrieval Version Lineages

Multiple retrieval lineages are retained to preserve provenance, including seed-qrels, document-level, and expanded-qrels runs. The revised manuscript uses the 45-query, 683-judgment benchmark and the reranking evaluation under:

- `04_eval_benchmarks/retrieval/expanded_query_set.jsonl`
- `04_eval_benchmarks/retrieval/retrieval_qrels_expanded.csv`
- `04_eval_benchmarks/retrieval/qrels_evaluation_run_with_rerank/`

Historical seed-qrels outputs are not the basis of the revised manuscript's final metric table.

## Alpha Sensitivity Interpretation

The revised manuscript statement refers specifically to the retained 700/80 reranked-hybrid expanded-qrels analysis. In the saved query-level results, alpha 0.7 and alpha 0.9 are identical. Supporting summaries are retained under:

- `03_processed_results/retrieval/expanded_qrels_paper_support_stability_analysis_20260402/`
- `03_processed_results/retrieval/stability_analysis_paper_support_doclevel_fix_20260402/`

Earlier seed-qrels alpha-ablation outputs remain archived as historical runs and should not be substituted for the scoped revised-manuscript statement.

## Traceability

The repository-root `PAPER_RESULTS_MAP.md` maps the revised manuscript's figures, tables, and principal claims to the current public artifacts, including retrieval, end-to-end answer evaluation, extraction, OCR, and table/figure text-layer analyses.

## Legacy Naming And Encoding

Some historical candidate-document files contain generic or truncated titles, and a small number of legacy filenames or environment snapshots may display differently across terminal encodings. These retained legacy records do not alter the frozen benchmark definitions or reported result files.
