# PDF Text Quality Audit Report

## Scope

This audit inspected `D:\workspace\123\ccc\astrobiology\data\pdfs` with 668 PDF files. It used existing files and logs only, plus lightweight text-layer extraction from the first 3 pages of each PDF. It did not run OCR, rebuild any Weaviate index, or modify retrieval/end-to-end/contamination-control results.

## Existing OCR/Processing Evidence

- `bench_log.jsonl` records inspected: 464
- Records with an OCR stage field: 32
- Records with nonzero OCR time: 0
- `astrobiology.log` OCR mentions: 0
- `astrobiology.log` scanned/no-text mentions: 0 / 0
- The codebase contains an OCR service and scanned-PDF detector, but the retained benchmark logs do not show OCR being used for the evaluated runs.

## Quality Classes

| quality_class | count |
| --- | --- |
| low_text_or_degraded_text | 10 |
| machine_readable | 657 |
| very_low_text_or_ocr_dependent_candidate | 1 |

## Median Text-Layer Metrics by Class

| quality_class | n | median_sample_chars | median_avg_chars_per_page | median_noise_score |
| --- | --- | --- | --- | --- |
| low_text_or_degraded_text | 10 | 980 | 980.0 | 0.000 |
| machine_readable | 657 | 14279 | 4854.7 | 0.003 |
| very_low_text_or_ocr_dependent_candidate | 1 | 81 | 81.0 | 0.000 |

## Interpretation

The audited corpus is dominated by PDFs with an extractable text layer. A small subset has very little extractable text in the sampled pages and should be treated as low-text or OCR-dependent candidates. The audit did not find enough clearly scanned/OCR-heavy literature PDFs to support a robustness claim for that setting. Because the retained benchmark logs show zero nonzero OCR-stage records, OCR-heavy material was not sufficiently evaluated by the frozen retrieval and answer-generation experiments.
