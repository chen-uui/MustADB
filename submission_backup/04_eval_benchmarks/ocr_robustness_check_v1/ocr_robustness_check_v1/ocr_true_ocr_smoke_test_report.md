# True OCR Smoke Test Report

## Scope

This true-OCR smoke test updates only OCR robustness artifacts in this directory. It does not modify the main retrieval index, rebuild Weaviate, change frozen retrieval/end-to-end/contamination results, or edit manuscript text.

## Runtime

- PyMuPDF/fitz available: True
- pytesseract available: True
- PIL/Pillow available: True
- Tesseract executable: `C:\Program Files\Tesseract-OCR\tesseract.exe`
- Tesseract version: tesseract v5.4.0.20240606
- OCR DPI: 200
- Pages rendered per PDF: up to 5

## Sample Summary

- Selected PDFs: 6
- Accessible PDFs: 6/6
- Quality-class distribution: {'very_low_text_or_ocr_dependent_candidate': 1, 'low_text_or_degraded_text': 5}
- True OCR success rows: 6/6
- Rows with increased OCR text length versus text layer: 3/6
- Rows with increased OCR token count versus text layer: 2/6
- Rows with increased EOM keyword hits: 2/6
- Rows with improved evidence-availability proxy: 2/6

## Interpretation

Selected low-text cases showed partial text recovery. OCR-heavy documents require OCR quality control and post-OCR evidence validation; this smoke test should not be interpreted as full OCR robustness evaluation.

The comparison explicitly separates text-layer extraction (`before_*`) from rendered-page OCR-recognized text (`after_*`). OCR output quality varies by PDF and should be validated before downstream retrieval or evidence extraction.

## Output

- `D:\workspace\123\submission_backup\04_eval_benchmarks\ocr_robustness_check_v1\ocr_true_ocr_smoke_test_results.csv`