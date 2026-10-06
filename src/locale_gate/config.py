"""Kapı yapılandırması: eşikler, ağırlıklar, alan sınırları.

Varsayılanlar `docs/rules.md` içinde gerekçeleriyle yazılıdır. Her şey dosyadan (TOML/JSON)
geçersiz kılınabilir; böylece kural setini kod değiştirmeden mağazaya uyarlayabilirsiniz.
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

DEFAULT_FIELD_LIMITS: dict[str, int] = {
    "title": 70,
    "bullet": 140,
    "description": 2000,
}

DEFAULT_WEIGHTS: dict[str, float] = {
    "terminology": 0.35,
    "tokens": 0.35,
    "turkish": 0.15,
    "length": 0.15,
}


class GateConfig(BaseModel):
    """Kapının eşikleri.

    Args:
        gate: Geçme eşiği (0-1). Ağırlıklı skor bunun altındaysa kapı düşer.
        fail_on_critical: Tek bir `critical` bulgu kapıyı düşürsün mü.
        max_expansion: Hedef metnin kaynağa göre izin verilen en büyük uzama oranı.
        field_limits: Alan başına karakter sınırı (pazaryeri/SEO kırpma riski).
        weights: Kural ağırlıkları (toplamı 1 olmak zorunda değil; normalize edilir).
        locales: Desteklenen dil çiftleri; farklı bir çift verilirse hata verilir.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    gate: float = Field(default=0.95, ge=0.0, le=1.0)
    fail_on_critical: bool = True
    max_expansion: float = Field(default=1.6, gt=0.0)
    field_limits: dict[str, int] = Field(default_factory=lambda: dict(DEFAULT_FIELD_LIMITS))
    weights: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    locales: tuple[str, ...] = ("tr", "en")

    @classmethod
    def from_file(cls, path: Path) -> GateConfig:
        """Load a config from TOML or JSON; unknown keys are rejected (typo safety)."""
        text = path.read_text(encoding="utf-8")
        raw: Any = tomllib.loads(text) if path.suffix == ".toml" else json.loads(text)
        if not isinstance(raw, dict):
            msg = f"{path} bir nesne içermeli"
            raise ValueError(msg)
        # `[tool.locale-gate]` altında da olabilir; ikisini de kabul et.
        if "tool" in raw and isinstance(raw["tool"], dict):
            raw = raw["tool"].get("locale-gate", raw)
        return cls.model_validate(raw)

    @classmethod
    def load(cls, path: Path | None) -> GateConfig:
        """Dosya verilmişse ondan, verilmemişse varsayılanlardan yükle."""
        return cls() if path is None else cls.from_file(path)

    def normalized_weights(self) -> dict[str, float]:
        """Ağırlıkları toplamı 1 olacak şekilde normalize et."""
        total = sum(self.weights.values())
        if total <= 0:
            msg = "weights toplamı sıfır olamaz"
            raise ValueError(msg)
        return {rule: weight / total for rule, weight in self.weights.items()}

    def limit_for(self, field: str, fallback: int | None) -> int | None:
        """Alanın karakter sınırını döndür (segment kendi sınırını getirdiyse o kazanır)."""
        return fallback if fallback is not None else self.field_limits.get(field)
