"""Kural 3 — Türkçe yazım: diakritikler, `i/İ` büyük harf kuralı ve kaynak sızıntısı.

İki yönlü çalışır:

* **hedef Türkçe:** ASCII'ye düşmüş kelimeleri (`urun` ↔ `ürün`) ve `i → İ` büyük harf kuralını
  denetler. Yalnızca kaynak metinde doğru yazım geçiyorsa uyarır — böylece "aslında doğru olan"
  kelimeyi yanlışlıkla hatalı saymaz.
* **hedef İngilizce:** Türkçe karakter sızıntısını ve hiç çevrilmemiş segmentleri yakalar.
"""

from __future__ import annotations

import re

from locale_gate.catalog import Segment
from locale_gate.models import Finding, Severity
from locale_gate.rules.context import RuleContext, RuleOutcome

TR_LETTERS = "çğıöşüÇĞİÖŞÜ"
TR_LETTER_RE = re.compile(f"[{TR_LETTERS}]")

# Türkçe e-ticaret metinlerinde en sık ASCII'ye düşen kelimeler (doğru yazım → yaygın hata).
FOLDED_PAIRS: tuple[tuple[str, str], ...] = (
    ("ürün", "urun"),
    ("ürünler", "urunler"),
    ("yoğun", "yogun"),
    ("şişme", "sisme"),
    ("göğüs", "gogus"),
    ("çerçeve", "cerceve"),
    ("kumaş", "kumas"),
    ("düğme", "dugme"),
    ("yıkama", "yikama"),
    ("ölçü", "olcu"),
    ("ölçüler", "olculer"),
    ("görsel", "gorsel"),
    ("güvenli", "guvenli"),
    ("kişi", "kisi"),
    ("çiçek", "cicek"),
    ("baskı", "baski"),
    ("hızlı", "hizli"),
    ("ışık", "isik"),
    ("seçenek", "secenek"),
    ("keşfedin", "kesfedin"),
    ("ücretsiz", "ucretsiz"),
    ("kırılmaz", "kirilmaz"),
    ("sıcak", "sicak"),
    ("ışıltılı", "isiltili"),
    ("gömlek", "gomlek"),
    ("tüy", "tuy"),
    ("şık", "sik"),
    ("ısı", "isi"),
)

_WORD = re.compile(r"[^\W\d_]+", re.UNICODE)

# Türkçede kesin `i` ile yazılan, İngilizce metinde büyük harfle geçebilen özel adlar.
KNOWN_DOTTED_I_PROPER_NOUNS: frozenset[str] = frozenset(
    {"istanbul", "izmir", "izmit", "iskenderun", "inegol", "inegöl", "istanbullu"}
)


def _folded_pattern(folded: str) -> re.Pattern[str]:
    """ASCII karşılığı 5 harften uzunsa ek alabilir; kısa olanlar tam kelime aranır.

    Türkçe eklemeli bir dildir: "olculer" gerçekte "Olculeri" olarak yazılır, bu yüzden uzun
    karşılıklarda sağdan sınır aranmaz. Kısa ve tehlikeli olanlarda ("ısı" → "isi" aynı zamanda
    "isim"in başlangıcıdır) tam kelime eşleşmesi şart koşulur.
    """
    if len(folded) >= 5:
        return re.compile(rf"(?<![^\W\d_]){re.escape(folded)}", re.IGNORECASE)
    return re.compile(rf"(?<![^\W\d_]){re.escape(folded)}(?![^\W\d_])", re.IGNORECASE)


def _exercise_diacritics(segment: Segment, *, target_locale: str) -> list[Finding]:
    findings: list[Finding] = []
    source_folded = segment.source.casefold()
    for correct, folded in FOLDED_PAIRS:
        # Kaynak doğru yazımı içeriyorsa, hedefteki ASCII biçimi hatadır (yön: TR → X).
        if correct.casefold() in source_folded and _folded_pattern(folded).search(segment.target):
            findings.append(
                Finding(
                    severity=Severity.WARNING,
                    code="TR_DIAKRITIK",
                    rule="turkish",
                    segment_id=segment.id,
                    field=segment.field,
                    message_tr=f"Diakritik düşmüş: “{folded}” → “{correct}”",
                    detail_tr="Türkçe metinde harf işaretleri korunmalı; arama ve SEO bu harflere duyarlıdır.",
                    hint_tr=f"Hedef metindeki “{folded}” kelimesini “{correct}” olarak düzeltin.",
                )
            )
    if target_locale == "tr":
        findings.extend(_exercise_dotted_i(segment))
    return findings


