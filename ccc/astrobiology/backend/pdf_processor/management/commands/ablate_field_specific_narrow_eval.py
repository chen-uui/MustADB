import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Compare baseline vs current field-specific vs narrow improved field-specific extraction."

    FIELDS = (
        "meteorite_name",
        "organic_compounds",
        "contamination_controls",
        "overall_macro_avg",
    )
    ORGANIC_ERROR_CATEGORIES = (
        "field_empty_or_missing",
        "missed_extraction",
        "wrong_extraction",
        "over_broad_or_generalized",
        "normalization_or_projection_issue",
        "duplicate_or_conflict",
    )

    def add_arguments(self, parser):
        parser.add_argument("--gold", type=str, required=True, help="Baseline gold CSV path.")
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_field_specific_narrow_<timestamp>/",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Optional cap on rerun rows after skip filtering.",
        )
        parser.add_argument(
            "--max-fetch-chunks",
            type=int,
            default=80,
            help="Maximum document chunks to load from Weaviate per document.",
        )
        parser.add_argument(
            "--max-selected-chunks",
            type=int,
            default=3,
            help="Maximum chunks per route sent to the extractor.",
        )

    def handle(self, *args, **options):
        gold_path = Path(str(options["gold"])).expanduser().resolve()
        if not gold_path.exists():
            raise CommandError(f"gold csv not found: {gold_path}")

        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        baseline_eval_dir = out_dir / "baseline_eval"
        current_best_dir = out_dir / "current_best_field_specific"
        narrow_improved_dir = out_dir / "narrow_improved"
        metric_summary_path = out_dir / "comparison_metric_summary.csv"
        organic_error_summary_path = out_dir / "comparison_organic_error_summary.csv"

        self.stdout.write(f"gold_path={gold_path}")
        self.stdout.write(f"out_dir={out_dir}")

        call_command("eval_extraction_accuracy", gold=str(gold_path), out=str(baseline_eval_dir))

        common_kwargs = {
            "gold": str(gold_path),
            "limit": options.get("limit"),
            "max_fetch_chunks": int(options["max_fetch_chunks"]),
            "max_selected_chunks": int(options["max_selected_chunks"]),
            "strict_organics_prompt": True,
            "field_specific_evidence": True,
        }

        call_command(
            "rerun_gold_extraction_eval",
            out=str(current_best_dir),
            **common_kwargs,
        )
        call_command(
            "rerun_gold_extraction_eval",
            out=str(narrow_improved_dir),
            meteorite_name_strategy="title_first_shared",
            organic_filter=True,
            organic_projection=True,
            expand_organic_evidence=True,
            expand_contamination_evidence=True,
            **common_kwargs,
        )

        self._build_metric_summary(
            baseline_summary_path=baseline_eval_dir / "accuracy_summary.csv",
            current_best_summary_path=current_best_dir / "rerun_eval" / "accuracy_summary.csv",
            narrow_improved_summary_path=narrow_improved_dir / "rerun_eval" / "accuracy_summary.csv",
            out_path=metric_summary_path,
        )
        self._build_organic_error_summary(
            baseline_summary_path=current_best_dir / "baseline_organic_error_summary.csv",
            current_best_summary_path=current_best_dir / "organic_error_summary.csv",
            narrow_improved_summary_path=narrow_improved_dir / "organic_error_summary.csv",
            out_path=organic_error_summary_path,
        )

        self.stdout.write(f"baseline_eval_dir={baseline_eval_dir}")
        self.stdout.write(f"current_best_dir={current_best_dir}")
        self.stdout.write(f"narrow_improved_dir={narrow_improved_dir}")
        self.stdout.write(f"metric_summary_path={metric_summary_path}")
        self.stdout.write(f"organic_error_summary_path={organic_error_summary_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_field_specific_narrow_{ts}").resolve()

    def _load_summary_rows(self, path: Path) -> Dict[str, Dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return {
                str(row.get("field", "") or "").strip(): {k: str(v or "").strip() for k, v in row.items()}
                for row in reader
            }

    def _load_error_summary_rows(self, path: Path) -> Dict[str, Dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return {
                str(row.get("category", "") or "").strip(): {k: str(v or "").strip() for k, v in row.items()}
                for row in reader
            }

    def _build_metric_summary(
        self,
        *,
        baseline_summary_path: Path,
        current_best_summary_path: Path,
        narrow_improved_summary_path: Path,
        out_path: Path,
    ) -> None:
        baseline = self._load_summary_rows(baseline_summary_path)
        current_best = self._load_summary_rows(current_best_summary_path)
        narrow_improved = self._load_summary_rows(narrow_improved_summary_path)

        rows: List[Dict[str, str]] = []
        for field in self.FIELDS:
            before = baseline.get(field, {})
            current = current_best.get(field, {})
            improved = narrow_improved.get(field, {})
            rows.append(
                {
                    "field": field,
                    "baseline_precision": before.get("precision", ""),
                    "baseline_recall": before.get("recall", ""),
                    "baseline_f1": before.get("f1", ""),
                    "baseline_n_samples": before.get("n_samples", ""),
                    "current_best_precision": current.get("precision", ""),
                    "current_best_recall": current.get("recall", ""),
                    "current_best_f1": current.get("f1", ""),
                    "current_best_n_samples": current.get("n_samples", ""),
                    "narrow_improved_precision": improved.get("precision", ""),
                    "narrow_improved_recall": improved.get("recall", ""),
                    "narrow_improved_f1": improved.get("f1", ""),
                    "narrow_improved_n_samples": improved.get("n_samples", ""),
                }
            )
        self._write_csv(out_path, list(rows[0].keys()), rows)

    def _build_organic_error_summary(
        self,
        *,
        baseline_summary_path: Path,
        current_best_summary_path: Path,
        narrow_improved_summary_path: Path,
        out_path: Path,
    ) -> None:
        baseline = self._load_error_summary_rows(baseline_summary_path)
        current_best = self._load_error_summary_rows(current_best_summary_path)
        narrow_improved = self._load_error_summary_rows(narrow_improved_summary_path)

        rows: List[Dict[str, str]] = []
        for category in self.ORGANIC_ERROR_CATEGORIES:
            rows.append(
                {
                    "category": category,
                    "baseline_count": baseline.get(category, {}).get("count", "0"),
                    "current_best_count": current_best.get(category, {}).get("count", "0"),
                    "narrow_improved_count": narrow_improved.get(category, {}).get("count", "0"),
                }
            )
        self._write_csv(out_path, list(rows[0].keys()), rows)

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
