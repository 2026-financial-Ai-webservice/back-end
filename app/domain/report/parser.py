from __future__ import annotations

import io
import re
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

from bs4 import BeautifulSoup, NavigableString, Tag

from app.domain.report.dart_client import DartReportError


@dataclass(frozen=True)
class ParsedChunk:
    major_section: str | None
    minor_section: str | None
    chunk_order: int
    content: str


class TokenEncoder(Protocol):
    def encode(self, text: str) -> list[int]: ...

    def decode(self, tokens: list[int]) -> str: ...


_MAJOR_HEADING = re.compile(r"^([IVX]+)\s*[.]\s*(.+)$", re.IGNORECASE)
_MINOR_HEADING = re.compile(r"^(\d+)\s*[.]\s*(.+)$")
_STANDARD_MAJOR_TITLES = {
    "회사의개요": "I. 회사의 개요",
    "사업의내용": "II. 사업의 내용",
    "재무에관한사항": "III. 재무에 관한 사항",
    "이사의경영진단및분석의견": "IV. 이사의 경영진단 및 분석의견",
    "감사인의감사의견등": "V. 감사인의 감사의견 등",
    "이사회등회사의기관에관한사항": "VI. 이사회 등 회사의 기관에 관한 사항",
    "주주에관한사항": "VII. 주주에 관한 사항",
    "임원및직원등에관한사항": "VIII. 임원 및 직원 등에 관한 사항",
    "계열회사등에관한사항": "IX. 계열회사 등에 관한 사항",
    "대주주등과의거래내용": "X. 대주주 등과의 거래내용",
    "그밖에투자자보호를위하여필요한사항": "XI. 그 밖에 투자자 보호를 위하여 필요한 사항",
}

_EXCLUDED_TAGS = (
    "table", "figure", "img", "svg", "canvas", "object", "embed", "iframe", "graph"
)


def _clean_text(value: str) -> str:
    value = value.replace("\xa0", " ").replace("\u200b", "")
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r" *\n *", "\n", value)
    return re.sub(r"\n{3,}", "\n\n", value).strip()


def extract_document(zip_bytes: bytes) -> bytes:
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        candidates = [
            item
            for item in archive.infolist()
            if not item.is_dir() and item.filename.lower().endswith((".xml", ".html", ".htm"))
        ]
        if not candidates:
            raise DartReportError("원문 ZIP에 XML/HTML 문서가 없습니다.")
        return archive.read(max(candidates, key=lambda item: item.file_size))


def _title(section: Tag) -> str | None:
    title = section.find(
        lambda tag: isinstance(tag, Tag) and tag.name.lower() == "title",
        recursive=False,
    )
    return _clean_text(title.get_text(" ")) if title else None


def _standardize_major(title: str | None) -> str | None:
    if not title:
        return None
    title = _clean_text(title)
    match = _MAJOR_HEADING.match(title)
    if not match:
        return title
    roman, label = match.groups()
    key = re.sub(r"[^0-9A-Za-z가-힣]", "", label)
    return _STANDARD_MAJOR_TITLES.get(key, f"{roman.upper()}. {label.strip()}")


def _standardize_minor(title: str | None) -> str | None:
    if not title:
        return None
    title = _clean_text(title)
    match = _MINOR_HEADING.match(title)
    return f"{match.group(1)}. {match.group(2).strip()}" if match else title


def _remove_non_text_content(soup: BeautifulSoup) -> None:
    """표/그래프 자체만 제거하고 그 앞뒤 설명 텍스트는 보존한다."""
    for tag in soup.find_all(
        lambda element: (
            isinstance(element, Tag)
            and element.name.lower() in _EXCLUDED_TAGS
        )
    ):
        tag.decompose()


def _section_text(section: Tag) -> str:
    pieces: list[str] = []
    for node in section.descendants:
        if not isinstance(node, NavigableString) or not node.strip():
            continue
        owner = node.find_parent(
            lambda tag: isinstance(tag, Tag) and tag.name.lower().startswith("section-")
        )
        title = node.find_parent(
            lambda tag: isinstance(tag, Tag) and tag.name.lower() == "title"
        )
        if owner is section and title is None:
            pieces.append(str(node))
    return _clean_text("\n".join(pieces))


@lru_cache(maxsize=1)
def _encoder() -> TokenEncoder:
    import tiktoken

    return tiktoken.get_encoding("cl100k_base")


def _split_tokens(
    text: str,
    target_tokens: int,
    max_tokens: int,
    encoder: TokenEncoder,
) -> Iterable[str]:
    if not 400 <= target_tokens <= max_tokens:
        raise ValueError("target_tokens는 400 이상 max_tokens 이하여야 합니다.")
    tokens = encoder.encode(text)
    while len(tokens) > max_tokens:
        # 450토큰을 기본 경계로 삼되, 문단/문장 끝이 가까우면 그 경계를 우선한다.
        candidate = encoder.decode(tokens[:target_tokens])
        boundary = max(candidate.rfind("\n\n"), candidate.rfind(". "), candidate.rfind("다. "))
        cut = len(encoder.encode(candidate[: boundary + 1])) if boundary > 0 else target_tokens
        cut = cut if 400 <= cut <= max_tokens else target_tokens
        yield encoder.decode(tokens[:cut]).strip()
        tokens = tokens[cut:]
    if tokens:
        yield encoder.decode(tokens).strip()


def _fallback_sections(soup: BeautifulSoup) -> list[tuple[str | None, str | None, str]]:
    """SECTION 태그가 없을 때 로마자/숫자 목차 패턴으로 본문을 분리한다."""
    major: str | None = None
    minor: str | None = None
    content: list[str] = []
    sections: list[tuple[str | None, str | None, str]] = []

    def flush() -> None:
        text = _clean_text("\n".join(content))
        if text:
            sections.append((major, minor, text))
        content.clear()

    for line in (_clean_text(part) for part in soup.get_text("\n").splitlines()):
        if not line:
            continue
        if _MAJOR_HEADING.match(line):
            flush()
            major, minor = _standardize_major(line), None
        elif _MINOR_HEADING.match(line):
            flush()
            minor = _standardize_minor(line)
        else:
            content.append(line)
    flush()
    return sections


def parse_report_chunks(
    document: bytes,
    target_tokens: int = 450,
    max_tokens: int = 500,
    encoder: TokenEncoder | None = None,
) -> list[ParsedChunk]:
    soup = BeautifulSoup(document, "lxml-xml")
    _remove_non_text_content(soup)
    sections = soup.find_all(
        lambda tag: isinstance(tag, Tag) and tag.name.lower().startswith("section-")
    )
    parsed: list[tuple[str | None, str | None, str]] = []
    encoder = encoder or _encoder()

    for section in sections:
        ancestors = [
            parent
            for parent in section.parents
            if isinstance(parent, Tag) and parent.name.lower().startswith("section-")
        ]
        major = _standardize_major(_title(ancestors[-1]) if ancestors else _title(section))
        minor = _standardize_minor(_title(section)) if ancestors else None
        content = _section_text(section)
        if content:
            parsed.append((major, minor, content))

    if not parsed:
        parsed = _fallback_sections(soup)
    if not parsed:
        text = _clean_text(soup.get_text("\n"))
        parsed = [(None, None, text)] if text else []

    chunks: list[ParsedChunk] = []
    for major, minor, text in parsed:
        for content in _split_tokens(text, target_tokens, max_tokens, encoder):
            chunks.append(
                ParsedChunk(
                    major_section=major[:200] if major else None,
                    minor_section=minor[:300] if minor else None,
                    chunk_order=len(chunks),
                    content=content,
                )
            )
    return chunks
