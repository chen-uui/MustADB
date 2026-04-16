import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Run retrieval alpha ablation and aggregate Recall/MRR/nDCG CSV outputs."

    DEFAULT_ALPHAS = (0.3, 0.5, 0.7, 0.9)
    DEFAULT_MODES = ("hybrid", "hybrid_rerank")

    SUMMARY_COLUMNS = (
        "alpha",
        "mode",
        "n_queries",
        "n_qrels",
        "recall_at_k",
        "mrr_at_k",
        "ndcg_at_k",
        "k",
        "n_queries_total",
        "n_queries_skipped_no_relevant",
        "collection_name",
        "summary_path",
    )

    DETAILS_COLUMNS = (
        "alpha",
        "qid",
        "mode",
        "hybrid_alpha",
        "topk_doc_ids_or_names",
        "relevant_doc_ids_or_names",
        "hit_at_k",
        "reciprocal_rank",
        "recall_at_k_query",
        "ndcg_at_k_query",
        "details_path",
    )

    def add_arguments(self, parser):
        parser.add_argument("--qrels", type=str, required=True, help="Qrels CSV path.")
        parser.add_argument(
            "--alphas",
            nargs="+",
            type=float,
            default=None,
            help="Hybrid alpha values. Default: 0.3 0.5 0.7 0.9.",
        )
        parser.add_argument(
            "--modes",
            nargs="+",
            choices=self.DEFAULT_MODES,
            default=None,
            help="Hybrid retrieval modes to evaluate. Default: hybrid hybrid_rerank.",
        )
        parser.add_argument("--k", type=int, default=5, help="Top-k cutoff. Default: 5.")
        parser.add_argument(
            "--collection-name",
            type=str,
            default=None,
            help="Optional Weaviate collection override.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/alpha_ablation_<timestamp>/",
        )

    def handle(self, *args, **options):
        qrels_path = Path(str(options["qrels"])).expanduser().resolve()
        if not qrels_path.exists():
            raise CommandError(f"qrels csv not found: {qrels_path}")

        k = int(options["k"])
        if k < 1:
            raise CommandError("--k must be >= 1")

        alphas = tuple(options.get("alphas") or self.DEFAULT_ALPHAS)
        for alpha in alphas:
            if not 0.0 <= float(alpha) <= 1.0:
                raise CommandError(f"invalid alpha: {alpha}")

        modes = tuple(options.get("modes") or self.DEFAULT_MODES)
        collection_name = str(options.get("collection_name") or "").strip() or None

        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        summary_rows: List[Dict[str, str]] = []
        details_rows: List[Dict[str, str]] = []

        for alpha in alphas:
            alpha_label = self._alpha_dir_label(alpha)
            alpha_dir = out_dir / f"alpha_{alpha_label}"
            alpha_dir.mkdir(parents=True, exist_ok=True)

            call_command(
                "eval_retrieval_quality",
                qrels=str(qrels_path),
                k=k,
                modes=list(modes),
                hybrid_alpha=float(alpha),
                collection_name=collection_name,
                out=str(alpha_dir),
            )

            run_summary_path = alpha_dir / "retrieval_quality_summary.csv"
            run_details_path = alpha_dir / "retrieval_quality_details.csv"

            for row in self._read_csv(run_summary_path):
                summary_rows.append(
                    {
                        "alpha": self._fmt(alpha),
                        "mode": row.get("mode", ""),
                        "n_queries": row.get("n_queries", ""),
                        "n_qrels": row.get("n_qrels", ""),
                        "recall_at_k": row.get("recall_at_k", ""),
                        "mrr_at_k": row.get("mrr_at_k", ""),
                        "ndcg_at_k": row.get("ndcg_at_k", ""),
                        "k": row.get("k", ""),
                        "n_queries_total": row.get("n_queries_total", ""),
                        "n_queries_skipped_no_relevant": row.get("n_queries_skipped_no_relevant", ""),
                        "collection_name": collection_name or "",
                        "summary_path": str(run_summary_path),
                    }
                )

            for row in self._read_csv(run_details_path):
                details_rows.append(
                    {
                        "alpha": self._fmt(alpha),
                        "qid": row.get("qid", ""),
                        "mode": row.get("mode", ""),
                        "hybrid_alpha": row.get("hybrid_alpha", ""),
                        "topk_doc_ids_or_names": row.get("topk_doc_ids_or_names", ""),
                        "relevant_doc_ids_or_names": row.get("relevant_doc_ids_or_names", ""),
                        "hit_at_k": row.get("hit_at_k", ""),
                        "reciprocal_rank": row.get("reciprocal_rank", ""),
                        "recall_at_k_query": row.get("recall_at_k_query", ""),
                        "ndcg_at_k_query": row.get("ndcg_at_k_query", ""),
                        "details_path": str(run_details_path),
                    }
                )

        summary_path = out_dir / "alpha_ablation_summary.csv"
        details_path = out_dir / "alpha_ablation_details.csv"
        self._write_csv(summary_path, self.SUMMARY_COLUMNS, summary_rows)
        self._write_csv(details_path, self.DETAILS_COLUMNS, details_rows)

        self.stdout.write(f"qrels_path={qrels_path}")
        self.stdout.write(f"alphas={','.join(self._fmt(alpha) for alpha in alphas)}")
        self.stdout.write(f"modes={','.join(modes)}")
        self.stdout.write(f"k={k}")
        if collection_name:
            self.stdout.write(f"collection_name={collection_name}")
        self.stdout.write(f"out_dir={out_dir}")
        self.stdout.write(f"summary_path={summary_path}")
        self.stdout.write(f"details_path={details_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"alpha_ablation_{ts}").resolve()

    def _alpha_dir_label(self, alpha: float) -> str:
        return self._fmt(alpha).replace(".", "p")

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
