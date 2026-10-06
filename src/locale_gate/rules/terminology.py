"""Kural 1 — Sözlük uyumu (terminology).

Zorunlu karşılık ve yasaklı varyant kontrolü. Yalnızca **kaynak metinde geçen** terimler
denetlenir; böylece segmentin konusu olmayan bir terim için yanlış alarm üretilmez.
"""

from __future__ import annotations

from locale_gate.models import Finding, Severity
from locale_gate.rules.context import RuleContext, RuleOutcome


def check(context: RuleContext) -> RuleOutcome:
    """Check every segment against the glossary terms it actually mentions."""
    findings: list[Finding] = []
    checked = 0

    for segment in context.catalog.segments:
        matched = context.glossary.terms_in(segment.source)
        if not matched:
            continue
        checked += 1
        for term in matched:
            required = term.target_pattern()
            if required is not None and not required.search(segment.target):
                findings.append(
                    Finding(
                        severity=Severity.CRITICAL,
                        code="TERM_EKSIK",
                        rule="terminology",
                        segment_id=segment.id,
                        field=segment.field,
                        message_tr=f"Sözlük karşılığı eksik: “{term.source}” → “{term.target}”",
                        detail_tr=f"Hedef metin zorunlu karşılığı içermiyor. Kaynak: “{segment.source}”",
                        hint_tr=(
                            f"Çeviriyi “{term.target}” ifadesini içerecek şekilde düzeltin"
                            + (f" ({term.note})" if term.note else "")
                        ),
                    )
                )
            for variant, variant_pattern in term.forbidden_patterns():
                if variant_pattern.search(segment.target):
                    findings.append(
                        Finding(
                            severity=Severity.WARNING,
                            code="TERM_YASAK",
                            rule="terminology",
                            segment_id=segment.id,
                            field=segment.field,
                            message_tr=f"Yasaklı çeviri kullanılmış: “{variant}”",
                            detail_tr=f"“{term.source}” için sözlük “{term.target or '—'}” diyor, “{variant}” yasaklı.",
                            hint_tr=f"“{variant}” yerine sözlükteki karşılığı kullanın.",
                        )
                    )

    return RuleOutcome(rule="terminology", checked=checked, findings=tuple(findings))
