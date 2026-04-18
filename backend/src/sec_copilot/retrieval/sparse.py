from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import List, Tuple

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-]*")
DEFAULT_SPARSE_DIMENSIONS = 32768


def hash_sparse_vectors(
    texts: List[str],
    dimensions: int = DEFAULT_SPARSE_DIMENSIONS,
) -> Tuple[List[List[int]], List[List[float]]]:
    indices: List[List[int]] = []
    values: List[List[float]] = []

    for text in texts:
        token_counts: Counter[int] = Counter()
        for token in TOKEN_PATTERN.findall(text.lower()):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            token_counts[int.from_bytes(digest[:4], byteorder="big") % dimensions] += 1

        norm = math.sqrt(sum(count * count for count in token_counts.values()))
        if norm == 0:
            indices.append([])
            values.append([])
            continue

        sorted_indices = sorted(token_counts)
        indices.append(sorted_indices)
        values.append([token_counts[index] / norm for index in sorted_indices])

    return indices, values
