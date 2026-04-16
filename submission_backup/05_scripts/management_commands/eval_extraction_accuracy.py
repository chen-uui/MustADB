import csv
import ast
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from pdf_processor.extraction_postprocess import ExtractionFieldPostprocessor


class Command(BaseCommand):
    help = "Evaluate extraction accuracy from gold CSV and export P/R/F1 reports."

    REQUIRED_COLUMNS = (
        "doc_id",
        "doc_name",
        "pred_meteorite_name",
        "pred_organic_compounds",
        "pred_contamination_controls",
        "gold_meteorite_name",
        "gold_organic_compounds",
        "gold_contamination_controls",
    )
    OPTIONAL_COLUMNS = ("in_scope", "skip_row", "notes")

    SUMMARY_COLUMNS = (
        "field",
        "total_rows",
        "evaluated_rows",
        "skipped_rows",
        "coverage_rate",
        "n_samples",
        "precision",
        "recall",
        "f1",
        "matching_rule",
    )

    ERROR_COLUMNS = (
        "doc_id",
        "doc_name",
        "field",
        "pred_value",
        "gold_value",
        "error_type",
    )

    PLACEHOLDER_TEXTS = {
        "",
        "unknown",
        "not specified",
        "none",
        "null",
        "n/a",
        "na",
    }
    YES_VALUES = {"yes", "y", "true", "1"}
    NO_VALUES = {"no", "n", "false", "0"}
    NO_RELEVANT_MARKER = "\u8be5\u8bba\u6587\u4e0d\u5305\u542b"

    ORGANIC_SPLIT_PATTERN = re.compile(r"[;,\uFF0C\uFF1B\u3001]+")

    def add_arguments(self, parser):
        parser.add_argument(
            "--gold",
            type=str,
            required=True,
            help="Path to filled gold CSV.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/accuracy_<timestamp>/",
        )

    def handle(self, *args, **options):
        gold_path = Path(str(options["gold"])).expanduser().resolve()
        if not gold_path.exists():
            raise CommandError(f"gold csv not found: {gold_path}")

        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        total_rows_data = self._load_gold_rows(gold_path)
        evaluated_rows_data, skipped_rows = self._split_rows_for_evaluation(total_rows_data)

        total_rows = len(total_rows_data)
        evaluated_rows = len(evaluated_rows_data)
        coverage_rate = (float(evaluated_rows) / float(total_rows)) if total_rows > 0 else 0.0
        dataset_stats = {
            "total_rows": str(total_rows),
            "evaluated_rows": str(evaluated_rows),
            "skipped_rows": str(skipped_rows),
            "coverage_rate": self._fmt(coverage_rate),
        }

        summary_rows: List[Dict[str, str]] = []
        error_rows: List[Dict[str, str]] = []

        meteorite_summary, meteorite_errors = self._eval_exact_field(
            rows=evaluated_rows_data,
            field_name="meteorite_name",
            pred_col="pred_meteorite_name",
            gold_col="gold_meteorite_name",
            matching_rule="case-insensitive exact match (trim); empty-empty ignored",
        )
        summary_rows.append(meteorite_summary)
        error_rows.extend(meteorite_errors)

        contamination_summary, contamination_errors = self._eval_token_set_field(
            rows=evaluated_rows_data,
            field_name="contamination_controls",
            pred_col="pred_contamination_controls",
            gold_col="gold_contamination_controls",
            matching_rule=(
                "lowercase+trim; normalize comma/semicolon separators; parse Python/JSON list-string; "
                "token-set micro P/R/F1 by overlap; empty-empty ignored"
            ),
        )
        summary_rows.append(contamination_summary)
        error_rows.extend(contamination_errors)

        organic_summary, organic_errors = self._eval_token_set_field(
            rows=evaluated_rows_data,
            field_name="organic_compounds",
            pred_col="pred_organic_compounds",
            gold_col="gold_organic_compounds",
            matching_rule=(
                "shared organic canonicalization via ExtractionFieldPostprocessor; "
                "token-set micro P/R/F1 by overlap; empty-empty ignored"
            ),
        )
        summary_rows.append(organic_summary)
        error_rows.extend(organic_errors)

        overall_row = self._build_overall_macro_row(summary_rows)
        summary_rows.append(overall_row)

        summary_rows = [self._merge_dataset_stats(row, dataset_stats) for row in summary_rows]

        summary_path = out_dir / "accuracy_summary.csv"
        errors_path = out_dir / "accuracy_errors.csv"
        self._write_csv(summary_path, self.SUMMARY_COLUMNS, summary_rows)
        self._write_csv(errors_path, self.ERROR_COLUMNS, error_rows)

        self.stdout.write(f"total_rows={total_rows}")
        self.stdout.write(f"evaluated_rows={evaluated_rows}")
        self.stdout.write(f"skipped_rows={skipped_rows}")
        self.stdout.write(f"coverage_rate={self._fmt(coverage_rate)}")
        self.stdout.write(f"error_rows={len(error_rows)}")
        self.stdout.write(f"out_dir={out_dir}")
        self.stdout.write(f"summary_path={summary_path}")
        self.stdout.write(f"errors_path={errors_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"accuracy_{ts}").resolve()

    def _load_gold_rows(self, gold_path: Path) -> List[Dict[str, str]]:
        with gold_path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames is None:
                raise CommandError(f"gold csv has no header: {gold_path}")

            missing = [col for col in self.REQUIRED_COLUMNS if col not in reader.fieldnames]
            if missing:
                raise CommandError(f"gold csv missing required columns: {', '.join(missing)}")

            rows: List[Dict[str, str]] = []
            for row in reader:
                normalized = {key: str(row.get(key, "") or "").strip() for key in self.REQUIRED_COLUMNS}
                for opt_key in self.OPTIONAL_COLUMNS:
                    normalized[opt_key] = str(row.get(opt_key, "") or "").strip()
                rows.append(normalized)

        if not rows:
            raise CommandError(f"gold csv has no data rows: {gold_path}")
        return rows

    def _split_rows_for_evaluation(
        self, rows: Sequence[Dict[str, str]]
    ) -> Tuple[List[Dict[str, str]], int]:
        evaluated_rows: List[Dict[str, str]] = []
        skipped = 0
        for row in rows:
            if self._should_skip_row(row):
                skipped += 1
                continue
            evaluated_rows.append(row)
        return evaluated_rows, skipped

    def _should_skip_row(self, row: Dict[str, str]) -> bool:
        skip_value = self._normalize_bool_value(row.get("skip_row", ""))
        if skip_value is True:
            return True

        in_scope_value = self._normalize_bool_value(row.get("in_scope", ""))
        if in_scope_value is False:
            return True

        return False

    def _normalize_bool_value(self, value: str) -> Optional[bool]:
        lowered = str(value or "").strip().lower()
        if lowered in self.YES_VALUES:
            return True
        if lowered in self.NO_VALUES:
            return False
        return None

    def _merge_dataset_stats(self, row: Dict[str, str], stats: Dict[str, str]) -> Dict[str, str]:
        merged = dict(row)
        merged.update(stats)
        return merged

    def _eval_exact_field(
        self,
        *,
        rows: Sequence[Dict[str, str]],
        field_name: str,
        pred_col: str,
        gold_col: str,
        matching_rule: str,
    ) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
        tp = 0
        fp = 0
        fn = 0
        n_samples = 0
        errors: List[Dict[str, str]] = []

        for row in rows:
            pred_raw = row.get(pred_col, "")
            gold_raw = row.get(gold_col, "")
            pred_norm = self._normalize_for_match(pred_raw)
            gold_norm = self._normalize_for_match(gold_raw)

            if not pred_norm and not gold_norm:
                continue

            n_samples += 1
            if pred_norm and gold_norm and pred_norm == gold_norm:
                tp += 1
                continue

            if pred_norm and gold_norm:
                fp += 1
                fn += 1
                errors.append(
                    {
                        "doc_id": row.get("doc_id", ""),
                        "doc_name": row.get("doc_name", ""),
                        "field": field_name,
                        "pred_value": pred_raw,
                        "gold_value": gold_raw,
                        "error_type": "MISMATCH",
                    }
                )
                continue

            if pred_norm and not gold_norm:
                fp += 1
                errors.append(
                    {
                        "doc_id": row.get("doc_id", ""),
                        "doc_name": row.get("doc_name", ""),
                        "field": field_name,
                        "pred_value": pred_raw,
                        "gold_value": gold_raw,
                        "error_type": "FP",
                    }
                )
                continue

            fn += 1
            errors.append(
                {
                    "doc_id": row.get("doc_id", ""),
                    "doc_name": row.get("doc_name", ""),
                    "field": field_name,
                    "pred_value": pred_raw,
                    "gold_value": gold_raw,
                    "error_type": "FN",
                }
            )

        precision, recall, f1 = self._prf(tp=tp, fp=fp, fn=fn)
        summary = {
            "field": field_name,
            "n_samples": str(n_samples),
            "precision": self._fmt(precision),
            "recall": self._fmt(recall),
            "f1": self._fmt(f1),
            "matching_rule": matching_rule,
        }
        return summary, errors

    def _eval_token_set_field(
        self,
        *,
        rows: Sequence[Dict[str, str]],
        field_name: str,
        pred_col: str,
        gold_col: str,
        matching_rule: str,
    ) -> Tuple[Dict[str, str], List[Dict[str, str]]]:
        tp = 0
        fp = 0
        fn = 0
        n_samples = 0
        errors: List[Dict[str, str]] = []

        for row in rows:
            pred_raw = row.get(pred_col, "")
            gold_raw = row.get(gold_col, "")
            if field_name == "organic_compounds":
                pred_set = self._parse_organic_token_set(pred_raw)
                gold_set = self._parse_organic_token_set(gold_raw)
            else:
                pred_set = self._parse_token_set(pred_raw)
                gold_set = self._parse_token_set(gold_raw)

            if not pred_set and not gold_set:
                continue

            n_samples += 1
            overlap = pred_set & gold_set
            fp_set = pred_set - gold_set
            fn_set = gold_set - pred_set

            tp += len(overlap)
            fp += len(fp_set)
            fn += len(fn_set)

            if not fp_set and not fn_set:
                continue

            if pred_set and not gold_set:
                error_type = "FP"
            elif gold_set and not pred_set:
                error_type = "FN"
            else:
                error_type = "MISMATCH"

            errors.append(
                {
                    "doc_id": row.get("doc_id", ""),
                    "doc_name": row.get("doc_name", ""),
                    "field": field_name,
                    "pred_value": pred_raw,
                    "gold_value": gold_raw,
                    "error_type": error_type,
                }
            )

        precision, recall, f1 = self._prf(tp=tp, fp=fp, fn=fn)
        summary = {
            "field": field_name,
            "n_samples": str(n_samples),
            "precision": self._fmt(precision),
            "recall": self._fmt(recall),
            "f1": self._fmt(f1),
            "matching_rule": matching_rule,
        }
        return summary, errors

    def _parse_organic_token_set(self, value: Any) -> set[str]:
        tokens = set()
        for item in ExtractionFieldPostprocessor.normalize_organic_compounds_list(value):
            normalized = self._normalize_for_match(item)
            if normalized:
                tokens.add(normalized)
        return tokens

    def _build_overall_macro_row(self, summary_rows: Sequence[Dict[str, str]]) -> Dict[str, str]:
        active_rows = []
        for row in summary_rows:
            try:
                if int(row.get("n_samples", "0")) > 0:
                    active_rows.append(row)
            except ValueError:
                continue

        if not active_rows:
            return {
                "field": "overall_macro_avg",
                "n_samples": "0",
                "precision": self._fmt(0.0),
                "recall": self._fmt(0.0),
                "f1": self._fmt(0.0),
                "matching_rule": "macro average over fields with n_samples>0; no active samples",
            }

        precisions = [float(row["precision"]) for row in active_rows]
        recalls = [float(row["recall"]) for row in active_rows]
        f1s = [float(row["f1"]) for row in active_rows]
        total_samples = sum(int(row["n_samples"]) for row in active_rows)

        return {
            "field": "overall_macro_avg",
            "n_samples": str(total_samples),
            "precision": self._fmt(sum(precisions) / len(precisions)),
            "recall": self._fmt(sum(recalls) / len(recalls)),
            "f1": self._fmt(sum(f1s) / len(f1s)),
            "matching_rule": "macro average over fields with n_samples>0",
        }

    def _parse_token_set(self, value: Any) -> set[str]:
        tokens = set()
        for item in self._flatten_token_candidates(value):
            token = self._normalize_for_match(item)
            if token:
                tokens.add(token)
        return tokens

    def _flatten_token_candidates(self, value: Any) -> List[str]:
        if value is None:
            return []

        if isinstance(value, (list, tuple, set)):
            out: List[str] = []
            for item in value:
                out.extend(self._flatten_token_candidates(item))
            return out

        if isinstance(value, dict):
            out: List[str] = []
            for item in value.values():
                out.extend(self._flatten_token_candidates(item))
            return out

        text = str(value).strip()
        if not text:
            return []

        parsed = self._try_parse_list_literal(text)
        if isinstance(parsed, (list, tuple, set)):
            out: List[str] = []
            for item in parsed:
                out.extend(self._flatten_token_candidates(item))
            return out

        parts = self.ORGANIC_SPLIT_PATTERN.split(text)
        return [re.sub(r"\s+", " ", part).strip() for part in parts if part and str(part).strip()]

    def _try_parse_list_literal(self, text: str) -> Optional[Any]:
        stripped = str(text or "").strip()
        if not stripped:
            return None
        if stripped[0] not in "[{(":
            return None
        try:
            parsed = ast.literal_eval(stripped)
        except (ValueError, SyntaxError):
            return None
        return parsed

    def _normalize_for_match(self, value: Any) -> str:
        text = str(value or "").strip()
        if not text:
            return ""
        text = re.sub(r"\s+", " ", text)
        lowered = text.lower()
        if lowered in self.PLACEHOLDER_TEXTS:
            return ""
        if self.NO_RELEVANT_MARKER in text:
            return ""
        return lowered

    def _prf(self, *, tp: int, fp: int, fn: int) -> Tuple[float, float, float]:
        precision = float(tp) / float(tp + fp) if (tp + fp) > 0 else 0.0
        recall = float(tp) / float(tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        return precision, recall, f1

    def _fmt(self, value: float) -> str:
        return f"{value:.4f}"

    def _write_csv(
        self,
        path: Path,
        fieldnames: Sequence[str],
        rows: Sequence[Dict[str, str]],
    ) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(fieldnames))
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
