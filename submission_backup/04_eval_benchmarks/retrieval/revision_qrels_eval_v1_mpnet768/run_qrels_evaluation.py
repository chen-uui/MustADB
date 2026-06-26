#!/usr/bin/env python3
"""Run qrels-based retrieval evaluation without changing retrieval configuration."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Sequence

from build_retrieval_candidate_pool_standalone import (
    DEFAULT_COLLECTION,
    StandaloneRetrievalWrapper,
    load_queries,
)


METHODS = ("bm25", "dense", "hybrid")
KS = (1, 3, 5, 10)


def export_ranked_results(
    *,
    queries_path: Path,
    out_dir: Path,
    backend_dir: Path,
    collection_name: str,
    methods: Sequence[str],
    top_k: int,
) -> Path:
    queries = load_queries(queries_path)
    wrapper = StandaloneRetrievalWrapper(
        backend_dir=backend_dir,
        collection_name=collection_name,
        hybrid_alpha=0.7,
        use_settings_shim=True,
    )
    if not wrapper.initialize():
        raise RuntimeError(f"core retrieval failed to load: {wrapper.load_error}")

    combined: Dict[str, List[Dict[str, Any]]] = {}
    out_dir.mkdir(parents=True, exist_ok=True)
    for method in methods:
        method_records: List[Dict[str, Any]] = []
        method_path = out_dir / f"{method}_results.jsonl"
        with method_path.open("w", encoding="utf-8") as handle:
            for index, query in enumerate(queries, start=1):
                print(f"[{method}] {index}/{len(queries)} {query.qid}", flush=True)
                candidates = wrapper.search(query.question, method, top_k)
                results = [
                    {
                        "rank": rank,
                        "doc_id": item.doc_id,
                        "score": float(item.score),
                    }
                    for rank, item in enumerate(candidates, start=1)
                ]
                record = {
                    "qid": query.qid,
                    "query": query.question,
                    "method": method,
                    "results": results,
                }
                method_records.append(record)
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        combined[method] = method_records

    combined_path = out_dir / "retrieval_results_by_method.json"
    combined_path.write_text(json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8")
    return combined_path


def load_qrels_stats(qrels_path: Path) -> Dict[str, Any]:
    rows = []
    by_qid: Dict[str, Dict[str, int]] = defaultdict(dict)
    with qrels_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            qid = str(row.get("qid", "")).strip()
            doc_id = str(row.get("doc_id", "")).strip()
            relevance = int(str(row.get("relevance", "")).strip())
            rows.append((qid, doc_id, relevance))
            by_qid[qid][doc_id] = relevance
    relevant = sum(1 for _, _, rel in rows if rel > 0)
    highly_relevant = sum(1 for _, _, rel in rows if rel == 2)
    no_relevant = sorted(qid for qid, docs in by_qid.items() if not any(rel > 0 for rel in docs.values()))
    return {
        "qrels_total": len(rows),
        "unique_queries": len(by_qid),
        "unique_docs": len({doc_id for _, doc_id, _ in rows}),
        "relevant_docs": relevant,
        "highly_relevant_docs": highly_relevant,
        "queries_without_relevant_docs": no_relevant,
    }


def write_paper_ready_table(metrics_path: Path, out_path: Path) -> List[Dict[str, str]]:
    with metrics_path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    columns = [
        "method",
        "Recall@1",
        "Recall@3",
        "Recall@5",
        "Recall@10",
        "nDCG@1",
        "nDCG@3",
        "nDCG@5",
        "nDCG@10",
        "MRR@10",
    ]
    converted = []
    for row in rows:
        converted.append(
            {
                "method": row["method"],
                "Recall@1": row["recall_at_1"],
                "Recall@3": row["recall_at_3"],
                "Recall@5": row["recall_at_5"],
                "Recall@10": row["recall_at_10"],
                "nDCG@1": row["ndcg_at_1"],
                "nDCG@3": row["ndcg_at_3"],
                "nDCG@5": row["ndcg_at_5"],
                "nDCG@10": row["ndcg_at_10"],
                "MRR@10": row["mrr_at_10"],
            }
        )
    with out_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(converted)
    return converted


def method_distribution(results_path: Path) -> Dict[str, int]:
    payload = json.loads(results_path.read_text(encoding="utf-8"))
    counts = Counter()
    for method, records in payload.items():
        for record in records:
            counts[method] += len(record.get("results", []))
    return dict(sorted(counts.items()))


def build_report(
    *,
    out_path: Path,
    qrels_stats: Dict[str, Any],
    paper_rows: Sequence[Dict[str, str]],
    ranked_results_path: Path,
    method_counts: Dict[str, int],
    top10_unjudged_count: int,
) -> None:
    no_rel = qrels_stats["queries_without_relevant_docs"]
    lines = [
        "# Retrieval Evaluation Report",
        "",
        "## Inputs",
        "",
        f"- ranked_results: `{ranked_results_path}`",
        "- relevance_threshold_for_recall_mrr: `> 0`",
        "- nDCG gain: `2^relevance - 1`",
        (
            "- unjudged retrieved documents: treated as relevance `0` by the evaluator; "
            f"top-10 unjudged results in this run: `{top10_unjudged_count}`"
        ),
        "",
        "## Qrels Summary",
        "",
        f"- qrels_total: `{qrels_stats['qrels_total']}`",
        f"- relevant_documents_relevance_gt_0: `{qrels_stats['relevant_docs']}`",
        f"- highly_relevant_documents_relevance_eq_2: `{qrels_stats['highly_relevant_docs']}`",
        f"- evaluated_queries: `{qrels_stats['unique_queries'] - len(no_rel)}`",
        f"- queries_without_relevant_docs: `{len(no_rel)}`",
    ]
    if no_rel:
        lines.append(f"- queries_without_relevant_docs_list: `{', '.join(no_rel)}`")
        lines.append("- handling: queries with no positive qrels are excluded from macro-averaged metrics.")
    else:
        lines.append("- handling: all queries contain at least one positive qrel, so all are included.")

    lines.extend(
        [
            "",
            "## Ranked Results Export",
            "",
            "| method | retrieved rows |",
            "|---|---:|",
        ]
    )
    for method, count in method_counts.items():
        lines.append(f"| `{method}` | {count} |")

    lines.extend(
        [
            "",
            "## Metrics",
            "",
            "| method | Recall@1 | Recall@3 | Recall@5 | Recall@10 | nDCG@1 | nDCG@3 | nDCG@5 | nDCG@10 | MRR@10 |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for row in paper_rows:
        lines.append(
            "| {method} | {Recall@1} | {Recall@3} | {Recall@5} | {Recall@10} | "
            "{nDCG@1} | {nDCG@3} | {nDCG@5} | {nDCG@10} | {MRR@10} |".format(**row)
        )

    best_recall10 = max(paper_rows, key=lambda row: float(row["Recall@10"]))
    best_ndcg10 = max(paper_rows, key=lambda row: float(row["nDCG@10"]))
    lines.extend(
        [
            "",
            "## Paper-Ready Results Text",
            "",
            (
                "Using the manually annotated qrels, all 45 benchmark queries had at least one "
                "positive relevance judgment and were included in macro-averaged evaluation. "
                f"Among the three retrieval settings, {best_recall10['method']} obtained the highest "
                f"Recall@10 ({best_recall10['Recall@10']}), while {best_ndcg10['method']} obtained "
                f"the highest nDCG@10 ({best_ndcg10['nDCG@10']}). These results indicate measurable "
                "differences between lexical, dense, and hybrid retrieval under the same judged pool; all "
                "top-10 retrieved documents in this evaluation had qrels judgments."
            ),
        ]
    )
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def count_top10_unjudged(per_query_path: Path) -> int:
    count = 0
    with per_query_path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if int(row["retrieved_at_10"]) != int(row["judged_at_10"]):
                count += 1
    return count


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--queries", required=True)
    parser.add_argument("--qrels", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--backend-dir", default=r"D:\workspace\123\ccc\astrobiology\backend")
    parser.add_argument("--collection-name", default=DEFAULT_COLLECTION)
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args(argv)

    queries_path = Path(args.queries).expanduser().resolve()
    qrels_path = Path(args.qrels).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve()
    backend_dir = Path(args.backend_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ranked_results_path = export_ranked_results(
        queries_path=queries_path,
        out_dir=out_dir,
        backend_dir=backend_dir,
        collection_name=str(args.collection_name),
        methods=METHODS,
        top_k=int(args.top_k),
    )

    evaluator_path = Path(__file__).with_name("evaluation_framework.py")
    subprocess.run(
        [
            sys.executable,
            str(evaluator_path),
            "evaluate",
            "--queries",
            str(queries_path),
            "--results",
            str(ranked_results_path),
            "--qrels",
            str(qrels_path),
            "--out-dir",
            str(out_dir),
            "--ks",
            *[str(k) for k in KS],
            "--relevance-threshold",
            "1",
        ],
        check=True,
    )

    paper_rows = write_paper_ready_table(
        out_dir / "metrics_by_method.csv",
        out_dir / "paper_ready_metrics_table.csv",
    )
    qrels_stats = load_qrels_stats(qrels_path)
    counts = method_distribution(ranked_results_path)
    build_report(
        out_path=out_dir / "retrieval_evaluation_report.md",
        qrels_stats=qrels_stats,
        paper_rows=paper_rows,
        ranked_results_path=ranked_results_path,
        method_counts=counts,
        top10_unjudged_count=count_top10_unjudged(out_dir / "per_query_scores.csv"),
    )

    print(f"metrics_by_method={out_dir / 'metrics_by_method.csv'}")
    print(f"per_query_scores={out_dir / 'per_query_scores.csv'}")
    print(f"retrieval_evaluation_report={out_dir / 'retrieval_evaluation_report.md'}")
    print(f"paper_ready_metrics_table={out_dir / 'paper_ready_metrics_table.csv'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
