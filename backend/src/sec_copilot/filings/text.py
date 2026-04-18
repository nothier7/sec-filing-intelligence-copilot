from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser


BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "br",
    "div",
    "dl",
    "dt",
    "dd",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "tfoot",
    "th",
    "thead",
    "tr",
    "ul",
}

IGNORED_TAGS = {"script", "style", "noscript"}


class FilingTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in IGNORED_TAGS and self._ignored_depth:
            self._ignored_depth -= 1
            return
        if tag in BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        text = unescape(data)
        if text.strip():
            self._parts.append(text)

    def text(self) -> str:
        return normalize_extracted_text("".join(self._parts))


def extract_text(document: str) -> str:
    if _looks_like_html(document):
        parser = FilingTextExtractor()
        parser.feed(document)
        parser.close()
        return parser.text()
    return normalize_extracted_text(document)


def normalize_extracted_text(text: str) -> str:
    text = unescape(text).replace("\xa0", " ")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t\f\v]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _looks_like_html(document: str) -> bool:
    sample = document[:500].lower()
    return "<html" in sample or "<body" in sample or "</" in sample

