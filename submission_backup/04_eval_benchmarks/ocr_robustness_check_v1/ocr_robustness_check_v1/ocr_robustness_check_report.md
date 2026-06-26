# OCR Robustness Check Report

## Purpose

This check provides limitation-oriented evidence for reviewer comments about OCR robustness. It is not intended to demonstrate strong OCR performance.

## Sample Composition

| quality_class | sample_count |
| --- | --- |
| low_text_or_degraded_text | 5 |
| machine_readable | 12 |
| very_low_text_or_ocr_dependent_candidate | 1 |

## Lightweight Test Design

For sampled PDFs, the script extracted text from up to the first 5 pages using the existing text layer only. It measured text length, token count, title/abstract/section markers, noise indicators, and a simple evidence-availability proxy based on enough readable text plus EOM keyword hits. OCR was intentionally not run, because the goal was to assess the limitation of the current indexed-text workflow without changing the corpus or rebuilding the index.

## Evidence Availability Proxy by Class

| quality_class | n | proxy_available | proxy_available_percent |
| --- | --- | --- | --- |
| low_text_or_degraded_text | 5 | 0 | 0.00% |
| machine_readable | 12 | 9 | 75.00% |
| very_low_text_or_ocr_dependent_candidate | 1 | 0 | 0.00% |

## Findings

- Clean machine-readable PDFs generally provide enough text for indexing and evidence extraction.
- Low-text and very-low-text/OCR-dependent candidates show shorter text, missing abstract/section markers, and weaker evidence availability proxies.
- The current frozen benchmark should therefore be described as primarily evaluating machine-readable PDFs rather than scanned/OCR-heavy literature.
- The available corpus did not contain enough clearly scanned/OCR-noisy literature PDFs for a full scanned-document benchmark.
- The project includes OCR service code, but OCR fallback was not materially exercised in the retained benchmark logs.

## Limitation

The sample is small and uses text-layer diagnostics rather than full OCR reprocessing. It supports a limitation statement, not a claim of OCR robustness.
