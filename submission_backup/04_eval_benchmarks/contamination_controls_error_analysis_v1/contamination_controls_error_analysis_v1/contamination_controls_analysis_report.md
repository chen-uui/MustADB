# contamination_controls Analysis Report

## Scope

This analysis audits the low-performing `contamination_controls` extraction field using existing gold/prediction files only. It does not modify frozen retrieval qrels results, end-to-end baseline results, benchmark queries, or manuscript text.

## Located Data Sources

| dataset_id | role | exists | path |
| --- | --- | --- | --- |
| legacy_gold_seed | legacy benchmark rows | True | D:\workspace\123\submission_backup\04_eval_benchmarks\extraction\gold_seed.csv |
| mainchain_rerun | mainchain extraction rerun rows | True | D:\workspace\123\submission_backup\02_raw_results\extraction\gold_rerun_mainchain_20260312_v2\gold_seed_rerun.csv |
| field_current_best | low-F1 field-specific run used for error analysis | True | D:\workspace\123\submission_backup\02_raw_results\extraction\gold_field_specific_narrow_20260312_v1\current_best_field_specific\gold_seed_rerun.csv |
| field_narrow_improved | existing conservative prompt/evidence refinement run | True | D:\workspace\123\submission_backup\02_raw_results\extraction\gold_field_specific_narrow_20260312_v1\narrow_improved\gold_seed_rerun.csv |
| gold_v2_fixed_eval_input | gold v2 row-level input corresponding to archived v2 evaluation | True | D:\workspace\123\ccc\astrobiology\backend\runs\gold_v2_eval_20260313_v1\gold_seed_v2_fixed_eval_input.csv |
| gold_v3 | gold v3 benchmark rows | True | D:\workspace\123\submission_backup\04_eval_benchmarks\extraction\gold_seed_v3.csv |

## Paper Result Source Mapping

`D:/workspace/123/PAPER_RESULTS_MAP.md` notes that final manuscript table numbering is not encoded in the repository. The corresponding extraction result sources are retained under `submission_backup/03_processed_results/extraction/`, especially `gold_v2_eval_20260313_v1/`, `gold_v3_eval_20260313_v1/`, and `gold_field_specific_narrow_20260312_v1/`. Therefore this report treats those retained processed summaries, plus their row-level prediction/gold inputs, as the source for the Table-6-style extraction metrics.

## Reproduced Baseline Metrics

| dataset | n_samples | TP | FP | FN | P | R | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| legacy_gold_seed | 4 | 9 | 0 | 1 | 1.0000 | 0.9000 | 0.9474 |
| mainchain_rerun | 4 | 0 | 0 | 10 | 0.0000 | 0.0000 | 0.0000 |
| field_current_best | 8 | 5 | 21 | 5 | 0.1923 | 0.5000 | 0.2778 |
| field_narrow_improved | 8 | 5 | 22 | 5 | 0.1852 | 0.5000 | 0.2703 |
| gold_v2_fixed_eval_input | 10 | 6 | 23 | 5 | 0.2069 | 0.5455 | 0.3000 |
| gold_v3 | 7 | 10 | 7 | 1 | 0.5882 | 0.9091 | 0.7143 |

The low-score field-specific run reproduced the archived contamination_controls metrics: P=0.1923, R=0.5000, F1=0.2778. The gold v2 fixed evaluation input reproduced P=0.2069, R=0.5455, F1=0.3000. Gold v3 reproduced P=0.5882, R=0.9091, F1=0.7143, demonstrating benchmark-version sensitivity.

## Main Error Patterns

| error_taxonomy | count |
| --- | --- |
| entity-boundary ambiguity | 6 |
| indirect wording / implicit procedural control | 14 |
| method vs control confusion | 6 |
| over-extraction of general lab procedures | 18 |
| sparse or absent explicit contamination description | 9 |
| under-extraction of sample-specific controls | 12 |

The dominant failures are boundary and specificity errors: the system often predicts generic controls such as blank controls, sterile handling, cold curation, aluminum foil storage, or freezer storage, while the gold labels either require a more specific form or intentionally leave the field empty. Recall failures also occur when controls are expressed indirectly, for example as curation practices or negative contamination assessments.

## Conservative Improvement Experiment

Two conservative comparisons were recorded:

- `rule_based_method_only_filter`: post-process existing predictions by dropping only analytical-method tokens that lack any contamination/control cue.
- `existing_ontology_guided_prompt_evidence_refinement`: compare the existing field-specific current-best run against the already archived narrow-improved prompt/evidence run.

| comparison | original_F1 | improved_F1 | delta_F1 | original_P/R | improved_P/R |
| --- | --- | --- | --- | --- | --- |
| original_vs_rule_based_method_only_filter | 0.9474 | 0.9474 | 0.0000 | 1.0000/0.9000 | 1.0000/0.9000 |
| original_vs_rule_based_method_only_filter | 0.0000 | 0.0000 | 0.0000 | 0.0000/0.0000 | 0.0000/0.0000 |
| original_vs_rule_based_method_only_filter | 0.2778 | 0.2778 | 0.0000 | 0.1923/0.5000 | 0.1923/0.5000 |
| original_vs_rule_based_method_only_filter | 0.2703 | 0.2703 | 0.0000 | 0.1852/0.5000 | 0.1852/0.5000 |
| original_vs_rule_based_method_only_filter | 0.3000 | 0.3000 | 0.0000 | 0.2069/0.5455 | 0.2069/0.5455 |
| original_vs_rule_based_method_only_filter | 0.7143 | 0.7143 | 0.0000 | 0.5882/0.9091 | 0.5882/0.9091 |
| existing_prompt_evidence_refinement | 0.2778 | 0.2703 | -0.0075 | 0.1923/0.5000 | 0.1852/0.5000 |

The conservative rule did not materially improve the evaluated runs because most false positives were not pure analytical methods; they were plausible but over-general contamination-control phrases. The archived narrow-improved run slightly reduced contamination_controls F1 compared with the current-best field-specific run. This supports the interpretation that the field is difficult mainly because of sparse evidence, implicit wording, and unstable annotation boundaries rather than a single easy-to-filter error class.

## Interpretation for Reviewer Response

The observed volatility across legacy, gold v2, and gold v3 reflects the small number of positive contamination_controls cases and the boundary-sensitive nature of the field. Adding or revising a few documents changes both false-positive and false-negative counts substantially. The field should therefore be discussed separately from higher-density fields such as meteorite names or organic compound classes.
