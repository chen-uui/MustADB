import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.test import Client


class Command(BaseCommand):
    help = "Smoke test for benchmark logging across retrieval modes."

    MODES = ("bm25", "dense", "hybrid", "hybrid_rerank")

    def add_arguments(self, parser):
        parser.add_argument(
            "--mode",
            choices=self.MODES,
            help="Run smoke test for one retrieval mode.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Run smoke test for all retrieval modes.",
        )

    def handle(self, *args, **options):
        run_all = bool(options.get("all"))
        mode = options.get("mode")

        if run_all and mode:
            raise CommandError("Use either --mode or --all, not both.")

        if run_all:
            modes = list(self.MODES)
        else:
            modes = [mode or "hybrid_rerank"]

        log_path = self._resolve_log_path()
        failures: List[str] = []

        for item in modes:
            ok, detail = self._run_single_mode(item, log_path)
            if ok:
                self.stdout.write(f"[{item}] OK")
            else:
                self.stdout.write(f"[{item}] FAIL: {detail}")
                failures.append(f"{item}: {detail}")

        if run_all:
            passed = len(modes) - len(failures)
            self.stdout.write(f"SUMMARY: {passed}/{len(modes)} passed")

        if failures:
            raise CommandError(" | ".join(failures))

        self.stdout.write("OK")
        self.stdout.write(f"log_path={log_path}")

    def _resolve_log_path(self) -> Path:
        bench_path = os.getenv("BENCH_LOG_PATH", "").strip()
        if bench_path:
            return Path(bench_path).expanduser().resolve()
        return (Path(settings.BASE_DIR) / "logs" / "bench_log.jsonl").resolve()

    def _read_non_empty_lines(self, log_path: Path) -> List[str]:
        if not log_path.exists():
            return []
        return [line.strip() for line in log_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _run_single_mode(self, mode: str, log_path: Path) -> Tuple[bool, str]:
        client = Client(HTTP_HOST="localhost")
        payload = {"question": "meteorite organic compounds benchmark"}

        before_lines = self._read_non_empty_lines(log_path)
        before_count = len(before_lines)

        env_keys = [
            "RAG_RETRIEVAL_MODE",
            "RAG_TOP_K",
            "RAG_RERANK_K",
            "RAG_HYBRID_ALPHA",
            "RAG_CONTEXT_TOKEN_LIMIT",
        ]
        previous: Dict[str, Optional[str]] = {k: os.environ.get(k) for k in env_keys}

        try:
            os.environ["RAG_RETRIEVAL_MODE"] = mode
            os.environ["RAG_TOP_K"] = "8"
            os.environ["RAG_RERANK_K"] = "16"
            os.environ["RAG_HYBRID_ALPHA"] = "0.7"
            os.environ.pop("RAG_CONTEXT_TOKEN_LIMIT", None)

            response = client.post(
                "/api/pdf/unified/question/",
                data=json.dumps(payload),
                content_type="application/json",
            )
            self.stdout.write(f"[{mode}] POST /api/pdf/unified/question/ => {response.status_code}")

            after_lines = self._read_non_empty_lines(log_path)
            after_count = len(after_lines)
            if after_count != before_count + 1:
                return False, f"log lines expected +1, got before={before_count} after={after_count}"

            try:
                last = json.loads(after_lines[-1])
            except json.JSONDecodeError as exc:
                return False, f"last log json decode error: {exc}"

            required_fields = [
                "timestamp_iso",
                "run_id",
                "endpoint",
                "success",
                "error_type",
                "config",
                "stage_ms",
                "question_hash",
            ]
            missing_fields = [k for k in required_fields if k not in last]
            if missing_fields:
                return False, f"missing fields: {missing_fields}"

            if last.get("endpoint") != "qa_ask":
                return False, f"endpoint expected qa_ask, got {last.get('endpoint')}"

            config = last.get("config") if isinstance(last.get("config"), dict) else {}
            retrieval_mode = config.get("retrieval_mode")
            if retrieval_mode != mode:
                return False, f"retrieval_mode expected {mode}, got {retrieval_mode}"

            stage_ms = last.get("stage_ms") if isinstance(last.get("stage_ms"), dict) else {}
            stage_keys = [
                "sparse_search",
                "dense_search",
                "fuse",
                "rerank",
                "context_build",
                "llm_generate",
                "postprocess",
                "db_write",
                "total",
            ]
            missing_stage_keys = [k for k in stage_keys if k not in stage_ms]
            if missing_stage_keys:
                return False, f"missing stage keys: {missing_stage_keys}"

            rerank_value = stage_ms.get("rerank")
            try:
                rerank_ms = float(rerank_value) if rerank_value is not None else 0.0
            except (TypeError, ValueError):
                rerank_ms = 0.0

            if mode in ("bm25", "dense", "hybrid"):
                if rerank_ms != 0.0:
                    return False, f"rerank must be 0 for mode={mode}, got {rerank_ms}"
            else:
                total_contexts = 0
                try:
                    body = response.json()
                    total_contexts = int(body.get("data", {}).get("total_contexts", 0))
                except Exception:
                    total_contexts = 0
                if total_contexts > 0 and rerank_ms <= 0.0:
                    return False, f"rerank must be >0 for hybrid_rerank with contexts>0, got {rerank_ms}"

            return True, "ok"
        finally:
            for key, value in previous.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
