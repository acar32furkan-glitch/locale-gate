"""Katalog: çevrilecek/kontrol edilecek segmentlerin yüklenmesi.

Desteklenen girdiler (gerçek pazaryeri dışa aktarımları bunlar):

* **JSON** — `{"source_locale", "target_locale", "field_limits", "segments": [...]}`
* **CSV** — başlık satırı: `id,field,source,target,limit`

CSV'de `limit` boş bırakılabilir; o durumda alan adına göre yapılandırmadaki sınır uygulanır.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Segment(BaseModel):
    """Tek bir metin alanı: kaynak cümle + hedef (çevrilmiş) cümle."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    field: str
    source: str
    target: str
    limit: int | None = None
    note: str | None = None


class Catalog(BaseModel):
    """Bir dışa aktarımın tamamı."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    source_locale: str = "tr"
    target_locale: str = "en"
    field_limits: dict[str, int] = Field(default_factory=dict)
    segments: tuple[Segment, ...]

    def segment_by_id(self, segment_id: str) -> Segment | None:
        """Kimliğe göre segment döndür (yoksa ``None``)."""
        return next((segment for segment in self.segments if segment.id == segment_id), None)

    def fields(self) -> list[str]:
        """Katalogda geçen alan adlarını sıralı döndür."""
        return sorted({segment.field for segment in self.segments})


def _segment_from_row(row: dict[str, Any], index: int) -> Segment:
    missing = [key for key in ("id", "field", "source", "target") if not str(row.get(key, "")).strip()]
    if missing:
        msg = f"{index}. satırda zorunlu alanlar eksik: {', '.join(missing)}"
        raise ValueError(msg)
    raw_limit = row.get("limit")
    limit: int | None = None
    if raw_limit is not None and str(raw_limit).strip() != "":
        try:
            limit = int(str(raw_limit))
        except ValueError:
            msg = f"{index}. satırda limit sayı değil: {raw_limit!r}"
            raise ValueError(msg) from None
    note = row.get("note")
    return Segment(
        id=str(row["id"]).strip(),
        field=str(row["field"]).strip(),
        source=str(row["source"]),
        target=str(row["target"]),
        limit=limit,
        note=None if note is None or str(note).strip() == "" else str(note),
    )


def load_catalog(path: Path) -> Catalog:
    """Load a catalog from JSON or CSV, whichever the extension says."""
    if not path.exists():
        msg = f"katalog bulunamadı: {path}"
        raise FileNotFoundError(msg)
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        segments = tuple(_segment_from_row(row, index) for index, row in enumerate(rows, start=2))
        return Catalog(segments=segments)
    raw = json.loads(path.read_text(encoding="utf-8"))
    segments = tuple(_segment_from_row(item, index) for index, item in enumerate(raw.get("segments", []), start=1))
    return Catalog(
        source_locale=str(raw.get("source_locale", "tr")),
        target_locale=str(raw.get("target_locale", "en")),
        field_limits={str(key): int(value) for key, value in (raw.get("field_limits") or {}).items()},
        segments=segments,
    )
