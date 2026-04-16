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
    help = (
        "Build a strict batch3 core-only review table from the existing 50-row candidate pool, "
        "excluding documents already in gold_v3 and batch2 supporting."
    )

    OUTPUT_COLUMNS = [
        "doc_id",
        "doc_name",
        "doc_filename",
        "doc_year",
        "doc_journal",
        "candidate_tags",
        "priority_score",
        "priority_reason",
        "pred_meteorite_name",
        "pred_organic_compounds_raw",
        "pred_organic_compounds_filtered",
        "pred_organic_compounds_projected",
        "pred_contamination_controls",
        "meteorite_evidence_snippet",
        "organic_evidence_snippet",
        "contamination_evidence_snippet",
        "batch3_core_likelihood",
        "batch3_scope_risk",
        "batch3_selection_reason",
    ]
    EXCLUDED_COLUMNS = OUTPUT_COLUMNS + ["batch3_exclusion_reason"]

    STRONG_CORE_TERMS = [
        "meteorite",
        "micrometeorite",
        "chondrite",
        "carbonaceous",
        "ryugu",
        "bennu",
        "asteroid",
        "extraterrestrial",
    ]
    HARD_EXCLUDE_TERMS = {
        "mars": "mars_or_martian_boundary",
        "martian": "mars_or_martian_boundary",
        "comet": "comet_boundary",
        "67p": "comet_boundary",
        "witness coupon": "curation_or_witness_coupon_supporting",
        "sample return": "curation_or_witness_coupon_supporting",
        "curation": "curation_or_witness_coupon_supporting",
        "contamination": "curation_or_witness_coupon_supporting",
        "survivability": "survivability_boundary",
    }
    SOFT_EXCLUDE_TERMS = {
        "interstellar": "analog_or_interstellar_boundary",
        "analog": "analog_or_interstellar_boundary",
        "analogue": "analog_or_interstellar_boundary",
        "nitrogen-rich ices": "analog_or_interstellar_boundary",
        "model compounds": "model_compound_boundary",
        "review": "broad_review_or_record",
        "record": "broad_review_or_record",
        "history": "broad_review_or_record",
        "composition": "broad_review_or_record",
        "biogenicity": "broad_review_or_record",
        "perspective": "broad_review_or_record",
        "biosignature": "broad_detection_or_scope_boundary",
        "microscopy": "broad_detection_or_scope_boundary",
        "detection of extraterrestrial life": "broad_detection_or_scope_boundary",
        "ceres": "non_sample_body_scope_boundary",
        "comment": "commentary_or_reply",
        "reply": "commentary_or_reply",
    }
    CATEGORY_GAP_HINTS = {
        "amino_acids": "amino-acid-heavy extraterrestrial samples",
        "carboxylic_acids": "carboxylic-acid coverage",
        "amines": "amine / aliphatic amine coverage",
        "pahs": "PAH-rich samples",
        "sugars": "sugar-rich meteoritic organics",
        "organic_matter": "organic matter / alteration interaction papers",
        "analytical_methods": "direct sample analytics with interpretable evidence",
        "volatile_organics": "volatile organic compound coverage",
    }

    def add_arguments(self, parser):
        parser.add_argument("--candidates-csv", type=str, required=True, help="Full candidate CSV path.")
        parser.add_argument("--gold-v3", type=str, required=True, help="Current official gold_seed_v3.csv path.")
        parser.add_argument(
            "--supporting-final",
            type=str,
            required=True,
            help="batch2 supporting final CSV path to exclude.",
        )
        parser.add_argument("--limit", type=int, default=10, help="Target batch3 candidate count. Default: 10.")
        parser.add_argument(
            "--out-dir",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_batch3_core_review_<timestamp>",
        )

    def handle(self, *args, **options):
        candidates_csv = Path(str(options["candidates_csv"])).expanduser().resolve()
        gold_v3_csv = Path(str(options["gold_v3"])).expanduser().resolve()
        supporting_csv = Path(str(options["supporting_final"])).expanduser().resolve()
        for path, label in (
            (candidates_csv, "candidates csv"),
            (gold_v3_csv, "gold v3 csv"),
            (supporting_csv, "batch2 supporting csv"),
        ):
            if not path.exists():
                raise CommandError(f"{label} not found: {path}")

        out_dir = self._resolve_out_dir(options.get("out_dir"))
        out_dir.mkdir(parents=True, exist_ok=True)

        candidate_rows = self._read_csv(candidates_csv)
        gold_rows = self._read_csv(gold_v3_csv)
        supporting_rows = self._read_csv(supporting_csv)

        remaining_rows = self._exclude_existing(candidate_rows, gold_rows + supporting_rows)
        selected_rows, excluded_rows = self._select_candidates(remaining_rows, int(options["limit"]))

        csv_path = out_dir / "batch3_core_review_candidates.csv"
        xlsx_path = out_dir / "batch3_core_review_candidates.xlsx"
        excluded_path = out_dir / "excluded_or_borderline.csv"
        summary_md_path = out_dir / "summary.md"
        summary_json_path = out_dir / "summary.json"

        self._write_csv(csv_path, self.OUTPUT_COLUMNS, selected_rows)
        self._write_xlsx(xlsx_path, "Batch3Core", self.OUTPUT_COLUMNS, selected_rows)
        self._write_csv(excluded_path, self.EXCLUDED_COLUMNS, excluded_rows)

        summary = self._build_summary(
            candidates_csv=candidates_csv,
            gold_v3_csv=gold_v3_csv,
            supporting_csv=supporting_csv,
            remaining_rows=remaining_rows,
            selected_rows=selected_rows,
            excluded_rows=excluded_rows,
            current_total_rows=len(gold_rows),
            current_evaluated_rows=self._count_evaluated_rows(gold_rows),
        )
        summary_md_path.write_text(self._build_summary_markdown(summary), encoding="utf-8")
        summary_json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

        self.stdout.write(f"remaining_candidates={len(remaining_rows)}")
        self.stdout.write(f"selected_count={len(selected_rows)}")
        self.stdout.write(f"excluded_count={len(excluded_rows)}")
        self.stdout.write(f"batch3_csv={csv_path}")
        self.stdout.write(f"batch3_xlsx={xlsx_path}")
        self.stdout.write(f"excluded_csv={excluded_path}")
        self.stdout.write(f"summary_md={summary_md_path}")
        self.stdout.write(f"summary_json={summary_json_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_batch3_core_review_{ts}").resolve()

    def _read_csv(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _exclude_existing(self, candidate_rows: List[Dict[str, str]], existing_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
        seen_doc_ids = {self._norm(row.get("doc_id", "")) for row in existing_rows if self._norm(row.get("doc_id", ""))}
        seen_titles = {self._norm_title(row.get("doc_name", "")) for row in existing_rows if self._norm_title(row.get("doc_name", ""))}
        out: List[Dict[str, str]] = []
        for row in candidate_rows:
            doc_id_key = self._norm(row.get("doc_id", ""))
            title_key = self._norm_title(row.get("doc_name", ""))
            if doc_id_key and doc_id_key in seen_doc_ids:
                continue
            if title_key and title_key in seen_titles:
                continue
            out.append(dict(row))
        return out

    def _select_candidates(
        self,
        remaining_rows: List[Dict[str, str]],
        limit: int,
    ) -> Tuple[List[Dict[str, str]], List[Dict[str, str]]]:
        accepted: List[Tuple[int, Dict[str, str]]] = []
        excluded: List[Dict[str, str]] = []
        gap_counter: Counter = Counter()

        for row in remaining_rows:
            decision = self._assess_row(row, gap_counter)
            if decision["include"]:
                accepted.append((decision["score"], decision["row"]))
                for tag in self._split_tags(decision["row"].get("candidate_tags", "")):
                    gap_counter[tag] += 1
            else:
                excluded.append(decision["row"])

        accepted.sort(key=lambda item: (item[0], self._sort_key(item[1])), reverse=True)
        selected_rows = [row for _, row in accepted[:limit]]
        selected_doc_ids = {self._norm(row.get("doc_id", "")) for row in selected_rows}
        selected_titles = {self._norm_title(row.get("doc_name", "")) for row in selected_rows}

        overflow_excluded = []
        for _, row in accepted[limit:]:
            extra = dict(row)
            extra["batch3_exclusion_reason"] = "reserve_overflow_after_limit"
            overflow_excluded.append(extra)

        final_excluded: List[Dict[str, str]] = []
        for row in excluded + overflow_excluded:
            doc_id_key = self._norm(row.get("doc_id", ""))
            title_key = self._norm_title(row.get("doc_name", ""))
            if (doc_id_key and doc_id_key in selected_doc_ids) or (title_key and title_key in selected_titles):
                continue
            final_excluded.append(row)

        return selected_rows, final_excluded

    def _assess_row(self, row: Dict[str, str], selected_tags: Counter) -> Dict[str, Any]:
        out = {field: row.get(field, "") for field in self.OUTPUT_COLUMNS}
        out["doc_id"] = row.get("doc_id", "")
        out["doc_name"] = row.get("doc_name", "")
        out["doc_filename"] = row.get("doc_filename", "")
        out["doc_year"] = row.get("doc_year", "")
        out["doc_journal"] = row.get("doc_journal", "")
        out["candidate_tags"] = row.get("candidate_tags", "")
        out["priority_score"] = row.get("priority_score", "")
        out["priority_reason"] = row.get("priority_reason", "")
        out["pred_meteorite_name"] = row.get("pred_meteorite_name", "")
        out["pred_organic_compounds_raw"] = row.get("pred_organic_compounds_raw", row.get("pred_organic_compounds", ""))
        out["pred_organic_compounds_filtered"] = row.get("pred_organic_compounds_filtered", row.get("pred_organic_compounds", ""))
        out["pred_organic_compounds_projected"] = row.get("pred_organic_compounds_projected", row.get("pred_organic_compounds", ""))
        out["pred_contamination_controls"] = row.get("pred_contamination_controls", "")
        out["meteorite_evidence_snippet"] = row.get("meteorite_evidence_snippet", "")
        out["organic_evidence_snippet"] = row.get("organic_evidence_snippet", "")
        out["contamination_evidence_snippet"] = row.get("contamination_evidence_snippet", "")

        title = self._norm(row.get("doc_name", ""))
        tags = self._split_tags(row.get("candidate_tags", ""))
        projected = self._split_semicolon(row.get("pred_organic_compounds_projected", ""))
        projected_count = len(projected)
        priority_score = int(row.get("priority_score") or 0)
        hard_risks = [label for term, label in self.HARD_EXCLUDE_TERMS.items() if term in title]
        soft_risks = [label for term, label in self.SOFT_EXCLUDE_TERMS.items() if term in title]

        if "martian_sample" in tags and "mars_or_martian_boundary" not in hard_risks:
            hard_risks.append("mars_or_martian_boundary")
        if "contamination_qc" in tags and any(token in title for token in ("sample return", "curation", "witness coupon", "contamination")):
            hard_risks.append("curation_or_witness_coupon_supporting")
        if not projected:
            hard_risks.append("missing_clear_organic_projection")

        has_sample_signal = any(term in title for term in self.STRONG_CORE_TERMS) or bool(self._norm(row.get("pred_meteorite_name", "")))
        if not has_sample_signal:
            soft_risks.append("weak_sample_anchor")

        evidence_strength = 0
        if self._norm(row.get("pred_meteorite_name", "")):
            evidence_strength += 2
        if projected_count >= 3:
            evidence_strength += 2
        elif projected_count >= 1:
            evidence_strength += 1
        if self._norm(row.get("organic_evidence_snippet", "")):
            evidence_strength += 2
        if self._norm(row.get("meteorite_evidence_snippet", "")):
            evidence_strength += 1
        if "results_or_analytical" in row.get("organic_evidence_section_hints", "") or "table_or_caption" in row.get("organic_evidence_section_hints", ""):
            evidence_strength += 1

        gap_hints = [self.CATEGORY_GAP_HINTS[tag] for tag in tags if tag in self.CATEGORY_GAP_HINTS and selected_tags.get(tag, 0) == 0]
        gap_bonus = min(3, len(gap_hints))

        score = priority_score + evidence_strength + gap_bonus
        if "likely_core_gold" in row.get("recommendation", ""):
            score += 3
        if row.get("review_priority", "") == "high":
            score += 3
        elif row.get("review_priority", "") == "medium":
            score += 1

        if hard_risks:
            score -= 100
        if soft_risks:
            score -= 10 * len(set(soft_risks))

        reserve_risk_labels = {
            "analog_or_interstellar_boundary",
            "model_compound_boundary",
            "broad_review_or_record",
            "broad_detection_or_scope_boundary",
            "weak_sample_anchor",
            "non_sample_body_scope_boundary",
        }

        if not hard_risks and not soft_risks and has_sample_signal and projected_count >= 2:
            likelihood = "recommended_core_now"
            scope_risk = "low_scope_risk"
            selection_reason = "clear sample-focused title plus explicit organics projection and evidence"
            include = True
        elif not hard_risks and has_sample_signal and projected_count >= 1 and not reserve_risk_labels.intersection(soft_risks):
            likelihood = "backup_after_scope_check"
            scope_risk = "medium_scope_risk" if soft_risks else "low_scope_risk"
            selection_reason = "sample-linked organics are present, but the paper is more methods-heavy or broad than ideal"
            include = True
        elif not hard_risks and projected_count >= 1 and reserve_risk_labels.intersection(soft_risks):
            likelihood = "reserve_not_recommended_first"
            scope_risk = "elevated_scope_risk"
            selection_reason = "kept only as reserve because it may fill a category gap, but scope is weaker than desired for core"
            include = True
        else:
            likelihood = "excluded"
            scope_risk = "; ".join(sorted(set(hard_risks + soft_risks))) or "excluded"
            selection_reason = "excluded under strict core-only standard"
            include = False

        if gap_hints:
            selection_reason = f"{selection_reason}; gap_fill={'; '.join(gap_hints)}"
        if row.get("priority_reason", ""):
            selection_reason = f"{selection_reason}; source_reason={row.get('priority_reason', '')}"

        out["batch3_core_likelihood"] = likelihood
        out["batch3_scope_risk"] = scope_risk
        out["batch3_selection_reason"] = selection_reason

        excluded_row = dict(out)
        excluded_row["batch3_exclusion_reason"] = scope_risk if not include else ""
        return {
            "include": include,
            "score": score,
            "row": out if include else excluded_row,
        }

    def _build_summary(
        self,
        *,
        candidates_csv: Path,
        gold_v3_csv: Path,
        supporting_csv: Path,
        remaining_rows: List[Dict[str, str]],
        selected_rows: List[Dict[str, str]],
        excluded_rows: List[Dict[str, str]],
        current_total_rows: int,
        current_evaluated_rows: int,
    ) -> Dict[str, Any]:
        strong = [row.get("doc_name", "") for row in selected_rows if row.get("batch3_core_likelihood", "") == "recommended_core_now"]
        backups = [row.get("doc_name", "") for row in selected_rows if row.get("batch3_core_likelihood", "") != "recommended_core_now"]
        review_first = [row.get("doc_name", "") for row in selected_rows[: min(6, len(selected_rows))]]
        reserve_only = [row.get("doc_name", "") for row in selected_rows[min(6, len(selected_rows)) :]]
        excluded_counter = Counter(row.get("batch3_exclusion_reason", "") for row in excluded_rows)
        gap_counter = Counter()
        for row in selected_rows:
            for tag in self._split_tags(row.get("candidate_tags", "")):
                if tag in self.CATEGORY_GAP_HINTS:
                    gap_counter[self.CATEGORY_GAP_HINTS[tag]] += 1
        selected_details = [
            {
                "doc_name": row.get("doc_name", ""),
                "review_priority": row.get("review_priority", ""),
                "batch3_core_likelihood": row.get("batch3_core_likelihood", ""),
                "batch3_scope_risk": row.get("batch3_scope_risk", ""),
                "candidate_tags": row.get("candidate_tags", ""),
                "priority_score": row.get("priority_score", ""),
                "selection_reason": row.get("batch3_selection_reason", ""),
            }
            for row in selected_rows
        ]
        return {
            "candidates_csv": str(candidates_csv),
            "gold_v3_csv": str(gold_v3_csv),
            "supporting_final_csv": str(supporting_csv),
            "remaining_after_gold_v3_and_supporting_exclusion": len(remaining_rows),
            "selected_count": len(selected_rows),
            "strong_recommended_count": len(strong),
            "backup_count": len(backups),
            "strong_recommended_titles": strong,
            "review_first_titles": review_first,
            "reserve_only_titles": reserve_only,
            "backup_titles": backups,
            "selected_details": selected_details,
            "excluded_reason_counts": dict(excluded_counter),
            "category_gap_summary": dict(gap_counter),
            "current_core_total_rows": current_total_rows,
            "current_core_evaluated_rows": current_evaluated_rows,
            "projected_total_rows_if_all_selected_merged": current_total_rows + len(selected_rows),
            "projected_evaluated_rows_if_all_selected_merged": current_evaluated_rows + len(selected_rows),
            "selected_likelihood_counts": dict(Counter(row.get("batch3_core_likelihood", "") for row in selected_rows)),
        }

    def _build_summary_markdown(self, summary: Dict[str, Any]) -> str:
        lines = [
            "# Batch3 Core-Only Review Summary",
            "",
            f"- candidates_csv: `{summary['candidates_csv']}`",
            f"- gold_v3_csv: `{summary['gold_v3_csv']}`",
            f"- supporting_final_csv: `{summary['supporting_final_csv']}`",
            f"- remaining_after_gold_v3_and_supporting_exclusion: `{summary['remaining_after_gold_v3_and_supporting_exclusion']}`",
            f"- selected_count: `{summary['selected_count']}`",
            f"- strong_recommended_count: `{summary['strong_recommended_count']}`",
            f"- backup_count: `{summary['backup_count']}`",
            "",
            "## Why These Are More Conservative Than Batch2",
            "",
            "- This pass excludes batch2 supporting items and keeps only core-review candidates.",
            "- Mars, comet, witness-coupon, sample-return contamination, and clear survivability boundary papers are filtered out first.",
            "- Analog/model/review-like papers are retained only as reserve when the remaining core pool is thin.",
            "",
            "## Recommended For Formal Core First",
        ]
        if summary["strong_recommended_titles"]:
            for title in summary["strong_recommended_titles"]:
                lines.append(f"- {title}")
        else:
            lines.append("- none; the remaining pool is weaker than batch1/batch2 and needs tighter human review")

        lines.extend(["", "## Backup Only, Not Priority Merge"])
        if summary["backup_titles"]:
            for title in summary["backup_titles"]:
                lines.append(f"- {title}")
        else:
            lines.append("- none")

        lines.extend(["", "## First Review Pass (Inspect These First)"])
        for title in summary["review_first_titles"] or ["none"]:
            lines.append(f"- {title}")

        lines.extend(["", "## Lower-Priority Reserves"])
        for title in summary["reserve_only_titles"] or ["none"]:
            lines.append(f"- {title}")

        lines.extend(["", "## Candidate Details"])
        for detail in summary["selected_details"]:
            lines.append(
                f"- {detail['doc_name']} | likelihood={detail['batch3_core_likelihood']} | scope_risk={detail['batch3_scope_risk']} | score={detail['priority_score']}"
            )
            if detail["candidate_tags"]:
                lines.append(f"  tags: {detail['candidate_tags']}")
            if detail["selection_reason"]:
                lines.append(f"  why: {detail['selection_reason']}")

        lines.extend(["", "## Category Gaps Potentially Addressed"])
        if summary["category_gap_summary"]:
            for gap, count in summary["category_gap_summary"].items():
                lines.append(f"- {gap}: {count}")
        else:
            lines.append("- none")

        lines.extend(["", "## Borderline Or Excluded Reasons"])
        for reason, count in sorted(summary["excluded_reason_counts"].items()):
            if reason:
                lines.append(f"- {reason}: {count}")

        lines.extend(
            [
                "",
                "## Estimated Core Size If All Batch3 Candidates Were Merged",
                f"- current_core_total_rows: `{summary['current_core_total_rows']}`",
                f"- current_core_evaluated_rows: `{summary['current_core_evaluated_rows']}`",
                f"- projected_total_rows_if_all_selected_merged: `{summary['projected_total_rows_if_all_selected_merged']}`",
                f"- projected_evaluated_rows_if_all_selected_merged: `{summary['projected_evaluated_rows_if_all_selected_merged']}`",
                "",
                "## Main Takeaway",
                "- The remaining pool after gold_v3 and batch2 supporting exclusion is notably weaker; batch3 can still add reviewable core candidates, but only a subset should be treated as near-term merge targets.",
            ]
        )
        return "\n".join(lines) + "\n"

    def _count_evaluated_rows(self, rows: List[Dict[str, str]]) -> int:
        count = 0
        for row in rows:
            if self._is_yes(row.get("skip_row", "")):
                continue
            if self._norm(row.get("in_scope", "")) == "no":
                continue
            count += 1
        return count

    def _sort_key(self, row: Dict[str, str]) -> Tuple[int, int, int, str]:
        likelihood_rank = {
            "recommended_core_now": 3,
            "backup_after_scope_check": 2,
            "reserve_not_recommended_first": 1,
        }.get(row.get("batch3_core_likelihood", ""), 0)
        risk_rank = {
            "low_scope_risk": 3,
            "medium_scope_risk": 2,
            "elevated_scope_risk": 1,
        }.get(row.get("batch3_scope_risk", ""), 0)
        projected_count = len(self._split_semicolon(row.get("pred_organic_compounds_projected", "")))
        return (likelihood_rank, risk_rank, projected_count, self._norm_title(row.get("doc_name", "")))

    def _is_yes(self, value: str) -> bool:
        return self._norm(value) in {"yes", "y", "true", "1"}

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
        if re.fullmatch(r"-?\\d+(?:\\.\\d+)?", text):
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
        safe_name = escape(sheet_name[:31] or "Batch3Core")
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
            "</cellXfs>"
            '<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>'
            "</styleSheet>"
        )
