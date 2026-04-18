from __future__ import annotations

import hashlib
import math
import re
from typing import Any, List

from sec_copilot.retrieval.llamaindex_compat import suppress_llamaindex_import_noise

with suppress_llamaindex_import_noise():
    from llama_index.core.bridge.pydantic import Field
    from llama_index.core.embeddings import BaseEmbedding

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-]*")


class HashEmbedding(BaseEmbedding):
    """Deterministic local embedding for tests and offline smoke workflows.

    This is not intended to beat real embedding models. It gives us a stable,
    key-free embedding path so retrieval plumbing can be tested without OpenAI
    credentials or local model downloads.
    """

    dimensions: int = Field(default=128, gt=0)

    @classmethod
    def class_name(cls) -> str:
        return "hash_embedding"

    def _get_query_embedding(self, query: str) -> List[float]:
        return self._embed(query)

    async def _aget_query_embedding(self, query: str) -> List[float]:
        return self._get_query_embedding(query)

    def _get_text_embedding(self, text: str) -> List[float]:
        return self._embed(text)

    async def _aget_text_embedding(self, text: str) -> List[float]:
        return self._get_text_embedding(text)

    def _get_text_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [self._embed(text) for text in texts]

    def _embed(self, text: str) -> List[float]:
        vector = [0.0] * self.dimensions
        for token in TOKEN_PATTERN.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], byteorder="big") % self.dimensions
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def to_dict(self, **kwargs: Any) -> dict[str, Any]:
        return {"class_name": self.class_name(), "dimensions": self.dimensions}
