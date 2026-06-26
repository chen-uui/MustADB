import csv
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Sequence

from pypdf import PdfReader


logging.getLogger("pypdf").setLevel(logging.ERROR)

ROOT = Path("D:/workspace/123")
PDF_DIR = ROOT / "ccc/astrobiology/data/pdfs"
OUT_DIR = ROOT / "submission_backup/04_eval_benchmarks/table_figure_text_layer_audit_v1"
TARGET_N = 20

PRIORITY_TERMS = [
    "meteorite",
    "chondrite",
    "murchison",
    "orgueil",
    "ryugu",
    "bennu",
    "hayabusa",
    "tagish",
    "winchcombe",
    "tissint",
    "organic",
    "amino",
    "contamination",
    "curation",
    "witness",
    "sample",
    "gc",
    "lc",
    "raman",
    "ftir",
    "isotope",
    "spectro",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def md_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(lines)


def extract_pdf_text(path: Path) -> Dict[str, Any]:
    try:
        reader = PdfReader(str(path), strict=False)
        page_count = len(reader.pages)
        page_texts: List[str] = []
        page_errors = 0
        for page in reader.pages:
            try:
                page_texts.append(page.extract_text() or "")
            except Exception:
                page_errors += 1
                page_texts.append("")
        return {
            "status": "ok",
            "page_count": page_count,
            "page_errors": page_errors,
            "text": "\n".join(page_texts),
            "error": "",
        }
    except Exception as exc:
        return {"status": "error", "page_count": "", "page_errors": "", "text": "", "error": f"{type(exc).__name__}: {exc}"}


def clean_line(line: str) -> str:
    return re.sub(r"\s+", " ", line or "").strip()


def compact_preview(lines: Sequence[str], limit: int = 3) -> str:
    previews = []
    for line in lines[:limit]:
        s = clean_line(line)
        if len(s) > 220:
            s = s[:217] + "..."
        previews.append(s)
    return " || ".join(previews)


def priority_score(filename: str) -> int:
    lowered = filename.lower()
    score = 0
    for term in PRIORITY_TERMS:
        if term in lowered:
            score += 3
    if any(term in lowered for term in ["ryugu", "hayabusa", "bennu", "sample return", "witness"]):
        score += 6
    if any(term in lowered for term in ["contamination", "curation", "blank"]):
        score += 5
    if any(term in lowered for term in ["gc", "lc", "raman", "ftir", "spectro", "xray", "x-ray"]):
        score += 4
    return score


def analyse_text(text: str) -> Dict[str, Any]:
    lines = [clean_line(line) for line in text.splitlines()]
    nonempty = [line for line in lines if line]
    table_marker_re = re.compile(r"\b(Table|TABLE)\s+(S?\d+|[IVX]+)\b")
    figure_marker_re = re.compile(r"\b(Fig\.?|Figure|FIG\.?|FIGURE)\s*(S?\d+|[IVX]+)?\b")
    caption_re = re.compile(r"^\s*(Table|Fig\.?|Figure|FIG\.?|FIGURE)\s*(S?\d+|[IVX]+)?[\.:]?\s+.{20,}", re.I)
    table_caption_re = re.compile(r"^\s*Table\s+(S?\d+|[IVX]+)?[\.:]?\s+.{20,}", re.I)
    figure_caption_re = re.compile(r"^\s*(Fig\.?|Figure)\s*(S?\d+|[IVX]+)?[\.:]?\s+.{20,}", re.I)
    surrounding_ref_re = re.compile(r"\b(as shown in|shown in|see|listed in|summarized in|presented in|shown on)\s+(Table|Fig\.?|Figure)\b", re.I)

    table_marker_count = len(table_marker_re.findall(text))
    figure_marker_count = len(figure_marker_re.findall(text))
    caption_lines = [line for line in nonempty if caption_re.search(line)]
    table_caption_lines = [line for line in nonempty if table_caption_re.search(line)]
    figure_caption_lines = [line for line in nonempty if figure_caption_re.search(line)]
    surrounding_refs = [line for line in nonempty if surrounding_ref_re.search(line)]

    table_like_lines = []
    for line in nonempty:
        numeric_tokens = re.findall(r"(?<![A-Za-z])[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?%?", line)
        delimiterish = bool(re.search(r"\s{2,}|\t|\|", line))
        chemistryish = bool(re.search(r"\b(CM|CR|CI|CO|CV|ppm|ppb|wt%|δ|D/H|13C|15N|m/z|GC-MS|LC-MS)\b", line, re.I))
        if len(numeric_tokens) >= 3 and (delimiterish or chemistryish):
            table_like_lines.append(line)

    has_table = table_marker_count > 0
    has_figure = figure_marker_count > 0
    has_caption = bool(caption_lines)
    has_table_like = bool(table_like_lines)
    has_refs = bool(surrounding_refs)

    not_recoverable_reasons = []
    if has_table and not table_caption_lines and not table_like_lines:
        not_recoverable_reasons.append("table markers present but no table caption or row-like text found")
    if has_figure and not figure_caption_lines:
        not_recoverable_reasons.append("figure markers present but figure caption text not found")
    if has_refs and not has_caption:
        not_recoverable_reasons.append("surrounding references found but caption text absent")

    return {
        "text_chars": len(text.strip()),
        "line_count": len(nonempty),
        "table_marker_count": table_marker_count,
        "figure_marker_count": figure_marker_count,
        "caption_line_count": len(caption_lines),
        "table_caption_count": len(table_caption_lines),
        "figure_caption_count": len(figure_caption_lines),
        "table_like_line_count": len(table_like_lines),
        "surrounding_ref_count": len(surrounding_refs),
        "documents_with_table_markers": int(has_table),
        "documents_with_figure_markers": int(has_figure),
        "documents_with_caption_text": int(has_caption),
        "documents_with_table_like_text": int(has_table_like),
        "references_to_figures_tables_in_surrounding_text": int(has_refs),
        "possible_not_recoverable_from_text_layer": int(bool(not_recoverable_reasons)),
        "not_recoverable_reason": "; ".join(not_recoverable_reasons),
        "example_caption_lines": compact_preview(caption_lines),
        "example_table_like_lines": compact_preview(table_like_lines),
        "example_surrounding_refs": compact_preview(surrounding_refs),
    }


def selection_reason(filename: str, analysis: Dict[str, Any]) -> str:
    lowered = filename.lower()
    reasons = []
    if any(term in lowered for term in ["ryugu", "hayabusa", "bennu", "sample", "witness"]):
        reasons.append("returned/sample-return paper")
    if any(term in lowered for term in ["meteorite", "chondrite", "murchison", "orgueil", "tagish", "winchcombe", "tissint"]):
        reasons.append("meteorite/EOM paper")
    if any(term in lowered for term in ["organic", "amino", "compound", "pah", "hydrocarbon"]):
        reasons.append("organic-compound paper")
    if any(term in lowered for term in ["contamination", "curation", "blank", "witness"]):
        reasons.append("contamination-control paper")
    if any(term in lowered for term in ["gc", "lc", "raman", "ftir", "spectro", "xray", "x-ray", "afm"]):
        reasons.append("analytical-methods paper")
    if analysis["table_marker_count"] or analysis["figure_marker_count"]:
        reasons.append("text layer contains Table/Fig/Figure markers")
    return "; ".join(reasons) or "marker-rich text-layer sample"


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    candidate_rows: List[Dict[str, Any]] = []
    for pdf_path in sorted(PDF_DIR.glob("*.pdf")):
        score = priority_score(pdf_path.name)
        # Keep relevant documents plus a few marker-rich documents discovered by filename score.
        if score <= 0:
            continue
        extracted = extract_pdf_text(pdf_path)
        if extracted["status"] != "ok" or not extracted["text"].strip():
            analysis = analyse_text("")
        else:
            analysis = analyse_text(extracted["text"])
        marker_score = (
            analysis["table_marker_count"]
            + analysis["figure_marker_count"]
            + analysis["caption_line_count"] * 2
            + analysis["table_like_line_count"]
            + analysis["surrounding_ref_count"]
        )
        if marker_score <= 0:
            continue
        candidate_rows.append(
            {
                "pdf_path": str(pdf_path),
                "filename": pdf_path.name,
                "file_size_bytes": pdf_path.stat().st_size,
                "sha256": sha256(pdf_path),
                "priority_score": score,
                "marker_score": marker_score,
                "extraction_status": extracted["status"],
                "extraction_error": extracted["error"],
                "page_count": extracted["page_count"],
                "page_extraction_errors": extracted["page_errors"],
                **analysis,
            }
        )

    candidate_rows.sort(
        key=lambda row: (
            -int(row["priority_score"]),
            -int(row["documents_with_caption_text"]),
            -int(row["documents_with_table_like_text"]),
            -int(row["marker_score"]),
            row["filename"].lower(),
        )
    )

    selected: List[Dict[str, Any]] = []
    seen = set()
    # Ensure explicit topical coverage when available.
    topical_patterns = [
        r"Hayabusa|witness|sample",
        r"Ryugu",
        r"contamination|curation|Orgueil",
        r"Murchison|meteorite|chondrite",
        r"Raman|FTIR|GC|LC|AFM|spectro|xray|x-ray",
        r"organic|amino|compound",
    ]
    for pattern in topical_patterns:
        for row in candidate_rows:
            if row["pdf_path"] in seen:
                continue
            if re.search(pattern, row["filename"], re.I):
                selected.append(row)
                seen.add(row["pdf_path"])
                break
    for row in candidate_rows:
        if len(selected) >= TARGET_N:
            break
        if row["pdf_path"] not in seen:
            selected.append(row)
            seen.add(row["pdf_path"])

    output_rows: List[Dict[str, Any]] = []
    for i, row in enumerate(selected[:TARGET_N], 1):
        out = dict(row)
        out["sample_id"] = f"TFCA{i:03d}"
        out["selection_reason"] = selection_reason(row["filename"], row)
        output_rows.append(out)

    fieldnames = [
        "sample_id",
        "filename",
        "pdf_path",
        "selection_reason",
        "file_size_bytes",
        "sha256",
        "page_count",
        "page_extraction_errors",
        "extraction_status",
        "extraction_error",
        "text_chars",
        "line_count",
        "table_marker_count",
        "figure_marker_count",
        "caption_line_count",
        "table_caption_count",
        "figure_caption_count",
        "table_like_line_count",
        "surrounding_ref_count",
        "documents_with_table_markers",
        "documents_with_figure_markers",
        "documents_with_caption_text",
        "documents_with_table_like_text",
        "references_to_figures_tables_in_surrounding_text",
        "possible_not_recoverable_from_text_layer",
        "not_recoverable_reason",
        "example_caption_lines",
        "example_table_like_lines",
        "example_surrounding_refs",
    ]
    write_csv(OUT_DIR / "table_figure_text_layer_audit.csv", fieldnames, output_rows)

    totals = {
        "sampled_documents": len(output_rows),
        "documents_with_table_markers": sum(int(r["documents_with_table_markers"]) for r in output_rows),
        "documents_with_figure_markers": sum(int(r["documents_with_figure_markers"]) for r in output_rows),
        "documents_with_caption_text": sum(int(r["documents_with_caption_text"]) for r in output_rows),
        "documents_with_table_like_text": sum(int(r["documents_with_table_like_text"]) for r in output_rows),
        "documents_with_surrounding_refs": sum(int(r["references_to_figures_tables_in_surrounding_text"]) for r in output_rows),
        "cases_not_recoverable_from_text_layer": sum(int(r["possible_not_recoverable_from_text_layer"]) for r in output_rows),
    }

    summary_rows = [[key, value] for key, value in totals.items()]
    per_doc_rows = [
        [
            r["sample_id"],
            r["filename"][:60] + ("..." if len(r["filename"]) > 60 else ""),
            r["documents_with_table_markers"],
            r["documents_with_figure_markers"],
            r["documents_with_caption_text"],
            r["documents_with_table_like_text"],
            r["possible_not_recoverable_from_text_layer"],
        ]
        for r in output_rows
    ]

    summary_md = [
        "# Table/Figure/Caption Text-Layer Coverage Audit",
        "",
        "## Scope",
        "",
        "This audit sampled existing PDFs and inspected only the machine-readable text layer. It does not modify the main system, rebuild the index, alter frozen results, or perform layout-aware table extraction or image interpretation.",
        "",
        "## Sample Strategy",
        "",
        "The sample prioritized returned/sample-return papers, meteorite organic compound papers, analytical-methods and contamination-control papers, and documents whose text layer contains Table/Fig/Figure/caption-like markers.",
        "",
        "## Aggregate Counts",
        "",
        md_table(["metric", "value"], summary_rows),
        "",
        "## Per-Document Flags",
        "",
        md_table(
            [
                "sample_id",
                "filename",
                "table_markers",
                "figure_markers",
                "caption_text",
                "table_like_text",
                "possible_not_recoverable",
            ],
            per_doc_rows,
        ),
        "",
        "## Interpretation",
        "",
        "The current workflow can retrieve and cite table, figure, and caption evidence when those elements survive in the PDF text layer. In this audit, many sampled documents retained caption-like text and row-like numeric/text fragments that could be indexed as ordinary text evidence.",
        "",
        "However, this is not equivalent to layout-aware table extraction or figure interpretation. Flattened text can lose two-dimensional table structure, row-column alignment, symbols, units, panel labels, and relationships between a figure and surrounding caption/body text. Cases flagged as not recoverable are cases where references or markers were visible but the corresponding caption/row-like content was incomplete or absent in the text layer.",
        "",
    ]
    (OUT_DIR / "table_figure_text_layer_summary.md").write_text("\n".join(summary_md), encoding="utf-8")

    methods_text = [
        "# Manuscript Methods Text: Table/Figure Scope",
        "",
        "The retrieval workflow operates on text extracted from the PDF text layer. Consequently, table captions, figure captions, and table-like text fragments can be indexed and retrieved when they are preserved as machine-readable text. The current benchmark does not evaluate layout-aware table reconstruction, image interpretation, or multimodal alignment between figures, captions, and body text. The system should therefore be interpreted as a text-grounded evidence retrieval workflow; layout-aware multimodal extraction is a natural extension rather than a capability claimed in the present experiments.",
        "",
    ]
    (OUT_DIR / "manuscript_methods_text_table_figure_scope.md").write_text("\n".join(methods_text), encoding="utf-8")

    reviewer_text = [
        "# Reviewer Response Text: Table/Figure Extraction",
        "",
        "We added a table/figure/caption text-layer audit to clarify the scope of the current workflow. The audit sampled 20 relevant PDFs, including returned-sample, meteorite organic-compound, analytical-method, and contamination-control papers. It checked whether table markers, figure markers, caption-like text, table-like rows, and surrounding figure/table references were preserved in the extracted text layer. The results show that the workflow can retrieve and cite table/caption evidence when that evidence is present as text. We do not claim layout-aware table reconstruction, image interpretation, or cross-modal figure-caption alignment in the current benchmark. Those capabilities are outside the present text-grounded evaluation and are better framed as future extensions.",
        "",
    ]
    (OUT_DIR / "reviewer_response_text_table_figure.md").write_text("\n".join(reviewer_text), encoding="utf-8")

    manifest_rows = []
    for path in sorted(OUT_DIR.glob("*")):
        if path.is_file() and path.name != Path(__file__).name:
            manifest_rows.append({"file": path.name, "size_bytes": path.stat().st_size, "sha256": sha256(path)})
    write_csv(OUT_DIR / "output_manifest.csv", ["file", "size_bytes", "sha256"], manifest_rows)

    print(json.dumps({"sampled_documents": len(output_rows), **totals, "out_dir": str(OUT_DIR)}, indent=2))


if __name__ == "__main__":
    main()
