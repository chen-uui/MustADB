# OCR Fallback Smoke Test Report

## Scope

This smoke test supplements the OCR limitation analysis. It does not modify the main index, rebuild Weaviate, or change frozen retrieval, end-to-end, or contamination-control results. It is not a main benchmark result.

## Selection

Selected up to 6 accessible PDFs from `low_text_or_degraded_text` and `very_low_text_or_ocr_dependent_candidate` rows in `ocr_robustness_sample.csv`.

## Existing OCR Tool Check

- Existing OCR fallback import available: `False`
- Import/dependency error: `ModuleNotFoundError: No module named 'fitz'`

## Summary

| metric | value |
| --- | --- |
| selected_documents | 6 |
| accessible_documents | 6 |
| existing_ocr_tool_available | 0 |
| dependency_unavailable_rows | 6 |
| ocr_success_rows | 0 |
| rows_with_text_length_increase_after_ocr | 0 |

## Per-Document Result

| sample_id | quality_class | before_text_length | after_text_length | ocr_status |
| --- | --- | --- | --- | --- |
| OCRS001 | very_low_text_or_ocr_dependent_candidate | 81 | NA | dependency_unavailable |
| OCRS002 | low_text_or_degraded_text | 523 | NA | dependency_unavailable |
| OCRS003 | low_text_or_degraded_text | 1501 | NA | dependency_unavailable |
| OCRS004 | low_text_or_degraded_text | 979 | NA | dependency_unavailable |
| OCRS005 | low_text_or_degraded_text | 980 | NA | dependency_unavailable |
| OCRS006 | low_text_or_degraded_text | 980 | NA | dependency_unavailable |

## Interpretation

The project includes OCR fallback code, but the current runtime lacks required dependencies (ModuleNotFoundError: No module named 'fitz'). This smoke test therefore records OCR fallback as dependency unavailable rather than fabricating after-OCR text.

This result separates implementation capability from evaluated benchmark scope: OCR fallback code exists in the project, but the frozen benchmark did not exercise it and this local smoke-test runtime did not have the OCR dependencies required to execute it.
