# QA Annotation Summary

- Input CSV: `external/Downloads/qa_annotation_samples_80_annotated.csv`
- Total rows: `80`

## Metric Definitions
- `answer_accuracy`: manual label distribution over `answer_correct` (`1/0/unclear`).
- `evidence_support_rate`: manual label distribution over `evidence_support` (`supported/partially_supported/unsupported/unclear`).
- `unsupported_output_rate`: manual proxy defined as the proportion of rows where `evidence_support = unsupported`.
- `unsupported_span_marked_rate`: share of rows with a non-empty `unsupported_span_note`.

## Summary

| group_type | group_value | metric | label | count | rate | annotated_rows |
|---|---|---|---|---:|---:|---:|
| overall | all | answer_accuracy | correct | 63 | 0.7875 | 80 |
| overall | all | answer_accuracy | incorrect | 17 | 0.2125 | 80 |
| overall | all | answer_accuracy | unclear | 0 | 0.0000 | 80 |
| overall | all | evidence_support_rate | supported | 21 | 0.2625 | 80 |
| overall | all | evidence_support_rate | partially_supported | 52 | 0.6500 | 80 |
| overall | all | evidence_support_rate | unsupported | 7 | 0.0875 | 80 |
| overall | all | evidence_support_rate | unclear | 0 | 0.0000 | 80 |
| overall | all | unsupported_output_rate | unsupported_by_evidence_support | 7 | 0.0875 | 80 |
| overall | all | unsupported_span_marked_rate | rows_with_unsupported_span_note | 59 | 0.7375 | 80 |
| mode | bm25 | answer_accuracy | correct | 16 | 0.8000 | 20 |
| mode | bm25 | answer_accuracy | incorrect | 4 | 0.2000 | 20 |
| mode | bm25 | answer_accuracy | unclear | 0 | 0.0000 | 20 |
| mode | bm25 | evidence_support_rate | supported | 7 | 0.3500 | 20 |
| mode | bm25 | evidence_support_rate | partially_supported | 11 | 0.5500 | 20 |
| mode | bm25 | evidence_support_rate | unsupported | 2 | 0.1000 | 20 |
| mode | bm25 | evidence_support_rate | unclear | 0 | 0.0000 | 20 |
| mode | bm25 | unsupported_output_rate | unsupported_by_evidence_support | 2 | 0.1000 | 20 |
| mode | bm25 | unsupported_span_marked_rate | rows_with_unsupported_span_note | 13 | 0.6500 | 20 |
| mode | dense | answer_accuracy | correct | 16 | 0.8000 | 20 |
| mode | dense | answer_accuracy | incorrect | 4 | 0.2000 | 20 |
| mode | dense | answer_accuracy | unclear | 0 | 0.0000 | 20 |
| mode | dense | evidence_support_rate | supported | 6 | 0.3000 | 20 |
| mode | dense | evidence_support_rate | partially_supported | 12 | 0.6000 | 20 |
| mode | dense | evidence_support_rate | unsupported | 2 | 0.1000 | 20 |
| mode | dense | evidence_support_rate | unclear | 0 | 0.0000 | 20 |
| mode | dense | unsupported_output_rate | unsupported_by_evidence_support | 2 | 0.1000 | 20 |
| mode | dense | unsupported_span_marked_rate | rows_with_unsupported_span_note | 14 | 0.7000 | 20 |
| mode | hybrid | answer_accuracy | correct | 14 | 0.7000 | 20 |
| mode | hybrid | answer_accuracy | incorrect | 6 | 0.3000 | 20 |
| mode | hybrid | answer_accuracy | unclear | 0 | 0.0000 | 20 |
| mode | hybrid | evidence_support_rate | supported | 5 | 0.2500 | 20 |
| mode | hybrid | evidence_support_rate | partially_supported | 12 | 0.6000 | 20 |
| mode | hybrid | evidence_support_rate | unsupported | 3 | 0.1500 | 20 |
| mode | hybrid | evidence_support_rate | unclear | 0 | 0.0000 | 20 |
| mode | hybrid | unsupported_output_rate | unsupported_by_evidence_support | 3 | 0.1500 | 20 |
| mode | hybrid | unsupported_span_marked_rate | rows_with_unsupported_span_note | 15 | 0.7500 | 20 |
| mode | hybrid_rerank | answer_accuracy | correct | 17 | 0.8500 | 20 |
| mode | hybrid_rerank | answer_accuracy | incorrect | 3 | 0.1500 | 20 |
| mode | hybrid_rerank | answer_accuracy | unclear | 0 | 0.0000 | 20 |
| mode | hybrid_rerank | evidence_support_rate | supported | 3 | 0.1500 | 20 |
| mode | hybrid_rerank | evidence_support_rate | partially_supported | 17 | 0.8500 | 20 |
| mode | hybrid_rerank | evidence_support_rate | unsupported | 0 | 0.0000 | 20 |
| mode | hybrid_rerank | evidence_support_rate | unclear | 0 | 0.0000 | 20 |
| mode | hybrid_rerank | unsupported_output_rate | unsupported_by_evidence_support | 0 | 0.0000 | 20 |
| mode | hybrid_rerank | unsupported_span_marked_rate | rows_with_unsupported_span_note | 17 | 0.8500 | 20 |
