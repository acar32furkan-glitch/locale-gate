"""Rapor ve bulgu modelleri.

Bulgular Türkçe yazılır (ürün içeriğini üreten ekip Türkçe konuşuyor), alan adları ve kodlar
İngilizcedir — böylece hem çevirmen hem CI logu aynı kaydı okuyabilir.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Severity(StrEnum):
    """Bulgu ağırlığı; `critical` bulgular yapılandırmaya göre kapıyı tek başına düşürebilir."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class Finding(BaseModel):
    """Tek bir kural ihlali."""

    model_config = ConfigDict(frozen=True)

    severity: Severity
    code: str
    rule: str
    segment_id: str
    field: str
    message_tr: str
    detail_tr: str
    hint_tr: str

    @property
    def severity_tr(self) -> str:
        """Türkçe önem etiketi (rapor metinlerinde kullanılır)."""
        return {"critical": "KRİTİK", "warning": "UYARI", "info": "BİLGİ"}[self.severity.value]


class RuleStat(BaseModel):
    """Bir kuralın kapsama ve başarı istatistiği.

    `failed` bulgu sayısıdır (bir segment birden fazla bulgu üretebilir), `failed_segments` ise
    etkilenen segment sayısıdır. Başarı oranı **segment** üzerinden hesaplanır; aksi hâlde tek bir
    segmentteki üç bulgu kuralı üç kez cezalandırır ve skor negatife düşebilir.
    """

    model_config = ConfigDict(frozen=True)

    rule: str
    label_tr: str
    checked: int
    failed: int
    failed_segments: int = 0

    @property
    def score(self) -> float:
        """Bu kuralın başarı oranı (1.0 = kapsamdaki hiçbir segmentte bulgu yok)."""
        if self.checked == 0:
            return 1.0
        return max(0.0, 1.0 - (self.failed_segments / self.checked))


class Report(BaseModel):
    """Kapının tam çıktısı: bulgular, kural istatistikleri, ağırlıklı skor ve karar."""

    model_config = ConfigDict(frozen=True)

    generated_at: datetime
    source_locale: str
    target_locale: str
    segments: int
    findings: tuple[Finding, ...]
    stats: tuple[RuleStat, ...]
    score: float
    gate: float

    @property
    def critical_count(self) -> int:
        """Kritik önemdeki bulgu sayısı."""
        return sum(1 for finding in self.findings if finding.severity is Severity.CRITICAL)

    def count(self, severity: Severity) -> int:
        """Verilen önem düzeyindeki bulgu sayısını döndür."""
        return sum(1 for finding in self.findings if finding.severity is severity)

    def by_code(self) -> dict[str, int]:
        """Kod → bulgu sayısı dağılımı."""
        codes: dict[str, int] = {}
        for finding in self.findings:
            codes[finding.code] = codes.get(finding.code, 0) + 1
        return codes

    def stat_for(self, rule: str) -> RuleStat | None:
        """Verilen kuralın istatistiğini döndür (kural skora girmemişse ``None``)."""
        return next((stat for stat in self.stats if stat.rule == rule), None)
