"""Konsol, Markdown ve GitHub Actions özeti biçiminde çıktı.

Metinler Türkçedir: kapıyı okuyan kişi içerik ekibidir. Sayısal alanlar (`code`, `field`, skor)
İngilizce kalır ki CI kaydı ve kural sözlüğü ile birebir eşleşsin.
"""

from __future__ import annotations

from locale_gate.models import Report, Severity

_BULLET = {Severity.CRITICAL: "[KRİTİK]", Severity.WARNING: "[UYARI]", Severity.INFO: "[BİLGİ]"}
_RULE_ORDER = ("terminology", "tokens", "turkish", "length")


def render_report_text(
    report: Report,
    *,
    passed: bool | None = None,
    reasons: list[str] | None = None,
    catalog_path: str = "",
    max_findings: int | None = None,
) -> str:
    """Render the Turkish console report."""
    lines: list[str] = []
    lines.append("ÇEVİRİ KALİTE KAPISI")
    lines.append(
        f"  yön: {report.source_locale} → {report.target_locale}  ·  segment: {report.segments}"
        + (f"  ·  katalog: {catalog_path}" if catalog_path else "")
    )
    lines.append(
        f"  skor: {report.score:.3f} / eşik {report.gate:.3f}  ·  "
        f"KRİTİK {report.critical_count}  ·  UYARI {report.count(Severity.WARNING)}  ·  "
        f"BİLGİ {report.count(Severity.INFO)}"
    )
    lines.append("")
    lines.append("KURAL BAŞARI ORANLARI")
    width = max((len(stat.label_tr) for stat in report.stats), default=10)
    for stat in sorted(report.stats, key=lambda s: _RULE_ORDER.index(s.rule) if s.rule in _RULE_ORDER else 99):
        coverage = f"{stat.checked} segment" if stat.checked else "denetlenecek segment yok"
        affected = ""
        if stat.failed_segments and stat.failed_segments != stat.failed:
            affected = f", {stat.failed_segments} segment etkilendi"
        lines.append(
            f"  {stat.label_tr:<{width}}  {stat.score * 100:5.1f}%   ({stat.failed} bulgu{affected} / {coverage})"
        )

    if report.findings:
        lines.append("")
        lines.append("BULGULAR")
        shown = report.findings if max_findings is None else report.findings[:max_findings]
        for index, finding in enumerate(shown, start=1):
            lines.append(f"{index:>3}. {_BULLET[finding.severity]} [{finding.code}] {finding.message_tr}")
            lines.append(f"      alan   : {finding.field}  ·  segment: {finding.segment_id}")
            lines.append(f"      durum  : {finding.detail_tr}")
            lines.append(f"      çözüm  : {finding.hint_tr}")
        hidden = len(report.findings) - len(shown)
        if hidden > 0:
            lines.append(f"  … {hidden} bulgu daha var (--max-findings ile sınırı artırın).")
    else:
        lines.append("")
        lines.append("Bulgu yok. 🎉")

    lines.append("")
    if passed is None:
        lines.append("KARAR: rapor üretildi (karar verilmedi)")
    elif passed:
        lines.append("KARAR: GEÇTİ ✔")
    else:
        lines.append("KARAR: KALDI ✘")
        for reason in reasons or []:
            lines.append(f"  neden: {reason}")
    return "\n".join(lines)


def render_markdown(report: Report, *, passed: bool, reasons: list[str] | None = None, top: int = 10) -> str:
    """Render a compact Markdown summary (PR yorumu veya iş özeti olarak)."""
    lines = [
        f"### Çeviri kalite kapısı — {report.source_locale} → {report.target_locale}",
        "",
        f"**Skor:** {report.score:.3f} / eşik {report.gate:.3f} → " + ("GEÇTİ ✔" if passed else "KALDI ✘"),
        "",
        f"- segment: {report.segments}",
        (
            f"- kritik: {report.critical_count} · uyarı: {report.count(Severity.WARNING)}"
            f" · bilgi: {report.count(Severity.INFO)}"
        ),
        "",
        "| Kural | Başarı | Bulgu | Kapsam |",
        "|-------|--------|-------|--------|",
    ]
    lines.extend(
        f"| {stat.label_tr} (`{stat.rule}`) | {stat.score * 100:.1f}% | {stat.failed} | {stat.checked or '—'} |"
        for stat in report.stats
    )
    codes = report.by_code()
    if codes:
        distribution = ", ".join(f"`{code}` ×{count}" for code, count in sorted(codes.items()))
        lines.extend(["", f"**Kod dağılımı:** {distribution}"])
    if report.findings:
        lines.extend(["", f"En önemli {min(top, len(report.findings))} bulgu:", ""])
        lines.extend(
            f"- `{finding.code}` · **{finding.segment_id}** ({finding.field}) — {finding.message_tr}"
            for finding in report.findings[:top]
        )
    if reasons:
        lines.extend(["", "**Kapı nedenleri:**"])
        lines.extend(f"- {reason}" for reason in reasons)
    lines.extend(["", "<sub>locale-gate · deterministik kural motoru, LLM çağrısı yok</sub>"])
    return "\n".join(lines)
