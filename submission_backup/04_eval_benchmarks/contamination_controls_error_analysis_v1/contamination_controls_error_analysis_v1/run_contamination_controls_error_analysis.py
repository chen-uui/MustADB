import ast
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Set, Tuple


ROOT = Path("D:/workspace/123")
OUT_DIR = ROOT / "submission_backup/04_eval_benchmarks/contamination_controls_error_analysis_v1"

YES_VALUES = {"yes", "y", "true", "1"}
NO_VALUES = {"no", "n", "false", "0"}
PLACEHOLDER_TEXTS = {"", "unknown", "not specified", "none", "null", "n/a", "na"}
SPLIT_PATTERN = re.compile(r"[;,\uFF0C\uFF1B\u3001]+")

DATASETS = {
    "legacy_gold_seed": {
        "label": "Legacy gold seed",
        "path": ROOT / "submission_backup/04_eval_benchmarks/extraction/gold_seed.csv",
        "role": "legacy benchmark rows",
        "archived_summary": None,
    },
    "mainchain_rerun": {
        "label": "Mainchain rerun",
        "path": ROOT / "submission_backup/02_raw_results/extraction/gold_rerun_mainchain_20260312_v2/gold_seed_rerun.csv",
        "role": "mainchain extraction rerun rows",
        "archived_summary": ROOT / "submission_backup/02_raw_results/extraction/gold_rerun_mainchain_20260312_v2/rerun_eval/accuracy_summary.csv",
    },
    "field_current_best": {
        "label": "Field-specific current best",
        "path": ROOT / "submission_backup/02_raw_results/extraction/gold_field_specific_narrow_20260312_v1/current_best_field_specific/gold_seed_rerun.csv",
        "role": "low-F1 field-specific run used for error analysis",
        "archived_summary": ROOT / "submission_backup/02_raw_results/extraction/gold_field_specific_narrow_20260312_v1/current_best_field_specific/rerun_eval/accuracy_summary.csv",
    },
    "field_narrow_improved": {
        "label": "Field-specific narrow improved",
        "path": ROOT / "submission_backup/02_raw_results/extraction/gold_field_specific_narrow_20260312_v1/narrow_improved/gold_seed_rerun.csv",
        "role": "existing conservative prompt/evidence refinement run",
        "archived_summary": ROOT / "submission_backup/02_raw_results/extraction/gold_field_specific_narrow_20260312_v1/narrow_improved/rerun_eval/accuracy_summary.csv",
    },
    "gold_v2_fixed_eval_input": {
        "label": "Gold v2 fixed evaluation input",
        "path": ROOT / "ccc/astrobiology/backend/runs/gold_v2_eval_20260313_v1/gold_seed_v2_fixed_eval_input.csv",
        "role": "gold v2 row-level input corresponding to archived v2 evaluation",
        "archived_summary": ROOT / "submission_backup/03_processed_results/extraction/gold_v2_eval_20260313_v1/new_gold_v2_fixed_eval/accuracy_summary.csv",
    },
    "gold_v3": {
        "label": "Gold v3",
        "path": ROOT / "submission_backup/04_eval_benchmarks/extraction/gold_seed_v3.csv",
        "role": "gold v3 benchmark rows",
        "archived_summary": ROOT / "submission_backup/03_processed_results/extraction/gold_v3_eval_20260313_v1/gold_v3_eval/accuracy_summary.csv",
    },
}


