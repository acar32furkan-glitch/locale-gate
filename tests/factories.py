"""Test kurucuları: kısa ve okunur katalog/bağlam üretimi.

Testler üretim kodundaki JSON dosyalarına bağlı değildir; burada kurulan minik kataloglar her
kuralın sınır davranışını tek bakışta görünür kılar.
"""

from __future__ import annotations

from collections.abc import Iterable

from locale_gate.catalog import Catalog, Segment
from locale_gate.config import GateConfig
from locale_gate.glossary import Glossary, Term
from locale_gate.models import Finding
from locale_gate.rules.context import RuleContext


def make_segment(
    segment_id: str = "S-1",
    *,
    field: str = "title",
    source: str = "",
    target: str = "",
    limit: int | None = None,
) -> Segment:
    return Segment(id=segment_id, field=field, source=source, target=target, limit=limit)


def make_catalog(
    segments: list[Segment],
    *,
    source_locale: str = "tr",
    target_locale: str = "en",
    field_limits: dict[str, int] | None = None,
) -> Catalog:
    return Catalog(
        source_locale=source_locale,
        target_locale=target_locale,
        field_limits=field_limits or {},
        segments=tuple(segments),
    )


def make_term(
    source: str,
    *,
    target: str | None = None,
    forbidden: tuple[str, ...] = (),
    case_sensitive: bool = False,
    note: str | None = None,
) -> Term:
    return Term(source=source, target=target, forbidden=forbidden, case_sensitive=case_sensitive, note=note)


def make_glossary(
    terms: list[Term],
    *,
    source_locale: str = "tr",
    target_locale: str = "en",
) -> Glossary:
    return Glossary(source_locale=source_locale, target_locale=target_locale, terms=tuple(terms))


def make_context(
    segments: list[Segment],
    *,
    glossary: Glossary | None = None,
    config: GateConfig | None = None,
    source_locale: str = "tr",
    target_locale: str = "en",
    field_limits: dict[str, int] | None = None,
) -> RuleContext:
    return RuleContext(
        catalog=make_catalog(
            segments,
            source_locale=source_locale,
            target_locale=target_locale,
            field_limits=field_limits or {},
        ),
        glossary=glossary or Glossary(),
        config=config or GateConfig(),
    )


def codes(findings: Iterable[Finding]) -> list[str]:
    """Bulguların kodlarını sıralı döndür (karşılaştırmayı okunur kılar)."""
    return sorted({finding.code for finding in findings})
