import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from pdf_processor.management.commands.eval_retrieval_quality import (
    Command as EvalRetrievalQualityCommand,
)


class Command(BaseCommand):
    help = "Sweep hybrid alpha values over retrieval evaluation and export aggregated CSV summaries."

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
        "run_dir",
    )

    DETAILS_COLUMNS = (
        "alpha",
        "qid",
        "mode",
        "topk_doc_ids_or_names",
        "relevant_doc_ids_or_names",
        "hit_at_k",
        "reciprocal_rank",
        "recall_at_k_query",
        "ndcg_at_k_query",
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
            "--k",
            type=int,
            default=5,
            help="Top-k cutoff for metrics. Default: 5.",
        )
        parser.add_argument(
            "--alphas",
            nargs="+",
            type=float,
            default=list(self.DEFAULT_ALPHAS),
            help="Hybrid alpha values to evaluate. Default: 0.3 0.5 0.7 0.9.",
        )
        parser.add_argument(
            "--modes",
            nargs="+",
            choices=EvalRetrievalQualityCommand.MODES,
            default=list(self.DEFAULT_MODES),
            help="Retrieval modes to evaluate. Default: hybrid hybrid_rerank.",
        )
        parser.add_argument(
            "--collection-name",
            type=str,
            default=None,
            help="Override Weaviate collection for this evaluation run only.",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/retrieval_alpha_<timestamp>/",
        )

    def handle(self, *args, **options):
        qrels_path = Path(str(options["qrels"])).expanduser().resolve()
        if not qrels_path.exists():
            raise CommandError(f"qrels csv not found: {qrels_path}")

        k = int(options["k"])
        if k < 1:
            raise CommandError("--k must be >= 1")

        alphas = [float(alpha) for alpha in options.get("alphas") or self.DEFAULT_ALPHAS]
        if not alphas:
            raise CommandError("at least one alpha is required")
        for alpha in alphas:
            if not 0.0 <= alpha <= 1.0:
                raise CommandError("all --alphas values must be between 0 and 1")

        modes = list(options.get("modes") or self.DEFAULT_MODES)
        collection_name = self._normalize_optional_str(options.get("collection_name"))
        out_dir = self._resolve_out_dir(options.get("out"))
        out_dir.mkdir(parents=True, exist_ok=True)

        eval_command = EvalRetrievalQualityCommand()
        eval_command.stdout = self.stdout
        eval_command.stderr = self.stderr

        aggregate_summary_rows: List[Dict[str, str]] = []
        aggregate_details_rows: List[Dict[str, str]] = []

        for alpha in alphas:
            run_dir = out_dir / f"alpha_{self._slug_alpha(alpha)}"
            run_dir.mkdir(parents=True, exist_ok=True)

            self.stdout.write(f"[alpha] {alpha:.4f}")
            evaluation = eval_command.evaluate(
                qrels_path=qrels_path,
                k=k,
                modes=modes,
                hybrid_alpha=alpha,
                collection_name=collection_name,
            )
            eval_command.write_outputs(
                out_dir=run_dir,
                summary_rows=evaluation["summary_rows"],
                details_rows=evaluation["details_rows"],
            )

            for row in evaluation["summary_rows"]:
                aggregate_summary_rows.append(
                    {
                        "alpha": self._fmt(alpha),
                        "mode": row["mode"],
                        "n_queries": row["n_queries"],
                        "n_qrels": row["n_qrels"],
                        "recall_at_k": row["recall_at_k"],
                        "mrr_at_k": row["mrr_at_k"],
                        "ndcg_at_k": row["ndcg_at_k"],
                        "k": row["k"],
                        "n_queries_total": row["n_queries_total"],
                        "n_queries_skipped_no_relevant": row["n_queries_skipped_no_relevant"],
                        "run_dir": str(run_dir),
                    }
                )

            for row in evaluation["details_rows"]:
                aggregate_details_rows.append(
                    {
                        "alpha": self._fmt(alpha),
                        "qid": row["qid"],
                        "mode": row["mode"],
                        "topk_doc_ids_or_names": row["topk_doc_ids_or_names"],
                        "relevant_doc_ids_or_names": row["relevant_doc_ids_or_names"],
                        "hit_at_k": row["hit_at_k"],
                        "reciprocal_rank": row["reciprocal_rank"],
                        "recall_at_k_query": row["recall_at_k_query"],
                        "ndcg_at_k_query": row["ndcg_at_k_query"],
                        "run_dir": str(run_dir),
                    }
                )

        summary_path = out_dir / "alpha_ablation_summary.csv"
        details_path = out_dir / "alpha_ablation_details.csv"
        self._write_csv(summary_path, self.SUMMARY_COLUMNS, aggregate_summary_rows)
        self._write_csv(details_path, self.DETAILS_COLUMNS, aggregate_details_rows)

        self.stdout.write(f"qrels_path={qrels_path}")
        self.stdout.write(f"alphas={','.join(self._fmt(alpha) for alpha in alphas)}")
        self.stdout.write(f"modes={','.join(modes)}")
        if collection_name:
            self.stdout.write(f"collection_name={collection_name}")
        self.stdout.write(f"out_dir={out_dir}")
        self.stdout.write(f"summary_path={summary_path}")
        self.stdout.write(f"details_path={details_path}")

    def _resolve_out_dir(self, out_arg: Optional[str]) -> Path:
        if out_arg and str(out_arg).strip():
            return Path(str(out_arg)).expanduser().resolve()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / f"retrieval_alpha_{timestamp}").resolve()

    def _normalize_optional_str(self, value: object) -> Optional[str]:
        normalized = str(value or "").strip()
        return normalized or None

    def _slug_alpha(self, alpha: float) -> str:
        return self._fmt(alpha).replace(".", "p")

    def _fmt(self, value: float) -> str:
        return f"{value:.4f}"

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
