import csv
import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from xml.sax.saxutils import escape

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Split reviewed batch2 candidates into core/supporting gold files."

    OUTPUT_COLUMNS = [
        "doc_id",
        "doc_name",
        "pred_meteorite_name",
        "pred_organic_compounds",
        "pred_contamination_controls",
        "in_scope",
        "skip_row",
        "notes",
        "gold_meteorite_name",
        "gold_organic_compounds",
        "gold_contamination_controls",
        "review_note",
        "doc_filename",
        "doc_year",
        "doc_journal",
        "prediction_source",
        "review_priority",
        "scope_type",
        "recommendation",
        "pred_organic_compounds_raw",
        "pred_organic_compounds_filtered",
        "pred_organic_compounds_projected",
        "rerun_strategy",
        "rerun_selected_chunk_ids",
    ]

    CORE_TITLES = {
        "Concentration and variability of the AIB amino acid in polar micrometeorites: Implications for the exogenous delivery of amino acids to the primitive Earth",
    }
    COMET_TITLE = "Oxygen-bearing organic molecules in comet 67Ps dusty coma: First evidence for abundant heterocycles"
    SUPPORTING_TITLES = {
        "Amino acids on witness coupons collected from the ISASJAXA curation facility for the assessment and quality control of the Hayabusa2 sampling procedure",
        "Concerns of Organic Contamination for Sample Return Space Missions",
        "Abiotic formation of alkylsulfonic acids in interstellar analog ices and implications for their detection on Ryugu",
        "Reanalysis of the Viking results suggests perchlorate and organics at midlatitudes on Mars",
    }

    def add_arguments(self, parser):
        parser.add_argument("--batch2-csv", type=str, required=True, help="batch2_review_candidates.csv path.")
        parser.add_argument(
            "--scope-accepts-comet-core",
            action="store_true",
            help="If set, place the comet 67P paper into core instead of supporting.",
        )
        parser.add_argument(
            "--out-dir",
            type=str,
            default=None,
            help="Output directory. Default: runs/gold_batch2_split_<timestamp>",
        )

    def handle(self, *args, **options):
        batch2_csv = Path(str(options["batch2_csv"])).expanduser().resolve()
        if not batch2_csv.exists():
            raise CommandError(f"batch2 csv not found: {batch2_csv}")

        out_dir = self._resolve_out_dir(options.get("out_dir"))
        out_dir.mkdir(parents=True, exist_ok=True)

        rows = self._read_csv(batch2_csv)
        row_map = {row.get("doc_name", ""): row for row in rows}

        core_titles = set(self.CORE_TITLES)
        supporting_titles = set(self.SUPPORTING_TITLES)
        comet_goes_to_core = bool(options.get("scope_accepts_comet_core"))
        if comet_goes_to_core:
            core_titles.add(self.COMET_TITLE)
        else:
            supporting_titles.add(self.COMET_TITLE)

        missing_titles = [title for title in sorted(core_titles | supporting_titles) if title not in row_map]
        if missing_titles:
            raise CommandError(f"required reviewed titles missing from batch2 csv: {missing_titles}")

        core_rows = [self._convert_row(row_map[title], layer="core_gold") for title in core_titles]
        supporting_rows = [self._convert_row(row_map[title], layer="supporting_gold") for title in supporting_titles]

        core_csv = out_dir / "gold_seed_batch2_core.csv"
        core_xlsx = out_dir / "gold_seed_batch2_core.xlsx"
        supporting_csv = out_dir / "gold_seed_batch2_supporting.csv"
        supporting_xlsx = out_dir / "gold_seed_batch2_supporting.xlsx"
        summary_md = out_dir / "summary.md"
        summary_json = out_dir / "summary.json"

        self._write_csv(core_csv, self.OUTPUT_COLUMNS, core_rows)
        self._write_xlsx(core_xlsx, "Batch2Core", self.OUTPUT_COLUMNS, core_rows)
        self._write_csv(supporting_csv, self.OUTPUT_COLUMNS, supporting_rows)
        self._write_xlsx(supporting_xlsx, "Batch2Supporting", self.OUTPUT_COLUMNS, supporting_rows)

        summary = {
            "batch2_csv": str(batch2_csv),
            "scope_accepts_comet_core": comet_goes_to_core,
            "comet_67p_layer": "core_gold" if comet_goes_to_core else "supporting_gold",
            "core_added_count": len(core_rows),
            "supporting_added_count": len(supporting_rows),
            "core_titles": [row["doc_name"] for row in core_rows],
            "supporting_titles": [row["doc_name"] for row in supporting_rows],
            "assumption": "No separate annotated batch2 gold fields were found locally, so gold_* values were provisionally filled from existing suggested_gold_* / gold_* / pred_* fields in that order.",
        }
        summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary_md.write_text(self._build_summary_markdown(summary), encoding="utf-8")

        self.stdout.write(f"core_csv={core_csv}")
        self.stdout.write(f"core_xlsx={core_xlsx}")
        self.stdout.write(f"supporting_csv={supporting_csv}")
        self.stdout.write(f"supporting_xlsx={supporting_xlsx}")
        self.stdout.write(f"summary_md={summary_md}")
        self.stdout.write(f"summary_json={summary_json}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"gold_batch2_split_{ts}").resolve()

    def _read_csv(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))

    def _convert_row(self, row: Dict[str, str], *, layer: str) -> Dict[str, str]:
        gold_meteorite = self._first_nonempty(
            row.get("suggested_gold_meteorite_name", ""),
            row.get("gold_meteorite_name", ""),
            row.get("pred_meteorite_name", ""),
        )
        gold_organics = self._first_nonempty(
            row.get("suggested_gold_organic_compounds", ""),
            row.get("gold_organic_compounds", ""),
            row.get("pred_organic_compounds_projected", ""),
            row.get("pred_organic_compounds_filtered", ""),
            row.get("pred_organic_compounds_raw", ""),
        )
        gold_contam = self._first_nonempty(
            row.get("suggested_gold_contamination_controls", ""),
            row.get("gold_contamination_controls", ""),
            row.get("pred_contamination_controls", ""),
        )
        review_note = (
            f"batch2_layer={layer}; "
            "gold_fields_provisionally_filled_from_existing_batch2_candidate_fields"
        )
        scope_type = "core_gold" if layer == "core_gold" else "supporting_gold"
        recommendation = row.get("batch2_inclusion_likelihood", "") or row.get("recommendation", "")
        return {
            "doc_id": row.get("doc_id", ""),
            "doc_name": row.get("doc_name", ""),
            "pred_meteorite_name": row.get("pred_meteorite_name", ""),
            "pred_organic_compounds": self._first_nonempty(
                row.get("pred_organic_compounds_projected", ""),
                row.get("pred_organic_compounds_filtered", ""),
                row.get("pred_organic_compounds_raw", ""),
            ),
            "pred_contamination_controls": row.get("pred_contamination_controls", ""),
            "in_scope": "yes",
            "skip_row": "no",
            "notes": row.get("notes", ""),
            "gold_meteorite_name": gold_meteorite,
            "gold_organic_compounds": gold_organics,
            "gold_contamination_controls": gold_contam,
            "review_note": review_note,
            "doc_filename": row.get("doc_filename", ""),
            "doc_year": row.get("doc_year", ""),
            "doc_journal": row.get("doc_journal", ""),
            "prediction_source": row.get("prediction_source", ""),
            "review_priority": row.get("review_priority", ""),
            "scope_type": scope_type,
            "recommendation": recommendation,
            "pred_organic_compounds_raw": row.get("pred_organic_compounds_raw", ""),
            "pred_organic_compounds_filtered": row.get("pred_organic_compounds_filtered", ""),
            "pred_organic_compounds_projected": row.get("pred_organic_compounds_projected", ""),
            "rerun_strategy": row.get("rerun_strategy", ""),
            "rerun_selected_chunk_ids": row.get("rerun_selected_chunk_ids", ""),
        }

    def _first_nonempty(self, *values: str) -> str:
        for value in values:
            text = re.sub(r"\s+", " ", str(value or "")).strip()
            if text:
                return text
        return ""

    def _build_summary_markdown(self, summary: Dict[str, Any]) -> str:
        lines = [
            "# Batch2 Layered Export Summary",
            "",
            f"- batch2_csv: `{summary['batch2_csv']}`",
            f"- core_added_count: `{summary['core_added_count']}`",
            f"- supporting_added_count: `{summary['supporting_added_count']}`",
            f"- comet_67p_layer: `{summary['comet_67p_layer']}`",
            f"- assumption: {summary['assumption']}",
            "",
            "## Core Gold",
        ]
        for title in summary["core_titles"] or ["none"]:
            lines.append(f"- {title}")
        lines.extend(["", "## Supporting Gold"])
        for title in summary["supporting_titles"] or ["none"]:
            lines.append(f"- {title}")
        return "\n".join(lines) + "\n"

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
        safe_name = escape(sheet_name[:31] or "Batch2")
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
