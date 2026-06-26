# OCR Fallback Smoke Test Report (Rerun)

## Scope

This rerun only updates the OCR robustness smoke-test artifacts in this directory. It does not modify the main retrieval index, Weaviate collection, frozen retrieval/end-to-end/contamination results, or manuscript text.

## Runtime Dependency Check

- PyMuPDF/fitz available: True
- PyMuPDF version string: PyMuPDF 1.27.2.3: Python bindings for the MuPDF 1.27.2 library.
- PIL available: True
- numpy available: True
- easyocr available: False
- pytesseract available: False
- paddleocr available: False
- pdf2image available: False
- tesseract binary: not found

## Project OCR Tool Check

- Project OCR service imported: True
- OCR engine available through project service: False
- OCR engine selected: none
- OCR service note: OCR runtime dependency incomplete: no OCR engine available (default easyocr missing; pytesseract/paddleocr unavailable or tesseract binary absent).

## Sample Summary

- Selected rows: 6
- Accessible PDFs: 6/6
- Quality-class distribution: {'very_low_text_or_ocr_dependent_candidate': 1, 'low_text_or_degraded_text': 5}
- OCR attempted through project fallback entry point: 6/6
- True OCR success rows: 0/6
- PyMuPDF page-render probe success rows: 6/6
- Rows with text-length increase after true OCR: 0/6

## Interpretation

True OCR did not complete in this runtime because the OCR runtime dependency is incomplete. The project OCR service can be imported and PyMuPDF can extract text layers and render pages, but no OCR engine is available (`easyocr`, `pytesseract`/system Tesseract, and `paddleocr` are absent).

The `after_*` fields therefore represent PyMuPDF text-layer fallback for these rows, not OCR-recognized text. This is an implementation smoke test of the fallback path and dependency state, not a main benchmark result.

## Result File

- `D:\workspace\123\submission_backup\04_eval_benchmarks\ocr_robustness_check_v1\ocr_fallback_smoke_test_results_rerun.csv`