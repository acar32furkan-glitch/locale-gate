"""Kapı: kuralları çalıştırır, ağırlıklı skoru hesaplar ve geçme kararını verir."""

from __future__ import annotations

from datetime import UTC, datetime

from locale_gate.catalog import Catalog
from locale_gate.config import GateConfig
from locale_gate.glossary import Glossary
from locale_gate.models import Finding, Report, RuleStat
from locale_gate.rules import RULE_LABELS, RULES, RuleContext


class GateInputError(ValueError):
    """Katalog, sözlük veya yapılandırma tutarsız (ör. kaynak ve hedef dil aynı)."""


def _validate(catalog: Catalog, glossary: Glossary, config: GateConfig) -> None:
    if catalog.source_locale == catalog.target_locale:
        msg = f"kaynak ve hedef dil aynı: {catalog.source_locale}"
        raise GateInputError(msg)
    for locale in (catalog.source_locale, catalog.target_locale):
        if locale not in config.locales:
            msg = f"desteklenmeyen dil: {locale} (desteklenen: {', '.join(config.locales)})"
            raise GateInputError(msg)
    if glossary.terms and (glossary.source_locale, glossary.target_locale) != (
        catalog.source_locale,
        catalog.target_locale,
    ):
        msg = (
            "sözlük dil çifti katalogla uyuşmuyor: "
            f"sözlük {glossary.source_locale}→{glossary.target_locale}, "
            f"katalog {catalog.source_locale}→{catalog.target_locale}"
        )
        raise GateInputError(msg)


def run_gate(
    catalog: Catalog,
    glossary: Glossary | None = None,
    config: GateConfig | None = None,
    *,
    now: datetime | None = None,
) -> Report:
    """Run every rule and return the report (pure function of its inputs)."""
    limits = config or GateConfig()
    terms = glossary or Glossary()
    _validate(catalog, terms, limits)

    context = RuleContext(catalog=catalog, glossary=terms, config=limits)
    findings: list[Finding] = []
    stats: list[RuleStat] = []
    for rule, check in RULES.items():
        outcome = check(context)
        findings.extend(outcome.findings)
        stats.append(
            RuleStat(
                rule=rule,
                label_tr=RULE_LABELS.get(rule, rule),
                checked=outcome.checked,
                failed=len(outcome.findings),
                failed_segments=len({finding.segment_id for finding in outcome.findings}),
            )
        )

    weights = limits.normalized_weights()
    weighted = [(weights[stat.rule], stat) for stat in stats if weights.get(stat.rule, 0.0) > 0 and stat.checked > 0]
    total_weight = sum(weight for weight, _ in weighted)
    score = 1.0 if total_weight == 0 else sum(weight * stat.score for weight, stat in weighted) / total_weight

    ordered = tuple(
        sorted(
            findings,
            key=lambda f: (
                {"critical": 0, "warning": 1, "info": 2}[f.severity.value],
                f.segment_id,
                f.code,
            ),
        )
    )
    return Report(
        generated_at=now or datetime.now(tz=UTC),
        source_locale=catalog.source_locale,
        target_locale=catalog.target_locale,
        segments=len(catalog.segments),
        findings=ordered,
        stats=tuple(stats),
        score=round(score, 4),
        gate=limits.gate,
    )


def decide(report: Report, config: GateConfig, *, fail_under: float | None = None) -> tuple[bool, list[str]]:
    """Return ``(passed, reasons)`` — two independent gates: score and critical findings."""
    threshold = config.gate if fail_under is None else fail_under
    reasons: list[str] = []
    if report.score < threshold:
        reasons.append(
            f"skor {report.score:.3f} < eşik {threshold:.3f} "
            f"({report.critical_count} kritik, {len(report.findings)} bulgu)"
        )
    if config.fail_on_critical and report.critical_count:
        reasons.append(f"{report.critical_count} kritik bulgu var (fail_on_critical=true)")
    return (not reasons, reasons)
