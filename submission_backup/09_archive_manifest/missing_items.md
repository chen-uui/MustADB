# Missing Items And Risks

This file lists gaps or ambiguities that matter for auditability and later reproduction. Nothing below was fabricated or silently resolved.

## Missing Source Materials

- No LaTeX source, Word source, or `.bib` file for the current manuscript was found during the repository scan.
- No clearly named supplementary-material source package tied to the current submission was found.
- The manual-evaluation summary points to `external/Downloads/qa_annotation_samples_80_annotated.csv`, but that annotated source CSV is not stored in this repository.
- The batch-2 benchmark summary points to `external/Downloads/batch2_review_candidates_annotated.xlsx`, but that annotated source XLSX is not stored in this repository.

## Version Ambiguity

- Retrieval results exist in multiple lineages:
  `ccc/astrobiology/backend/evaluation/retrieval_quality_summary.csv`
  `ccc/astrobiology/backend/runs/default_eval_seed_20260402_doclevel_fix/`
  `ccc/astrobiology/backend/runs/paper_ready_retrieval_quality_20260402_doclevel_fix/`
  `ccc/astrobiology/backend/runs/expanded_qrels_paper_support_stability_analysis_20260402/`
  The paper-ready/doc-level lineage appears to be the intended evidence chain, but the repository also contains stronger earlier numbers. Author confirmation is needed if any manuscript text cites a specific metric value.
- Alpha conclusions are not fully uniform across retained runs:
  `retrieval_alpha_ablation_20260402_doclevel_fix/alpha_ablation_summary.csv`
  shows separation across alpha settings on the seed benchmark, while
  `expanded_qrels_paper_support_stability_analysis_20260402/alpha_expanded_paired_ci_summary.csv`
  and
  `stability_analysis_paper_support_doclevel_fix_20260402/alpha_paired_ci_summary.csv`
  show no practical difference for the paper-support comparison. The manuscript wording should be checked against the intended benchmark scope.

## Naming And Encoding Risks

- Several candidate-document files contain generic or truncated titles such as `Academic Paper`, plus some filenames/snippets show encoding corruption in the current terminal session.
- `.env.template` also displays mojibake in the current shell view. The file itself is archived, but if it is later edited or quoted, encoding should be checked first.

## Traceability Gaps

- The repository does not contain an explicit author-written mapping from final manuscript table/figure numbers to result files. The traceability map in this package is therefore based on filenames, run summaries, and paper-support directory names.
- No explicit in-repo figure-source spreadsheets or plotting notebooks tied to the manuscript PDF were found. Table-ready CSVs were found for retrieval and manual evaluation, but final plot-generation scripts are not obvious.

## Follow-Up Checks Recommended

- Confirm that `Astrobiology Manuscript Revised.pdf` is the exact submission build.
- Confirm which retrieval table in the manuscript should be linked to the seed-only alpha ablation versus the expanded-qrels paper-support analysis.
- Confirm whether any response-letter or supplement draft exists outside the repository and should be added later.
