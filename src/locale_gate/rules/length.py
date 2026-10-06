"""Kural 4 — Uzunluk bütçesi (length).

Pazaryeri ve SEO alanlarında karakter sınırı vardır; sınırı aşan başlık sessizce kırpılır.
Ayrıca TR→EN çevirisi tipik olarak uzar; kaynağa göre aşırı uzama, çevirinin "şişirilmiş"
olduğunun işaretidir (ya da metnin bir kısmının eklenmiş olduğunun).
"""

from __future__ import annotations

from locale_gate.models import Finding, Severity
from locale_gate.rules.context import RuleContext, RuleOutcome

# Uzama oranı bu uzunluğun altındaki kaynaklarda ölçülmez: kısa segmentlerde oran gürültüdür.
MIN_EXPANSION_SOURCE_LEN = 25


def check(context: RuleContext) -> RuleOutcome:
    """Compare each target against its field limit and the allowed expansion ratio."""
    findings: list[Finding] = []
    checked = 0

    for segment in context.catalog.segments:
        limit = context.config.limit_for(segment.field, segment.limit)
        source_len = len(segment.source.strip())
        target_len = len(segment.target.strip())
        if limit is None and source_len == 0:
            continue
        checked += 1

        if limit is not None and target_len > limit:
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    code="LENGTH_SINIR",
                    rule="length",
                    segment_id=segment.id,
                    field=segment.field,
                    message_tr=f"Alan sınırı aşıldı: {target_len}/{limit} karakter",
                    detail_tr=(
                        f"“{segment.field}” alanının sınırı {limit}; çeviri {target_len - limit} karakter fazla. "
                        "Pazaryerleri bu alanı sessizce kırpar."
                    ),
                    hint_tr="Başlığı kısaltın ya da kısaltma/ek bilgiyi açıklamaya taşıyın.",
                )
            )

        # Kaynak çok kısaysa oran anlamsızdır ("Deri Cüzdan" → "Leather Wallet" x2.4).
        # Bu yüzden uzama denetimi yalnızca anlamlı uzunluktaki segmentlerde yapılır.
        if source_len >= MIN_EXPANSION_SOURCE_LEN:
            ratio = target_len / source_len
            if ratio > context.config.max_expansion:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        code="LENGTH_UZAMA",
                        rule="length",
                        segment_id=segment.id,
                        field=segment.field,
                        message_tr=f"Aşırı uzama: kaynak {source_len} → hedef {target_len} karakter (x{ratio:.2f})",
                        detail_tr=(
                            f"İzin verilen uzama oranı x{context.config.max_expansion:.2f}. "
                            "Bu oran genelde metne bilgi eklenmiş olduğunu gösterir."
                        ),
                        hint_tr="Çeviriyi kaynakla aynı bilgi düzeyine indirin; reklam dili eklemeyin.",
                    )
                )

    return RuleOutcome(rule="length", checked=checked, findings=tuple(findings))
