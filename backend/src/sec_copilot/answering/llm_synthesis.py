from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional

import httpx

from sec_copilot.answering.models import (
    AskResponse,
    NumericGrounding,
    NumericGroundingStatus,
    QueryType,
    SynthesisStatus,
)
from sec_copilot.config import Settings, get_settings


@dataclass(frozen=True)
class LlmSynthesisResult:
    status: SynthesisStatus
    answer: Optional[str] = None
    reason: Optional[str] = None
    model: Optional[str] = None


class LlmSynthesisService:
    def __init__(self, settings: Optional[Settings] = None) -> None:
        self.settings = settings or get_settings()
        self.model = self.settings.openai_synthesis_model

    def synthesize(self, response: AskResponse) -> LlmSynthesisResult:
        if not self.settings.openai_api_key:
            return LlmSynthesisResult(
                status=SynthesisStatus.UNAVAILABLE,
                reason="missing_openai_api_key",
            )
        preflight_reason = self._preflight_reason(response)
        if preflight_reason is not None:
            return LlmSynthesisResult(
                status=SynthesisStatus.FALLBACK,
                reason=preflight_reason,
            )

        try:
            raw_response = self._request_completion(response)
        except (httpx.HTTPError, ValueError):
            return LlmSynthesisResult(
                status=SynthesisStatus.FALLBACK,
                reason="openai_request_failed",
                model=self.model,
            )

        answer = _extract_response_text(raw_response)
        validation_reason = self._validate_answer(answer, response)
        if validation_reason is not None:
            return LlmSynthesisResult(
                status=SynthesisStatus.FALLBACK,
                reason=validation_reason,
                model=self.model,
            )
        return LlmSynthesisResult(
            status=SynthesisStatus.SUCCEEDED,
            answer=answer,
            model=self.model,
        )

    def _request_completion(self, response: AskResponse) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "instructions": _instructions(),
            "input": _prompt_for(response),
            "max_output_tokens": self.settings.openai_synthesis_max_output_tokens,
            "store": False,
        }
        if _supports_reasoning(self.model) and self.settings.openai_synthesis_reasoning_effort:
            payload["reasoning"] = {
                "effort": self.settings.openai_synthesis_reasoning_effort,
            }

        with httpx.Client(timeout=self.settings.openai_synthesis_timeout_seconds) as client:
            api_response = client.post(
                f"{self.settings.openai_base_url.rstrip('/')}/responses",
                headers={
                    "Authorization": f"Bearer {self.settings.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            api_response.raise_for_status()
            return api_response.json()

    def _preflight_reason(self, response: AskResponse) -> Optional[str]:
        if not response.supported or response.query_type == QueryType.UNSUPPORTED:
            return "unsupported_or_insufficient_evidence"
        if not response.citations:
            return "no_citations"
        if response.query_type == QueryType.NUMERIC and not _validated_numeric_grounding(
            response.numeric_grounding
        ):
            return "numeric_grounding_not_validated"
        return None

    def _validate_answer(self, answer: str, response: AskResponse) -> Optional[str]:
        if not answer.strip():
            return "empty_llm_answer"
        if _contains_investment_advice_language(answer):
            return "investment_advice_language"
        if _references_unknown_citations(answer, response):
            return "unknown_citation_reference"
        if response.query_type == QueryType.NUMERIC:
            return _numeric_validation_reason(answer, response.numeric_grounding)
        return None


def _instructions() -> str:
    return (
        "You polish deterministic SEC filing answers. Use only the supplied "
        "deterministic answer, citation snippets, and numeric facts. Keep support status, "
        "citations, exact numeric values, units, periods, and XBRL concepts unchanged. "
        "Do not add investment advice, forecasts, ratings, price targets, citation IDs, "
        "or source URLs. Return only a concise answer in plain English."
    )


def _prompt_for(response: AskResponse) -> str:
    lines = [
        f"Question: {response.question}",
        "",
        "Deterministic answer:",
        response.answer,
        "",
        "Citation snippets:",
    ]
    for index, citation in enumerate(response.citations, start=1):
        section = citation.section_name or citation.section_type or "unknown section"
        lines.extend(
            [
                f"{index}. chunk_id: {citation.chunk_id}",
                f"   section: {section}",
                f"   source_url: {citation.source_url or 'not provided'}",
                f"   snippet: {_clip(citation.snippet, max_chars=900)}",
            ]
        )

    if response.numeric_grounding:
        lines.extend(["", "Numeric grounding:"])
        for fact in response.numeric_grounding:
            lines.append(_numeric_grounding_line(fact))

    return "\n".join(lines).strip()


def _numeric_grounding_line(fact: NumericGrounding) -> str:
    period_parts = []
    if fact.fiscal_period:
        period_parts.append(fact.fiscal_period)
    if fact.fiscal_quarter is not None:
        period_parts.append(f"Q{fact.fiscal_quarter}")
    if fact.fiscal_year is not None:
        period_parts.append(str(fact.fiscal_year))
    period = " ".join(period_parts) or "unknown period"
    status = fact.status.value if isinstance(fact.status, NumericGroundingStatus) else fact.status
    return (
        "- "
        f"status={status}; "
        f"metric={fact.metric_label or fact.metric or 'unknown'}; "
        f"concept={fact.concept or 'unknown'}; "
        f"value={fact.value or 'unknown'}; "
        f"unit={fact.unit or 'unknown'}; "
        f"period={period}; "
        f"accession={fact.accession_number or 'unknown'}"
    )


def _validated_numeric_grounding(facts: list[NumericGrounding]) -> bool:
    return any(fact.status == NumericGroundingStatus.VALIDATED and fact.value for fact in facts)


def _numeric_validation_reason(answer: str, facts: list[NumericGrounding]) -> Optional[str]:
    validated_facts = [
        fact
        for fact in facts
        if fact.status == NumericGroundingStatus.VALIDATED and fact.value
    ]
    if not validated_facts:
        return "numeric_grounding_not_validated"
    normalized = answer.casefold()
    answer_digits = _digits(answer)
    years = set(re.findall(r"\b20\d{2}\b", answer))

    for fact in validated_facts:
        if _digits(fact.value or "") not in answer_digits:
            return "numeric_value_changed_or_omitted"
        if fact.unit and not _answer_contains_unit(normalized, answer, fact.unit):
            return "numeric_unit_changed_or_omitted"
        if fact.fiscal_year is not None:
            expected_year = str(fact.fiscal_year)
            if expected_year not in years:
                return "numeric_period_changed_or_omitted"
            if any(year != expected_year for year in years):
                return "numeric_period_changed_or_omitted"
        if fact.fiscal_quarter is not None and not _answer_contains_quarter(
            normalized, fact.fiscal_quarter
        ):
            return "numeric_period_changed_or_omitted"
        if fact.fiscal_period and not _answer_contains_period(normalized, fact.fiscal_period):
            return "numeric_period_changed_or_omitted"
    return None


def _answer_contains_unit(normalized_answer: str, raw_answer: str, unit: str) -> bool:
    normalized_unit = unit.casefold()
    if normalized_unit == "usd":
        return "usd" in normalized_answer or "$" in raw_answer or "dollar" in normalized_answer
    return normalized_unit in normalized_answer


def _answer_contains_quarter(normalized_answer: str, quarter: int) -> bool:
    return (
        f"q{quarter}" in normalized_answer
        or f"quarter {quarter}" in normalized_answer
        or f"{quarter}q" in normalized_answer
    )


def _answer_contains_period(normalized_answer: str, period: str) -> bool:
    normalized_period = period.casefold()
    if normalized_period == "fy":
        return (
            "fy" in normalized_answer
            or "fiscal year" in normalized_answer
            or "fiscal " in normalized_answer
        )
    if normalized_period.startswith("q") and normalized_period[1:].isdigit():
        return _answer_contains_quarter(normalized_answer, int(normalized_period[1:]))
    return normalized_period in normalized_answer


def _contains_investment_advice_language(answer: str) -> bool:
    normalized = answer.casefold()
    advice_markers = (
        "you should buy",
        "you should sell",
        "i recommend buying",
        "i recommend selling",
        "buy rating",
        "sell rating",
        "hold rating",
        "price target",
        "investment advice",
        "outperform rating",
        "underperform rating",
    )
    return any(marker in normalized for marker in advice_markers)


def _references_unknown_citations(answer: str, response: AskResponse) -> bool:
    allowed_ids = {citation.chunk_id for citation in response.citations}
    referenced_ids = set(_CHUNK_ID_RE.findall(answer))
    if referenced_ids - allowed_ids:
        return True

    allowed_urls = {citation.source_url for citation in response.citations if citation.source_url}
    referenced_urls = {_strip_url_punctuation(url) for url in _URL_RE.findall(answer)}
    return bool(referenced_urls - allowed_urls)


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


def _digits(value: str) -> str:
    return "".join(character for character in value if character.isdigit())


def _strip_url_punctuation(value: str) -> str:
    return value.rstrip(".,;:)]}")


def _clip(value: str, max_chars: int) -> str:
    text = " ".join(value.split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


_CHUNK_ID_RE = re.compile(r"\b\d{10}-\d{2}-\d{6}:s\d{4}:c\d{4}\b")
_URL_RE = re.compile(r"https?://[^\s)\]]+")