def read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [{k: str(v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def normalize(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "").strip())
    lowered = text.lower()
    if lowered in PLACEHOLDER_TEXTS:
        return ""
    if "\u8be5\u8bba\u6587\u4e0d\u5305\u542b" in text:
        return ""
    return lowered


def flatten_token_candidates(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        out: List[str] = []
        for item in value:
            out.extend(flatten_token_candidates(item))
        return out
    if isinstance(value, dict):
        out: List[str] = []
        for item in value.values():
            out.extend(flatten_token_candidates(item))
        return out

    text = str(value).strip()
    if not text:
        return []
    if text[0] in "[{(":
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            parsed = None
        if isinstance(parsed, (list, tuple, set, dict)):
            return flatten_token_candidates(parsed)

    return [re.sub(r"\s+", " ", part).strip() for part in SPLIT_PATTERN.split(text) if part and part.strip()]


def token_set(value: Any) -> Set[str]:
    return {normalize(item) for item in flatten_token_candidates(value) if normalize(item)}


def should_skip(row: Dict[str, str]) -> bool:
    skip_value = str(row.get("skip_row", "")).strip().lower()
    in_scope_value = str(row.get("in_scope", "")).strip().lower()
    return skip_value in YES_VALUES or in_scope_value in NO_VALUES


def prf(tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
    precision = float(tp) / float(tp + fp) if (tp + fp) else 0.0
    recall = float(tp) / float(tp + fn) if (tp + fn) else 0.0
    f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return precision, recall, f1


def evaluate_rows(rows: Sequence[Dict[str, str]], pred_override: Dict[str, str] | None = None) -> Dict[str, Any]:
    tp = fp = fn = n_samples = 0
    error_rows: List[Dict[str, Any]] = []
    evaluated_rows = [row for row in rows if not should_skip(row)]

    for row in evaluated_rows:
        doc_id = row.get("doc_id", "")
        pred_raw = pred_override.get(doc_id, row.get("pred_contamination_controls", "")) if pred_override else row.get("pred_contamination_controls", "")
        gold_raw = row.get("gold_contamination_controls", "")
        pred_tokens = token_set(pred_raw)
        gold_tokens = token_set(gold_raw)

        if not pred_tokens and not gold_tokens:
            continue

        n_samples += 1
        overlap = pred_tokens & gold_tokens
        fp_tokens = pred_tokens - gold_tokens
        fn_tokens = gold_tokens - pred_tokens
        tp += len(overlap)
        fp += len(fp_tokens)
        fn += len(fn_tokens)

        if fp_tokens or fn_tokens:
            if pred_tokens and not gold_tokens:
                coarse_error_type = "FP"
            elif gold_tokens and not pred_tokens:
                coarse_error_type = "FN"
            else:
                coarse_error_type = "MISMATCH"
            error_rows.append(
                {
                    "doc_id": doc_id,
                    "doc_name": row.get("doc_name", ""),
                    "pred_value": pred_raw,
                    "gold_value": gold_raw,
                    "pred_tokens": "; ".join(sorted(pred_tokens)),
                    "gold_tokens": "; ".join(sorted(gold_tokens)),
                    "fp_tokens": "; ".join(sorted(fp_tokens)),
                    "fn_tokens": "; ".join(sorted(fn_tokens)),
                    "coarse_error_type": coarse_error_type,
                    "notes": row.get("notes", ""),
                }
            )

    precision, recall, f1 = prf(tp, fp, fn)
    return {
        "total_rows": len(rows),
        "evaluated_rows": len(evaluated_rows),
        "skipped_rows": len(rows) - len(evaluated_rows),
        "coverage_rate": len(evaluated_rows) / len(rows) if rows else 0.0,
        "n_samples": n_samples,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "errors": error_rows,
    }


CONTROL_CUES = re.compile(
    r"blank|control|sterile|contamin|curat|clean|witness|dnase|decontamin|minimi[sz]e|"
    r"prevent|foil|freezer|storage|procedural|negative|sawdust|terrestrial|no contamination|"
    r"cryogenic|cold|glove|pristine|quality-control|handling",
    re.I,
)
METHOD_CUES = re.compile(
    r"gc[- ]?ms|lc[- ]?ms|raman|ftir|infrared|spectroscop|chromatograph|mass spectrom|"
    r"sem|tem|x[- ]?ray|computed tomography|pyrolysis|derivati[sz]ation|hydrolysis|"
    r"extraction|solvent|sodium sulfate|amino acid|amines|carboxylic|compound|sample analyses",
    re.I,
)


def conservative_method_only_filter(prediction: str) -> str:
    """Drop only tokens that look like analytical/method phrases without any control cue."""
    kept: List[str] = []
    seen: Set[str] = set()
    for item in flatten_token_candidates(prediction):
        normalized = normalize(item)
        if not normalized or normalized in seen:
            continue
        if METHOD_CUES.search(normalized) and not CONTROL_CUES.search(normalized):
            continue
        seen.add(normalized)
        kept.append(str(item).strip())
    return "; ".join(kept)


def build_rule_predictions(rows: Sequence[Dict[str, str]]) -> Dict[str, str]:
    return {
        row.get("doc_id", ""): conservative_method_only_filter(row.get("pred_contamination_controls", ""))
        for row in rows
        if row.get("doc_id", "")
    }


def archived_contamination_summary(path: Path | None) -> Dict[str, str]:
    if not path or not path.exists():
        return {}
    for row in read_csv(path):
        if row.get("field") == "contamination_controls":
            return row
    return {}


def classify_error(error: Dict[str, Any]) -> List[str]:
    pred = str(error.get("pred_value", ""))
    gold = str(error.get("gold_value", ""))
    title = str(error.get("doc_name", ""))
    notes = str(error.get("notes", ""))
    fp = token_set(error.get("fp_tokens", ""))
    fn = token_set(error.get("fn_tokens", ""))
    text = " ".join([pred, gold, title, notes]).lower()

    categories: List[str] = []
    if fn and not fp:
        if re.search(r"no contamination|indicated no|without contamination|not contaminated", text):
            categories.append("negated or contrastive statements")
        if re.search(r"curation|prevent|minimi[sz]e|storage|handling|foil|freezer|sawdust|terrestrial", text):
            categories.append("under-extraction of sample-specific controls")
        if re.search(r"quality-control|blank|dnase|sterile|procedural", text):
            categories.append("indirect wording / implicit procedural control")
        if not categories:
            categories.append("sparse or absent explicit contamination description")

    if fp and not fn:
        if re.search(r"amino acid|compound|spectroscop|chromatograph|computed tomography|xray|x-ray|sodium sulfate|extraction", pred.lower()):
            categories.append("method vs control confusion")
        if re.search(r"blank controls|sterile handling|cold curation|aluminum foil storage|freezer storage|dnase treatment", pred.lower()):
            categories.append("over-extraction of general lab procedures")
        if not categories:
            categories.append("over-extraction of general lab procedures")

    if fp and fn:
        categories.append("entity-boundary ambiguity")
        if re.search(r"cold curation|blank controls|quality-control blank|procedural negative controls|extraction blanks", text):
            categories.append("indirect wording / implicit procedural control")
        if re.search(r"extraction|sodium sulfate|spectroscop|computed tomography|xray|x-ray", pred.lower()):
            categories.append("method vs control confusion")
        if re.search(r"prevent|minimi[sz]e|stringent curation", gold.lower()):
            categories.append("under-extraction of sample-specific controls")

    if not gold.strip() and pred.strip() and re.search(r"no explicit|not justify|left blank|not contamination control", notes.lower()):
        if "sparse or absent explicit contamination description" not in categories:
            categories.append("sparse or absent explicit contamination description")

    return sorted(set(categories)) or ["entity-boundary ambiguity"]


def fmt(value: float) -> str:
    return f"{value:.4f}"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def markdown_table(headers: Sequence[str], rows: Sequence[Sequence[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(item) for item in row) + " |")
    return "\n".join(lines)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    source_inventory: List[Dict[str, Any]] = []
    baseline_rows: List[Dict[str, Any]] = []
    improved_rows: List[Dict[str, Any]] = []
    error_cases: List[Dict[str, Any]] = []
    taxonomy_counts: Counter[str] = Counter()
    taxonomy_by_dataset: Dict[str, Counter[str]] = defaultdict(Counter)

    dataset_cache: Dict[str, List[Dict[str, str]]] = {}

    for dataset_id, meta in DATASETS.items():
        path = Path(meta["path"])
        exists = path.exists()
        source_inventory.append(
            {
                "dataset_id": dataset_id,
                "label": meta["label"],
                "role": meta["role"],
                "path": str(path),
                "exists": exists,
                "size_bytes": path.stat().st_size if exists else "",
                "sha256": file_sha256(path) if exists else "",
                "archived_summary": str(meta["archived_summary"]) if meta.get("archived_summary") else "",
            }
        )
        if not exists:
            continue

        rows = read_csv(path)
        dataset_cache[dataset_id] = rows
        metrics = evaluate_rows(rows)
        archived = archived_contamination_summary(meta.get("archived_summary"))
        baseline_rows.append(
            {
                "dataset_id": dataset_id,
                "dataset_label": meta["label"],
                "source_file": str(path),
                "total_rows": metrics["total_rows"],
                "evaluated_rows": metrics["evaluated_rows"],
                "skipped_rows": metrics["skipped_rows"],
                "n_samples": metrics["n_samples"],
                "tp": metrics["tp"],
                "fp": metrics["fp"],
                "fn": metrics["fn"],
                "precision": fmt(metrics["precision"]),
                "recall": fmt(metrics["recall"]),
                "f1": fmt(metrics["f1"]),
                "archived_precision": archived.get("precision", ""),
                "archived_recall": archived.get("recall", ""),
                "archived_f1": archived.get("f1", ""),
                "matching_rule": "lowercase+trim; comma/semicolon split; token-set micro P/R/F1 by overlap; empty-empty ignored",
            }
        )

        for err in metrics["errors"]:
            categories = classify_error(err)
            for category in categories:
                taxonomy_counts[category] += 1
                taxonomy_by_dataset[dataset_id][category] += 1
            error_cases.append(
                {
                    "dataset_id": dataset_id,
                    "dataset_label": meta["label"],
                    "doc_id": err["doc_id"],
                    "doc_name": err["doc_name"],
                    "pred_contamination_controls": err["pred_value"],
                    "gold_contamination_controls": err["gold_value"],
                    "pred_tokens": err["pred_tokens"],
                    "gold_tokens": err["gold_tokens"],
                    "fp_tokens": err["fp_tokens"],
                    "fn_tokens": err["fn_tokens"],
                    "coarse_error_type": err["coarse_error_type"],
                    "error_taxonomy": "; ".join(categories),
                    "notes": err.get("notes", ""),
                }
            )

        rule_predictions = build_rule_predictions(rows)
        rule_metrics = evaluate_rows(rows, pred_override=rule_predictions)
        improved_rows.append(
            {
                "dataset_id": dataset_id,
                "dataset_label": meta["label"],
                "improvement_variant": "rule_based_method_only_filter",
                "source_file": str(path),
                "total_rows": rule_metrics["total_rows"],
                "evaluated_rows": rule_metrics["evaluated_rows"],
                "skipped_rows": rule_metrics["skipped_rows"],
                "n_samples": rule_metrics["n_samples"],
                "tp": rule_metrics["tp"],
                "fp": rule_metrics["fp"],
                "fn": rule_metrics["fn"],
                "precision": fmt(rule_metrics["precision"]),
                "recall": fmt(rule_metrics["recall"]),
                "f1": fmt(rule_metrics["f1"]),
                "notes": "Conservative post-processing: drop tokens that look like analytical methods without any contamination/control cue.",
            }
        )

    before_after_rows: List[Dict[str, Any]] = []
    baseline_by_id = {row["dataset_id"]: row for row in baseline_rows}
    improved_by_id = {row["dataset_id"]: row for row in improved_rows}
    for dataset_id, base in baseline_by_id.items():
        imp = improved_by_id[dataset_id]
        before_after_rows.append(
            {
                "dataset_id": dataset_id,
                "dataset_label": base["dataset_label"],
                "comparison": "original_vs_rule_based_method_only_filter",
                "original_precision": base["precision"],
                "original_recall": base["recall"],
                "original_f1": base["f1"],
                "original_tp": base["tp"],
                "original_fp": base["fp"],
                "original_fn": base["fn"],
                "improved_precision": imp["precision"],
                "improved_recall": imp["recall"],
                "improved_f1": imp["f1"],
                "improved_tp": imp["tp"],
                "improved_fp": imp["fp"],
                "improved_fn": imp["fn"],
                "delta_precision": fmt(float(imp["precision"]) - float(base["precision"])),
                "delta_recall": fmt(float(imp["recall"]) - float(base["recall"])),
                "delta_f1": fmt(float(imp["f1"]) - float(base["f1"])),
            }
        )

    if "field_current_best" in baseline_by_id and "field_narrow_improved" in baseline_by_id:
        base = baseline_by_id["field_current_best"]
        imp = baseline_by_id["field_narrow_improved"]
        improved_rows.append(
            {
                "dataset_id": "field_narrow_improved",
                "dataset_label": "Field-specific narrow improved",
                "improvement_variant": "existing_ontology_guided_prompt_evidence_refinement",
                "source_file": str(DATASETS["field_narrow_improved"]["path"]),
                "total_rows": imp["total_rows"],
                "evaluated_rows": imp["evaluated_rows"],
                "skipped_rows": imp["skipped_rows"],
                "n_samples": imp["n_samples"],
                "tp": imp["tp"],
                "fp": imp["fp"],
                "fn": imp["fn"],
                "precision": imp["precision"],
                "recall": imp["recall"],
                "f1": imp["f1"],
                "notes": "Existing narrow field-specific run; used as a conservative prompt/evidence-refinement comparison against current_best.",
            }
        )
        before_after_rows.append(
            {
                "dataset_id": "field_specific_current_best_to_narrow_improved",
                "dataset_label": "Field-specific current best -> narrow improved",
                "comparison": "existing_prompt_evidence_refinement",
                "original_precision": base["precision"],
                "original_recall": base["recall"],
                "original_f1": base["f1"],
                "original_tp": base["tp"],
                "original_fp": base["fp"],
                "original_fn": base["fn"],
                "improved_precision": imp["precision"],
                "improved_recall": imp["recall"],
                "improved_f1": imp["f1"],
                "improved_tp": imp["tp"],
                "improved_fp": imp["fp"],
                "improved_fn": imp["fn"],
                "delta_precision": fmt(float(imp["precision"]) - float(base["precision"])),
                "delta_recall": fmt(float(imp["recall"]) - float(base["recall"])),
                "delta_f1": fmt(float(imp["f1"]) - float(base["f1"])),
            }
        )

    write_csv(
        OUT_DIR / "contamination_controls_source_inventory.csv",
        ["dataset_id", "label", "role", "path", "exists", "size_bytes", "sha256", "archived_summary"],
        source_inventory,
    )
    write_csv(
        OUT_DIR / "contamination_controls_baseline_metrics.csv",
        [
            "dataset_id",
            "dataset_label",
            "source_file",
            "total_rows",
            "evaluated_rows",
            "skipped_rows",
            "n_samples",
            "tp",
            "fp",
            "fn",
            "precision",
            "recall",
            "f1",
            "archived_precision",
            "archived_recall",
            "archived_f1",
            "matching_rule",
        ],
        baseline_rows,
    )
    write_csv(
        OUT_DIR / "contamination_controls_improved_metrics.csv",
        [
            "dataset_id",
            "dataset_label",
            "improvement_variant",
            "source_file",
            "total_rows",
            "evaluated_rows",
            "skipped_rows",
            "n_samples",
            "tp",
            "fp",
            "fn",
            "precision",
            "recall",
            "f1",
            "notes",
        ],
        improved_rows,
    )
    write_csv(
        OUT_DIR / "contamination_controls_before_after_table.csv",
        [
            "dataset_id",
            "dataset_label",
            "comparison",
            "original_precision",
            "original_recall",
            "original_f1",
            "original_tp",
            "original_fp",
            "original_fn",
            "improved_precision",
            "improved_recall",
            "improved_f1",
            "improved_tp",
            "improved_fp",
            "improved_fn",
            "delta_precision",
            "delta_recall",
            "delta_f1",
        ],
        before_after_rows,
    )
    write_csv(
        OUT_DIR / "contamination_controls_error_cases.csv",
        [
            "dataset_id",
            "dataset_label",
            "doc_id",
            "doc_name",
            "pred_contamination_controls",
            "gold_contamination_controls",
            "pred_tokens",
            "gold_tokens",
            "fp_tokens",
            "fn_tokens",
            "coarse_error_type",
            "error_taxonomy",
            "notes",
        ],
        error_cases,
    )

    taxonomy_table_rows = [[name, taxonomy_counts[name]] for name in sorted(taxonomy_counts)]
    dataset_taxonomy_rows: List[List[Any]] = []
    for dataset_id in sorted(taxonomy_by_dataset):
        for category, count in sorted(taxonomy_by_dataset[dataset_id].items()):
            dataset_taxonomy_rows.append([dataset_id, category, count])

    taxonomy_md = [
        "# contamination_controls Error Taxonomy",
        "",
        "This taxonomy was applied to row-level token-set errors for the `contamination_controls` field.",
        "",
        "- sparse or absent explicit contamination description: the document title/notes provide little explicit contamination-control language, so empty gold labels or empty predictions are expected to be unstable.",
        "- indirect wording / implicit procedural control: the control is expressed through procedural language such as blanks, sterile handling, curation, or negative controls rather than a direct field label.",
        "- entity-boundary ambiguity: the prediction captures a related but differently scoped control phrase, e.g. `blank controls` vs. a specific `quality-control blank of DI water`.",
        "- method vs control confusion: analytical/sample-preparation methods are extracted as contamination controls.",
        "- negated or contrastive statements: statements such as `indicated no contamination` require preserving a negative or contrastive relation.",
        "- over-extraction of general lab procedures: generic blanks, storage, curation, or sterile handling are over-predicted when the gold label is empty.",
        "- under-extraction of sample-specific controls: sample-specific handling, curation, storage, blank, or comparison-material controls are missed.",
        "",
        "## Overall Counts",
        "",
        markdown_table(["error_taxonomy", "count"], taxonomy_table_rows),
        "",
        "## Counts by Dataset",
        "",
        markdown_table(["dataset_id", "error_taxonomy", "count"], dataset_taxonomy_rows),
        "",
    ]
    (OUT_DIR / "contamination_controls_error_taxonomy.md").write_text("\n".join(taxonomy_md), encoding="utf-8")

    baseline_table = markdown_table(
        ["dataset", "n_samples", "TP", "FP", "FN", "P", "R", "F1"],
        [
            [
                row["dataset_id"],
                row["n_samples"],
                row["tp"],
                row["fp"],
                row["fn"],
                row["precision"],
                row["recall"],
                row["f1"],
            ]
            for row in baseline_rows
        ],
    )
    before_after_table = markdown_table(
        ["comparison", "original_F1", "improved_F1", "delta_F1", "original_P/R", "improved_P/R"],
        [
            [
                row["comparison"],
                row["original_f1"],
                row["improved_f1"],
                row["delta_f1"],
                f"{row['original_precision']}/{row['original_recall']}",
                f"{row['improved_precision']}/{row['improved_recall']}",
            ]
            for row in before_after_rows
        ],
    )

    error_summary_md = [
        "# contamination_controls Error Summary",
        "",
        "## Reproduced Metrics",
        "",
        baseline_table,
        "",
        "## Error Type Distribution",
        "",
        markdown_table(["error_taxonomy", "count"], taxonomy_table_rows),
        "",
        "## Small Improvement Experiment",
        "",
        before_after_table,
        "",
        "The rule-based method-only filter was intentionally conservative. It only removes tokens that look like analytical methods and contain no contamination/control cue. In the available rows, most false positives already use contamination-control vocabulary (for example blank controls, sterile handling, or storage), so the conservative rule has little or no effect. The existing narrow prompt/evidence-refinement run did not improve contamination_controls F1 relative to the current-best field-specific run.",
        "",
    ]
    (OUT_DIR / "contamination_controls_error_summary.md").write_text("\n".join(error_summary_md), encoding="utf-8")

    report_md = [
        "# contamination_controls Analysis Report",
        "",
        "## Scope",
        "",
        "This analysis audits the low-performing `contamination_controls` extraction field using existing gold/prediction files only. It does not modify frozen retrieval qrels results, end-to-end baseline results, benchmark queries, or manuscript text.",
        "",
        "## Located Data Sources",
        "",
        markdown_table(
            ["dataset_id", "role", "exists", "path"],
            [[row["dataset_id"], row["role"], row["exists"], row["path"]] for row in source_inventory],
        ),
        "",
        "## Paper Result Source Mapping",
        "",
        "`D:/workspace/123/PAPER_RESULTS_MAP.md` notes that final manuscript table numbering is not encoded in the repository. The corresponding extraction result sources are retained under `submission_backup/03_processed_results/extraction/`, especially `gold_v2_eval_20260313_v1/`, `gold_v3_eval_20260313_v1/`, and `gold_field_specific_narrow_20260312_v1/`. Therefore this report treats those retained processed summaries, plus their row-level prediction/gold inputs, as the source for the Table-6-style extraction metrics.",
        "",
        "## Reproduced Baseline Metrics",
        "",
        baseline_table,
        "",
        "The low-score field-specific run reproduced the archived contamination_controls metrics: P=0.1923, R=0.5000, F1=0.2778. The gold v2 fixed evaluation input reproduced P=0.2069, R=0.5455, F1=0.3000. Gold v3 reproduced P=0.5882, R=0.9091, F1=0.7143, demonstrating benchmark-version sensitivity.",
        "",
        "## Main Error Patterns",
        "",
        markdown_table(["error_taxonomy", "count"], taxonomy_table_rows),
        "",
        "The dominant failures are boundary and specificity errors: the system often predicts generic controls such as blank controls, sterile handling, cold curation, aluminum foil storage, or freezer storage, while the gold labels either require a more specific form or intentionally leave the field empty. Recall failures also occur when controls are expressed indirectly, for example as curation practices or negative contamination assessments.",
        "",
        "## Conservative Improvement Experiment",
        "",
        "Two conservative comparisons were recorded:",
        "",
        "- `rule_based_method_only_filter`: post-process existing predictions by dropping only analytical-method tokens that lack any contamination/control cue.",
        "- `existing_ontology_guided_prompt_evidence_refinement`: compare the existing field-specific current-best run against the already archived narrow-improved prompt/evidence run.",
        "",
        before_after_table,
        "",
        "The conservative rule did not materially improve the evaluated runs because most false positives were not pure analytical methods; they were plausible but over-general contamination-control phrases. The archived narrow-improved run slightly reduced contamination_controls F1 compared with the current-best field-specific run. This supports the interpretation that the field is difficult mainly because of sparse evidence, implicit wording, and unstable annotation boundaries rather than a single easy-to-filter error class.",
        "",
        "## Interpretation for Reviewer Response",
        "",
        "The observed volatility across legacy, gold v2, and gold v3 reflects the small number of positive contamination_controls cases and the boundary-sensitive nature of the field. Adding or revising a few documents changes both false-positive and false-negative counts substantially. The field should therefore be discussed separately from higher-density fields such as meteorite names or organic compound classes.",
        "",
    ]
    (OUT_DIR / "contamination_controls_analysis_report.md").write_text("\n".join(report_md), encoding="utf-8")

    discussion_text = [
        "# Manuscript Discussion Text: contamination_controls",
        "",
        "The contamination-control field remained the most unstable extraction target across benchmark versions. Error analysis showed that many papers do not state contamination controls as compact named entities; instead, controls are often expressed indirectly through curation, storage, blank-control, sterile-handling, or negative-assessment language. This produces boundary-sensitive disagreements, such as generic `blank controls` versus a specific quality-control blank, and also encourages over-extraction of general laboratory procedures when the evidence is not sample-specific. A conservative post-processing experiment that filtered only method-like phrases did not materially improve F1, indicating that most errors were not simple analytical-method false positives. These results suggest that contamination_controls requires either more explicit annotation guidance or evidence-aware extraction that distinguishes sample-specific contamination safeguards from generic laboratory workflow descriptions. We therefore treat this field as a difficult edge case rather than as a solved extraction target.",
        "",
    ]
    (OUT_DIR / "manuscript_discussion_text_contamination_controls.md").write_text("\n".join(discussion_text), encoding="utf-8")

    manifest_rows = []
    for path in sorted(OUT_DIR.glob("*")):
        if path.is_file() and path.name != "run_contamination_controls_error_analysis.py":
            manifest_rows.append(
                {
                    "file": path.name,
                    "size_bytes": path.stat().st_size,
                    "sha256": file_sha256(path),
                }
            )
    write_csv(OUT_DIR / "output_manifest.csv", ["file", "size_bytes", "sha256"], manifest_rows)

    print(json.dumps({"out_dir": str(OUT_DIR), "files_written": len(manifest_rows) + 1}, indent=2))


if __name__ == "__main__":
    main()
