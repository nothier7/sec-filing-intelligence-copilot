"""Evaluation harness for SEC filing RAG workflows."""

from sec_copilot.evals.dataset import load_eval_questions
from sec_copilot.evals.models import (
    EvalExpected,
    EvalPrediction,
    EvalQuestion,
    EvalQuestionResult,
    EvalRunResult,
    EvalVariant,
)
from sec_copilot.evals.report import format_eval_report
from sec_copilot.evals.runner import EvaluationRunner, parse_variants

__all__ = [
    "EvalExpected",
    "EvalPrediction",
    "EvalQuestion",
    "EvalQuestionResult",
    "EvalRunResult",
    "EvalVariant",
    "EvaluationRunner",
    "format_eval_report",
    "load_eval_questions",
    "parse_variants",
]
