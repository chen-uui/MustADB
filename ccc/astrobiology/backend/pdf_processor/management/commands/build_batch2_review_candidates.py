import csv
import json
import re
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Build batch2 review candidates from the 50-row candidate table, excluding current gold_v2 documents."

    EXTRA_COLUMNS = [
        "batch_round",
        "batch2_selection_rank",
        "batch2_selection_bucket",
        "batch2_inclusion_likelihood",
        "batch2_scope_risk",
        "batch2_selection_reason",
        "batch2_category_gap_hint",
    ]
    TAG_GAP_HINTS = {
        "asteroid_return": "asteroid return / sample-return curation",
        "contamination_qc": "contamination-control / curation evidence",
        "amino_acids": "amino-acid-rich samples or QA papers",
        "sugars": "sugars / carbohydrate organics",
        "pahs": "PAH-focused evidence",
        "carboxylic_acids": "carboxylic-acid coverage",
        "amines": "amine / aliphatic amine coverage",
        "organic_matter": "SOM/IOM / organic-matter coverage",
        "analytical_methods": "analytical-method-heavy papers",
        "martian_sample": "Mars / martian sample boundary cases",
    }
    BATCH1_FINAL_TITLES = {
        "Indigenous OrganicOxidized Fluid Interactions in the Tissint Mars Meteorite",
        "Investigating the impact of xray computed tomography imaging on soluble organic matter in the Murchison meteorite: Implications for Bennu sample analyses",
        "Extraterrestrial ribose and other sugars in primitive meteorites",
        "Molecular distribution and 13C isotope composition of volatile organic compounds in the Murchison and Sutters Mill carbonaceous chondrites",
        "Extraterrestrial hexamethylenetetramine Yasuhiro Oba",
        "High-spatial resolution functional chemistry of nitrogen compounds in the observed UK meteorite fall Winchcombe",
        "Speciation of organosulfur compounds in carbonaceous chondrites",
    }
    METEORITE_ERROR_OUTPUT_FIELDS = [
        "doc_id",
        "doc_name",
        "pred_meteorite_name",
        "gold_meteorite_name",
        "meteorite_name_issue_type",
        "meteorite_name_issue_note",
    ]

    def add_arguments(self, parser):
        parser.add_argument("--candidates-csv", type=str, required=True, help="Full candidate CSV path.")
        parser.add_argument("--gold-v2", type=str, required=True, help="Current official gold_seed_v2.csv path.")
        parser.add_argument(
            "--accuracy-errors",
            type=str,
            required=True,
            help="accuracy_errors.csv from the gold_v2 evaluation run.",
        )
        parser.add_argument("--limit", type=int, default=12, help="Target batch2 candidate count. Default: 12.")
        parser.add_argument(
            "--out-dir",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_batch2_review_<timestamp>",
        )

    def handle(self, *args, **options):
        candidates_csv = Path(str(options["candidates_csv"])).expanduser().resolve()
        gold_v2_csv = Path(str(options["gold_v2"])).expanduser().resolve()
        accuracy_errors_csv = Path(str(options["accuracy_errors"])).expanduser().resolve()
        if not candidates_csv.exists():
            raise CommandError(f"candidates csv not found: {candidates_csv}")
        if not gold_v2_csv.exists():
            raise CommandError(f"gold v2 csv not found: {gold_v2_csv}")
        if not accuracy_errors_csv.exists():
            raise CommandError(f"accuracy errors csv not found: {accuracy_errors_csv}")

        out_dir = self._resolve_out_dir(options.get("out_dir"))
        out_dir.mkdir(parents=True, exist_ok=True)

        candidate_rows = self._read_csv(candidates_csv)
        gold_rows = self._read_csv(gold_v2_csv)
        error_rows = self._read_csv(accuracy_errors_csv)

        remaining_rows = self._exclude_existing_gold(candidate_rows, gold_rows)
        selected_rows = self._select_batch2_candidates(remaining_rows, int(options["limit"]))
        output_columns = self._build_output_columns(candidate_rows)

        csv_path = out_dir / "batch2_review_candidates.csv"
        xlsx_path = out_dir / "batch2_review_candidates.xlsx"
        summary_md_path = out_dir / "summary.md"
        summary_json_path = out_dir / "summary.json"
        meteorite_analysis_csv_path = out_dir / "batch1_meteorite_name_loss_analysis.csv"

        self._write_csv(csv_path, output_columns, selected_rows)
        self._write_xlsx(xlsx_path, "Batch2Review", output_columns, selected_rows)

        meteorite_analysis_rows, meteorite_summary = self._build_batch1_meteorite_name_analysis(gold_rows, error_rows)
        self._write_csv(meteorite_analysis_csv_path, self.METEORITE_ERROR_OUTPUT_FIELDS, meteorite_analysis_rows)

        summary = self._build_summary_dict(
            candidates_csv=candidates_csv,
            gold_v2_csv=gold_v2_csv,
            selected_rows=selected_rows,
            remaining_rows=remaining_rows,
            meteorite_summary=meteorite_summary,
            meteorite_analysis_csv=meteorite_analysis_csv_path,
        )
        summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary_md_path.write_text(self._build_summary_markdown(summary), encoding="utf-8")

        self.stdout.write(f"remaining_candidates={len(remaining_rows)}")
        self.stdout.write(f"selected_count={len(selected_rows)}")
        self.stdout.write(f"batch2_csv={csv_path}")
        self.stdout.write(f"batch2_xlsx={xlsx_path}")
        self.stdout.write(f"summary_md={summary_md_path}")
        self.stdout.write(f"summary_json={summary_json_path}")
        self.stdout.write(f"meteorite_analysis_csv={meteorite_analysis_csv_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_batch2_review_{ts}").resolve()

    def _read_csv(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _exclude_existing_gold(self, candidate_rows: List[Dict[str, str]], gold_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
        seen_doc_ids = {self._norm(row.get("doc_id", "")) for row in gold_rows if self._norm(row.get("doc_id", ""))}
        seen_titles = {self._norm_title(row.get("doc_name", "")) for row in gold_rows if self._norm_title(row.get("doc_name", ""))}
        out = []
        for row in candidate_rows:
            doc_id_key = self._norm(row.get("doc_id", ""))
            title_key = self._norm_title(row.get("doc_name", ""))
            if doc_id_key and doc_id_key in seen_doc_ids:
                continue
            if title_key and title_key in seen_titles:
                continue
            out.append(dict(row))
        return out

    def _select_batch2_candidates(self, remaining_rows: List[Dict[str, str]], limit: int) -> List[Dict[str, str]]:
        core_high = [row for row in remaining_rows if row.get("recommendation", "") == "likely_core_gold" and row.get("review_priority", "") == "high"]
        core_medium = [row for row in remaining_rows if row.get("recommendation", "") == "likely_core_gold" and row.get("review_priority", "") == "medium"]
        support_high = [row for row in remaining_rows if row.get("recommendation", "") == "likely_supporting_gold" and row.get("review_priority", "") == "high"]
        support_medium = [row for row in remaining_rows if row.get("recommendation", "") == "likely_supporting_gold" and row.get("review_priority", "") == "medium"]

        for bucket in (core_high, core_medium, support_high, support_medium):
            bucket.sort(key=self._sort_key, reverse=True)

        selected: List[Dict[str, str]] = []
        seen_doc_ids = set()
        seen_titles = set()
        selected_tags = Counter()

        def add_row(row: Dict[str, str], bucket_name: str, inclusion: str, scope_risk: str, reason_prefix: str):
            doc_id_key = self._norm(row.get("doc_id", ""))
            title_key = self._norm_title(row.get("doc_name", ""))
            if (doc_id_key and doc_id_key in seen_doc_ids) or (title_key and title_key in seen_titles):
                return False
            selected.append(self._decorate_row(row, bucket_name, inclusion, scope_risk, len(selected) + 1, reason_prefix, selected_tags))
            if doc_id_key:
                seen_doc_ids.add(doc_id_key)
            if title_key:
                seen_titles.add(title_key)
            for tag in self._split_tags(row.get("candidate_tags", "")):
                selected_tags[tag] += 1
            return True

        for row in core_high:
            add_row(
                row,
                bucket_name="core_high",
                inclusion=self._default_inclusion_likelihood(row),
                scope_risk=self._default_scope_risk(row),
                reason_prefix="core/high priority carry-over from remaining pool",
            )

        remainder_pool = []
        for row in core_medium:
            remainder_pool.append((self._diversity_score(row, selected_tags) + 300, "core_medium", row))
        for row in support_high:
            remainder_pool.append((self._diversity_score(row, selected_tags) + 250, "support_high", row))
        for row in support_medium:
            remainder_pool.append((self._diversity_score(row, selected_tags) + 150, "support_medium", row))
        remainder_pool.sort(key=lambda item: (item[0], self._sort_key(item[2])), reverse=True)

        for _, bucket_name, row in remainder_pool:
            if len(selected) >= limit:
                break
            add_row(
                row,
                bucket_name=bucket_name,
                inclusion=self._default_inclusion_likelihood(row),
                scope_risk=self._default_scope_risk(row),
                reason_prefix="added for diversity/category-gap coverage",
            )

        return selected[:limit]

    def _decorate_row(
        self,
        row: Dict[str, str],
        bucket_name: str,
        inclusion: str,
        scope_risk: str,
        rank: int,
        reason_prefix: str,
        selected_tags: Counter,
    ) -> Dict[str, str]:
        out = dict(row)
        tags = self._split_tags(row.get("candidate_tags", ""))
        gap_hints = [self.TAG_GAP_HINTS[tag] for tag in tags if tag in self.TAG_GAP_HINTS and selected_tags.get(tag, 0) == 0]
        out["batch_round"] = "batch2"
        out["batch2_selection_rank"] = str(rank)
        out["batch2_selection_bucket"] = bucket_name
        out["batch2_inclusion_likelihood"] = inclusion
        out["batch2_scope_risk"] = scope_risk
        out["batch2_category_gap_hint"] = "; ".join(gap_hints)
        base_reason = row.get("priority_reason", "")
        if gap_hints:
            out["batch2_selection_reason"] = f"{reason_prefix}; gap_fill={'; '.join(gap_hints)}; source_reason={base_reason}"
        else:
            out["batch2_selection_reason"] = f"{reason_prefix}; source_reason={base_reason}"
        return out

    def _default_inclusion_likelihood(self, row: Dict[str, str]) -> str:
        recommendation = row.get("recommendation", "")
        priority = row.get("review_priority", "")
        tags = self._split_tags(row.get("candidate_tags", ""))
        title = row.get("doc_name", "")
        if recommendation == "likely_core_gold" and priority == "high" and "martian_sample" not in tags and "comet" not in title.lower():
            return "most_likely_formal_include"
        if recommendation == "likely_supporting_gold" and priority == "high" and self._default_scope_risk(row) == "low_scope_risk":
            return "most_likely_formal_include"
        if recommendation == "likely_core_gold":
            return "review_after_scope_check"
        if priority == "high":
            return "high_value_supporting_candidate"
        return "reserve_candidate"

    def _default_scope_risk(self, row: Dict[str, str]) -> str:
        tags = self._split_tags(row.get("candidate_tags", ""))
        title = row.get("doc_name", "").lower()
        if "martian_sample" in tags or "mars" in title:
            return "scope_boundary_mars"
        if "comet" in title or "67p" in title:
            return "scope_boundary_comet"
        if "interstellar" in title or "analogs" in title or "model compounds" in title:
            return "scope_boundary_analog_or_model"
        return "low_scope_risk"

    def _diversity_score(self, row: Dict[str, str], selected_tags: Counter) -> int:
        score = int(float(row.get("priority_score", "") or 0))
        for tag in self._split_tags(row.get("candidate_tags", "")):
            if selected_tags.get(tag, 0) == 0:
                score += 6
        if row.get("pred_contamination_controls", "").strip():
            score += 2
        if row.get("organic_evidence_snippet", "").strip():
            score += 2
        return score

    def _sort_key(self, row: Dict[str, str]) -> Tuple[float, int]:
        priority_score = float(row.get("priority_score", "") or 0)
        projected_count = len([item for item in self._split_semicolon(row.get("pred_organic_compounds_projected", "")) if item])
        return priority_score, projected_count

    def _build_output_columns(self, candidate_rows: List[Dict[str, str]]) -> List[str]:
        base_columns = list(candidate_rows[0].keys()) if candidate_rows else []
        return base_columns + [column for column in self.EXTRA_COLUMNS if column not in base_columns]

    def _build_batch1_meteorite_name_analysis(
        self,
        gold_rows: List[Dict[str, str]],
        error_rows: List[Dict[str, str]],
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        batch1_rows = [row for row in gold_rows if row.get("doc_name", "") in self.BATCH1_FINAL_TITLES]
        meteorite_errors = {
            row.get("doc_name", ""): row
            for row in error_rows
            if row.get("field", "") == "meteorite_name" and row.get("doc_name", "") in self.BATCH1_FINAL_TITLES
        }

        analysis_rows: List[Dict[str, str]] = []
        issue_counter = Counter()
        for row in batch1_rows:
            title = row.get("doc_name", "")
            pred_name = row.get("pred_meteorite_name", "")
            gold_name = row.get("gold_meteorite_name", "")
            error = meteorite_errors.get(title)
            if not error:
                issue_type = "no_issue"
                issue_note = "predicted meteorite name matches the current gold label or both are empty."
            elif not gold_name.strip() and pred_name.strip():
                issue_type = "gold_empty_policy_vs_predicted_name"
                issue_note = "gold intentionally keeps meteorite_name empty, but the fixed prediction emits a meteorite/sample name from title/body evidence."
            elif ";" in pred_name and pred_name.strip() != gold_name.strip():
                issue_type = "multi_sample_or_scope_mismatch"
                issue_note = "prediction keeps a composite sample/mission label, while gold keeps a narrower single-name label."
            else:
                issue_type = "naming_convention_mismatch"
                issue_note = "prediction and gold both contain meteorite names, but the naming granularity differs."
            issue_counter[issue_type] += 1
            analysis_rows.append(
                {
                    "doc_id": row.get("doc_id", ""),
                    "doc_name": title,
                    "pred_meteorite_name": pred_name,
                    "gold_meteorite_name": gold_name,
                    "meteorite_name_issue_type": issue_type,
                    "meteorite_name_issue_note": issue_note,
                }
            )

        summary = {
            "batch1_total_rows": len(batch1_rows),
            "meteorite_name_issue_counts": dict(issue_counter),
            "main_takeaway": self._build_meteorite_takeaway(issue_counter),
        }
        return analysis_rows, summary

    def _build_meteorite_takeaway(self, issue_counter: Counter) -> str:
        if not issue_counter:
            return "No meteorite_name issue was found among the seven batch1 additions."
        parts = []
        if issue_counter.get("gold_empty_policy_vs_predicted_name"):
            parts.append(
                f"{issue_counter['gold_empty_policy_vs_predicted_name']} rows are driven by intentional empty-gold policy, not by missing retrieval evidence"
            )
        if issue_counter.get("multi_sample_or_scope_mismatch"):
            parts.append(
                f"{issue_counter['multi_sample_or_scope_mismatch']} row reflects multi-sample naming mismatch"
            )
        if issue_counter.get("naming_convention_mismatch"):
            parts.append(
                f"{issue_counter['naming_convention_mismatch']} row reflects naming-convention mismatch"
            )
        if issue_counter.get("no_issue"):
            parts.append(f"{issue_counter['no_issue']} rows have no meteorite_name issue")
        return "; ".join(parts)

    def _build_summary_dict(
        self,
        *,
        candidates_csv: Path,
        gold_v2_csv: Path,
        selected_rows: List[Dict[str, str]],
        remaining_rows: List[Dict[str, str]],
        meteorite_summary: Dict[str, Any],
        meteorite_analysis_csv: Path,
    ) -> Dict[str, Any]:
        selected_titles = [row.get("doc_name", "") for row in selected_rows]
        likely_formal = [row.get("doc_name", "") for row in selected_rows if row.get("batch2_inclusion_likelihood", "") == "most_likely_formal_include"]
        scope_boundary = [row.get("doc_name", "") for row in selected_rows if row.get("batch2_scope_risk", "") != "low_scope_risk"]
        gap_counter = Counter()
        for row in selected_rows:
            for hint in self._split_semicolon(row.get("batch2_category_gap_hint", "")):
                if hint:
                    gap_counter[hint] += 1
        candidate_details = []
        for row in selected_rows:
            candidate_details.append(
                {
                    "doc_name": row.get("doc_name", ""),
                    "selection_bucket": row.get("batch2_selection_bucket", ""),
                    "inclusion_likelihood": row.get("batch2_inclusion_likelihood", ""),
                    "scope_risk": row.get("batch2_scope_risk", ""),
                    "candidate_tags": row.get("candidate_tags", ""),
                    "priority_score": row.get("priority_score", ""),
                    "selection_reason": row.get("batch2_selection_reason", ""),
                }
            )
        return {
            "candidates_csv": str(candidates_csv),
            "gold_v2_csv": str(gold_v2_csv),
            "remaining_candidates_after_gold_v2_exclusion": len(remaining_rows),
            "selected_count": len(selected_rows),
            "selected_titles": selected_titles,
            "likely_formal_include_titles": likely_formal,
            "scope_boundary_titles": scope_boundary,
            "category_gap_summary": dict(gap_counter),
            "candidate_details": candidate_details,
            "selected_recommendation_counts": dict(Counter(row.get("recommendation", "") for row in selected_rows)),
            "selected_priority_counts": dict(Counter(row.get("review_priority", "") for row in selected_rows)),
            "meteorite_name_batch1_summary": meteorite_summary,
            "meteorite_name_batch1_analysis_csv": str(meteorite_analysis_csv),
        }

    def _build_summary_markdown(self, summary: Dict[str, Any]) -> str:
        lines = [
            "# Batch2 Review Summary",
            "",
            f"- candidates_csv: `{summary['candidates_csv']}`",
            f"- gold_v2_csv: `{summary['gold_v2_csv']}`",
            f"- remaining_candidates_after_gold_v2_exclusion: `{summary['remaining_candidates_after_gold_v2_exclusion']}`",
            f"- selected_count: `{summary['selected_count']}`",
            "",
            "## Batch2 Candidate Documents",
        ]
        for detail in summary["candidate_details"]:
            lines.append(
                f"- {detail['doc_name']} | bucket={detail['selection_bucket']} | likelihood={detail['inclusion_likelihood']} | scope_risk={detail['scope_risk']}"
            )
            if detail["candidate_tags"]:
                lines.append(f"  tags: {detail['candidate_tags']}")
            if detail["selection_reason"]:
                lines.append(f"  why: {detail['selection_reason']}")
        lines.extend(["", "## Most Likely Formal Includes"])
        for title in summary["likely_formal_include_titles"] or ["none"]:
            lines.append(f"- {title}")
        lines.extend(["", "## Category Gaps Addressed"])
        if summary["category_gap_summary"]:
            for gap, count in summary["category_gap_summary"].items():
                lines.append(f"- {gap}: {count}")
        else:
            lines.append("- none")
        lines.extend(["", "## Scope Boundary Items"])
        if summary["scope_boundary_titles"]:
            for title in summary["scope_boundary_titles"]:
                lines.append(f"- {title}")
        else:
            lines.append("- none")
        lines.extend(["", "## Batch1 Meteorite Name Loss Check"])
        lines.append(f"- analysis_csv: `{summary['meteorite_name_batch1_analysis_csv']}`")
        lines.append(f"- takeaway: {summary['meteorite_name_batch1_summary']['main_takeaway']}")
        for issue_type, count in summary["meteorite_name_batch1_summary"]["meteorite_name_issue_counts"].items():
            lines.append(f"- {issue_type}: {count}")
        return "\n".join(lines) + "\n"

    def _norm(self, value: str) -> str:
        return re.sub(r"\s+", " ", str(value or "")).strip().lower()

    def _norm_title(self, value: str) -> str:
        text = self._norm(value)
        text = re.sub(r"[^a-z0-9]+", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _split_tags(self, value: str) -> List[str]:
        return [item.strip() for item in str(value or "").split(";") if item.strip()]

    def _split_semicolon(self, value: str) -> List[str]:
        return [item.strip() for item in str(value or "").split(";") if item.strip()]

    def _write_csv(self, path: Path, fieldnames: Sequence[str], rows: Sequence[Dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(fieldnames))
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})

    def _write_xlsx(
        self,
        path: Path,
        sheet_name: str,
        fieldnames: Sequence[str],
        rows: Sequence[Dict[str, str]],
    ) -> None:
        headers = list(fieldnames)
        table_rows: List[List[Any]] = [headers]
        for row in rows:
            table_rows.append([row.get(field, "") for field in headers])

        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", self._build_content_types_xml())
            zf.writestr("_rels/.rels", self._build_root_rels_xml())
            zf.writestr("xl/workbook.xml", self._build_workbook_xml(sheet_name))
            zf.writestr("xl/_rels/workbook.xml.rels", self._build_workbook_rels_xml())
            zf.writestr("xl/styles.xml", self._build_styles_xml())
            zf.writestr("xl/worksheets/sheet1.xml", self._build_sheet_xml(table_rows))

    def _build_sheet_xml(self, table_rows: Sequence[Sequence[Any]]) -> str:
        max_col = max((len(row) for row in table_rows), default=0)
        max_row = len(table_rows)
        ref = f"A1:{self._col_name(max_col)}{max_row}" if max_col and max_row else "A1:A1"

        rows_xml: List[str] = []
        for row_idx, row in enumerate(table_rows, start=1):
            cells: List[str] = []
            for col_idx, value in enumerate(row, start=1):
                cell_ref = f"{self._col_name(col_idx)}{row_idx}"
                style_id = "1" if row_idx == 1 else "0"
                cells.append(self._build_cell_xml(cell_ref, value, style_id))
            rows_xml.append(f'<row r="{row_idx}">{"".join(cells)}</row>')

        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheetViews><sheetView workbookViewId="0"><pane ySplit="1" topLeftCell="A2" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>'
            f'<dimension ref="{ref}"/>'
            f'<sheetData>{"".join(rows_xml)}</sheetData>'
            f'<autoFilter ref="{ref}"/>'
            "</worksheet>"
        )

    def _build_cell_xml(self, cell_ref: str, value: Any, style_id: str) -> str:
        text = "" if value is None else str(value)
        if text == "":
            return f'<c r="{cell_ref}" s="{style_id}" t="inlineStr"><is><t></t></is></c>'
        if re.fullmatch(r"-?\d+(?:\.\d+)?", text):
            return f'<c r="{cell_ref}" s="{style_id}"><v>{escape(text)}</v></c>'
        safe = escape(text)
        preserve = ' xml:space="preserve"' if text != text.strip() or "\n" in text else ""
        return f'<c r="{cell_ref}" s="{style_id}" t="inlineStr"><is><t{preserve}>{safe}</t></is></c>'

    def _col_name(self, idx: int) -> str:
        out = ""
        value = idx
        while value > 0:
            value, rem = divmod(value - 1, 26)
            out = chr(65 + rem) + out
        return out or "A"

    def _build_content_types_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
            "</Types>"
        )

    def _build_root_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        )

    def _build_workbook_xml(self, sheet_name: str) -> str:
        safe_name = escape(sheet_name[:31] or "Batch2Review")
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets>'
            f'<sheet name="{safe_name}" sheetId="1" r:id="rId1"/>'
            "</sheets>"
            "</workbook>"
        )

    def _build_workbook_rels_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            "</Relationships>"
        )

    def _build_styles_xml(self) -> str:
        return (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<fonts count="2"><font><sz val="11"/><name val="Calibri"/></font><font><b/><sz val="11"/><name val="Calibri"/></font></fonts>'
            '<fills count="2"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill></fills>'
            '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
            '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
            '<cellXfs count="2">'
            '<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
            '<xf numFmtId="0" fontId="1" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>'
            '</cellXfs>'
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            "</styleSheet>"
        )
