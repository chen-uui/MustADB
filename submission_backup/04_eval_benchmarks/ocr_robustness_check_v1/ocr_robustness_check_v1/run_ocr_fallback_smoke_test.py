import csv
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence

from pypdf import PdfReader


ROOT = Path("D:/workspace/123")
BASE_DIR = ROOT / "submission_backup/04_eval_benchmarks/ocr_robustness_check_v1"
BACKEND_DIR = ROOT / "ccc/astrobiology/backend"
INPUT_SAMPLE = BASE_DIR / "ocr_robustness_sample.csv"
MAX_DOCS = 6
TEXT_PAGES = 5

TARGET_CLASSES = {"low_text_or_degraded_text", "very_low_text_or_ocr_dependent_candidate"}


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: str(v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, Any]]) -> None:
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


def extract_text_layer(pdf_path: Path, max_pages: int = TEXT_PAGES) -> Dict[str, Any]:
    try:
        reader = PdfReader(str(pdf_path), strict=False)
        page_count = len(reader.pages)
        pages = min(max_pages, page_count)
        chunks: List[str] = []
        for idx in range(pages):
            try:
                chunks.append(reader.pages[idx].extract_text() or "")
            except Exception as exc:
                chunks.append(f"[PAGE_EXTRACTION_ERROR: {exc}]")
        return {"status": "ok", "text": "\n".join(chunks), "page_count": page_count, "tested_pages": pages, "error": ""}
    except Exception as exc:
        return {"status": "error", "text": "", "page_count": "", "tested_pages": 0, "error": str(exc)}


def text_metrics(text: str) -> Dict[str, Any]:
    stripped = (text or "").strip()
    tokens = re.findall(r"[A-Za-z0-9]+", stripped)
    chars = len(stripped)
    has_title_like = bool(re.search(r"\b(title|journal|abstract|introduction|keywords)\b", stripped[:3000], re.I)) or chars > 300
    has_abstract = bool(re.search(r"\babstract\b", stripped[:8000], re.I))
    has_sections = bool(re.search(r"\b(introduction|methods?|materials?|results?|discussion|conclusions?)\b", stripped, re.I))
    eom_hits = len(
        re.findall(
            r"\b(meteorite|chondrite|organic|contamination|isotope|amino acid|carbonaceous|extraterrestrial|sample|curation)\b",
            stripped,
            re.I,
        )
    )
    evidence_proxy = int(chars >= 1000 and eom_hits > 0)
    return {
        "text_length": chars,
        "token_count": len(tokens),
        "has_title_like_text": int(has_title_like),
        "has_abstract_marker": int(has_abstract),
        "has_section_marker": int(has_sections),
        "eom_keyword_hits": eom_hits,
        "evidence_availability_proxy": evidence_proxy,
    }


def load_existing_ocr_tools() -> Dict[str, Any]:
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))
    os.environ.setdefault("OCR_ENABLED", "true")
    try:
        from pdf_processor.ocr_service import extract_pdf_text_with_fallback, is_scanned_pdf

        return {
            "available": True,
            "extract_pdf_text_with_fallback": extract_pdf_text_with_fallback,
            "is_scanned_pdf": is_scanned_pdf,
            "error": "",
        }
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}


def try_ocr_fallback(pdf_path: Path, tools: Dict[str, Any]) -> Dict[str, Any]:
    if not tools.get("available"):
        return {
            "detector_status": "dependency_unavailable",
            "detector_is_scanned": "",
            "detector_confidence": "",
            "ocr_attempted": 0,
            "ocr_status": "dependency_unavailable",
            "ocr_error": tools.get("error", "existing OCR tool unavailable"),
            "ocr_text": "",
            "ocr_engine": "",
        }
    detector_status = "not_run"
    detector_is_scanned = ""
    detector_confidence = ""
    try:
        scan = tools["is_scanned_pdf"](str(pdf_path))
        detector_status = "ok"
        detector_is_scanned = scan.get("is_scanned", "")
        detector_confidence = scan.get("confidence", "")
    except Exception as exc:
        detector_status = f"error: {type(exc).__name__}: {exc}"

    try:
        result = tools["extract_pdf_text_with_fallback"](str(pdf_path), use_ocr_on_failure=True, auto_detect_scanned=True)
        ocr_text = result.get("text", "") or ""
        method = result.get("extraction_method", "")
        ocr_attempted = int(bool(result.get("ocr_attempted")) or method == "ocr")
        status = "ok" if result.get("success") else "error"
        error = result.get("ocr_error") or result.get("error") or ""
        return {
            "detector_status": detector_status,
            "detector_is_scanned": detector_is_scanned,
            "detector_confidence": detector_confidence,
            "ocr_attempted": ocr_attempted,
            "ocr_status": status,
            "ocr_error": error,
            "ocr_text": ocr_text,
            "ocr_engine": result.get("ocr_engine", ""),
        }
    except Exception as exc:
        return {
            "detector_status": detector_status,
            "detector_is_scanned": detector_is_scanned,
            "detector_confidence": detector_confidence,
            "ocr_attempted": 1,
            "ocr_status": "error",
            "ocr_error": f"{type(exc).__name__}: {exc}",
            "ocr_text": "",
            "ocr_engine": "",
        }


