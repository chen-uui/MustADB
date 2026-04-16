import hashlib
import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings

# Keep stage schema fixed for benchmark compatibility.
STAGE_KEYS = (
    "sparse_search",
    "dense_search",
    "fuse",
    "rerank",
    "context_build",
    "llm_generate",
    "postprocess",
    "db_write",
    "total",
)

CONFIG_KEYS = (
    "retrieval_mode",
    "top_k",
    "rerank_k",
    "hybrid_alpha",
    "context_token_limit",
)

_WRITE_LOCK = threading.Lock()
def _resolve_bench_log_path() -> Path:
    override = os.getenv("BENCH_LOG_PATH", "").strip()
    if override:
        return Path(override).expanduser().resolve()

    try:
        base_dir = Path(settings.BASE_DIR)
        return (base_dir / "logs" / "bench_log.jsonl").resolve()
    except Exception:
        # Fallback for non-Django contexts.
        return (Path.cwd() / "logs" / "bench_log.jsonl").resolve()


_BENCH_LOG_PATH = _resolve_bench_log_path()


def new_run_id() -> str:
    return str(uuid.uuid4())


def question_hash(question: str, prefix_len: int = 12) -> Optional[str]:
    if not question:
        return None
    digest = hashlib.sha256(question.encode("utf-8")).hexdigest()
    return digest[:prefix_len]


def init_stage_ms() -> Dict[str, float]:
    return {k: 0.0 for k in STAGE_KEYS}


def normalize_stage_ms(stage_ms: Optional[Dict[str, Any]]) -> Dict[str, float]:
    normalized = init_stage_ms()
    if not stage_ms:
        return normalized
    for key in STAGE_KEYS:
        value = stage_ms.get(key, 0.0)
        try:
            normalized[key] = float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            normalized[key] = 0.0
    # Preserve additional stage keys for forward compatibility, e.g. extraction benchmarks.
    for key, value in stage_ms.items():
        if key in normalized:
            continue
        try:
            normalized[key] = float(value) if value is not None else 0.0
        except (TypeError, ValueError):
            normalized[key] = 0.0
    return normalized


def normalize_config(config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    normalized = {k: None for k in CONFIG_KEYS}
    if not config:
        return normalized
    for key in CONFIG_KEYS:
        normalized[key] = config.get(key, None)
    return normalized


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_bench_log(
    *,
    run_id: str,
    endpoint: str,
    success: bool,
    error_type: Optional[str],
    config: Optional[Dict[str, Any]],
    stage_ms: Optional[Dict[str, Any]],
    question: str = "",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    payload: Dict[str, Any] = {
        "timestamp_iso": now_iso(),
        "run_id": run_id,
        "endpoint": endpoint,
        "success": bool(success),
        "error_type": error_type if error_type else None,
        "config": normalize_config(config),
        "stage_ms": normalize_stage_ms(stage_ms),
    }

    q_hash = question_hash(question)
    if q_hash:
        payload["question_hash"] = q_hash

    if extra:
        payload.update(extra)

    _BENCH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(payload, ensure_ascii=False)

    with _WRITE_LOCK:
        with _BENCH_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
