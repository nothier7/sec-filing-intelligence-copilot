from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

from pydantic import ValidationError

from sec_copilot.evals.models import EvalQuestion


def load_eval_questions(path: Path) -> list[EvalQuestion]:
    questions: list[EvalQuestion] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            raw_question = json.loads(stripped)
            questions.append(EvalQuestion.model_validate(raw_question))
        except JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc.msg}") from exc
        except ValidationError as exc:
            raise ValueError(f"Invalid eval question at {path}:{line_number}: {exc}") from exc

    if not questions:
        raise ValueError(f"No eval questions found in {path}")
    return questions
