# contamination_controls Error Summary

## Reproduced Metrics

| dataset | n_samples | TP | FP | FN | P | R | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| legacy_gold_seed | 4 | 9 | 0 | 1 | 1.0000 | 0.9000 | 0.9474 |
| mainchain_rerun | 4 | 0 | 0 | 10 | 0.0000 | 0.0000 | 0.0000 |
| field_current_best | 8 | 5 | 21 | 5 | 0.1923 | 0.5000 | 0.2778 |
| field_narrow_improved | 8 | 5 | 22 | 5 | 0.1852 | 0.5000 | 0.2703 |
| gold_v2_fixed_eval_input | 10 | 6 | 23 | 5 | 0.2069 | 0.5455 | 0.3000 |
| gold_v3 | 7 | 10 | 7 | 1 | 0.5882 | 0.9091 | 0.7143 |

## Error Type Distribution

| error_taxonomy | count |
| --- | --- |
| entity-boundary ambiguity | 6 |
| indirect wording / implicit procedural control | 14 |
| method vs control confusion | 6 |
| over-extraction of general lab procedures | 18 |
| sparse or absent explicit contamination description | 9 |
| under-extraction of sample-specific controls | 12 |

## Small Improvement Experiment

| comparison | original_F1 | improved_F1 | delta_F1 | original_P/R | improved_P/R |
| --- | --- | --- | --- | --- | --- |
| original_vs_rule_based_method_only_filter | 0.9474 | 0.9474 | 0.0000 | 1.0000/0.9000 | 1.0000/0.9000 |
| original_vs_rule_based_method_only_filter | 0.0000 | 0.0000 | 0.0000 | 0.0000/0.0000 | 0.0000/0.0000 |
| original_vs_rule_based_method_only_filter | 0.2778 | 0.2778 | 0.0000 | 0.1923/0.5000 | 0.1923/0.5000 |
| original_vs_rule_based_method_only_filter | 0.2703 | 0.2703 | 0.0000 | 0.1852/0.5000 | 0.1852/0.5000 |
| original_vs_rule_based_method_only_filter | 0.3000 | 0.3000 | 0.0000 | 0.2069/0.5455 | 0.2069/0.5455 |
| original_vs_rule_based_method_only_filter | 0.7143 | 0.7143 | 0.0000 | 0.5882/0.9091 | 0.5882/0.9091 |
| existing_prompt_evidence_refinement | 0.2778 | 0.2703 | -0.0075 | 0.1923/0.5000 | 0.1852/0.5000 |

The rule-based method-only filter was intentionally conservative. It only removes tokens that look like analytical methods and contain no contamination/control cue. In the available rows, most false positives already use contamination-control vocabulary (for example blank controls, sterile handling, or storage), so the conservative rule has little or no effect. The existing narrow prompt/evidence-refinement run did not improve contamination_controls F1 relative to the current-best field-specific run.
