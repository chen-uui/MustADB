# contamination_controls Error Taxonomy

This taxonomy was applied to row-level token-set errors for the `contamination_controls` field.

- sparse or absent explicit contamination description: the document title/notes provide little explicit contamination-control language, so empty gold labels or empty predictions are expected to be unstable.
- indirect wording / implicit procedural control: the control is expressed through procedural language such as blanks, sterile handling, curation, or negative controls rather than a direct field label.
- entity-boundary ambiguity: the prediction captures a related but differently scoped control phrase, e.g. `blank controls` vs. a specific `quality-control blank of DI water`.
- method vs control confusion: analytical/sample-preparation methods are extracted as contamination controls.
- negated or contrastive statements: statements such as `indicated no contamination` require preserving a negative or contrastive relation.
- over-extraction of general lab procedures: generic blanks, storage, curation, or sterile handling are over-predicted when the gold label is empty.
- under-extraction of sample-specific controls: sample-specific handling, curation, storage, blank, or comparison-material controls are missed.

## Overall Counts

| error_taxonomy | count |
| --- | --- |
| entity-boundary ambiguity | 6 |
| indirect wording / implicit procedural control | 14 |
| method vs control confusion | 6 |
| over-extraction of general lab procedures | 18 |
| sparse or absent explicit contamination description | 9 |
| under-extraction of sample-specific controls | 12 |

## Counts by Dataset

| dataset_id | error_taxonomy | count |
| --- | --- | --- |
| field_current_best | entity-boundary ambiguity | 2 |
| field_current_best | indirect wording / implicit procedural control | 3 |
| field_current_best | method vs control confusion | 2 |
| field_current_best | over-extraction of general lab procedures | 5 |
| field_current_best | sparse or absent explicit contamination description | 3 |
| field_current_best | under-extraction of sample-specific controls | 2 |
| field_narrow_improved | entity-boundary ambiguity | 2 |
| field_narrow_improved | indirect wording / implicit procedural control | 3 |
| field_narrow_improved | method vs control confusion | 2 |
| field_narrow_improved | over-extraction of general lab procedures | 5 |
| field_narrow_improved | sparse or absent explicit contamination description | 3 |
| field_narrow_improved | under-extraction of sample-specific controls | 2 |
| gold_v2_fixed_eval_input | entity-boundary ambiguity | 2 |
| gold_v2_fixed_eval_input | indirect wording / implicit procedural control | 3 |
| gold_v2_fixed_eval_input | method vs control confusion | 2 |
| gold_v2_fixed_eval_input | over-extraction of general lab procedures | 6 |
| gold_v2_fixed_eval_input | sparse or absent explicit contamination description | 3 |
| gold_v2_fixed_eval_input | under-extraction of sample-specific controls | 2 |
| gold_v3 | indirect wording / implicit procedural control | 1 |
| gold_v3 | over-extraction of general lab procedures | 2 |
| gold_v3 | under-extraction of sample-specific controls | 1 |
| legacy_gold_seed | indirect wording / implicit procedural control | 1 |
| legacy_gold_seed | under-extraction of sample-specific controls | 1 |
| mainchain_rerun | indirect wording / implicit procedural control | 3 |
| mainchain_rerun | under-extraction of sample-specific controls | 4 |
