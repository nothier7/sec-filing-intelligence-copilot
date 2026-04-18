from __future__ import annotations

import io
from collections.abc import Iterator
from contextlib import contextmanager, redirect_stderr
from typing import Any


@contextmanager
def suppress_llamaindex_import_noise() -> Iterator[None]:
    """Keep LlamaIndex import-time NLTK bootstrapping from writing to stderr."""

    try:
        import nltk
    except ImportError:
        yield
        return

    original_download = nltk.download

    def quiet_download(*args: Any, **kwargs: Any) -> bool:
        return False

    nltk.download = quiet_download
    try:
        with redirect_stderr(io.StringIO()):
            yield
    finally:
        nltk.download = original_download
