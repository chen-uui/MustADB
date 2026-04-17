# Gold V3 Evaluation Summary

- gold_v2: `backend/evaluation/gold_seed_v2.csv`
- gold_v3: `backend/evaluation/gold_seed_v3.csv`
- v2_summary: `backend/runs/gold_v2_eval_20260313_v1\new_gold_v2_fixed_eval\accuracy_summary.csv`
- v3_eval_dir: `backend/runs/gold_v3_eval_20260313_v1\gold_v3_eval`
- comparison_csv: `backend/runs/gold_v3_eval_20260313_v1\before_after_comparison.csv`

## v2 to v3 New Addition
- Concentration and variability of the AIB amino acid in polar micrometeorites: Implications for the exogenous delivery of amino acids to the primitive Earth

## Supporting Status
- supporting_final remains separate and did not enter formal core gold in v3.

## Metric Changes
- meteorite_name: total_rows 22 -> 23, evaluated_rows 18 -> 19, skipped_rows 4 -> 4, P 0.6667 -> 0.5556, R 0.8333 -> 0.7692, F1 0.7407 -> 0.6452
- organic_compounds: total_rows 22 -> 23, evaluated_rows 18 -> 19, skipped_rows 4 -> 4, P 0.5733 -> 0.4839, R 0.9149 -> 0.9184, F1 0.7049 -> 0.6338
- contamination_controls: total_rows 22 -> 23, evaluated_rows 18 -> 19, skipped_rows 4 -> 4, P 0.2069 -> 0.5882, R 0.5455 -> 0.9091, F1 0.3000 -> 0.7143
- overall_macro_avg: total_rows 22 -> 23, evaluated_rows 18 -> 19, skipped_rows 4 -> 4, P 0.4823 -> 0.5426, R 0.7646 -> 0.8656, F1 0.5819 -> 0.6644
