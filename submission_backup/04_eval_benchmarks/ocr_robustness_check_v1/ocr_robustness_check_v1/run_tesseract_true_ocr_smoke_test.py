from __future__ import annotations

import csv
import importlib.util
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Dict, Iterable, List


ROOT = Path(r"D:\workspace\123")
BASE_DIR = ROOT / "submission_backup" / "04_eval_benchmarks" / "ocr_robustness_check_v1"
INPUT_SAMPLE = BASE_DIR / "ocr_robustness_sample.csv"
TARGET_CLASSES = {"low_text_or_degraded_text", "very_low_text_or_ocr_dependent_candidate"}
MAX_DOCS = 6
MAX_OCR_PAGES = 5
OCR_DPI = 200
TESSERACT_CANDIDATES = [
    Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
    Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
]

RESULT_CSV = BASE_DIR / "ocr_true_ocr_smoke_test_results.csv"
REPORT_MD = BASE_DIR / "ocr_true_ocr_smoke_test_report.md"
LIMITATIONS_MD = BASE_DIR / "final_manuscript_limitations_text_ocr.md"
RESPONSE_MD = BASE_DIR / "final_reviewer_response_text_ocr.md"

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


def find_tesseract() -> str:
    path = shutil.which("tesseract")
    if path:
        return path
    for candidate in TESSERACT_CANDIDATES:
        if candidate.exists():
            return str(candidate)
    return ""


