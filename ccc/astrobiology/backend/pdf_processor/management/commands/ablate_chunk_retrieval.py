import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from pdf_processor.models import PDFDocument
from pdf_processor.weaviate_services import WeaviateConfig, WeaviateDocumentProcessor


class Command(BaseCommand):
    help = "Build experimental chunked collections and run retrieval evaluation for each chunk config."

    DEFAULT_CHUNK_CONFIGS = ("500:50", "700:80", "900:100")
    DEFAULT_MODES = ("hybrid_rerank",)

    SUMMARY_COLUMNS = (
        "chunk_size",
        "chunk_overlap",
        "collection_name",
        "build_total_docs",
        "build_success_docs",
        "build_failed_docs",
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
        "eval_summary_path",
    )

    def add_arguments(self, parser):
        parser.add_argument("--qrels", type=str, required=True, help="Qrels CSV path.")
        parser.add_argument(
            "--chunk-configs",
            nargs="+",
            default=None,
            help="Chunk configs in size:overlap form. Default: 500:50 700:80 900:100.",
        )
        parser.add_argument(
            "--modes",
            nargs="+",
            choices=("bm25", "dense", "hybrid", "hybrid_rerank"),
            default=None,
            help="Retrieval modes to evaluate. Default: hybrid_rerank.",
        )
        parser.add_argument(
            "--hybrid-alpha",
            type=float,
            default=0.7,
            help="Hybrid alpha used during retrieval evaluation. Default: 0.7.",
        )
        parser.add_argument("--k", type=int, default=5, help="Top-k cutoff. Default: 5.")
        parser.add_argument("--workers", type=int, default=2, help="Batch ingest worker count.")
        parser.add_argument(
            "--limit-docs",
            type=int,
            default=None,
            help="Optional cap on the number of PDFDocument rows to ingest per config.",
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

        hybrid_alpha = float(options["hybrid_alpha"])
        if not 0.0 <= hybrid_alpha <= 1.0:
            raise CommandError("--hybrid-alpha must be between 0 and 1")

        chunk_configs = tuple(options.get("chunk_configs") or self.DEFAULT_CHUNK_CONFIGS)
        parsed_configs = [self._parse_chunk_config(item) for item in chunk_configs]
        modes = tuple(options.get("modes") or self.DEFAULT_MODES)

        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        docs = self._select_documents(limit_docs=options.get("limit_docs"))
        if not docs:
            raise CommandError("No PDFDocument rows with file_path available for chunk ablation")

        run_tag = datetime.now().strftime("%Y%m%d%H%M%S")
        summary_rows: List[Dict[str, str]] = []

        for chunk_size, chunk_overlap in parsed_configs:
            config_dir = out_dir / f"chunk_{chunk_size}_{chunk_overlap}"
            config_dir.mkdir(parents=True, exist_ok=True)

            collection_name = self._build_collection_name(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                run_tag=run_tag,
            )

            build_results = self._build_experimental_collection(
                docs=docs,
                collection_name=collection_name,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                workers=int(options["workers"]),
            )

            eval_dir = config_dir / "retrieval_eval"
            call_command(
                "eval_retrieval_quality",
                qrels=str(qrels_path),
                k=k,
                modes=list(modes),
                hybrid_alpha=hybrid_alpha,
                collection_name=collection_name,
                out=str(eval_dir),
            )

            eval_summary_path = eval_dir / "retrieval_quality_summary.csv"
            for row in self._read_csv(eval_summary_path):
                summary_rows.append(
                    {
                        "chunk_size": str(chunk_size),
                        "chunk_overlap": str(chunk_overlap),
                        "collection_name": collection_name,
                        "build_total_docs": str(build_results["total_docs"]),
                        "build_success_docs": str(build_results["success_docs"]),
                        "build_failed_docs": str(build_results["failed_docs"]),
                        "mode": row.get("mode", ""),
                        "hybrid_alpha": row.get("hybrid_alpha", self._fmt(hybrid_alpha)),
                        "n_queries": row.get("n_queries", ""),
                        "n_qrels": row.get("n_qrels", ""),
                        "recall_at_k": row.get("recall_at_k", ""),
                        "mrr_at_k": row.get("mrr_at_k", ""),
                        "ndcg_at_k": row.get("ndcg_at_k", ""),
                        "k": row.get("k", ""),
                        "n_queries_total": row.get("n_queries_total", ""),
                        "n_queries_skipped_no_relevant": row.get("n_queries_skipped_no_relevant", ""),
                        "eval_summary_path": str(eval_summary_path),
                    }
                )

        summary_path = out_dir / "chunk_ablation_summary.csv"
        self._write_csv(summary_path, self.SUMMARY_COLUMNS, summary_rows)

        self.stdout.write(f"qrels_path={qrels_path}")
        self.stdout.write(
            "chunk_configs="
            + ",".join(f"{chunk_size}:{chunk_overlap}" for chunk_size, chunk_overlap in parsed_configs)
        )
        self.stdout.write(f"modes={','.join(modes)}")
        self.stdout.write(f"hybrid_alpha={self._fmt(hybrid_alpha)}")
        self.stdout.write(f"k={k}")
        self.stdout.write(f"docs_selected={len(docs)}")
        self.stdout.write(f"out_dir={out_dir}")
        self.stdout.write(f"summary_path={summary_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"chunk_ablation_{ts}").resolve()

    def _parse_chunk_config(self, raw_value: str) -> Tuple[int, int]:
        normalized = str(raw_value or "").strip()
        if ":" not in normalized:
            raise CommandError(f"invalid chunk config '{raw_value}', expected size:overlap")
        size_text, overlap_text = normalized.split(":", 1)
        try:
            chunk_size = int(size_text)
            chunk_overlap = int(overlap_text)
        except ValueError as exc:
            raise CommandError(f"invalid chunk config '{raw_value}', expected integers") from exc
        if chunk_size < 1 or chunk_overlap < 0:
            raise CommandError(f"invalid chunk config '{raw_value}', expected size>=1 overlap>=0")
        return chunk_size, chunk_overlap

    def _select_documents(self, *, limit_docs: Optional[int]) -> List[PDFDocument]:
        queryset = (
            PDFDocument.objects.exclude(file_path__isnull=True)
            .exclude(file_path="")
            .order_by("id")
        )
        if limit_docs is not None:
            if int(limit_docs) < 1:
                raise CommandError("--limit-docs must be >= 1")
            queryset = queryset[: int(limit_docs)]
        return list(queryset)

    def _build_collection_name(self, *, chunk_size: int, chunk_overlap: int, run_tag: str) -> str:
        return f"PDFDocumentChunk{chunk_size}O{chunk_overlap}T{run_tag}"

    def _build_experimental_collection(
        self,
        *,
        docs: Sequence[PDFDocument],
        collection_name: str,
        chunk_size: int,
        chunk_overlap: int,
        workers: int,
    ) -> Dict[str, int]:
        config = WeaviateConfig(collection_name=collection_name)
        processor = WeaviateDocumentProcessor(config)
        processor.vector_service.create_collection_if_not_exists(collection_name)

        try:
            results = processor.process_documents_batch(
                [doc.file_path for doc in docs],
                max_workers=workers,
                metadata_list=[
                    {
                        "id": str(doc.id),
                        "title": doc.title,
                        "authors": doc.authors or "",
                        "year": str(doc.year) if doc.year else "",
                        "journal": doc.journal or "",
                        "doi": doc.doi or "",
                        "category": doc.category,
                        "upload_date": str(doc.upload_date),
                        "file_path": doc.file_path,
                    }
                    for doc in docs
                ],
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
            )
        finally:
            processor.close()

        success_docs = sum(1 for result in results if result.get("status") == "success")
        return {
            "total_docs": len(docs),
            "success_docs": success_docs,
            "failed_docs": len(results) - success_docs,
        }

    def _fmt(self, value: float) -> str:
        return f"{float(value):.4f}"

    def _read_csv(self, path: Path) -> List[Dict[str, str]]:
        with path.open("r", encoding="utf-8", newline="") as handle:
            return [{k: str(v or "").strip() for k, v in row.items()} for row in csv.DictReader(handle)]

    def _write_csv(
        self,
        path: Path,
        fieldnames: Sequence[str],
        rows: Sequence[Dict[str, str]],
    ) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(fieldnames))
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
