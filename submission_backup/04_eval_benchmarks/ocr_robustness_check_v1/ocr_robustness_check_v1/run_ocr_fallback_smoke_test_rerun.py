from __future__ import annotations

import csv
import importlib.util
import os
import re
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


ROOT = Path(r"D:\workspace\123")
BASE_DIR = ROOT / "submission_backup" / "04_eval_benchmarks" / "ocr_robustness_check_v1"
INPUT_SAMPLE = BASE_DIR / "ocr_robustness_sample.csv"
BACKEND_DIR = ROOT / "ccc" / "astrobiology" / "backend"
TARGET_CLASSES = {"low_text_or_degraded_text", "very_low_text_or_ocr_dependent_candidate"}
MAX_DOCS = 6
TEXT_LAYER_PAGES = 5
OCR_PROBE_DPI = 150

RESULT_CSV = BASE_DIR / "ocr_fallback_smoke_test_results_rerun.csv"
REPORT_MD = BASE_DIR / "ocr_fallback_smoke_test_report_rerun.md"
LIMITATIONS_MD = BASE_DIR / "revised_manuscript_limitations_text_ocr_rerun.md"
RESPONSE_MD = BASE_DIR / "revised_reviewer_response_text_ocr_rerun.md"

EOM_KEYWORDS = [
    "meteorite",
    "chondrite",
    "carbonaceous",
    "extraterrestrial",
    "organic",
    "amino acid",
    "isotope",
    "contamination",
    "sample",
    "curation",
    "mars",
]


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def dependency_status() -> Dict[str, Any]:
    status = {
        "fitz": module_available("fitz"),
        "PIL": module_available("PIL"),
        "numpy": module_available("numpy"),
        "easyocr": module_available("easyocr"),
        "pytesseract": module_available("pytesseract"),
        "paddleocr": module_available("paddleocr"),
        "pdf2image": module_available("pdf2image"),
        "tesseract_binary": shutil.which("tesseract") or "",
        "pymupdf_doc": "",
    }
    if status["fitz"]:
        import fitz

        status["pymupdf_doc"] = (fitz.__doc__ or "").strip().splitlines()[0]
    return status


def load_project_ocr_tools() -> Dict[str, Any]:
    tools: Dict[str, Any] = {
        "service_imported": False,
        "ocr_engine_available": False,
        "ocr_engine": "",
        "error": "",
        "ocr_service": None,
    }
    sys.path.insert(0, str(BACKEND_DIR))
    os.environ.setdefault("OCR_ENABLED", "true")
    try:
        from pdf_processor import ocr_service

        tools["service_imported"] = True
        tools["ocr_service"] = ocr_service
        engine = ocr_service.get_ocr_engine()
        if engine:
            tools["ocr_engine_available"] = True
            tools["ocr_engine"] = engine[1]
        else:
            tools["error"] = (
                "OCR runtime dependency incomplete: no OCR engine available "
                "(default easyocr missing; pytesseract/paddleocr unavailable or tesseract binary absent)."
            )
    except Exception as exc:
        tools["error"] = f"{type(exc).__name__}: {exc}"
    return tools


def selected_rows() -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with INPUT_SAMPLE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row.get("quality_class") in TARGET_CLASSES and Path(row.get("pdf_path", "")).exists():
                rows.append(row)
            if len(rows) >= MAX_DOCS:
                break
    return rows


def extract_text_layer(pdf_path: Path, max_pages: int = TEXT_LAYER_PAGES) -> Dict[str, Any]:
    import fitz

    page_texts: List[str] = []
    try:
        with fitz.open(str(pdf_path)) as doc:
            for page_idx in range(min(max_pages, len(doc))):
                page_texts.append(doc[page_idx].get_text("text") or "")
        return {"success": True, "text": "\n".join(page_texts), "error": ""}
    except Exception as exc:
        return {"success": False, "text": "", "error": f"{type(exc).__name__}: {exc}"}


def render_probe(pdf_path: Path) -> Dict[str, Any]:
    import fitz

    try:
        with fitz.open(str(pdf_path)) as doc:
            if len(doc) == 0:
                return {"success": False, "details": "zero-page PDF"}
            page = doc[0]
            matrix = fitz.Matrix(OCR_PROBE_DPI / 72.0, OCR_PROBE_DPI / 72.0)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            return {
                "success": True,
                "details": f"first page rendered at {pix.width}x{pix.height}px",
            }
    except Exception as exc:
        return {"success": False, "details": f"{type(exc).__name__}: {exc}"}


def scan_probe(pdf_path: Path, tools: Dict[str, Any]) -> Dict[str, Any]:
    service = tools.get("ocr_service")
    if not service:
        return {"status": "unavailable", "is_scanned": "", "confidence": "", "details": tools.get("error", "")}
    try:
        result = service.is_scanned_pdf(str(pdf_path), sample_pages=3)
        return {
            "status": "ok",
            "is_scanned": result.get("is_scanned", ""),
            "confidence": result.get("confidence", ""),
            "details": result.get("error", ""),
        }
    except Exception as exc:
        return {"status": "error", "is_scanned": "", "confidence": "", "details": f"{type(exc).__name__}: {exc}"}


