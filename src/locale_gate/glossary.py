"""Sözlük (glossary): zorunlu karşılıklar ve yasaklı ifadeler.

Sözlük, çeviri kalitesinde en yüksek getirili kuraldır: "kargo ücreti" her yerde "shipping fee"
olmalıysa, bunu gözle yakalamak yerine CI'a bırakmak gerekir. Dosya biçimi YAML veya JSON:

```yaml
source_locale: tr
target_locale: en
terms:
  - source: kargo ücreti
    target: shipping fee
    forbidden: [cargo fee, cargo price]
    note: Pazaryeri sözlüğü zorunlu karşılığı
```
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

_TR_WORD = r"0-9A-Za-zÇĞİÖŞÜçğıöşü"


class Term(BaseModel):
    """Tek sözlük kaydı."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source: str
    target: str | None = None
    forbidden: tuple[str, ...] = ()
    case_sensitive: bool = False
    note: str | None = None

    def source_pattern(self) -> re.Pattern[str]:
        """Kaynak terimi tanıyan derlenmiş desen."""
        return compile_term(self.source, case_sensitive=self.case_sensitive)

    def target_pattern(self) -> re.Pattern[str] | None:
        """Zorunlu karşılığın deseni (karşılık tanımlı değilse ``None``)."""
        if self.target is None:
            return None
        return compile_term(self.target, case_sensitive=self.case_sensitive)

    def forbidden_patterns(self) -> tuple[tuple[str, re.Pattern[str]], ...]:
        """Yasaklı varyantları ve desenlerini birlikte döndür."""
        return tuple((variant, compile_term(variant, case_sensitive=self.case_sensitive)) for variant in self.forbidden)


class Glossary(BaseModel):
    """Sözlük dosyasının tamamı."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_locale: str = "tr"
    target_locale: str = "en"
    terms: tuple[Term, ...] = Field(default_factory=tuple)

    def terms_in(self, text: str) -> list[Term]:
        """Metinde geçen sözlük terimlerini döndür."""
        return [term for term in self.terms if term.source_pattern().search(text)]


def compile_term(term: str, *, case_sensitive: bool) -> re.Pattern[str]:
    r"""Build a word-boundary matcher that understands Turkish letters.

    ``\\b`` treats ``ş``/``ı`` as word characters, but a term such as ``%100 pamuk`` starts with a
    symbol, so the boundary is expressed explicitly with lookarounds instead of relying on ``\\b``.
    """
    flags = 0 if case_sensitive else re.IGNORECASE
    escaped = re.escape(term.strip())
    return re.compile(rf"(?<![{_TR_WORD}]){escaped}(?![{_TR_WORD}])", flags)


def load_glossary(path: Path | None) -> Glossary:
    """Load a glossary from YAML/JSON, or return an empty one when ``path`` is ``None``."""
    if path is None:
        return Glossary()
    if not path.exists():
        msg = f"sözlük bulunamadı: {path}"
        raise FileNotFoundError(msg)
    text = path.read_text(encoding="utf-8")
    raw: Any = json.loads(text) if path.suffix.lower() == ".json" else yaml.safe_load(text)
    if raw is None:
        return Glossary()
    if not isinstance(raw, dict):
        msg = f"{path} bir nesne içermeli"
        raise ValueError(msg)
    entries: list[dict[str, Any]] = []
    for item in raw.get("terms", []):
        if isinstance(item, str):  # kısa biçim: yalnızca kaynak terim
            entries.append({"source": item})
        elif isinstance(item, dict):
            entries.append(item)
        else:
            msg = f"sözlükte geçersiz kayıt: {item!r}"
            raise ValueError(msg)
    return Glossary(
        source_locale=str(raw.get("source_locale", "tr")),
        target_locale=str(raw.get("target_locale", "en")),
        terms=tuple(Term.model_validate(entry) for entry in entries),
    )