def tesseract_version(tesseract_cmd: str) -> str:
    if not tesseract_cmd:
        return ""
    try:
        result = subprocess.run(
            [tesseract_cmd, "--version"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        return (result.stdout or result.stderr).splitlines()[0].strip()
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def selected_rows() -> List[Dict[str, str]]:
    selected: List[Dict[str, str]] = []
    with INPUT_SAMPLE.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            pdf_path = Path(row.get("pdf_path", ""))
            if row.get("quality_class") in TARGET_CLASSES and pdf_path.exists():
                selected.append(row)
            if len(selected) >= MAX_DOCS:
                break
    return selected


def extract_text_layer(pdf_path: Path, max_pages: int = MAX_OCR_PAGES) -> Dict[str, Any]:
    import fitz

    texts: List[str] = []
    try:
        with fitz.open(str(pdf_path)) as doc:
            page_count = min(max_pages, len(doc))
            for page_idx in range(page_count):
                texts.append(doc[page_idx].get_text("text") or "")
        return {"success": True, "text": "\n".join(texts), "pages": page_count, "error": ""}
    except Exception as exc:
        return {"success": False, "text": "", "pages": 0, "error": f"{type(exc).__name__}: {exc}"}


def run_tesseract_ocr(pdf_path: Path, tesseract_cmd: str, max_pages: int = MAX_OCR_PAGES) -> Dict[str, Any]:
    import fitz
    import pytesseract
    from PIL import Image

    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    page_texts: List[str] = []
    page_errors: List[str] = []
    pages_attempted = 0
    pages_succeeded = 0

    try:
        with fitz.open(str(pdf_path)) as doc:
            for page_idx in range(min(max_pages, len(doc))):
                pages_attempted += 1
                try:
                    page = doc[page_idx]
                    matrix = fitz.Matrix(OCR_DPI / 72.0, OCR_DPI / 72.0)
                    pix = page.get_pixmap(matrix=matrix, alpha=False)
                    mode = "RGB" if pix.n < 4 else "RGBA"
                    image = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
                    text = pytesseract.image_to_string(image, lang="eng", config="--psm 3") or ""
                    page_texts.append(text)
                    pages_succeeded += 1
                except Exception as exc:
                    page_errors.append(f"page {page_idx + 1}: {type(exc).__name__}: {exc}")
        joined = "\n".join(page_texts)
        success = pages_succeeded > 0 and bool(joined.strip())
        return {
            "success": success,
            "text": joined,
            "pages_attempted": pages_attempted,
            "pages_succeeded": pages_succeeded,
            "failure_reason": "; ".join(page_errors) if page_errors else ("" if success else "OCR returned no text"),
        }
    except Exception as exc:
        return {
            "success": False,
            "text": "",
            "pages_attempted": pages_attempted,
            "pages_succeeded": pages_succeeded,
            "failure_reason": f"{type(exc).__name__}: {exc}",
        }


def text_metrics(text: str) -> Dict[str, Any]:
    lowered = text.lower()
    tokens = re.findall(r"[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)?", text)
    keyword_hits = sum(len(re.findall(re.escape(term), lowered)) for term in EOM_KEYWORDS)
    evidence_proxy = int(len(text.strip()) >= 500 and keyword_hits > 0)
    return {
        "text_length": len(text),
        "token_count": len(tokens),
        "eom_keyword_hits": keyword_hits,
        "evidence_proxy": evidence_proxy,
    }


def write_csv(path: Path, rows: List[Dict[str, Any]], fieldnames: Iterable[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    deps = {
        "fitz": module_available("fitz"),
        "pytesseract": module_available("pytesseract"),
        "PIL": module_available("PIL"),
    }
    tesseract_cmd = find_tesseract()
    tesseract_ver = tesseract_version(tesseract_cmd)
    if not deps["fitz"]:
        raise RuntimeError("PyMuPDF/fitz is unavailable.")
    if not deps["pytesseract"] or not deps["PIL"]:
        raise RuntimeError("pytesseract and pillow/PIL are required for true OCR smoke test.")
    if not tesseract_cmd:
        raise RuntimeError("System Tesseract OCR binary was not found.")

    rows = selected_rows()
    output_rows: List[Dict[str, Any]] = []
    for row in rows:
        pdf_path = Path(row["pdf_path"])
        accessible = int(pdf_path.exists() and pdf_path.is_file())
        text_layer = extract_text_layer(pdf_path) if accessible else {
            "success": False,
            "text": "",
            "pages": 0,
            "error": "file not accessible",
        }
        before = text_metrics(text_layer["text"])
        ocr = run_tesseract_ocr(pdf_path, tesseract_cmd) if accessible else {
            "success": False,
            "text": "",
            "pages_attempted": 0,
            "pages_succeeded": 0,
            "failure_reason": "file not accessible",
        }
        after = text_metrics(ocr["text"])
        notes = (
            f"text-layer pages={text_layer['pages']}; "
            f"rendered-page OCR pages attempted={ocr['pages_attempted']}, succeeded={ocr['pages_succeeded']}; "
            "after_* metrics are OCR-recognized rendered-page text, not text-layer text."
        )
        output_rows.append(
            {
                "pdf_path": str(pdf_path),
                "quality_class": row.get("quality_class", ""),
                "accessible": accessible,
                "text_layer_extraction_success": int(bool(text_layer["success"])),
                "ocr_attempted": int(accessible),
                "ocr_success": int(bool(ocr["success"])),
                "ocr_pages_attempted": ocr["pages_attempted"],
                "ocr_pages_succeeded": ocr["pages_succeeded"],
                "failure_reason": "" if ocr["success"] else ocr["failure_reason"],
                "before_text_length": before["text_length"],
                "after_text_length": after["text_length"],
                "before_token_count": before["token_count"],
                "after_token_count": after["token_count"],
                "before_eom_keyword_hits": before["eom_keyword_hits"],
                "after_eom_keyword_hits": after["eom_keyword_hits"],
                "before_evidence_availability_proxy": before["evidence_proxy"],
                "after_evidence_availability_proxy": after["evidence_proxy"],
                "text_recovery_delta": after["text_length"] - before["text_length"],
                "token_recovery_delta": after["token_count"] - before["token_count"],
                "eom_keyword_hit_delta": after["eom_keyword_hits"] - before["eom_keyword_hits"],
                "evidence_proxy_delta": after["evidence_proxy"] - before["evidence_proxy"],
                "notes": notes,
            }
        )

    fields = [
        "pdf_path",
        "quality_class",
        "accessible",
        "text_layer_extraction_success",
        "ocr_attempted",
        "ocr_success",
        "ocr_pages_attempted",
        "ocr_pages_succeeded",
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
        "token_recovery_delta",
        "eom_keyword_hit_delta",
        "evidence_proxy_delta",
        "notes",
    ]
    write_csv(RESULT_CSV, output_rows, fields)

    total = len(output_rows)
    accessible_count = sum(int(r["accessible"]) for r in output_rows)
    ocr_success_count = sum(int(r["ocr_success"]) for r in output_rows)
    improved_text = sum(1 for r in output_rows if int(r["text_recovery_delta"]) > 0)
    improved_tokens = sum(1 for r in output_rows if int(r["token_recovery_delta"]) > 0)
    improved_keywords = sum(1 for r in output_rows if int(r["eom_keyword_hit_delta"]) > 0)
    improved_proxy = sum(1 for r in output_rows if int(r["evidence_proxy_delta"]) > 0)
    class_counts = Counter(r["quality_class"] for r in output_rows)

    interpretation = []
    if improved_text or improved_tokens or improved_keywords or improved_proxy:
        interpretation.append("Selected low-text cases showed partial text recovery.")
    else:
        interpretation.append("The selected low-text cases did not show meaningful text recovery from rendered-page OCR.")
    interpretation.append(
        "OCR-heavy documents require OCR quality control and post-OCR evidence validation; this smoke test should not be interpreted as full OCR robustness evaluation."
    )

    report = [
        "# True OCR Smoke Test Report",
        "",
        "## Scope",
        "",
        "This true-OCR smoke test updates only OCR robustness artifacts in this directory. It does not modify the main retrieval index, rebuild Weaviate, change frozen retrieval/end-to-end/contamination results, or edit manuscript text.",
        "",
        "## Runtime",
        "",
        f"- PyMuPDF/fitz available: {deps['fitz']}",
        f"- pytesseract available: {deps['pytesseract']}",
        f"- PIL/Pillow available: {deps['PIL']}",
        f"- Tesseract executable: `{tesseract_cmd}`",
        f"- Tesseract version: {tesseract_ver}",
        f"- OCR DPI: {OCR_DPI}",
        f"- Pages rendered per PDF: up to {MAX_OCR_PAGES}",
        "",
        "## Sample Summary",
        "",
        f"- Selected PDFs: {total}",
        f"- Accessible PDFs: {accessible_count}/{total}",
        f"- Quality-class distribution: {dict(class_counts)}",
        f"- True OCR success rows: {ocr_success_count}/{total}",
        f"- Rows with increased OCR text length versus text layer: {improved_text}/{total}",
        f"- Rows with increased OCR token count versus text layer: {improved_tokens}/{total}",
        f"- Rows with increased EOM keyword hits: {improved_keywords}/{total}",
        f"- Rows with improved evidence-availability proxy: {improved_proxy}/{total}",
        "",
        "## Interpretation",
        "",
        " ".join(interpretation),
        "",
        "The comparison explicitly separates text-layer extraction (`before_*`) from rendered-page OCR-recognized text (`after_*`). OCR output quality varies by PDF and should be validated before downstream retrieval or evidence extraction.",
        "",
        "## Output",
        "",
        f"- `{RESULT_CSV}`",
    ]
    REPORT_MD.write_text("\n".join(report), encoding="utf-8")

    limitations = [
        "# Final Manuscript Limitations Text: OCR",
        "",
        "The current benchmark primarily evaluates documents with machine-readable PDF text layers. A small smoke test on selected low-text files confirmed that rendered-page OCR can be executed, but OCR-heavy documents require OCR quality control and post-OCR evidence validation. We therefore do not claim that OCR robustness has been fully established for scanned or OCR-heavy historical literature; a dedicated OCR quality-control benchmark remains future work.",
    ]
    LIMITATIONS_MD.write_text("\n".join(limitations), encoding="utf-8")

    response = [
        "# Final Reviewer Response Text: OCR",
        "",
        "We added a focused OCR limitation check and a small true-OCR smoke test on selected low-text candidate PDFs. The test distinguishes the existing PDF text layer from text recognized after rendering pages and applying Tesseract OCR, without rebuilding the index or changing frozen retrieval results. The results support a limitation statement rather than a robustness claim: OCR-heavy documents require OCR quality control and post-OCR evidence validation, and a dedicated scanned-document benchmark remains future work.",
    ]
    RESPONSE_MD.write_text("\n".join(response), encoding="utf-8")

    print(f"wrote {RESULT_CSV}")
    print(f"wrote {REPORT_MD}")
    print(f"wrote {LIMITATIONS_MD}")
    print(f"wrote {RESPONSE_MD}")


if __name__ == "__main__":
    main()