def ocr_probe(pdf_path: Path, tools: Dict[str, Any]) -> Dict[str, Any]:
    service = tools.get("ocr_service")
    if not service:
        return {
            "attempted": 1,
            "success": 0,
            "failure_reason": tools.get("error", "project OCR service unavailable"),
            "text": "",
            "engine": "",
        }
    try:
        result = service.extract_text_with_ocr(str(pdf_path), pages=[0], dpi=OCR_PROBE_DPI)
        if result.get("error_code") == "OCR_NOT_AVAILABLE":
            failure_reason = (
                "OCR runtime dependency incomplete: project OCR service was called, "
                "but no OCR engine is available."
            )
        else:
            failure_reason = result.get("error", "OCR failed")
        return {
            "attempted": 1,
            "success": int(bool(result.get("success"))),
            "failure_reason": "" if result.get("success") else failure_reason,
            "text": result.get("text", "") or "",
            "engine": result.get("engine", ""),
        }
    except Exception as exc:
        return {
            "attempted": 1,
            "success": 0,
            "failure_reason": f"{type(exc).__name__}: {exc}",
            "text": "",
            "engine": "",
        }


def text_metrics(text: str) -> Dict[str, Any]:
    lowered = text.lower()
    tokens = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", text)
    keyword_hits = sum(len(re.findall(re.escape(term), lowered)) for term in EOM_KEYWORDS)
    title_marker = bool(re.search(r"\b(title|erratum|abstract)\b", lowered))
    abstract_marker = "abstract" in lowered
    section_marker = bool(re.search(r"\b(introduction|methods?|materials?|results?|discussion|conclusions?)\b", lowered))
    evidence_proxy = int(len(text.strip()) >= 500 and keyword_hits > 0)
    return {
        "text_length": len(text),
        "token_count": len(tokens),
        "eom_keyword_hits": keyword_hits,
        "title_marker": int(title_marker),
        "abstract_marker": int(abstract_marker),
        "section_marker": int(section_marker),
        "evidence_proxy": evidence_proxy,
    }


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: Iterable[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{100.0 * numerator / denominator:.1f}%"


def main() -> None:
    deps = dependency_status()
    if not deps["fitz"]:
        raise RuntimeError("PyMuPDF/fitz is unavailable in this Python runtime.")

    tools = load_project_ocr_tools()
    rows = selected_rows()
    output_rows: List[Dict[str, Any]] = []

    for row in rows:
        pdf_path = Path(row["pdf_path"])
        accessible = int(pdf_path.exists() and pdf_path.is_file())
        before = extract_text_layer(pdf_path) if accessible else {"success": False, "text": "", "error": "file not accessible"}
        before_metrics = text_metrics(before["text"])

        render = render_probe(pdf_path) if accessible else {"success": False, "details": "file not accessible"}
        scan = scan_probe(pdf_path, tools) if accessible else {"status": "unavailable", "is_scanned": "", "confidence": "", "details": "file not accessible"}
        ocr = ocr_probe(pdf_path, tools) if accessible else {
            "attempted": 0,
            "success": 0,
            "failure_reason": "file not accessible",
            "text": "",
            "engine": "",
        }

        if ocr["success"] and ocr["text"].strip():
            after_text = ocr["text"]
            notes = f"True OCR completed with {ocr.get('engine', '')}."
        else:
            after_text = before["text"]
            notes = (
                "True OCR did not run successfully; after_* metrics reflect PyMuPDF text-layer fallback, "
                "not OCR-recognized text. "
                + ("Page image render succeeded. " if render["success"] else "Page image render failed. ")
                + f"Render probe: {render['details']}. Scan detector: {scan['status']}."
            )

        after_metrics = text_metrics(after_text)
        output_rows.append(
            {
                "pdf_path": str(pdf_path),
                "quality_class": row.get("quality_class", ""),
                "accessible": accessible,
                "ocr_attempted": ocr["attempted"],
                "ocr_success": ocr["success"],
                "failure_reason": ocr["failure_reason"],
                "before_text_length": before_metrics["text_length"],
                "after_text_length": after_metrics["text_length"],
                "before_token_count": before_metrics["token_count"],
                "after_token_count": after_metrics["token_count"],
                "before_eom_keyword_hits": before_metrics["eom_keyword_hits"],
                "after_eom_keyword_hits": after_metrics["eom_keyword_hits"],
                "before_evidence_availability_proxy": before_metrics["evidence_proxy"],
                "after_evidence_availability_proxy": after_metrics["evidence_proxy"],
                "text_recovery_delta": after_metrics["text_length"] - before_metrics["text_length"],
                "notes": notes,
            }
        )

    fields = [
        "pdf_path",
        "quality_class",
        "accessible",
        "ocr_attempted",
        "ocr_success",
        "failure_reason",
        "before_text_length",
        "after_text_length",
        "before_token_count",
        "after_token_count",
        "before_eom_keyword_hits",
        "after_eom_keyword_hits",
        "before_evidence_availability_proxy",
        "after_evidence_availability_proxy",
        "text_recovery_delta",
        "notes",
    ]
    write_csv(RESULT_CSV, output_rows, fields)

    total = len(output_rows)
    accessible_count = sum(int(r["accessible"]) for r in output_rows)
    ocr_attempted = sum(int(r["ocr_attempted"]) for r in output_rows)
    ocr_success = sum(int(r["ocr_success"]) for r in output_rows)
    render_success = sum("Page image render succeeded" in str(r["notes"]) for r in output_rows)
    deltas = [int(r["text_recovery_delta"]) for r in output_rows]
    class_counts = Counter(r["quality_class"] for r in output_rows)
    improved_rows = sum(1 for value in deltas if value > 0)

    report = [
        "# OCR Fallback Smoke Test Report (Rerun)",
        "",
        "## Scope",
        "",
        "This rerun only updates the OCR robustness smoke-test artifacts in this directory. It does not modify the main retrieval index, Weaviate collection, frozen retrieval/end-to-end/contamination results, or manuscript text.",
        "",
        "## Runtime Dependency Check",
        "",
        f"- PyMuPDF/fitz available: {deps['fitz']}",
        f"- PyMuPDF version string: {deps['pymupdf_doc']}",
        f"- PIL available: {deps['PIL']}",
        f"- numpy available: {deps['numpy']}",
        f"- easyocr available: {deps['easyocr']}",
        f"- pytesseract available: {deps['pytesseract']}",
        f"- paddleocr available: {deps['paddleocr']}",
        f"- pdf2image available: {deps['pdf2image']}",
        f"- tesseract binary: {deps['tesseract_binary'] or 'not found'}",
        "",
        "## Project OCR Tool Check",
        "",
        f"- Project OCR service imported: {tools['service_imported']}",
        f"- OCR engine available through project service: {tools['ocr_engine_available']}",
        f"- OCR engine selected: {tools['ocr_engine'] or 'none'}",
        f"- OCR service note: {tools['error'] or 'none'}",
        "",
        "## Sample Summary",
        "",
        f"- Selected rows: {total}",
        f"- Accessible PDFs: {accessible_count}/{total}",
        f"- Quality-class distribution: {dict(class_counts)}",
        f"- OCR attempted through project fallback entry point: {ocr_attempted}/{total}",
        f"- True OCR success rows: {ocr_success}/{total}",
        f"- PyMuPDF page-render probe success rows: {render_success}/{total}",
        f"- Rows with text-length increase after true OCR: {improved_rows}/{total}",
        "",
        "## Interpretation",
        "",
    ]

    if ocr_success:
        report.append("Selected low-text cases showed partial text recovery where true OCR completed successfully.")
    else:
        report.append(
            "True OCR did not complete in this runtime because the OCR runtime dependency is incomplete. "
            "The project OCR service can be imported and PyMuPDF can extract text layers and render pages, "
            "but no OCR engine is available (`easyocr`, `pytesseract`/system Tesseract, and `paddleocr` are absent)."
        )

    report.extend(
        [
            "",
            "The `after_*` fields therefore represent PyMuPDF text-layer fallback for these rows, not OCR-recognized text. "
            "This is an implementation smoke test of the fallback path and dependency state, not a main benchmark result.",
            "",
            "## Result File",
            "",
            f"- `{RESULT_CSV}`",
        ]
    )
    REPORT_MD.write_text("\n".join(report), encoding="utf-8")

    limitation_text = [
        "# Revised Manuscript Limitations Text: OCR Rerun",
        "",
        "The current benchmark primarily evaluates documents with machine-readable PDF text layers. OCR-heavy documents require dedicated OCR runtime validation and quality-control benchmark. In the supplementary limitation check, low-text candidate files were used to verify the text-layer and page-rendering fallback path without rebuilding the main index. We therefore do not claim that OCR robustness has been fully established for scanned or OCR-heavy historical literature; future work should evaluate OCR quality control, text recovery, and downstream evidence availability in a dedicated scanned-document benchmark.",
    ]
    LIMITATIONS_MD.write_text("\n".join(limitation_text), encoding="utf-8")

    response_text = [
        "# Revised Reviewer Response Text: OCR Rerun",
        "",
        "We added a small OCR fallback smoke test to clarify implementation scope versus evaluated benchmark scope. The test reused selected low-text candidate PDFs and verified that the workflow can inspect the PDF text layer and render pages for OCR fallback without modifying the main index or frozen results. The current benchmark remains primarily text-layer based, and OCR-heavy documents require dedicated OCR runtime validation and quality-control benchmark. We therefore describe scanned/OCR-heavy literature as a limitation and future-work direction, rather than claiming that OCR robustness has been fully demonstrated.",
    ]
    RESPONSE_MD.write_text("\n".join(response_text), encoding="utf-8")

    print(f"wrote {RESULT_CSV}")
    print(f"wrote {REPORT_MD}")
    print(f"wrote {LIMITATIONS_MD}")
    print(f"wrote {RESPONSE_MD}")


if __name__ == "__main__":
    main()
