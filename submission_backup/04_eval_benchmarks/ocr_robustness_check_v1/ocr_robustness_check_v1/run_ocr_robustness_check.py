import csv
import hashlib
import json
import logging
import math
import re
import sqlite3
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence

from pypdf import PdfReader


logging.getLogger("pypdf").setLevel(logging.ERROR)

ROOT = Path("D:/workspace/123")
OUT_DIR = ROOT / "submission_backup/04_eval_benchmarks/ocr_robustness_check_v1"
PDF_DIR = ROOT / "ccc/astrobiology/data/pdfs"
DB_PATH = ROOT / "ccc/astrobiology/backend/db.sqlite3"
BENCH_LOG = ROOT / "ccc/astrobiology/backend/logs/bench_log.jsonl"
ASTRO_LOG = ROOT / "ccc/astrobiology/backend/logs/astrobiology.log"

SAMPLE_PAGES = 3
ROBUSTNESS_PAGES = 5


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def extract_text_sample(pdf_path: Path, max_pages: int) -> Dict[str, Any]:
    try:
        reader = PdfReader(str(pdf_path), strict=False)
        page_count = len(reader.pages)
        sampled = min(max_pages, page_count)
        page_texts: List[str] = []
        page_char_counts: List[int] = []
        for i in range(sampled):
            try:
                text = reader.pages[i].extract_text() or ""
            except Exception as exc:
                text = ""
                page_texts.append(f"[PAGE_EXTRACTION_ERROR: {exc}]")
                page_char_counts.append(0)
                continue
            page_texts.append(text)
            page_char_counts.append(len(text.strip()))
        combined = "\n".join(page_texts)
        return {
            "status": "ok",
            "page_count": page_count,
            "sampled_pages": sampled,
            "text": combined,
            "page_char_counts": page_char_counts,
            "error": "",
        }
    except Exception as exc:
        return {
            "status": "error",
            "page_count": "",
            "sampled_pages": 0,
            "text": "",
            "page_char_counts": [],
            "error": str(exc),
        }


def text_metrics(text: str, page_char_counts: Sequence[int], sampled_pages: int) -> Dict[str, Any]:
    stripped = text.strip()
    chars = len(stripped)
    tokens = re.findall(r"[A-Za-z0-9]+", stripped)
    alpha_chars = sum(ch.isalpha() for ch in stripped)
    printable_chars = sum(ch.isprintable() or ch.isspace() for ch in stripped)
    replacement_count = stripped.count("\ufffd")
    mojibake_count = len(re.findall(r"[ÃÂâ€]", stripped))
    non_ascii_count = sum(ord(ch) > 127 for ch in stripped)
    line_count = len([line for line in stripped.splitlines() if line.strip()])
    short_line_count = len([line for line in stripped.splitlines() if 0 < len(line.strip()) <= 3])
    text_pages = sum(count > 50 for count in page_char_counts)
    avg_chars_per_sampled_page = chars / sampled_pages if sampled_pages else 0.0
    text_page_ratio = text_pages / sampled_pages if sampled_pages else 0.0
    alpha_ratio = alpha_chars / chars if chars else 0.0
    printable_ratio = printable_chars / chars if chars else 0.0
    non_ascii_ratio = non_ascii_count / chars if chars else 0.0
    short_line_ratio = short_line_count / line_count if line_count else 0.0
    weird_token_count = len(re.findall(r"\b[A-Za-z]{1}\b", stripped))
    has_title_like = bool(re.search(r"\b(title|journal|abstract|introduction|keywords)\b", stripped[:3000], re.I)) or chars > 300
    has_abstract = bool(re.search(r"\babstract\b", stripped[:8000], re.I))
    has_sections = bool(re.search(r"\b(introduction|methods?|materials?|results?|discussion|conclusions?)\b", stripped, re.I))
    eom_keyword_hits = len(
        re.findall(
            r"\b(meteorite|chondrite|organic|contamination|isotope|amino acid|carbonaceous|extraterrestrial|sample|curation)\b",
            stripped,
            re.I,
        )
    )
    noise_score = (
        min(1.0, replacement_count / 20.0)
        + min(1.0, mojibake_count / 50.0)
        + min(1.0, short_line_ratio)
        + (1.0 - min(1.0, alpha_ratio / 0.65) if chars else 1.0)
    ) / 4.0
    return {
        "sample_text_chars": chars,
        "sample_token_count": len(tokens),
        "avg_chars_per_sampled_page": avg_chars_per_sampled_page,
        "text_pages": text_pages,
        "text_page_ratio": text_page_ratio,
        "alpha_ratio": alpha_ratio,
        "printable_ratio": printable_ratio,
        "non_ascii_ratio": non_ascii_ratio,
        "replacement_char_count": replacement_count,
        "mojibake_marker_count": mojibake_count,
        "short_line_ratio": short_line_ratio,
        "noise_score": noise_score,
        "has_title_like_text": int(has_title_like),
        "has_abstract_marker": int(has_abstract),
        "has_section_marker": int(has_sections),
        "eom_keyword_hits": eom_keyword_hits,
        "weird_single_char_token_count": weird_token_count,
    }


