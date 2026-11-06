"""Taban çizgisi: bilinen bulgu borcunu kapının dışında tutar.

Bir PR yalnızca **kendi getirdiği** bulguyla yargılanmalı. Mevcut borç yüzünden her PR'ın kırmızı
olması kapıyı "herkesin görmezden geldiği" bir tören hâline getirir; borcu düzeltmek için ayrı bir
PR açmak da kimseyi motive etmez. `--baseline report.json` önceki koşunun raporunu okur, bulguları
``(code, segment_id, field)`` üçlüsüyle eşler ve yalnızca yeni bulguları skora + kritik kapısına
sokar.

Tasarım sınırları:

* Taban dosyası **hiçbir zaman** kendiliğinden güncellenmez; güncellemek bilinçli bir eylemdir
  (``--report`` ile yeni rapor yazıp commit etmek). Aksi hâlde borç sessizce büyürdü.
* Eşleşme mesaj metnine değil kimliğe bakar: bir bulgunun sözü değişse de aynı bulgu sayılır,
  aksi hâlde her çeviri düzeltmesi borcu "yeni bulgu" gibi yeniden doğururdu.
* Düzeltilen bulgu tabanda kalırsa "kapanmış" sayılır (``stale``); skoru yukarı çeker, kapıyı
  etkilemez.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from locale_gate.gate import weighted_score
from locale_gate.models import Finding, Report, RuleStat

BaselineKey = tuple[str, str, str]
"""Bir bulgunun kimliği: ``(code, segment_id, field)``."""

_REQUIRED_KEYS = ("code", "segment_id", "field")


class BaselineError(ValueError):
    """Taban dosyası okunamadı veya bu koşuyla uyuşmuyor."""


@dataclass(frozen=True)
class Baseline:
    """Diskten okunan taban: kimlik kümesi + hangi dil çiftinden geldiği."""

    path: Path
    source_locale: str | None
    target_locale: str | None
    keys: frozenset[BaselineKey]
    entries: int

    def covers(self, finding: Finding) -> bool:
        """Bu bulgu tabanda var mı (yani bilinen borç mu)?"""
        return finding_key(finding) in self.keys


@dataclass(frozen=True)
class BaselineSummary:
    """Taban uygulandıktan sonra raporun taşıdığı sayaçlar (konsol/JSON için)."""

    path: str
    entries: int
    suppressed: int
    new: int
    stale: int
    raw_score: float

    def text_tr(self) -> str:
        """Konsol satırı: ne devralındı, ne yeni, ne kapanmış."""
        return (
            f"taban {self.path}: {self.suppressed} bilinen bulgu devralındı (kapıya girmiyor) · "
            f"{self.new} yeni · {self.stale} kapanmış · ham skor {self.raw_score:.3f}"
        )

    def to_json(self) -> dict[str, object]:
        """``--json``/``--report`` sözleşmesindeki ``baseline`` bloğu."""
        return {
            "path": self.path,
            "entries": self.entries,
            "suppressed": self.suppressed,
            "new": self.new,
            "stale": self.stale,
            "raw_score": self.raw_score,
        }


def finding_key(finding: Finding) -> BaselineKey:
    """Bir bulgunun tabanla eşleşen kimliği."""
    return (finding.code, finding.segment_id, finding.field)


def _entry_key(entry: Any, index: int, path: Path) -> BaselineKey:
    if not isinstance(entry, dict):
        msg = f"taban dosyası {path}: findings[{index}] bir nesne değil"
        raise BaselineError(msg)
    parts: list[str] = []
    for name in _REQUIRED_KEYS:
        value = entry.get(name)
        if not isinstance(value, str) or not value:
            msg = f"taban dosyası {path}: findings[{index}] içinde geçerli '{name}' yok"
            raise BaselineError(msg)
        parts.append(value)
    code, segment_id, field = parts
    return (code, segment_id, field)


def load_baseline(path: Path) -> Baseline:
    """``--report`` ile yazılmış bir raporu taban olarak oku.

    Bozuk dosya, eksik ``findings`` veya kimlik alanı taşımayan bulgu **sessizce yok sayılmaz**:
    yutulan bir taban, borcun kapıya geri dönmesi ya da tamamen kaybolması demektir.
    """
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        msg = f"taban dosyası bulunamadı: {path}"
        raise BaselineError(msg) from exc
    except json.JSONDecodeError as exc:
        msg = f"taban dosyası {path}: geçersiz JSON ({exc.lineno}. satır, {exc.colno}. sütun)"
        raise BaselineError(msg) from exc

    if not isinstance(raw, dict):
        msg = f"taban dosyası {path}: kök bir nesne olmalı"
        raise BaselineError(msg)
    findings = raw.get("findings")
    if not isinstance(findings, list):
        msg = f"taban dosyası {path}: 'findings' listesi yok (locale-gate --report çıktısı bekleniyor)"
        raise BaselineError(msg)

    keys = frozenset(_entry_key(entry, index, path) for index, entry in enumerate(findings))
    source = raw.get("source_locale")
    target = raw.get("target_locale")
    return Baseline(
        path=path,
        source_locale=source if isinstance(source, str) else None,
        target_locale=target if isinstance(target, str) else None,
        keys=keys,
        entries=len(findings),
    )


def apply_baseline(
    report: Report,
    baseline: Baseline,
    weights: Mapping[str, float],
) -> tuple[Report, BaselineSummary]:
    """Bilinen bulguları raporun dışına al ve skoru kalan bulgularla yeniden hesapla.

    Args:
        report: Bu koşunun ham raporu (``run_gate`` çıktısı).
        baseline: ``load_baseline`` ile okunmuş taban.
        weights: Normalize edilmiş kural ağırlıkları (``GateConfig.normalized_weights()``).

    Raises:
        BaselineError: Taban başka bir dil çiftinden geliyorsa. Yön kontrolü şart: ters yönün
            raporu verilirse kodlar aynı olduğu için borç sessizce "tanınıyor" görünür ve kapı
            hiçbir şeyi denetlemez.
    """
    direction = (baseline.source_locale, baseline.target_locale)
    if direction not in {(None, None), (report.source_locale, report.target_locale)}:
        msg = (
            "taban farklı bir dil çiftinden: "
            f"taban {baseline.source_locale}→{baseline.target_locale}, "
            f"bu koşu {report.source_locale}→{report.target_locale}"
        )
        raise BaselineError(msg)

    kept = tuple(finding for finding in report.findings if not baseline.covers(finding))
    suppressed = len(report.findings) - len(kept)
    present = {finding_key(finding) for finding in report.findings}
    stale = len(baseline.keys - present)

    per_rule: dict[str, list[Finding]] = {}
    for finding in kept:
        per_rule.setdefault(finding.rule, []).append(finding)
    stats: tuple[RuleStat, ...] = tuple(
        RuleStat(
            rule=stat.rule,
            label_tr=stat.label_tr,
            checked=stat.checked,
            failed=len(per_rule.get(stat.rule, ())),
            failed_segments=len({finding.segment_id for finding in per_rule.get(stat.rule, ())}),
        )
        for stat in report.stats
    )

    filtered = report.model_copy(
        update={
            "findings": kept,
            "stats": stats,
            "score": round(weighted_score(stats, weights), 4),
        }
    )
    summary = BaselineSummary(
        path=str(baseline.path),
        entries=baseline.entries,
        suppressed=suppressed,
        new=len(kept),
        stale=stale,
        raw_score=report.score,
    )
    return filtered, summary
