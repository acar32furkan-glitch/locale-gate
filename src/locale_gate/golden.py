"""Altın set (golden set): kuralların davranışını sabitleyen regresyon vakaları.

Her vaka kendi katalog + sözlük + yapılandırmasını getirir ve **beklenen bulgu kodlarını segment
bazında** bildirir. Böylece "kural bir vaka daha yakaladı" ya da "yanlış alarm üretmeye başladı"
durumları sessizce geçemez; CI kırmızıya döner.

Dosya biçimi (`examples/golden/golden.json`):

```json
{"cases": [{"name": "tr-en-temel", "catalog": "tr_en/catalog.json", "glossary": "tr_en/glossary.yaml",
            "expected": {"P-1001-title": ["TERM_EKSIK"]}, "expect_passed": false}]}
```
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from locale_gate.catalog import load_catalog
from locale_gate.config import GateConfig
from locale_gate.gate import decide, run_gate
from locale_gate.glossary import load_glossary


class GoldenCase(BaseModel):
    """Tek regresyon vakası."""

    model_config = ConfigDict(frozen=True)

    name: str
    catalog: str
    glossary: str | None = None
    config: str | None = None
    expected: dict[str, tuple[str, ...]] = Field(default_factory=dict)
    expect_passed: bool | None = None
    expect_codes: dict[str, int] = Field(default_factory=dict)


class CaseResult(BaseModel):
    """Bir vakanın sonucu: eşleşen/kaçan/fazla çıkan kodlar."""

    model_config = ConfigDict(frozen=True)

    name: str
    passed: bool
    score: float
    gate_passed: bool
    missing: dict[str, tuple[str, ...]]
    unexpected: dict[str, tuple[str, ...]]
    mismatches: tuple[str, ...]


class GoldenResult(BaseModel):
    """Altın setin tamamı."""

    model_config = ConfigDict(frozen=True)

    cases: tuple[CaseResult, ...]

    @property
    def passed(self) -> bool:
        """Tüm vakalar beklendiği gibi davrandıysa ``True``."""
        return all(case.passed for case in self.cases)


def load_golden(root: Path) -> list[GoldenCase]:
    """Load ``golden.json`` from a directory (or read the file directly)."""
    path = root / "golden.json" if root.is_dir() else root
    if not path.exists():
        msg = f"altın set dosyası yok: {path}"
        raise FileNotFoundError(msg)
    raw: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("cases"), list):
        msg = f"{path} içinde 'cases' listesi olmalı"
        raise ValueError(msg)
    return [GoldenCase.model_validate(case) for case in raw["cases"]]


def run_case(case: GoldenCase, root: Path) -> CaseResult:
    """Run one case and diff its finding codes against the expectation."""
    base = root if root.is_dir() else root.parent
    catalog = load_catalog(base / case.catalog)
    glossary = load_glossary(base / case.glossary) if case.glossary else None
    config = GateConfig.load(base / case.config if case.config else None)
    report = run_gate(catalog, glossary, config)
    gate_passed, _ = decide(report, config)

    actual: dict[str, set[str]] = {}
    for finding in report.findings:
        actual.setdefault(finding.segment_id, set()).add(finding.code)

    missing: dict[str, tuple[str, ...]] = {}
    unexpected: dict[str, tuple[str, ...]] = {}
    mismatches: list[str] = []

    # Kapsam: katalogdaki tüm segmentler + beklentide geçen kimlikler. Beklentide olmayan bir
    # segmentte bulgu çıkması da hatadır (yeni yanlış alarm sessizce geçemez).
    for segment in catalog.segments:
        found = actual.get(segment.id, set())
        expected_codes = set(case.expected.get(segment.id, ()))
        absent = tuple(sorted(expected_codes - found))
        extra = tuple(sorted(found - expected_codes))
        if absent:
            missing[segment.id] = absent
        if extra:
            unexpected[segment.id] = extra
        if absent or extra:
            mismatches.append(f"{segment.id}: beklenen {sorted(expected_codes)} ≠ bulunan {sorted(found)}")

    codes = report.by_code()
    for code, expected_count in case.expect_codes.items():
        if codes.get(code, 0) != expected_count:
            mismatches.append(f"kod {code}: beklenen {expected_count}, bulunan {codes.get(code, 0)}")

    if case.expect_passed is not None and gate_passed is not case.expect_passed:
        mismatches.append(f"kapı kararı: beklenen {'GEÇTİ' if case.expect_passed else 'KALDI'}, bulunan {gate_passed}")

    return CaseResult(
        name=case.name,
        passed=not mismatches,
        score=report.score,
        gate_passed=gate_passed,
        missing=missing,
        unexpected=unexpected,
        mismatches=tuple(mismatches),
    )


def run_golden(root: Path) -> GoldenResult:
    """Run every case in the golden set."""
    cases = load_golden(root)
    return GoldenResult(cases=tuple(run_case(case, root) for case in cases))


def render_golden_text(result: GoldenResult) -> str:
    """Human-readable Turkish summary of a golden run."""
    lines = ["ALTIN SET (regresyon) SONUCU", ""]
    for case in result.cases:
        mark = "✔" if case.passed else "✘"
        gate = "GEÇTİ" if case.gate_passed else "KALDI"
        lines.append(f"  {mark} {case.name:<24} skor {case.score:.3f} · kapı {gate}")
        for mismatch in case.mismatches:
            lines.append(f"      {mismatch}")
    lines.append("")
    lines.append(f"SONUÇ: {sum(1 for c in result.cases if c.passed)}/{len(result.cases)} vaka beklenen davranışı verdi")
    return "\n".join(lines)
