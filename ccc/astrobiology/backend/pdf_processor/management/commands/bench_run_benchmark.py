import csv
import json
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client

from pdf_processor.bench_logging import STAGE_KEYS, init_stage_ms, question_hash


class Command(BaseCommand):
    help = "Run benchmark batch and export raw.jsonl + summary_by_mode.csv."

    MODES = ("bm25", "dense", "hybrid", "hybrid_rerank")
    ENDPOINT = "/api/pdf/unified/question/"
    ENV_KEYS = (
        "RAG_RETRIEVAL_MODE",
        "RAG_TOP_K",
        "RAG_RERANK_K",
        "RAG_HYBRID_ALPHA",
        "RAG_CONTEXT_TOKEN_LIMIT",
    )
    DEFAULT_RUNTIME_ENV = {
        "RAG_TOP_K": "8",
        "RAG_RERANK_K": "16",
        "RAG_HYBRID_ALPHA": "0.7",
    }

    def add_arguments(self, parser):
        parser.add_argument(
            "--queries",
            type=str,
            default=None,
            help="Path to queries jsonl file. Default: evaluation/queries.jsonl",
        )
        parser.add_argument(
            "--out",
            type=str,
            default=None,
            help="Output directory. Default: runs/<timestamp>/",
        )
        parser.add_argument(
            "--modes",
            nargs="+",
            choices=self.MODES,
            default=None,
            help="Retrieval modes to run. Default: all modes.",
        )
        parser.add_argument(
            "--repeat",
            type=int,
            default=1,
            help="Repeat each qid per mode. Default: 1.",
        )
        parser.add_argument(
            "--warmup",
            type=int,
            default=1,
            help="Warmup runs per mode, not included in summary. Default: 1.",
        )
        parser.add_argument(
            "--summary-scope",
            choices=("all", "qid_median"),
            default="all",
            help="Use all successful repeats or per-qid median for quantiles.",
        )

    def handle(self, *args, **options):
        repeat = int(options["repeat"])
        warmup = int(options["warmup"])
        if repeat < 1:
            raise CommandError("--repeat must be >= 1")
        if warmup < 0:
            raise CommandError("--warmup must be >= 0")

        modes = options.get("modes") or list(self.MODES)
        queries_path = self._resolve_queries_path(options.get("queries"))
        out_dir = self._resolve_out_dir(options.get("out"))
        log_path = self._resolve_log_path()
        summary_scope = options["summary_scope"]

        queries = self._load_queries(queries_path)
        if len(queries) < 20:
            self.stdout.write(
                self.style.WARNING(
                    f"queries count is {len(queries)} (<20). This is allowed but not recommended."
                )
            )

        out_dir.mkdir(parents=True, exist_ok=True)
        raw_path = out_dir / "raw.jsonl"
        summary_path = out_dir / "summary_by_mode.csv"
        raw_path.write_text("", encoding="utf-8")

        self.stdout.write(f"queries_path={queries_path}")
        self.stdout.write(f"bench_log_path={log_path}")
        self.stdout.write(f"modes={','.join(modes)} warmup={warmup} repeat={repeat} summary_scope={summary_scope}")

        client = Client(HTTP_HOST="localhost")
        env_backup = self._backup_env()
        raw_records: List[Dict[str, Any]] = []
        try:
            for mode in modes:
                self._apply_mode_env(mode)
                self.stdout.write(f"[mode] {mode}")

                for warmup_idx in range(warmup):
                    warmup_question = queries[warmup_idx % len(queries)]["question"]
                    warmup_result = self._run_single_request(
                        client=client,
                        question=warmup_question,
                        log_path=log_path,
                    )
                    warmup_state = "OK" if warmup_result["success"] else f"FAIL:{warmup_result['error_type']}"
                    self.stdout.write(
                        f"[warmup] mode={mode} {warmup_idx + 1}/{warmup} {warmup_state}"
                    )

                for query in queries:
                    qid = query["qid"]
                    question = query["question"]
                    for repeat_idx in range(repeat):
                        result = self._run_single_request(
                            client=client,
                            question=question,
                            log_path=log_path,
                        )
                        raw_record = self._build_raw_record(
                            qid=qid,
                            mode=mode,
                            repeat_idx=repeat_idx,
                            result=result,
                        )
                        raw_records.append(raw_record)
                        self._append_jsonl(raw_path, raw_record)

                        state = "OK" if raw_record["success"] else f"FAIL:{raw_record['error_type']}"
                        self.stdout.write(
                            f"[run] mode={mode} qid={qid} repeat={repeat_idx + 1}/{repeat} {state}"
                        )
        finally:
            self._restore_env(env_backup)

        summary_rows = self._build_summary_rows(
            raw_records=raw_records,
            modes=modes,
            summary_scope=summary_scope,
        )
        self._write_summary_csv(summary_path, summary_rows)

        n_total = len(raw_records)
        n_success = sum(1 for item in raw_records if item["success"])
        n_fail = n_total - n_success

        self.stdout.write(f"completed total={n_total} success={n_success} fail={n_fail}")
        self.stdout.write(f"out_dir={out_dir}")
        self.stdout.write(f"raw_path={raw_path}")
        self.stdout.write(f"summary_path={summary_path}")

    def _resolve_queries_path(self, path_arg: Optional[str]) -> Path:
        if path_arg and path_arg.strip():
            return Path(path_arg).expanduser().resolve()
        return (Path(settings.BASE_DIR) / "evaluation" / "queries.jsonl").resolve()

    def _resolve_out_dir(self, path_arg: Optional[str]) -> Path:
        if path_arg and path_arg.strip():
            return Path(path_arg).expanduser().resolve()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return (Path(settings.BASE_DIR) / "runs" / timestamp).resolve()

    def _resolve_log_path(self) -> Path:
        bench_path = os.getenv("BENCH_LOG_PATH", "").strip()
        if bench_path:
            return Path(bench_path).expanduser().resolve()
        return (Path(settings.BASE_DIR) / "logs" / "bench_log.jsonl").resolve()

    def _load_queries(self, path: Path) -> List[Dict[str, str]]:
        if not path.exists():
            raise CommandError(f"queries file not found: {path}")

        items: List[Dict[str, str]] = []
        seen_qids = set()
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            content = line.strip()
            if not content:
                continue
            try:
                data = json.loads(content)
            except json.JSONDecodeError as exc:
                raise CommandError(f"invalid json at {path}:{line_no}: {exc}") from exc

            if not isinstance(data, dict):
                raise CommandError(f"invalid item at {path}:{line_no}: must be object")

            qid = str(data.get("qid", "")).strip()
            question = str(data.get("question", "")).strip()
            if not qid:
                raise CommandError(f"invalid item at {path}:{line_no}: qid is required")
            if not question:
                raise CommandError(f"invalid item at {path}:{line_no}: question is required")
            if qid in seen_qids:
                raise CommandError(f"duplicate qid at {path}:{line_no}: {qid}")
            seen_qids.add(qid)
            items.append({"qid": qid, "question": question})

        if not items:
            raise CommandError(f"queries file has no valid rows: {path}")
        return items

    def _backup_env(self) -> Dict[str, Optional[str]]:
        return {key: os.environ.get(key) for key in self.ENV_KEYS}

    def _restore_env(self, backup: Dict[str, Optional[str]]) -> None:
        for key, value in backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _apply_mode_env(self, mode: str) -> None:
        os.environ["RAG_RETRIEVAL_MODE"] = mode
        for key, value in self.DEFAULT_RUNTIME_ENV.items():
            os.environ[key] = value
        os.environ.pop("RAG_CONTEXT_TOKEN_LIMIT", None)

    def _read_log_state(self, log_path: Path) -> Tuple[int, Optional[str]]:
        if not log_path.exists():
            return 0, None
        lines = [line.strip() for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not lines:
            return 0, None
        return len(lines), lines[-1]

    def _run_single_request(self, client: Client, question: str, log_path: Path) -> Dict[str, Any]:
        before_count, _ = self._read_log_state(log_path)

        status_code = None
        try:
            response = client.post(
                self.ENDPOINT,
                data=json.dumps({"question": question}),
                content_type="application/json",
            )
            status_code = int(response.status_code)
        except Exception as exc:
            return {
                "success": False,
                "error_type": f"CLIENT_POST_ERROR:{type(exc).__name__}",
                "stage_ms": init_stage_ms(),
                "status_code": status_code,
            }

        after_count, latest_line = self._read_log_state(log_path)
        if after_count <= before_count or not latest_line:
            return {
                "success": False,
                "error_type": "BENCH_LOG_NOT_APPENDED",
                "stage_ms": init_stage_ms(),
                "status_code": status_code,
            }

        try:
            log_item = json.loads(latest_line)
        except json.JSONDecodeError:
            return {
                "success": False,
                "error_type": "BENCH_LOG_INVALID_JSON",
                "stage_ms": init_stage_ms(),
                "status_code": status_code,
            }

        stage_ms = self._normalize_stage_ms(log_item.get("stage_ms"))
        success = bool(log_item.get("success"))
        error_type = log_item.get("error_type")

        checks: List[str] = []
        if after_count != before_count + 1:
            checks.append(f"LOG_DELTA_{after_count - before_count}")
        if log_item.get("endpoint") != "qa_ask":
            checks.append("ENDPOINT_MISMATCH")
        if log_item.get("question_hash") != question_hash(question):
            checks.append("QUESTION_HASH_MISMATCH")

        if checks:
            check_error = "LOG_VALIDATION_FAILED:" + ",".join(checks)
            error_type = f"{error_type};{check_error}" if error_type else check_error
            success = False

        return {
            "success": success,
            "error_type": error_type,
            "stage_ms": stage_ms,
            "status_code": status_code,
        }

    def _normalize_stage_ms(self, stage_ms: Any) -> Dict[str, float]:
        normalized = init_stage_ms()
        if not isinstance(stage_ms, dict):
            return normalized
        for key in STAGE_KEYS:
            try:
                normalized[key] = float(stage_ms.get(key, 0.0) or 0.0)
            except (TypeError, ValueError):
                normalized[key] = 0.0
        return normalized

    def _build_raw_record(
        self,
        *,
        qid: str,
        mode: str,
        repeat_idx: int,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        stage_ms = self._normalize_stage_ms(result.get("stage_ms"))
        retrieval_ms = (
            stage_ms["sparse_search"]
            + stage_ms["dense_search"]
            + stage_ms["fuse"]
            + stage_ms["rerank"]
        )
        return {
            "qid": qid,
            "mode": mode,
            "repeat_idx": int(repeat_idx),
            "success": bool(result.get("success")),
            "error_type": result.get("error_type"),
            "stage_ms": stage_ms,
            "total_ms": stage_ms["total"],
            "retrieval_ms": retrieval_ms,
            "llm_generate_ms": stage_ms["llm_generate"],
        }

    def _append_jsonl(self, path: Path, payload: Dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def _build_summary_rows(
        self,
        *,
        raw_records: List[Dict[str, Any]],
        modes: List[str],
        summary_scope: str,
    ) -> List[Dict[str, Any]]:
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in raw_records:
            grouped[item["mode"]].append(item)

        rows: List[Dict[str, Any]] = []
        for mode in modes:
            mode_records = grouped.get(mode, [])
            n_total = len(mode_records)
            n_success = sum(1 for item in mode_records if item["success"])
            n_fail = n_total - n_success

            success_records = self._select_success_records(mode_records, summary_scope)
            total_values = [float(item["total_ms"]) for item in success_records]
            retrieval_values = [float(item["retrieval_ms"]) for item in success_records]
            llm_values = [float(item["llm_generate_ms"]) for item in success_records]
            context_values = [float(item["stage_ms"]["context_build"]) for item in success_records]

            rows.append(
                {
                    "mode": mode,
                    "n_total": n_total,
                    "n_success": n_success,
                    "n_fail": n_fail,
                    "total_ms_p50": self._fmt(self._percentile(total_values, 50)),
                    "total_ms_p95": self._fmt(self._percentile(total_values, 95)),
                    "total_ms_max": self._fmt(max(total_values) if total_values else None),
                    "retrieval_ms_p50": self._fmt(self._percentile(retrieval_values, 50)),
                    "retrieval_ms_p95": self._fmt(self._percentile(retrieval_values, 95)),
                    "llm_generate_ms_p50": self._fmt(self._percentile(llm_values, 50)),
                    "llm_generate_ms_p95": self._fmt(self._percentile(llm_values, 95)),
                    "context_build_ms_p50": self._fmt(self._percentile(context_values, 50)),
                    "context_build_ms_p95": self._fmt(self._percentile(context_values, 95)),
                }
            )
        return rows

    def _select_success_records(
        self, mode_records: List[Dict[str, Any]], summary_scope: str
    ) -> List[Dict[str, Any]]:
        success_records = [item for item in mode_records if item["success"]]
        if summary_scope != "qid_median":
            return success_records

        by_qid: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for item in success_records:
            by_qid[item["qid"]].append(item)

        reduced: List[Dict[str, Any]] = []
        for qid, records in by_qid.items():
            total_vals = [float(item["total_ms"]) for item in records]
            retrieval_vals = [float(item["retrieval_ms"]) for item in records]
            llm_vals = [float(item["llm_generate_ms"]) for item in records]
            context_vals = [float(item["stage_ms"]["context_build"]) for item in records]

            reduced.append(
                {
                    "qid": qid,
                    "success": True,
                    "stage_ms": {"context_build": float(np.median(np.asarray(context_vals, dtype=float)))},
                    "total_ms": float(np.median(np.asarray(total_vals, dtype=float))),
                    "retrieval_ms": float(np.median(np.asarray(retrieval_vals, dtype=float))),
                    "llm_generate_ms": float(np.median(np.asarray(llm_vals, dtype=float))),
                }
            )
        return reduced

    def _percentile(self, values: List[float], q: float) -> Optional[float]:
        if not values:
            return None
        array = np.asarray(values, dtype=float)
        return float(np.percentile(array, q, method="linear"))

    def _fmt(self, value: Optional[float]) -> str:
        if value is None:
            return ""
        return f"{value:.3f}"

    def _write_summary_csv(self, summary_path: Path, rows: List[Dict[str, Any]]) -> None:
        fieldnames = [
            "mode",
            "n_total",
            "n_success",
            "n_fail",
            "total_ms_p50",
            "total_ms_p95",
            "total_ms_max",
            "retrieval_ms_p50",
            "retrieval_ms_p95",
            "llm_generate_ms_p50",
            "llm_generate_ms_p95",
            "context_build_ms_p50",
            "context_build_ms_p95",
        ]
        with summary_path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
