"""PDF处理器应用启动时的运行环境配置"""

import io
import os
import sys
from typing import Iterable, Iterator, Optional, TextIO


def configure_runtime() -> None:
    """在Django AppConfig.ready()时调用，配置运行期行为"""
    _silence_external_progress_bars()


def _silence_external_progress_bars() -> None:
    """禁止第三方库（weaviate/tqdm）输出批处理进度条"""
    os.environ.setdefault("TQDM_DISABLE", "1")
    os.environ.setdefault("DISABLE_TQDM", "1")
    os.environ.setdefault("WEAVIATE_PROGRESS_BAR_DISABLE", "true")
    os.environ.setdefault("WEAVIATE_NO_PROGRESS_BAR", "1")
    os.environ.setdefault("WEAVIATE_PROGRESS_BAR", "false")

    try:
        import tqdm  # type: ignore

        class _SilentTqdm:
            def __init__(self, iterable: Optional[Iterable] = None, *args, **kwargs) -> None:
                self._iterable = iterable

            def __iter__(self) -> Iterator:
                if self._iterable is None:
                    return iter(())
                return iter(self._iterable)

            def update(self, *args, **kwargs) -> None:
                return None

            def set_description(self, *args, **kwargs) -> None:
                return None

            def set_postfix(self, *args, **kwargs) -> None:
                return None

            def close(self) -> None:
                return None

            def refresh(self, *args, **kwargs) -> None:
                return None

            def clear(self, *args, **kwargs) -> None:
                return None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

        tqdm.tqdm = _SilentTqdm  # type: ignore

        try:
            import tqdm.auto as tqdm_auto  # type: ignore

            tqdm_auto.tqdm = _SilentTqdm  # type: ignore[attr-defined]
        except Exception:
            pass
    except Exception:
        pass

    _apply_stdout_filter()


class _StdoutFilter(io.TextIOBase):
    """用于过滤包含tqdm批次输出的stdout/stderr包装器"""

    def __init__(self, wrapped: TextIO) -> None:
        self._wrapped = wrapped

    def write(self, data: str) -> int:  # type: ignore[override]
        stripped = data.strip()
        if not stripped:
            return 0

        if "Batches:" in stripped or stripped.startswith("Batches"):
            return 0

        if stripped.endswith("it/s]") and "%|" in stripped:
            return 0

        try:
            return self._wrapped.write(data)
        except UnicodeEncodeError:
            encoding = getattr(self._wrapped, "encoding", None) or "utf-8"
            safe_data = data.encode(encoding, errors="replace").decode(encoding, errors="replace")
            return self._wrapped.write(safe_data)

    def flush(self) -> None:  # type: ignore[override]
        self._wrapped.flush()

    @property
    def encoding(self):  # type: ignore[override]
        return getattr(self._wrapped, "encoding", None)

    def isatty(self) -> bool:  # type: ignore[override]
        return getattr(self._wrapped, "isatty", lambda: False)()


def _apply_stdout_filter() -> None:
    if not isinstance(sys.stdout, _StdoutFilter):
        sys.stdout = _StdoutFilter(sys.stdout)
    if not isinstance(sys.stderr, _StdoutFilter):
        sys.stderr = _StdoutFilter(sys.stderr)