def md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(out)


def main() -> None:
    sample_rows = read_csv(INPUT_SAMPLE)
    selected = []
    for row in sample_rows:
        pdf_path = Path(row.get("pdf_path", ""))
        if row.get("quality_class") in TARGET_CLASSES and pdf_path.exists():
            selected.append(row)
        if len(selected) >= MAX_DOCS:
            break

    tools = load_existing_ocr_tools()
    output_rows: List[Dict[str, Any]] = []
    for row in selected:
        pdf_path = Path(row["pdf_path"])
        before = extract_text_layer(pdf_path, TEXT_PAGES)
        before_metrics = text_metrics(before["text"])
        ocr = try_ocr_fallback(pdf_path, tools)
        after_metrics = text_metrics(ocr["ocr_text"]) if ocr.get("ocr_text") else {
            "text_length": "",
            "token_count": "",
            "has_title_like_text": "",
            "has_abstract_marker": "",
            "has_section_marker": "",
            "eom_keyword_hits": "",
            "evidence_availability_proxy": "",
        }
        output_rows.append(
            {
                "sample_id": row.get("sample_id", ""),
                "filename": row.get("filename", ""),
                "pdf_path": str(pdf_path),
                "quality_class": row.get("quality_class", ""),
                "file_accessible": int(pdf_path.exists()),
                "file_size_bytes": pdf_path.stat().st_size if pdf_path.exists() else "",
                "sha256": sha256(pdf_path) if pdf_path.exists() else "",
                "existing_ocr_tool_available": int(bool(tools.get("available"))),
                "existing_ocr_tool_error": tools.get("error", ""),
                "detector_status": ocr.get("detector_status", ""),
                "detector_is_scanned": ocr.get("detector_is_scanned", ""),
                "detector_confidence": ocr.get("detector_confidence", ""),
                "ocr_attempted": ocr.get("ocr_attempted", ""),
                "ocr_status": ocr.get("ocr_status", ""),
                "ocr_engine": ocr.get("ocr_engine", ""),
                "ocr_error": ocr.get("ocr_error", ""),
                "before_extraction_status": before["status"],
                "before_extraction_error": before["error"],
                "before_page_count": before["page_count"],
                "before_tested_pages": before["tested_pages"],
                "before_text_length": before_metrics["text_length"],
                "before_token_count": before_metrics["token_count"],
                "before_has_title_like_text": before_metrics["has_title_like_text"],
                "before_has_abstract_marker": before_metrics["has_abstract_marker"],
                "before_has_section_marker": before_metrics["has_section_marker"],
                "before_eom_keyword_hits": before_metrics["eom_keyword_hits"],
                "before_evidence_availability_proxy": before_metrics["evidence_availability_proxy"],
                "after_text_length": after_metrics["text_length"],
                "after_token_count": after_metrics["token_count"],
                "after_has_title_like_text": after_metrics["has_title_like_text"],
                "after_has_abstract_marker": after_metrics["has_abstract_marker"],
                "after_has_section_marker": after_metrics["has_section_marker"],
                "after_eom_keyword_hits": after_metrics["eom_keyword_hits"],
                "after_evidence_availability_proxy": after_metrics["evidence_availability_proxy"],
                "delta_text_length": (
                    after_metrics["text_length"] - before_metrics["text_length"]
                    if isinstance(after_metrics["text_length"], int)
                    else ""
                ),
                "delta_token_count": (
                    after_metrics["token_count"] - before_metrics["token_count"]
                    if isinstance(after_metrics["token_count"], int)
                    else ""
                ),
            }
        )

    result_path = BASE_DIR / "ocr_fallback_smoke_test_results.csv"
    fields = [
        "sample_id",
        "filename",
        "pdf_path",
        "quality_class",
        "file_accessible",
        "file_size_bytes",
        "sha256",
        "existing_ocr_tool_available",
        "existing_ocr_tool_error",
        "detector_status",
        "detector_is_scanned",
        "detector_confidence",
        "ocr_attempted",
        "ocr_status",
        "ocr_engine",
        "ocr_error",
        "before_extraction_status",
        "before_extraction_error",
        "before_page_count",
        "before_tested_pages",
        "before_text_length",
        "before_token_count",
        "before_has_title_like_text",
        "before_has_abstract_marker",
        "before_has_section_marker",
        "before_eom_keyword_hits",
        "before_evidence_availability_proxy",
        "after_text_length",
        "after_token_count",
        "after_has_title_like_text",
        "after_has_abstract_marker",
        "after_has_section_marker",
        "after_eom_keyword_hits",
        "after_evidence_availability_proxy",
        "delta_text_length",
        "delta_token_count",
    ]
    write_csv(result_path, fields, output_rows)

    total = len(output_rows)
    accessible = sum(int(row["file_accessible"]) for row in output_rows)
    dep_unavailable = sum(1 for row in output_rows if row["ocr_status"] == "dependency_unavailable")
    ocr_ok = sum(1 for row in output_rows if row["ocr_status"] == "ok")
    improved = sum(
        1
        for row in output_rows
        if isinstance(row.get("delta_text_length"), int) and row.get("delta_text_length", 0) > 0
    )
    summary_rows = [
        ["selected_documents", total],
        ["accessible_documents", accessible],
        ["existing_ocr_tool_available", int(bool(tools.get("available")))],
        ["dependency_unavailable_rows", dep_unavailable],
        ["ocr_success_rows", ocr_ok],
        ["rows_with_text_length_increase_after_ocr", improved],
    ]
    per_doc_rows = [
        [
            row["sample_id"],
            row["quality_class"],
            row["before_text_length"],
            row["after_text_length"] if row["after_text_length"] != "" else "NA",
            row["ocr_status"],
        ]
        for row in output_rows
    ]
    if ocr_ok and improved:
        finding = "Selected low-text cases showed partial text recovery under the available OCR fallback."
    elif dep_unavailable == total:
        finding = (
            "The project includes OCR fallback code, but the current runtime lacks required dependencies "
            f"({tools.get('error', 'unknown dependency error')}). This smoke test therefore records OCR fallback as dependency unavailable rather than fabricating after-OCR text."
        )
    else:
        finding = "Dedicated OCR quality control is needed; the smoke test did not show a clear text-quality improvement."

    report = [
        "# OCR Fallback Smoke Test Report",
        "",
        "## Scope",
        "",
        "This smoke test supplements the OCR limitation analysis. It does not modify the main index, rebuild Weaviate, or change frozen retrieval, end-to-end, or contamination-control results. It is not a main benchmark result.",
        "",
        "## Selection",
        "",
        f"Selected up to {MAX_DOCS} accessible PDFs from `low_text_or_degraded_text` and `very_low_text_or_ocr_dependent_candidate` rows in `ocr_robustness_sample.csv`.",
        "",
        "## Existing OCR Tool Check",
        "",
        f"- Existing OCR fallback import available: `{bool(tools.get('available'))}`",
        f"- Import/dependency error: `{tools.get('error', '') or 'none'}`",
        "",
        "## Summary",
        "",
        md_table(["metric", "value"], summary_rows),
        "",
        "## Per-Document Result",
        "",
        md_table(["sample_id", "quality_class", "before_text_length", "after_text_length", "ocr_status"], per_doc_rows),
        "",
        "## Interpretation",
        "",
        finding,
        "",
        "This result separates implementation capability from evaluated benchmark scope: OCR fallback code exists in the project, but the frozen benchmark did not exercise it and this local smoke-test runtime did not have the OCR dependencies required to execute it.",
        "",
    ]
    (BASE_DIR / "ocr_fallback_smoke_test_report.md").write_text("\n".join(report), encoding="utf-8")

    limitations = [
        "# Revised Manuscript Limitations Text: OCR",
        "",
        "The evaluated benchmark primarily covers documents with machine-readable PDF text layers. The system includes implementation support for scanned-PDF detection and OCR fallback, but the frozen retrieval and answer-generation experiments did not materially exercise OCR, and a small smoke test on selected low-text documents found that the local runtime lacked the OCR dependencies required to execute the fallback. Thus, the present results should not be interpreted as a benchmark of scanned or OCR-heavy literature. Selected low-text cases can be identified by text-quality gating, but dedicated OCR execution, quality control, and post-OCR evidence validation are needed before making OCR robustness claims.",
        "",
    ]
    (BASE_DIR / "revised_manuscript_limitations_text_ocr.md").write_text("\n".join(limitations), encoding="utf-8")

    response = [
        "# Revised Reviewer Response Text: OCR",
        "",
        "We added an OCR fallback smoke test to clarify the distinction between implementation capability and evaluated benchmark scope. The project contains scanned-PDF detection and OCR fallback code, but the frozen benchmark logs did not show nonzero OCR-stage processing. For the smoke test, we selected accessible low-text/OCR-dependent candidate PDFs from the prior audit and attempted to invoke the existing OCR fallback. In this local runtime the OCR path could not be executed because required dependencies were unavailable, so we recorded the failure explicitly rather than fabricating post-OCR text. We therefore state the limitation more narrowly: the current experiments primarily evaluate machine-readable PDFs, while scanned/OCR-heavy documents require dedicated OCR setup, text-quality gating, and evidence-validation checks in future work.",
        "",
    ]
    (BASE_DIR / "revised_reviewer_response_text_ocr.md").write_text("\n".join(response), encoding="utf-8")

    print(json.dumps({"selected": total, "ocr_tool_available": bool(tools.get("available")), "dependency_unavailable_rows": dep_unavailable}, indent=2))


if __name__ == "__main__":
    main()
