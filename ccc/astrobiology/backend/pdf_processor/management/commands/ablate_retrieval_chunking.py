import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Sweep chunk size/overlap configs by rebuilding isolated collections and running retrieval evaluation."

    DEFAULT_CONFIGS = ("500:50", "700:80", "900:100")
    DEFAULT_MODES = ("hybrid_rerank",)

    SUMMARY_COLUMNS = (
        "chunk_size",
        "chunk_overlap",
        "collection_name",
        "mode",
        "hybrid_alpha",
        "n_queries",
        "n_qrels",
        "recall_at_k",
        "mrr_at_k",
        "ndcg_at_k",
        "k",
        "n_queries_total",
        "n_queries_skipped_no_relevant",
        "run_dir",
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--qrels",
            type=str,
            required=True,
            help="Path to manually filled qrels CSV.",
        )
        parser.add_argument(
            "--configs",
            nargs="+",
            default=list(self.DEFAULT_CONFIGS),
            help="Chunk configs as size:overlap pairs. Default: 500:50 700:80 900:100.",
        )
        parser.add_argument(
            "--k",
            type=int,
            default=5,
            help="Top-k cutoff for metrics. Default: 5.",
        )
        parser.add_argument(
            "--modes",
            nargs="+",
            choices=("bm25", "dense", "hybrid", "hybrid_rerank"),
            default=list(self.DEFAULT_MODES),
            help="Retrieval modes to evaluate. Default: hybrid_rerank.",
        )
        parser.add_argument(
            "--hybrid-alpha",
            type=float,
            default=None,
            help="Override hybrid alpha during evaluation. Default: current runtime default (0.7).",
        )
        parser.add_argument(
            "--pdf-dir",
            type=str,
            default=None,
            help="Override the PDF source directory for rebuild.",
        )
        parser.add_argument(
            "--file",
            dest="single_file",
            type=str,
            default=None,
            help="Process only one PDF file per config.",
        )
        parser.add_argument(
            "--max-files",
            type=int,
            default=0,
            help="Maximum number of PDF files to process per config. Use 0 for all. Default: 0.",
        )
        parser.add_argument(
            "--collection-prefix",
            type=str,
            default="PDFDocument_chunk_ablation",
            help="Collection name prefix for isolated experiment collections.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/chunk_ablation_<timestamp>/",
        )

    def handle(self, *args, **options):
        qrels_path = Path(str(options["qrels"])).expanduser().resolve()
        if not qrels_path.exists():
            raise CommandError(f"qrels csv not found: {qrels_path}")

        k = int(options["k"])
        if k < 1:
            raise CommandError("--k must be >= 1")

        hybrid_alpha = options.get("hybrid_alpha")
        if hybrid_alpha is not None and not 0.0 <= float(hybrid_alpha) <= 1.0:
            raise CommandError("--hybrid-alpha must be between 0 and 1")

        configs = [self._parse_config(item) for item in (options.get("configs") or self.DEFAULT_CONFIGS)]
        modes = list(options.get("modes") or self.DEFAULT_MODES)
        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        aggregate_rows: List[Dict[str, str]] = []

        for chunk_size, chunk_overlap in configs:
            run_dir = out_dir / f"chunk_{chunk_size}_{chunk_overlap}"
            eval_dir = run_dir / "retrieval_eval"
            eval_dir.mkdir(parents=True, exist_ok=True)

            collection_name = self._build_collection_name(
                prefix=str(options["collection_prefix"]),
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )

            self.stdout.write(
                f"[chunk] size={chunk_size} overlap={chunk_overlap} collection={collection_name}"
            )

            reprocess_kwargs = {
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "collection_name": collection_name,
                "reset_collection": True,
                "dry_run": False,
                "max_files": int(options.get("max_files", 0)),
            }
            if options.get("pdf_dir"):
                reprocess_kwargs["pdf_dir"] = str(options["pdf_dir"])
            if options.get("single_file"):
                reprocess_kwargs["single_file"] = str(options["single_file"])

            call_command("reprocess_pdfs", **reprocess_kwargs)

            eval_kwargs = {
                "qrels": str(qrels_path),
                "k": k,
                "modes": modes,
                "collection_name": collection_name,
                "out": str(eval_dir),
            }
            if hybrid_alpha is not None:
                eval_kwargs["hybrid_alpha"] = float(hybrid_alpha)

            call_command("eval_retrieval_quality", **eval_kwargs)

            summary_path = eval_dir / "retrieval_quality_summary.csv"
            if not summary_path.exists():
                raise CommandError(f"expected retrieval summary not found: {summary_path}")

            for row in self._load_csv_rows(summary_path):
                aggregate_rows.append(
                    {
                        "chunk_size": str(chunk_size),
                        "chunk_overlap": str(chunk_overlap),
                        "collection_name": collection_name,
                        "mode": row.get("mode", ""),
                        "hybrid_alpha": row.get("hybrid_alpha", ""),
                        "n_queries": row.get("n_queries", ""),
                        "n_qrels": row.get("n_qrels", ""),
                        "recall_at_k": row.get("recall_at_k", ""),
                        "mrr_at_k": row.get("mrr_at_k", ""),
                        "ndcg_at_k": row.get("ndcg_at_k", ""),
                        "k": row.get("k", ""),
                        "n_queries_total": row.get("n_queries_total", ""),
                        "n_queries_skipped_no_relevant": row.get(
                            "n_queries_skipped_no_relevant", ""
                        ),
                        "run_dir": str(run_dir),
                    }
                )

        summary_path = out_dir / "chunk_ablation_summary.csv"
        self._write_csv(summary_path, self.SUMMARY_COLUMNS, aggregate_rows)

        self.stdout.write(f"qrels_path={qrels_path}")
        self.stdout.write(
            "configs=" + ",".join(f"{chunk_size}:{chunk_overlap}" for chunk_size, chunk_overlap in configs)
        )
        self.stdout.write(f"modes={','.join(modes)}")
        if hybrid_alpha is not None:
            self.stdout.write(f"hybrid_alpha={hybrid_alpha:.4f}")
        self.stdout.write(f"out_dir={out_dir}")
        self.stdout.write(f"summary_path={summary_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"chunk_ablation_{timestamp}").resolve()

    def _parse_config(self, raw: str) -> Tuple[int, int]:
        text = str(raw or "").strip()
        if ":" not in text:
            raise CommandError(f"invalid config '{raw}'; expected size:overlap")
        size_part, overlap_part = text.split(":", 1)
        try:
            chunk_size = int(size_part)
            chunk_overlap = int(overlap_part)
        except ValueError as exc:
            raise CommandError(f"invalid config '{raw}'; size and overlap must be integers") from exc
        if chunk_size < 1:
            raise CommandError(f"invalid config '{raw}'; chunk size must be >= 1")
        if chunk_overlap < 0:
            raise CommandError(f"invalid config '{raw}'; chunk overlap must be >= 0")
        if chunk_overlap >= chunk_size:
            raise CommandError(f"invalid config '{raw}'; overlap must be smaller than size")
        return chunk_size, chunk_overlap

    def _build_collection_name(self, *, prefix: str, chunk_size: int, chunk_overlap: int) -> str:
        normalized_prefix = str(prefix or "").strip() or "PDFDocument_chunk_ablation"
        return f"{normalized_prefix}_{chunk_size}_{chunk_overlap}"

    def _load_csv_rows(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            return [dict(row) for row in reader]

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
