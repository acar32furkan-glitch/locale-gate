"""Kural 3 (turkish): diakritikler, `i/İ` büyük harf kuralı ve çevrilmemiş içerik."""

from __future__ import annotations

from locale_gate.rules.turkish import check
from tests.factories import codes, make_context, make_segment


def test_diakritik_dusmesi_yakalanir() -> None:
    context = make_context([make_segment("S-1", source="Ürün ölçüleri", target="Urun Olculeri")], target_locale="tr")
    findings = check(context).findings
    assert codes(findings) == ["TR_DIAKRITIK"]
    assert len(findings) == 2  # urun + olculer


def test_kaynakta_dogru_yazim_yoksa_uyarilmaz() -> None:
    """Kaynak zaten ASCII ise kural tahmin yürütmez."""
    context = make_context(
        [make_segment("S-1", source="Urun ozellikleri", target="Urun ozellikleri")], target_locale="tr"
    )
    assert codes(check(context).findings) == []


def test_dogru_diakritikli_ceviri_sorun_degil() -> None:
    context = make_context(
        [make_segment("S-1", source="Ürün ölçüleri", target="Ürün ölçüleri burada")], target_locale="tr"
    )
    assert check(context).findings == ()


def test_turkce_buyuk_harf_kurali() -> None:
    context = make_context(
        [make_segment("S-1", source="Delivery in Istanbul", target="ISTANBUL'DA TESLİM")],
        source_locale="en",
        target_locale="tr",
    )
    findings = check(context).findings
    assert codes(findings) == ["TR_BUYUK_I"]
    assert "İSTANBUL" in findings[0].message_tr


def test_noktasiz_i_ile_baslayan_kelime_uyari_uretmez() -> None:
    """`ı` harfinin büyüğü `I`dır; burada hata yok."""
    context = make_context(
        [make_segment("S-1", source="Delivery to Isparta", target="ISPARTA'YA TESLİM")],
        source_locale="en",
        target_locale="tr",
    )
    assert check(context).findings == ()


def test_cevrilmemis_segment_kritik() -> None:
    context = make_context([make_segment("S-1", source="Kadın Kışlık Şişme Mont", target="Kadın Kışlık Şişme Mont")])
    findings = check(context).findings
    assert codes(findings) == ["CEVRILMEMIS"]
    assert findings[0].severity.value == "critical"


def test_kisa_ayni_metin_cevrilmemis_sayilmaz() -> None:
    context = make_context([make_segment("S-1", source="iPhone", target="iPhone")])
    assert check(context).findings == ()


def test_ingilizce_hedefte_turkce_karakter_uyarisi() -> None:
    context = make_context(
        [make_segment("S-1", source="Ürün açıklaması", target="Product description with ürün inside")]
    )
    assert codes(check(context).findings) == ["TR_KARAKTER"]


def test_turkce_hedefte_sizinti_kurali_calismaz() -> None:
    context = make_context(
        [make_segment("S-1", source="Product details", target="Ürün detayları")],
        source_locale="en",
        target_locale="tr",
    )
    assert check(context).findings == ()


def test_buyuk_i_kurali_yalnizca_turkce_hedefte() -> None:
    context = make_context(
        [make_segment("S-1", source="Delivery in Istanbul", target="ISTANBUL DELIVERY")],
        source_locale="en",
        target_locale="en",
    )
    assert check(context).findings == ()


def test_kapsam_tum_segmentleri_sayar() -> None:
    context = make_context([make_segment("S-1", source="a", target="b"), make_segment("S-2", source="c", target="d")])
    assert check(context).checked == 2
