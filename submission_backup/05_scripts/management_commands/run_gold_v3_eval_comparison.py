import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run formal evaluation on gold_seed_v3.csv and compare it against the existing gold_v2 evaluation."

    FIELDS = (
        "meteorite_name",
        "organic_compounds",
        "contamination_controls",
        "overall_macro_avg",
    )

    def add_arguments(self, parser):
        parser.add_argument("--gold-v2", type=str, required=True, help="gold_seed_v2.csv path.")
        parser.add_argument("--gold-v3", type=str, required=True, help="gold_seed_v3.csv path.")
        parser.add_argument(
            "--v2-summary",
            type=str,
            required=True,
            help="Existing gold_v2 accuracy_summary.csv path.",
        )
        parser.add_argument(
            "--supporting-final",
            type=str,
            default=None,
            help="Optional batch2 supporting final CSV path, used only for summary wording.",
        )
        parser.add_argument(
            "--out-dir",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_v3_eval_<timestamp>",
        )

    def handle(self, *args, **options):
        gold_v2 = Path(str(options["gold_v2"])).expanduser().resolve()
        gold_v3 = Path(str(options["gold_v3"])).expanduser().resolve()
        v2_summary = Path(str(options["v2_summary"])).expanduser().resolve()
        supporting_final = (
            Path(str(options["supporting_final"])).expanduser().resolve()
            if options.get("supporting_final")
            else None
        )
        if not gold_v2.exists():
            raise CommandError(f"gold_v2 not found: {gold_v2}")
        if not gold_v3.exists():
            raise CommandError(f"gold_v3 not found: {gold_v3}")
        if not v2_summary.exists():
            raise CommandError(f"v2 summary not found: {v2_summary}")
        if supporting_final and not supporting_final.exists():
            raise CommandError(f"supporting final not found: {supporting_final}")

        out_dir = self._resolve_out_dir(options.get("out_dir"))
        out_dir.mkdir(parents=True, exist_ok=True)

        v3_eval_dir = out_dir / "gold_v3_eval"
        comparison_csv = out_dir / "before_after_comparison.csv"
        summary_md = out_dir / "summary.md"
        summary_json = out_dir / "summary.json"

        call_command("eval_extraction_accuracy", gold=str(gold_v3), out=str(v3_eval_dir))

        v2_rows = self._load_summary(v2_summary)
        v3_rows = self._load_summary(v3_eval_dir / "accuracy_summary.csv")
        self._write_comparison_csv(v2_rows, v3_rows, comparison_csv)

        added_titles = self._diff_titles(gold_v2, gold_v3)
        supporting_titles = self._load_titles(supporting_final) if supporting_final else []
        summary = {
            "gold_v2": str(gold_v2),
            "gold_v3": str(gold_v3),
            "v2_summary": str(v2_summary),
            "v3_eval_dir": str(v3_eval_dir),
            "comparison_csv": str(comparison_csv),
            "added_titles_from_v2_to_v3": added_titles,
            "supporting_final_provided": bool(supporting_final),
            "supporting_titles": supporting_titles,
        }
        summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary_md.write_text(self._build_summary_markdown(summary, v2_rows, v3_rows), encoding="utf-8")

        self.stdout.write(f"v3_eval_dir={v3_eval_dir}")
        self.stdout.write(f"comparison_csv={comparison_csv}")
        self.stdout.write(f"summary_md={summary_md}")
        self.stdout.write(f"summary_json={summary_json}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_v3_eval_{ts}").resolve()

    def _load_summary(self, path: Path) -> Dict[str, Dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return {
                str(row.get("field", "") or "").strip(): {k: str(v or "").strip() for k, v in row.items()}
                for row in reader
            }

    def _read_csv_rows(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _diff_titles(self, gold_v2: Path, gold_v3: Path) -> List[str]:
        v2_rows = self._read_csv_rows(gold_v2)
        v3_rows = self._read_csv_rows(gold_v3)
        v2_keys = {(r.get("doc_id", ""), r.get("doc_name", "")) for r in v2_rows}
        return [r.get("doc_name", "") for r in v3_rows if (r.get("doc_id", ""), r.get("doc_name", "")) not in v2_keys]

    def _load_titles(self, path: Path) -> List[str]:
        return [row.get("doc_name", "") for row in self._read_csv_rows(path)]

    def _write_comparison_csv(
        self,
        v2_rows: Dict[str, Dict[str, str]],
        v3_rows: Dict[str, Dict[str, str]],
        out_path: Path,
    ) -> None:
        rows = []
        for field in self.FIELDS:
            old = v2_rows.get(field, {})
            new = v3_rows.get(field, {})
            rows.append(
                {
                    "field": field,
                    "v2_total_rows": old.get("total_rows", ""),
                    "v2_evaluated_rows": old.get("evaluated_rows", ""),
                    "v2_skipped_rows": old.get("skipped_rows", ""),
                    "v2_precision": old.get("precision", ""),
                    "v2_recall": old.get("recall", ""),
                    "v2_f1": old.get("f1", ""),
                    "v3_total_rows": new.get("total_rows", ""),
                    "v3_evaluated_rows": new.get("evaluated_rows", ""),
                    "v3_skipped_rows": new.get("skipped_rows", ""),
                    "v3_precision": new.get("precision", ""),
                    "v3_recall": new.get("recall", ""),
                    "v3_f1": new.get("f1", ""),
                    "delta_precision": self._delta(old.get("precision", ""), new.get("precision", "")),
                    "delta_recall": self._delta(old.get("recall", ""), new.get("recall", "")),
                    "delta_f1": self._delta(old.get("f1", ""), new.get("f1", "")),
                }
            )
        with out_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

    def _delta(self, old_value: str, new_value: str) -> str:
        try:
            return f"{float(new_value) - float(old_value):.4f}"
        except Exception:
            return ""

    def _build_summary_markdown(
        self,
        summary: Dict[str, object],
        v2_rows: Dict[str, Dict[str, str]],
        v3_rows: Dict[str, Dict[str, str]],
    ) -> str:
        added_titles = summary["added_titles_from_v2_to_v3"]
        lines = [
            "# Gold V3 Evaluation Summary",
            "",
            f"- gold_v2: `{summary['gold_v2']}`",
            f"- gold_v3: `{summary['gold_v3']}`",
            f"- v2_summary: `{summary['v2_summary']}`",
            f"- v3_eval_dir: `{summary['v3_eval_dir']}`",
            f"- comparison_csv: `{summary['comparison_csv']}`",
            "",
            "## v2 to v3 New Addition",
        ]
        if added_titles:
            for title in added_titles:
                lines.append(f"- {title}")
        else:
            lines.append("- none")
        lines.extend(["", "## Supporting Status", "- supporting_final remains separate and did not enter formal core gold in v3."])
        lines.extend(["", "## Metric Changes"])
        for field in self.FIELDS:
            old = v2_rows.get(field, {})
            new = v3_rows.get(field, {})
            lines.append(
                f"- {field}: total_rows {old.get('total_rows', '')} -> {new.get('total_rows', '')}, evaluated_rows {old.get('evaluated_rows', '')} -> {new.get('evaluated_rows', '')}, skipped_rows {old.get('skipped_rows', '')} -> {new.get('skipped_rows', '')}, P {old.get('precision', '')} -> {new.get('precision', '')}, R {old.get('recall', '')} -> {new.get('recall', '')}, F1 {old.get('f1', '')} -> {new.get('f1', '')}"
            )
        return "\n".join(lines) + "\n"
