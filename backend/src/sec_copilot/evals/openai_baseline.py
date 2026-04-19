from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Optional

import httpx

from sec_copilot.answering import Citation
from sec_copilot.answering.classifier import classify_query
from sec_copilot.answering.models import QueryType
from sec_copilot.config import Settings
from sec_copilot.evals.models import EvalPrediction, EvalQuestion, EvalVariant


@dataclass(frozen=True)
class OpenAIContextExcerpt:
    citation: Citation
    text: str


@dataclass(frozen=True)
class OpenAIEvalRequest:
    question: EvalQuestion
    variant: EvalVariant
    context_excerpts: tuple[OpenAIContextExcerpt, ...] = ()


class OpenAIEvalClient:
    def __init__(
        self,
        settings: Settings,
        model: Optional[str] = None,
        refresh_cache: bool = False,
    ) -> None:
        self.settings = settings
        self.model = model or settings.openai_eval_model
        self.refresh_cache = refresh_cache
        self.cache_dir = Path(settings.openai_eval_cache_dir)

    def predict(self, request: OpenAIEvalRequest) -> EvalPrediction:
        started_at = perf_counter()
        try:
            answer, metadata = self._answer(request)
            supported = not _looks_like_refusal(answer)
            query_type = classify_query(request.question.question)
            insufficient_reason = _insufficient_reason(answer, query_type)
            return EvalPrediction(
                question_id=request.question.id,
                variant=request.variant,
                supported=supported,
                answer=answer,
                citations=[excerpt.citation for excerpt in request.context_excerpts],
                retrieval_count=len(request.context_excerpts),
                insufficient_evidence_reason=insufficient_reason,
                latency_ms=_elapsed_ms(started_at),
                metadata=metadata,
            )
        except Exception as exc:  # noqa: BLE001 - eval baselines should fail per row.
            return EvalPrediction(
                question_id=request.question.id,
                variant=request.variant,
                supported=False,
                answer="OpenAI baseline failed to produce an answer.",
                citations=[excerpt.citation for excerpt in request.context_excerpts],
                retrieval_count=len(request.context_excerpts),
                insufficient_evidence_reason="openai_eval_error",
                latency_ms=_elapsed_ms(started_at),
                error=str(exc),
                metadata={"model": self.model},
            )

    def _answer(self, request: OpenAIEvalRequest) -> tuple[str, dict[str, Any]]:
        prompt = _prompt_for(
            request,
            max_context_chars=self.settings.openai_eval_context_chars,
        )
        cache_path = self._cache_path(request=request, prompt=prompt)
        if cache_path.exists() and not self.refresh_cache:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            metadata = dict(cached.get("metadata") or {})
            metadata["cache_hit"] = True
            return str(cached["answer"]), metadata

        if not self.settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI eval variants")

        instructions = _instructions_for(request.variant)
        payload = {
            "model": self.model,
            "instructions": instructions,
            "input": prompt,
            "max_output_tokens": self.settings.openai_eval_max_output_tokens,
            "store": False,
        }
        if _supports_reasoning(self.model) and self.settings.openai_eval_reasoning_effort:
            payload["reasoning"] = {
                "effort": self.settings.openai_eval_reasoning_effort,
            }
        with httpx.Client(timeout=60.0) as client:
            response = client.post(
                f"{self.settings.openai_base_url.rstrip('/')}/responses",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
            raw_response = response.json()

        answer = _extract_response_text(raw_response)
        metadata = {
            "model": self.model,
            "cache_hit": False,
            "response_id": raw_response.get("id"),
            "usage": raw_response.get("usage") or {},
        }
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps({"answer": answer, "metadata": metadata}, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return answer, metadata

    def _cache_path(self, request: OpenAIEvalRequest, prompt: str) -> Path:
        digest = hashlib.sha256(
            json.dumps(
                {
                    "variant": request.variant.value,
                    "model": self.model,
                    "max_output_tokens": self.settings.openai_eval_max_output_tokens,
                    "reasoning_effort": self.settings.openai_eval_reasoning_effort,
                    "context_chars": self.settings.openai_eval_context_chars,
                    "instructions": _instructions_for(request.variant),
                    "question_id": request.question.id,
                    "question": request.question.question,
                    "prompt": prompt,
                },
                sort_keys=True,
            ).encode("utf-8")
        ).hexdigest()[:24]
        filename = f"{request.variant.value}-{request.question.id}-{digest}.json"
        return self.cache_dir / filename


def _instructions_for(variant: EvalVariant) -> str:
    base = (
        "You are an SEC filing benchmark baseline. Answer the user's question directly. "
        "If the prompt truly does not contain enough evidence to answer confidently, say exactly: "
        "\"I do not have enough filing evidence to answer that confidently.\" "
        "Do not give investment advice, forecasts, or price targets."
    )
    if variant == EvalVariant.OPENAI_RETRIEVED_CONTEXT:
        return (
            f"{base} Use only the provided filing excerpts. Treat the excerpts as authoritative "
            "SEC filing evidence for the accession named in the prompt; do not require the "
            "accession number to appear inside the excerpt text. For descriptive questions, one "
            "relevant excerpt is enough evidence. For numeric questions, flattened table rows are "
            "valid evidence, and dollar amounts are commonly in millions when the excerpt says so. "
            "If the excerpts conflict or do not support the answer, use the insufficient-evidence "
            "sentence."
        )
    return base


def _prompt_for(request: OpenAIEvalRequest, max_context_chars: int) -> str:
    question = request.question
    lines = [
        f"Question: {question.question}",
        f"Accession number: {question.accession_number}",
    ]
    if question.form_type:
        lines.append(f"Form type: {question.form_type}")
    if question.fiscal_year:
        period = f"FY {question.fiscal_year}"
        if question.fiscal_quarter:
            period = f"Q{question.fiscal_quarter} {question.fiscal_year}"
        lines.append(f"Period: {period}")

    if request.variant == EvalVariant.OPENAI_RETRIEVED_CONTEXT:
        lines.append("")
        lines.append("Filing excerpts:")
        if not request.context_excerpts:
            lines.append("No filing excerpts were retrieved.")
        for index, excerpt in enumerate(request.context_excerpts, start=1):
            citation = excerpt.citation
            section = citation.section_name or citation.section_type or "unknown section"
            lines.append(f"[{index}] {citation.chunk_id} / {section}")
            lines.append(_clip(excerpt.text, max_chars=max_context_chars))
            lines.append("")

    return "\n".join(lines).strip()


def _extract_response_text(raw_response: dict[str, Any]) -> str:
    output_text = raw_response.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    text_parts: list[str] = []
    for item in raw_response.get("output") or []:
        if item.get("type") != "message":
            continue
        for content in item.get("content") or []:
            if content.get("type") in {"output_text", "text"} and content.get("text"):
                text_parts.append(str(content["text"]))
    return " ".join(part.strip() for part in text_parts if part.strip()).strip()


def _supports_reasoning(model: str) -> bool:
    return model.startswith(("gpt-5", "o1", "o3", "o4"))


def _clip(value: str, max_chars: int) -> str:
    text = " ".join(value.split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def _looks_like_refusal(answer: str) -> bool:
    normalized = answer.casefold()
    refusal_markers = (
        "do not have enough filing evidence",
        "cannot answer",
        "can't answer",
        "not enough information",
        "insufficient information",
        "cannot provide investment advice",
        "can't provide investment advice",
        "not investment advice",
    )
    return any(marker in normalized for marker in refusal_markers)


def _insufficient_reason(answer: str, query_type: QueryType) -> Optional[str]:
    if not _looks_like_refusal(answer):
        return None
    if query_type == QueryType.UNSUPPORTED:
        return "unsupported_query_type"
    return "openai_insufficient_evidence"


def _elapsed_ms(started_at: float) -> float:
    return (perf_counter() - started_at) * 1000.0