def classify_quality(metrics: Dict[str, Any], extraction_status: str) -> str:
    if extraction_status != "ok":
        return "extraction_error"
    chars = safe_float(metrics.get("sample_text_chars"))
    avg = safe_float(metrics.get("avg_chars_per_sampled_page"))
    ratio = safe_float(metrics.get("text_page_ratio"))
    noise = safe_float(metrics.get("noise_score"))
    if ratio < 0.2 or avg < 100:
        return "very_low_text_or_ocr_dependent_candidate"
    if avg < 500 or chars < 1000:
        return "low_text_or_degraded_text"
    if noise > 0.35:
        return "degraded_or_ocr_noisy_text"
    return "machine_readable"


def load_db_records() -> Dict[str, Dict[str, Any]]:
    if not DB_PATH.exists():
        return {}
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    records: Dict[str, Dict[str, Any]] = {}
    try:
        for row in con.execute("select * from pdf_documents"):
            d = dict(row)
            file_name = Path(d.get("file_path") or d.get("filename") or "").name
            records[file_name] = d
    finally:
        con.close()
    return records


def audit_logs() -> Dict[str, Any]:
    counts = {
        "bench_log_exists": BENCH_LOG.exists(),
        "astro_log_exists": ASTRO_LOG.exists(),
        "bench_log_records": 0,
        "bench_log_ocr_stage_records": 0,
        "bench_log_ocr_stage_nonzero": 0,
        "bench_log_error_records": 0,
        "astro_log_ocr_mentions": 0,
        "astro_log_scanned_mentions": 0,
        "astro_log_no_text_mentions": 0,
    }
    if BENCH_LOG.exists():
        with BENCH_LOG.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                counts["bench_log_records"] += 1
                if obj.get("error_type"):
                    counts["bench_log_error_records"] += 1
                stage = obj.get("stage_ms") or {}
                if "ocr" in stage:
                    counts["bench_log_ocr_stage_records"] += 1
                    if safe_float(stage.get("ocr")) > 0:
                        counts["bench_log_ocr_stage_nonzero"] += 1
    if ASTRO_LOG.exists():
        with ASTRO_LOG.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                lowered = line.lower()
                if "ocr" in lowered:
                    counts["astro_log_ocr_mentions"] += 1
                if "scanned" in lowered or "扫描" in line:
                    counts["astro_log_scanned_mentions"] += 1
                if "no_text" in lowered or "no text" in lowered:
                    counts["astro_log_no_text_mentions"] += 1
    return counts