def _exercise_dotted_i(segment: Segment) -> list[Finding]:
    """`i` harfinin büyük hâli `İ`dir; `I` yalnızca `ı` harfinden gelir.

    Belirsizlik yönetimi: kaynak kelime küçük harfle geçiyorsa ("istanbul") `i → İ` kesin bir
    kuraldır. Kaynak kelime büyük harfle geçiyorsa ("Istanbul") `i` mi `ı` mı olduğu yazıdan
    anlaşılmaz; bu durumda yalnızca Türkçede kesin `i` ile yazılan özel adlar için uyarılır
    (Isparta → ı, İstanbul → i). Böylece "doğru olanı hatalı sayma" riski ortadan kalkar.
    """
    findings: list[Finding] = []
    source_words = {word.casefold() for word in _WORD.findall(segment.source)}
    source_lower_words = {word.casefold() for word in _WORD.findall(segment.source) if word[:1].islower()}
    for word in _WORD.findall(segment.target):
        if len(word) < 2 or word != word.upper() or not word.startswith("I"):
            continue
        candidate = word.casefold().replace("ı", "i")
        if not candidate.startswith("i"):
            continue
        exact_source = candidate in source_words
        lower_source = candidate in source_lower_words
        known_name = candidate in KNOWN_DOTTED_I_PROPER_NOUNS
        if not (exact_source and (lower_source or known_name)):
            continue
        findings.append(
            Finding(
                severity=Severity.WARNING,
                code="TR_BUYUK_I",
                rule="turkish",
                segment_id=segment.id,
                field=segment.field,
                message_tr=f"Büyük harf kuralı: “{word}” → “İ{word[1:]}”",
                detail_tr="Türkçede “i”nin büyüğü “İ”, “ı”nın büyüğü “I”dır; ASCII katlaması bunu bozar.",
                hint_tr=f"Kelimeyi “İ{word[1:]}” olarak yazın.",
            )
        )
    return findings


def _exercise_leakage(segment: Segment) -> list[Finding]:
    """English target: Turkish characters and identical source/target mean unlocalized content."""
    findings: list[Finding] = []
    normalized_source = re.sub(r"\s+", " ", segment.source).strip()
    normalized_target = re.sub(r"\s+", " ", segment.target).strip()
    if normalized_source == normalized_target and TR_LETTER_RE.search(segment.source) and len(segment.source) > 12:
        findings.append(
            Finding(
                severity=Severity.CRITICAL,
                code="CEVRILMEMIS",
                rule="turkish",
                segment_id=segment.id,
                field=segment.field,
                message_tr="Segment çevrilmemiş görünüyor",
                detail_tr=f"Hedef metin kaynakla birebir aynı: “{segment.target}”",
                hint_tr="Bu alanı hedef dile çevirin ya da bilinçli olarak dışarıda bırakıldıysa segmenti işaretleyin.",
            )
        )
    elif TR_LETTER_RE.search(segment.target):
        findings.append(
            Finding(
                severity=Severity.WARNING,
                code="TR_KARAKTER",
                rule="turkish",
                segment_id=segment.id,
                field=segment.field,
                message_tr="Hedef metinde Türkçe karakter var",
                detail_tr=f"“{segment.target}” içinde çevrilmemiş Türkçe ifade olabilir.",
                hint_tr="İlgili kelimeyi hedef dile çevirin (marka/model adları istisnadır).",
            )
        )
    return findings


def check(context: RuleContext) -> RuleOutcome:
    """Run the Turkish-specific checks in the direction the catalog declares."""
    target_locale = context.catalog.target_locale
    findings: list[Finding] = []
    for segment in context.catalog.segments:
        if target_locale == "en":
            findings.extend(_exercise_leakage(segment))
        findings.extend(_exercise_diacritics(segment, target_locale=target_locale))
    return RuleOutcome(rule="turkish", checked=len(context.catalog.segments), findings=tuple(findings))
