"""Kural sözleşmesi: bağlam ve çıktı tipleri.

Ayrı bir modülde durur çünkü hem kural motoru (`rules/__init__.py`) hem de tek tek kurallar
bunlara ihtiyaç duyar; tek dosyada tutmak dairesel import yaratır.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from locale_gate.catalog import Catalog
from locale_gate.config import GateConfig
from locale_gate.glossary import Glossary
from locale_gate.models import Finding


@dataclass(frozen=True, slots=True)
class RuleContext:
    """Bir kuralın ihtiyaç duyduğu her şey (IO yok, saat yok → deterministik)."""

    catalog: Catalog
    glossary: Glossary
    config: GateConfig


@dataclass(frozen=True, slots=True)
class RuleOutcome:
    """Bir kuralın çıktısı: kapsam (`checked` segment) ve bulgular."""

    rule: str
    checked: int
    findings: tuple[Finding, ...]


RuleFn = Callable[[RuleContext], RuleOutcome]