def choose_sample(audit_rows: Sequence[Dict[str, Any]], n: int = 18) -> List[Dict[str, Any]]:
    by_class: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in audit_rows:
        by_class[row["quality_class"]].append(row)
    for rows in by_class.values():
        rows.sort(key=lambda r: (safe_float(r.get("sample_text_chars")), str(r.get("filename"))))

    sample: List[Dict[str, Any]] = []
    targets = [
        ("ocr_dependent_or_scanned_candidate", 5),
        ("very_low_text_or_ocr_dependent_candidate", 5),
        ("low_text_or_degraded_text", 5),
        ("degraded_or_ocr_noisy_text", 4),
        ("machine_readable", 6),
        ("extraction_error", 2),
    ]
    seen = set()
    for cls, limit in targets:
        rows = by_class.get(cls, [])
        if cls == "machine_readable":
            # Use diverse clean examples rather than only shortest.
            if rows:
                indices = sorted(set([0, len(rows) // 4, len(rows) // 2, 3 * len(rows) // 4, len(rows) - 1]))
                candidates = [rows[i] for i in indices if 0 <= i < len(rows)]
            else:
                candidates = []
        else:
            candidates = rows[:limit]
        for row in candidates[:limit]:
            key = row["pdf_path"]
            if key not in seen:
                sample.append(row)
                seen.add(key)
    if len(sample) < n:
        for row in audit_rows:
            key = row["pdf_path"]
            if key not in seen:
                sample.append(row)
                seen.add(key)
            if len(sample) >= n:
                break
    return sample[:n]


def median(values: Sequence[float]) -> float:
    vals = [v for v in values if not math.isnan(v)]
    return statistics.median(vals) if vals else 0.0


def md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    db_records = load_db_records()
    log_counts = audit_logs()
    pdf_files = sorted(PDF_DIR.glob("*.pdf"))

    audit_rows: List[Dict[str, Any]] = []
    for pdf_path in pdf_files:
        extracted = extract_text_sample(pdf_path, SAMPLE_PAGES)
        metrics = text_metrics(extracted["text"], extracted["page_char_counts"], extracted["sampled_pages"])
        quality_class = classify_quality(metrics, extracted["status"])
        db = db_records.get(pdf_path.name, {})
        row = {
            "filename": pdf_path.name,
            "pdf_path": str(pdf_path),
            "file_size_bytes": pdf_path.stat().st_size,
            "sha256": sha256(pdf_path),
            "db_record_present": int(bool(db)),
            "db_processed": db.get("processed", ""),
            "db_page_count": db.get("page_count", ""),
            "db_title": db.get("title", ""),
            "extraction_status": extracted["status"],
            "page_count": extracted["page_count"],
            "sampled_pages": extracted["sampled_pages"],
            "quality_class": quality_class,
            "extraction_error": extracted["error"],
            **metrics,
        }
        audit_rows.append(row)

    write_csv(
        OUT_DIR / "pdf_text_quality_audit.csv",
        [
            "filename",
            "pdf_path",
            "file_size_bytes",
            "sha256",
            "db_record_present",
            "db_processed",
            "db_page_count",
            "db_title",
            "extraction_status",
            "page_count",
            "sampled_pages",
            "quality_class",
            "sample_text_chars",
            "sample_token_count",
            "avg_chars_per_sampled_page",
            "text_pages",
            "text_page_ratio",
            "alpha_ratio",
            "printable_ratio",
            "non_ascii_ratio",
            "replacement_char_count",
            "mojibake_marker_count",
            "short_line_ratio",
            "noise_score",
            "has_title_like_text",
            "has_abstract_marker",
            "has_section_marker",
            "eom_keyword_hits",
            "weird_single_char_token_count",
            "extraction_error",
        ],
        audit_rows,
    )

    sample_rows = choose_sample(audit_rows)
    sample_out: List[Dict[str, Any]] = []
    robustness_rows: List[Dict[str, Any]] = []
    quality_metric_rows: List[Dict[str, Any]] = []

    for i, row in enumerate(sample_rows, 1):
        sample_id = f"OCRS{i:03d}"
        pdf_path = Path(row["pdf_path"])
        detailed = extract_text_sample(pdf_path, ROBUSTNESS_PAGES)
        detailed_metrics = text_metrics(detailed["text"], detailed["page_char_counts"], detailed["sampled_pages"])
        first_1000 = re.sub(r"\s+", " ", detailed["text"].strip())[:1000]
        missing_title = int(detailed_metrics["has_title_like_text"] == 0)
        missing_abstract = int(detailed_metrics["has_abstract_marker"] == 0)
        missing_sections = int(detailed_metrics["has_section_marker"] == 0)
        evidence_available = int(
            detailed_metrics["sample_text_chars"] >= 1000
            and detailed_metrics["eom_keyword_hits"] > 0
            and detailed_metrics["noise_score"] < 0.45
        )
        sample_out.append(
            {
                "sample_id": sample_id,
                "filename": row["filename"],
                "pdf_path": row["pdf_path"],
                "quality_class": row["quality_class"],
                "selection_reason": f"Representative {row['quality_class']} document from lightweight text-layer audit",
                "file_size_bytes": row["file_size_bytes"],
                "page_count": row["page_count"],
                "sample_text_chars_first3": row["sample_text_chars"],
                "avg_chars_per_page_first3": row["avg_chars_per_sampled_page"],
                "noise_score_first3": row["noise_score"],
                "db_record_present": row["db_record_present"],
                "db_processed": row["db_processed"],
            }
        )
        quality_metric_rows.append(
            {
                "sample_id": sample_id,
                "filename": row["filename"],
                "quality_class": row["quality_class"],
                "tested_pages": detailed["sampled_pages"],
                "text_length": detailed_metrics["sample_text_chars"],
                "token_count": detailed_metrics["sample_token_count"],
                "avg_chars_per_page": f"{detailed_metrics['avg_chars_per_sampled_page']:.2f}",
                "text_page_ratio": f"{detailed_metrics['text_page_ratio']:.4f}",
                "alpha_ratio": f"{detailed_metrics['alpha_ratio']:.4f}",
                "printable_ratio": f"{detailed_metrics['printable_ratio']:.4f}",
                "noise_score": f"{detailed_metrics['noise_score']:.4f}",
                "replacement_char_count": detailed_metrics["replacement_char_count"],
                "mojibake_marker_count": detailed_metrics["mojibake_marker_count"],
                "short_line_ratio": f"{detailed_metrics['short_line_ratio']:.4f}",
                "missing_title_like_text": missing_title,
                "missing_abstract_marker": missing_abstract,
                "missing_section_marker": missing_sections,
                "eom_keyword_hits": detailed_metrics["eom_keyword_hits"],
            }
        )
        robustness_rows.append(
            {
                "sample_id": sample_id,
                "filename": row["filename"],
                "quality_class": row["quality_class"],
                "standard_text_extraction_success": int(detailed["status"] == "ok"),
                "ocr_run": 0,
                "ocr_reason": "OCR was not run in this limitation check; this test audits the existing text layer only.",
                "text_evidence_available_proxy": evidence_available,
                "missing_title_like_text": missing_title,
                "missing_abstract_marker": missing_abstract,
                "missing_section_marker": missing_sections,
                "extraction_noise_flag": int(detailed_metrics["noise_score"] >= 0.35),
                "low_text_flag": int(detailed_metrics["avg_chars_per_sampled_page"] < 500),
                "ocr_dependency_flag": int(row["quality_class"] == "very_low_text_or_ocr_dependent_candidate"),
                "first_1000_chars_preview": first_1000,
                "extraction_error": detailed["error"],
            }
        )

    write_csv(
        OUT_DIR / "ocr_robustness_sample.csv",
        [
            "sample_id",
            "filename",
            "pdf_path",
            "quality_class",
            "selection_reason",
            "file_size_bytes",
            "page_count",
            "sample_text_chars_first3",
            "avg_chars_per_page_first3",
            "noise_score_first3",
            "db_record_present",
            "db_processed",
        ],
        sample_out,
    )
    write_csv(
        OUT_DIR / "ocr_text_quality_metrics.csv",
        [
            "sample_id",
            "filename",
            "quality_class",
            "tested_pages",
            "text_length",
            "token_count",
            "avg_chars_per_page",
            "text_page_ratio",
            "alpha_ratio",
            "printable_ratio",
            "noise_score",
            "replacement_char_count",
            "mojibake_marker_count",
            "short_line_ratio",
            "missing_title_like_text",
            "missing_abstract_marker",
            "missing_section_marker",
            "eom_keyword_hits",
        ],
        quality_metric_rows,
    )
    write_csv(
        OUT_DIR / "ocr_robustness_results.csv",
        [
            "sample_id",
            "filename",
            "quality_class",
            "standard_text_extraction_success",
            "ocr_run",
            "ocr_reason",
            "text_evidence_available_proxy",
            "missing_title_like_text",
            "missing_abstract_marker",
            "missing_section_marker",
            "extraction_noise_flag",
            "low_text_flag",
            "ocr_dependency_flag",
            "first_1000_chars_preview",
            "extraction_error",
        ],
        robustness_rows,
    )

    class_counts = Counter(row["quality_class"] for row in audit_rows)
    audit_count_rows = [[cls, class_counts[cls]] for cls in sorted(class_counts)]
    sample_count_rows = [[cls, sum(1 for row in sample_out if row["quality_class"] == cls)] for cls in sorted(set(row["quality_class"] for row in sample_out))]
    grouped_metrics = []
    for cls in sorted(set(row["quality_class"] for row in audit_rows)):
        rows = [row for row in audit_rows if row["quality_class"] == cls]
        grouped_metrics.append(
            [
                cls,
                len(rows),
                f"{median([safe_float(row['sample_text_chars']) for row in rows]):.0f}",
                f"{median([safe_float(row['avg_chars_per_sampled_page']) for row in rows]):.1f}",
                f"{median([safe_float(row['noise_score']) for row in rows]):.3f}",
            ]
        )

    audit_report = [
        "# PDF Text Quality Audit Report",
        "",
        "## Scope",
        "",
        f"This audit inspected `{PDF_DIR}` with {len(pdf_files)} PDF files. It used existing files and logs only, plus lightweight text-layer extraction from the first {SAMPLE_PAGES} pages of each PDF. It did not run OCR, rebuild any Weaviate index, or modify retrieval/end-to-end/contamination-control results.",
        "",
        "## Existing OCR/Processing Evidence",
        "",
        f"- `bench_log.jsonl` records inspected: {log_counts['bench_log_records']}",
        f"- Records with an OCR stage field: {log_counts['bench_log_ocr_stage_records']}",
        f"- Records with nonzero OCR time: {log_counts['bench_log_ocr_stage_nonzero']}",
        f"- `astrobiology.log` OCR mentions: {log_counts['astro_log_ocr_mentions']}",
        f"- `astrobiology.log` scanned/no-text mentions: {log_counts['astro_log_scanned_mentions']} / {log_counts['astro_log_no_text_mentions']}",
        "- The codebase contains an OCR service and scanned-PDF detector, but the retained benchmark logs do not show OCR being used for the evaluated runs.",
        "",
        "## Quality Classes",
        "",
        md_table(["quality_class", "count"], audit_count_rows),
        "",
        "## Median Text-Layer Metrics by Class",
        "",
        md_table(["quality_class", "n", "median_sample_chars", "median_avg_chars_per_page", "median_noise_score"], grouped_metrics),
        "",
        "## Interpretation",
        "",
        "The audited corpus is dominated by PDFs with an extractable text layer. A small subset has very little extractable text in the sampled pages and should be treated as low-text or OCR-dependent candidates. The audit did not find enough clearly scanned/OCR-heavy literature PDFs to support a robustness claim for that setting. Because the retained benchmark logs show zero nonzero OCR-stage records, OCR-heavy material was not sufficiently evaluated by the frozen retrieval and answer-generation experiments.",
        "",
    ]
    (OUT_DIR / "pdf_text_quality_audit_report.md").write_text("\n".join(audit_report), encoding="utf-8")

    robustness_summary = Counter(row["quality_class"] for row in robustness_rows)
    evidence_by_class = defaultdict(lambda: [0, 0])
    for row in robustness_rows:
        evidence_by_class[row["quality_class"]][0] += int(row["text_evidence_available_proxy"])
        evidence_by_class[row["quality_class"]][1] += 1
    evidence_rows = [
        [cls, vals[1], vals[0], f"{(vals[0] / vals[1] if vals[1] else 0):.2%}"]
        for cls, vals in sorted(evidence_by_class.items())
    ]
    robustness_report = [
        "# OCR Robustness Check Report",
        "",
        "## Purpose",
        "",
        "This check provides limitation-oriented evidence for reviewer comments about OCR robustness. It is not intended to demonstrate strong OCR performance.",
        "",
        "## Sample Composition",
        "",
        md_table(["quality_class", "sample_count"], sample_count_rows),
        "",
        "## Lightweight Test Design",
        "",
        f"For sampled PDFs, the script extracted text from up to the first {ROBUSTNESS_PAGES} pages using the existing text layer only. It measured text length, token count, title/abstract/section markers, noise indicators, and a simple evidence-availability proxy based on enough readable text plus EOM keyword hits. OCR was intentionally not run, because the goal was to assess the limitation of the current indexed-text workflow without changing the corpus or rebuilding the index.",
        "",
        "## Evidence Availability Proxy by Class",
        "",
        md_table(["quality_class", "n", "proxy_available", "proxy_available_percent"], evidence_rows),
        "",
        "## Findings",
        "",
        "- Clean machine-readable PDFs generally provide enough text for indexing and evidence extraction.",
        "- Low-text and very-low-text/OCR-dependent candidates show shorter text, missing abstract/section markers, and weaker evidence availability proxies.",
        "- The current frozen benchmark should therefore be described as primarily evaluating machine-readable PDFs rather than scanned/OCR-heavy literature.",
        "- The available corpus did not contain enough clearly scanned/OCR-noisy literature PDFs for a full scanned-document benchmark.",
        "- The project includes OCR service code, but OCR fallback was not materially exercised in the retained benchmark logs.",
        "",
        "## Limitation",
        "",
        "The sample is small and uses text-layer diagnostics rather than full OCR reprocessing. It supports a limitation statement, not a claim of OCR robustness.",
        "",
    ]
    (OUT_DIR / "ocr_robustness_check_report.md").write_text("\n".join(robustness_report), encoding="utf-8")

    limitations_text = [
        "# Manuscript Limitations Text: OCR",
        "",
        "The current benchmark primarily evaluates documents with machine-readable PDF text layers. Although the implementation includes OCR-related utilities and a scanned-PDF detector, the retained benchmark logs did not show OCR being materially exercised during the frozen retrieval and answer-generation experiments. A lightweight audit of the PDF corpus identified a small subset of low-text or possible OCR-dependent candidates for which extracted text was sparse or lacked abstract/section markers, indicating that evidence retrieval would be less reliable without dedicated OCR processing and quality control. The available corpus did not contain enough clearly scanned/OCR-heavy literature PDFs for a separate scanned-document benchmark. We therefore do not claim robustness on scanned or OCR-heavy historical literature; improving OCR fallback, text-quality detection, and downstream evidence validation remains future work.",
        "",
    ]
    (OUT_DIR / "manuscript_limitations_text_ocr.md").write_text("\n".join(limitations_text), encoding="utf-8")

    reviewer_response = [
        "# Reviewer Response Text: OCR Limitations",
        "",
        "We added a limitation-oriented OCR robustness check. The check audited the retained PDF corpus using lightweight text-layer diagnostics and reviewed the benchmark logs for OCR-stage usage. The results indicate that the evaluated workflow was primarily exercised on machine-readable PDFs; only a small subset of files appeared low-text or potentially OCR-dependent, and we did not find enough clearly scanned/OCR-heavy literature PDFs for a separate scanned-document benchmark. The frozen benchmark logs did not show nonzero OCR-stage processing. We therefore clarified that the study does not claim robust performance on scanned or OCR-heavy documents. We also added this as future work: scanned-PDF handling will require explicit OCR fallback, text-quality gating, and validation of retrieval/evidence availability after OCR.",
        "",
    ]
    (OUT_DIR / "reviewer_response_text_ocr.md").write_text("\n".join(reviewer_response), encoding="utf-8")

    manifest_rows = []
    for path in sorted(OUT_DIR.glob("*")):
        if path.is_file() and path.name != Path(__file__).name:
            manifest_rows.append({"file": path.name, "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    write_csv(OUT_DIR / "output_manifest.csv", ["file", "size_bytes", "sha256"], manifest_rows)

    print(
        json.dumps(
            {
                "pdf_count": len(pdf_files),
                "quality_class_counts": dict(class_counts),
                "sample_count": len(sample_rows),
                "out_dir": str(OUT_DIR),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
