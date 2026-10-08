"""Kural 2 (tokens): yer tutucular, etiketler, ölçüler ve Türkçe sayı biçimi."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from locale_gate.config import GateConfig
from locale_gate.gate import run_gate
from locale_gate.rules.tokens import check, protect
from tests.factories import codes, make_catalog, make_context, make_segment

NOW = datetime(2026, 10, 8, 21, 0, tzinfo=UTC)


def test_yer_tutucular_korunursa_sorun_yok() -> None:
    context = make_context(
        [
            make_segment(
                "S-1",
                source="Sipariş {order_id} 2 gün içinde kargoda",
                target="Order {order_id} ships in 2 days",
            )
        ]
    )
    assert check(context).findings == ()


def test_kaybolan_yer_tutucu_kritik() -> None:
    context = make_context(
        [make_segment("S-1", source="Sipariş {order_id} kargoda", target="Your order is on the way")]
    )
    outcome = check(context)
    assert codes(outcome.findings) == ["TOKEN_KAYIP"]
    assert outcome.findings[0].severity.value == "critical"
    assert "{order_id}" in outcome.findings[0].message_tr


def test_html_etiketi_kaybi_kritik() -> None:
    context = make_context([make_segment("S-1", source="<b>İndirim</b> başladı", target="Discount started")])
    findings = check(context).findings
    assert codes(findings) == ["TOKEN_KAYIP"]
    assert any("<b>" in finding.message_tr for finding in findings)


def test_baglanti_ve_eposta_kaybi_uyari() -> None:
    context = make_context(
        [
            make_segment(
                "S-1",
                source="Detay: https://ornek.com/iade veya destek@ornek.com",
                target="Details on our returns page",
            )
        ]
    )
    findings = check(context).findings
    assert codes(findings) == ["TOKEN_KAYIP"]
    assert {finding.severity.value for finding in findings} == {"warning"}
    assert len(findings) == 2  # bağlantı + e-posta


def test_kaybolan_olcu_uyari_uretir() -> None:
    context = make_context(
        [
            make_segment(
                "S-1",
                source="45 x 30 x 12 cm ölçülerinde, 780 gram",
                target="Measures 45 x 30 x 12 cm and weighs 0.78 kg",
            )
        ]
    )
    findings = check(context).findings
    assert codes(findings) == ["SAYI_KAYIP"]
    assert "780" in findings[0].message_tr


def test_ondalik_ayirici_degisimi_gecerlidir() -> None:
    """2,5 kg → 2.5 kg ayırıcı yerelleşmesidir; rakam dizisi aynı kaldığı için bulgu olmamalı."""
    context = make_context([make_segment("S-1", source="2,5 kg ağırlık", target="2.5 kg weight")])
    assert check(context).findings == ()


def test_model_numarasi_korunmali() -> None:
    context = make_context([make_segment("S-1", source="Model B-2000, 256 GB", target="Model B-2000 with storage")])
    assert codes(check(context).findings) == ["SAYI_KAYIP"]


def test_ayni_rakam_dizisi_tekrar_eden_bulgu_uretmez() -> None:
    context = make_context([make_segment("S-1", source="256 GB ve 256 GB", target="256 GB storage")])
    assert check(context).findings == ()


@pytest.mark.parametrize(
    ("target", "expected"),
    [
        ("Ağırlık 2,5 kg", []),  # Türkçe doğru biçim
        ("Ağırlık 2.5 kg", ["NUM_AYIRICI"]),  # nokta ondalık
        ("Toplam 1.234,56 TL", []),  # Türkçe doğru binlik/ondalık
        ("Toplam 1,234.56 TL", ["NUM_AYIRICI"]),  # İngilizce biçim sızmış
        ("Bugün %20 indirim", []),
        ("Bugün 20% indirim", ["YUZDE_KONUM"]),
    ],
)
def test_turkce_sayi_bicimi(target: str, expected: list[str]) -> None:
    context = make_context(
        [make_segment("S-1", source="Source text here", target=target)],
        target_locale="tr",
    )
    assert codes(check(context).findings) == expected


def test_ingilizce_hedefte_turkce_sayi_kurali_calismaz() -> None:
    context = make_context([make_segment("S-1", source="Kaynak", target="Weight 2.5 kg")], target_locale="en")
    assert check(context).findings == ()


def test_kapsam_yalnizca_korunan_ifade_olan_segmentleri_sayar() -> None:
    context = make_context(
        [
            make_segment("S-1", source="45 cm uzunluk", target="45 cm length"),
            make_segment("S-2", source="Sadece metin", target="Just text"),
        ]
    )
    assert check(context).checked == 1


def test_placeholder_cesitleri_taninir() -> None:
    protected = protect("Değer {price}, %s, %(count)s, {{ name }}, ${amount}")
    assert protected["placeholder"] == ["{price}", "%s", "%(count)s", "{{ name }}", "${amount}"]


def test_ayni_segmentte_bes_bulgu_skoru_sifira_kirpar() -> None:
    """Tek segment beş farklı kayıp üretse bile kural en fazla bir segment cezalanır.

    `%(count)s` yerine geçen `%s`, açılış/kapanış etiketleri, bağlantı ve ölçü aynı segmentte
    kaybolduğunda beş bulgu çıkar; skor formülü bunu segment üzerinden saydığı için 0.0'da kalır
    (ham bulgu sayısıyla bölünseydi skor negatife düşerdi).
    """
    catalog = make_catalog(
        [
            make_segment(
                "S-1",
                source="<b>%s</b> https://ornek.co 45 cm",
                target="Translation text",
            )
        ]
    )
    report = run_gate(catalog, now=NOW)
    tokens = report.stat_for("tokens")
    assert tokens is not None
    assert tokens.failed == 5  # %s · <b> · </b> · bağlantı · 45 cm
    assert tokens.failed_segments == 1
    assert tokens.score == 0.0  # 1.0 - (1/1); kırpılma sayesinde negatife düşmez
    assert 0.0 <= report.score <= 1.0


def test_kapsam_sifir_olan_tokens_kurali_skora_girmez() -> None:
    """Kapsamı olmayan kuralın skoru 1.0 kalır ama ağırlıklı ortalamaya girmez.

    Korunan ifade içermeyen katalogda tokens kapsamı 0'dır; yoksa "hiç denenmemiş" kural skoru
    yapay olarak yükseltirdi.
    """
    catalog = make_catalog([make_segment("S-1", source="Kısa kaynak", target="x" * 200)])
    report = run_gate(catalog, now=NOW)

    tokens = report.stat_for("tokens")
    assert tokens is not None
    assert tokens.checked == 0
    assert tokens.score == 1.0

    # Yalnızca kapsamı olan kurallar skora girer: length (sınır aşıldı → 0.0) ve turkish (temiz
    # → 1.0). tokens'ın 1.0'ı bu ortalamaya karışmamalı.
    weights = GateConfig().normalized_weights()
    covered = [stat for stat in report.stats if weights.get(stat.rule, 0.0) > 0 and stat.checked > 0]
    assert {stat.rule for stat in covered} == {"length", "turkish"}
    total = sum(weights[stat.rule] for stat in covered)
    expected = sum(weights[stat.rule] * stat.score for stat in covered) / total
    assert report.score == round(expected, 4)


@pytest.mark.parametrize(
    ("source", "target", "source_locale", "target_locale"),
    [
        ("Weight 2.5 kg", "Ağırlık 2,5 kg", "en", "tr"),  # ayırıcı virgüle yerelleşti
        ("Ağırlık 2,5 kg", "Weight 2.5 kg", "tr", "en"),  # ayırıcı noktaya yerelleşti
    ],
)
def test_ondalik_ayirici_yerellesmesi_her_iki_yonde_kabul_edilir(
    source: str, target: str, source_locale: str, target_locale: str
) -> None:
    """Sayı karşılaştırması rakam dizisi üzerinden yapılır: `2,5 kg` ↔ `2.5 kg` kabul edilir."""
    context = make_context(
        [make_segment("S-1", source=source, target=target)],
        source_locale=source_locale,
        target_locale=target_locale,
    )
    assert check(context).findings == ()
