import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Compare baseline vs prior narrow_improved vs fixed gold-class preservation organics extraction."

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
            "--prior-narrow-dir",
            type=str,
            default=None,
            help="Existing narrow_improved directory to compare against.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_class_preservation_<timestamp>/",
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

        prior_narrow_dir = self._resolve_prior_narrow_dir(options.get("prior_narrow_dir"))
        if not prior_narrow_dir.exists():
            raise CommandError(f"prior narrow_improved dir not found: {prior_narrow_dir}")

        prior_summary_path = prior_narrow_dir / "rerun_eval" / "accuracy_summary.csv"
        prior_organic_summary_path = prior_narrow_dir / "organic_error_summary.csv"
        if not prior_summary_path.exists():
            raise CommandError(f"prior narrow accuracy summary not found: {prior_summary_path}")
        if not prior_organic_summary_path.exists():
            raise CommandError(f"prior narrow organic error summary not found: {prior_organic_summary_path}")

        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        baseline_eval_dir = out_dir / "baseline_eval"
        fixed_dir = out_dir / "gold_class_preserved"
        metric_summary_path = out_dir / "comparison_metric_summary.csv"
        organic_error_summary_path = out_dir / "comparison_organic_error_summary.csv"

        self.stdout.write(f"gold_path={gold_path}")
        self.stdout.write(f"prior_narrow_dir={prior_narrow_dir}")
        self.stdout.write(f"out_dir={out_dir}")

        call_command("eval_extraction_accuracy", gold=str(gold_path), out=str(baseline_eval_dir))
        call_command(
            "rerun_gold_extraction_eval",
            gold=str(gold_path),
            out=str(fixed_dir),
            limit=options.get("limit"),
            max_fetch_chunks=int(options["max_fetch_chunks"]),
            max_selected_chunks=int(options["max_selected_chunks"]),
            strict_organics_prompt=True,
            field_specific_evidence=True,
            meteorite_name_strategy="title_first_shared",
            organic_filter=True,
            organic_projection=True,
            expand_organic_evidence=True,
            expand_contamination_evidence=True,
        )

        self._build_metric_summary(
            baseline_summary_path=baseline_eval_dir / "accuracy_summary.csv",
            prior_narrow_summary_path=prior_summary_path,
            fixed_summary_path=fixed_dir / "rerun_eval" / "accuracy_summary.csv",
            out_path=metric_summary_path,
        )
        self._build_organic_error_summary(
            baseline_summary_path=fixed_dir / "baseline_organic_error_summary.csv",
            prior_narrow_summary_path=prior_organic_summary_path,
            fixed_summary_path=fixed_dir / "organic_error_summary.csv",
            out_path=organic_error_summary_path,
        )

        self.stdout.write(f"baseline_eval_dir={baseline_eval_dir}")
        self.stdout.write(f"fixed_dir={fixed_dir}")
        self.stdout.write(f"metric_summary_path={metric_summary_path}")
        self.stdout.write(f"organic_error_summary_path={organic_error_summary_path}")

    def _resolve_prior_narrow_dir(self, prior_arg: Optional[str]) -> Path:
        if prior_arg and str(prior_arg).strip():
            return Path(str(prior_arg)).expanduser().resolve()
        return (
            Path(settings.BASE_DIR)
            / "runs"
            / "gold_field_specific_narrow_20260312_v1"
            / "narrow_improved"
        ).resolve()

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_class_preservation_{ts}").resolve()

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
        prior_narrow_summary_path: Path,
        fixed_summary_path: Path,
        out_path: Path,
    ) -> None:
        baseline = self._load_summary_rows(baseline_summary_path)
        prior = self._load_summary_rows(prior_narrow_summary_path)
        fixed = self._load_summary_rows(fixed_summary_path)

        rows = []
        for field in self.FIELDS:
            base = baseline.get(field, {})
            old = prior.get(field, {})
            new = fixed.get(field, {})
            rows.append(
                {
                    "field": field,
                    "baseline_precision": base.get("precision", ""),
                    "baseline_recall": base.get("recall", ""),
                    "baseline_f1": base.get("f1", ""),
                    "baseline_n_samples": base.get("n_samples", ""),
                    "prior_narrow_precision": old.get("precision", ""),
                    "prior_narrow_recall": old.get("recall", ""),
                    "prior_narrow_f1": old.get("f1", ""),
                    "prior_narrow_n_samples": old.get("n_samples", ""),
                    "fixed_precision": new.get("precision", ""),
                    "fixed_recall": new.get("recall", ""),
                    "fixed_f1": new.get("f1", ""),
                    "fixed_n_samples": new.get("n_samples", ""),
                }
            )

        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def _build_organic_error_summary(
        self,
        *,
        baseline_summary_path: Path,
        prior_narrow_summary_path: Path,
        fixed_summary_path: Path,
        out_path: Path,
    ) -> None:
        baseline = self._load_error_summary_rows(baseline_summary_path)
        prior = self._load_error_summary_rows(prior_narrow_summary_path)
        fixed = self._load_error_summary_rows(fixed_summary_path)

        rows = []
        for category in self.ORGANIC_ERROR_CATEGORIES:
            rows.append(
                {
                    "category": category,
                    "baseline_count": baseline.get(category, {}).get("count", "0"),
                    "prior_narrow_count": prior.get(category, {}).get("count", "0"),
                    "fixed_count": fixed.get(category, {}).get("count", "0"),
                }
            )

        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
