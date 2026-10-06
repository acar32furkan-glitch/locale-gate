"""Kural 2 — Korunan ifadeler (tokens).

Çeviri sırasında **değişmemesi gereken** parçalar: yer tutucular (`{price}`, `%s`, `{{ name }}`),
HTML etiketleri, bağlantılar, e-postalar ve ürün ölçüleri/sayıları (`45 x 30 cm`, `256 GB`,
`1.234,56 TL`). Yer tutucu kaybı üretimde çalışma zamanı hatası, ölçü kaybı yanlış ürün bilgisi
demektir; ikisi de gözle fark edilmez.

Sayı karşılaştırması **rakam dizisi** üzerinden yapılır: `2,5 kg` → `2.5 kg` geçerlidir (ayırıcı
yerelleşir) ama `2,5` → `2` kayıptır.
"""

from __future__ import annotations

import re

from locale_gate.models import Finding, Severity
from locale_gate.rules.context import RuleContext, RuleOutcome

PLACEHOLDER = re.compile(
    r"""
    \{\{\s*[A-Za-z0-9_.]+\s*\}\}      # {{ name }}
    | \{[A-Za-z0-9_.]+\}              # {price}, {0}
    | %\(\s*[A-Za-z0-9_]+\s*\)[sd]    # %(count)s
    | %[sd]                           # %s
    | \$\{[A-Za-z0-9_.]+\}            # ${amount}
    """,
    re.VERBOSE,
)
HTML_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9]*(?:\s[^<>]*)?/?>")
URL = re.compile(r"https?://[^\s<>()\]]+")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
QUANTITY = re.compile(
    r"\d+(?:[.,]\d+)?\s*(?:[xX×]\s*\d+(?:[.,]\d+)?\s*)?"
    r"(?:cm|mm|kg|gr|ml|lt|gb|tb|mb|w|v|mah|inç|inch|adet|pcs|piece|pack|set|kişilik|kisi|person)",
    re.IGNORECASE,
)
BARE_NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
MODEL_CODE = re.compile(r"\b[A-Z]{1,4}[- ]?\d{2,}[A-Za-z0-9]*\b")

_DIGITS = re.compile(r"\d")


def _digits(text: str) -> str:
    return "".join(_DIGITS.findall(text))


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def protect(segment_source: str) -> dict[str, list[str]]:
    """Extract every protected token, grouped by kind (public for tests and tooling)."""
    return {
        "placeholder": PLACEHOLDER.findall(segment_source),
        "html": HTML_TAG.findall(segment_source),
        "url": URL.findall(segment_source),
        "email": EMAIL.findall(segment_source),
        "quantity": QUANTITY.findall(segment_source),
        "model": MODEL_CODE.findall(segment_source),
    }


def check(context: RuleContext) -> RuleOutcome:
    """Verify that placeholders, markup and numeric specs survive translation."""
    findings: list[Finding] = []
    target_is_turkish = context.catalog.target_locale == "tr"
    interesting = 0

    for segment in context.catalog.segments:
        protected = protect(segment.source)
        if any(protected.values()):
            interesting += 1
        if not any(protected.values()) and not target_is_turkish:
            continue
        target_digits = _digits(segment.target)

        for kind, severity, label in (
            ("placeholder", Severity.CRITICAL, "yer tutucu"),
            ("html", Severity.CRITICAL, "HTML etiketi"),
        ):
            for token in protected[kind]:
                if token.casefold() not in _normalize(segment.target):
                    findings.append(
                        Finding(
                            severity=severity,
                            code="TOKEN_KAYIP",
                            rule="tokens",
                            segment_id=segment.id,
                            field=segment.field,
                            message_tr=f"{label.capitalize()} korunmamış: {token}",
                            detail_tr=(
                                f"Kaynakta bulunan `{token}` hedef metinde yok. "
                                "Şablon bozulursa çıktı çalışma zamanında hata verir."
                            ),
                            hint_tr=f"Çeviriye `{token}` parçasını aynen ekleyin.",
                        )
                    )

        for token in protected["url"] + protected["email"]:
            if token.casefold() not in _normalize(segment.target):
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        code="TOKEN_KAYIP",
                        rule="tokens",
                        segment_id=segment.id,
                        field=segment.field,
                        message_tr=f"Bağlantı/adres korunmamış: {token}",
                        detail_tr=f"Kaynakta bulunan `{token}` hedef metinde yok.",
                        hint_tr=f"Çeviriye `{token}` parçasını aynen ekleyin.",
                    )
                )

        specs = protected["quantity"] + protected["model"]
        seen: set[str] = set()
        for token in specs:
            digits = _digits(token)
            if not digits or digits in seen:
                continue
            seen.add(digits)
            if digits not in target_digits:
                findings.append(
                    Finding(
                        severity=Severity.WARNING,
                        code="SAYI_KAYIP",
                        rule="tokens",
                        segment_id=segment.id,
                        field=segment.field,
                        message_tr=f"Ölçü/model bilgisi kaybolmuş: {token.strip()}",
                        detail_tr=(f"Kaynakta `{token.strip()}` var; hedef metinde `{digits}` rakam dizisi geçmiyor."),
                        hint_tr="Ölçü ve model numaraları çevrilmez, aynen taşınır.",
                    )
                )

        if target_is_turkish:
            findings.extend(_number_format_findings(segment.id, segment.field, segment.target))

    # Kapsam: Türkçe hedefte sayı biçimi denetimi **her** segmentte çalışır, bu yüzden tüm
    # segmentler kapsama girer; İngilizce hedefte yalnızca korunan ifade içerenler.
    checked = len(context.catalog.segments) if target_is_turkish else interesting
    return RuleOutcome(rule="tokens", checked=checked, findings=tuple(findings))


_DOT_DECIMAL = re.compile(r"\b\d+\.\d+(?=\s*(?:cm|mm|kg|gr|ml|lt|gb|tb|mb|w|v|tl|₺))", re.IGNORECASE)
_COMMA_THOUSAND = re.compile(r"\b\d{1,3}(?:,\d{3})+\b")
_PERCENT_AFTER = re.compile(r"\b\d+\s?%")
_PERCENT_BEFORE = re.compile(r"%\s?\d+")


def _number_format_findings(segment_id: str, field: str, target: str) -> list[Finding]:
    """Turkish number conventions: decimal comma, dot thousands, `%` before the number."""
    findings: list[Finding] = []
    for pattern, code, message, hint in (
        (
            _DOT_DECIMAL,
            "NUM_AYIRICI",
            "Türkçe metinde ondalık ayırıcı virgül olmalı",
            "“2.5 kg” değil “2,5 kg” yazılır.",
        ),
        (
            _COMMA_THOUSAND,
            "NUM_AYIRICI",
            "Türkçe metinde binlik ayırıcı nokta olmalı",
            "“1,234.56 TL” değil “1.234,56 TL” yazılır.",
        ),
        (
            _PERCENT_AFTER,
            "YUZDE_KONUM",
            "Yüzde işareti sayının önüne gelir",
            "“20% indirim” değil “%20 indirim” yazılır.",
        ),
    ):
        for match in pattern.finditer(target):
            if code == "YUZDE_KONUM" and _PERCENT_BEFORE.search(target):
                continue  # metinde doğru biçim de varsa stil uyarısı tekrar edilmesin
            findings.append(
                Finding(
                    severity=Severity.INFO,
                    code=code,
                    rule="tokens",
                    segment_id=segment_id,
                    field=field,
                    message_tr=f"{message}: “{match.group(0).strip()}”",
                    detail_tr=f"Hedef metin: “{target}”",
                    hint_tr=hint,
                )
            )
    return findings
