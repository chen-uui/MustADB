import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run baseline vs prompt-only vs field-specific-evidence ablations on gold extraction."

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
        "normalization_error",
        "duplicate_or_conflict",
    )

    def add_arguments(self, parser):
        parser.add_argument("--gold", type=str, required=True, help="Baseline gold CSV path.")
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_ablation_<timestamp>/",
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
        prompt_only_dir = out_dir / "prompt_only"
        field_specific_dir = out_dir / "prompt_plus_field_specific_evidence"
        metric_summary_path = out_dir / "ablation_metric_summary.csv"
        organic_error_summary_path = out_dir / "ablation_organic_error_summary.csv"

        self.stdout.write(f"gold_path={gold_path}")
        self.stdout.write(f"out_dir={out_dir}")

        call_command("eval_extraction_accuracy", gold=str(gold_path), out=str(baseline_eval_dir))

        rerun_kwargs = {
            "gold": str(gold_path),
            "limit": options.get("limit"),
            "max_fetch_chunks": int(options["max_fetch_chunks"]),
            "max_selected_chunks": int(options["max_selected_chunks"]),
            "strict_organics_prompt": True,
        }

        call_command(
            "rerun_gold_extraction_eval",
            out=str(prompt_only_dir),
            **rerun_kwargs,
        )
        call_command(
            "rerun_gold_extraction_eval",
            out=str(field_specific_dir),
            field_specific_evidence=True,
            **rerun_kwargs,
        )

        self._build_metric_summary(
            baseline_summary_path=baseline_eval_dir / "accuracy_summary.csv",
            prompt_only_summary_path=prompt_only_dir / "rerun_eval" / "accuracy_summary.csv",
            field_specific_summary_path=field_specific_dir / "rerun_eval" / "accuracy_summary.csv",
            out_path=metric_summary_path,
        )
        self._build_organic_error_summary(
            baseline_summary_path=prompt_only_dir / "baseline_organic_error_summary.csv",
            prompt_only_summary_path=prompt_only_dir / "organic_error_summary.csv",
            field_specific_summary_path=field_specific_dir / "organic_error_summary.csv",
            out_path=organic_error_summary_path,
        )

        self.stdout.write(f"baseline_eval_dir={baseline_eval_dir}")
        self.stdout.write(f"prompt_only_dir={prompt_only_dir}")
        self.stdout.write(f"field_specific_dir={field_specific_dir}")
        self.stdout.write(f"metric_summary_path={metric_summary_path}")
        self.stdout.write(f"organic_error_summary_path={organic_error_summary_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_ablation_{ts}").resolve()

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
        prompt_only_summary_path: Path,
        field_specific_summary_path: Path,
        out_path: Path,
    ) -> None:
        baseline = self._load_summary_rows(baseline_summary_path)
        prompt_only = self._load_summary_rows(prompt_only_summary_path)
        field_specific = self._load_summary_rows(field_specific_summary_path)

        rows: List[Dict[str, str]] = []
        for field in self.FIELDS:
            before = baseline.get(field, {})
            prompt = prompt_only.get(field, {})
            routed = field_specific.get(field, {})
            rows.append(
                {
                    "field": field,
                    "baseline_precision": before.get("precision", ""),
                    "baseline_recall": before.get("recall", ""),
                    "baseline_f1": before.get("f1", ""),
                    "baseline_n_samples": before.get("n_samples", ""),
                    "prompt_only_precision": prompt.get("precision", ""),
                    "prompt_only_recall": prompt.get("recall", ""),
                    "prompt_only_f1": prompt.get("f1", ""),
                    "prompt_only_n_samples": prompt.get("n_samples", ""),
                    "field_specific_precision": routed.get("precision", ""),
                    "field_specific_recall": routed.get("recall", ""),
                    "field_specific_f1": routed.get("f1", ""),
                    "field_specific_n_samples": routed.get("n_samples", ""),
                }
            )
        self._write_csv(out_path, list(rows[0].keys()), rows)

    def _build_organic_error_summary(
        self,
        *,
        baseline_summary_path: Path,
        prompt_only_summary_path: Path,
        field_specific_summary_path: Path,
        out_path: Path,
    ) -> None:
        baseline = self._load_error_summary_rows(baseline_summary_path)
        prompt_only = self._load_error_summary_rows(prompt_only_summary_path)
        field_specific = self._load_error_summary_rows(field_specific_summary_path)

        rows: List[Dict[str, str]] = []
        for category in self.ORGANIC_ERROR_CATEGORIES:
            rows.append(
                {
                    "category": category,
                    "baseline_count": baseline.get(category, {}).get("count", "0"),
                    "prompt_only_count": prompt_only.get(category, {}).get("count", "0"),
                    "field_specific_count": field_specific.get(category, {}).get("count", "0"),
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
