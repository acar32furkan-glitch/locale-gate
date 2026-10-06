"""Kural 2 (tokens): yer tutucular, etiketler, ölçüler ve Türkçe sayı biçimi."""

from __future__ import annotations

import pytest

from locale_gate.rules.tokens import check, protect
from tests.factories import codes, make_context, make_segment


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
