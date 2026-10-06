"""Kural 1 (terminology): sözlük karşılıkları ve yasaklı varyantlar."""

from __future__ import annotations

from locale_gate.rules.terminology import check
from tests.factories import codes, make_context, make_glossary, make_segment, make_term

GLOSSARY = make_glossary(
    [
        make_term("kargo ücreti", target="shipping fee", forbidden=("cargo fee",), note="Ödeme sayfası"),
        make_term("şişme mont", target="puffer jacket", forbidden=("puffer coat",)),
        make_term("yıkanabilir", target="washable"),
    ]
)


def test_uygun_ceviri_bulgu_uretmez() -> None:
    context = make_context(
        [make_segment("S-1", source="Kargo ücreti alınmaz", target="No shipping fee is charged")],
        glossary=GLOSSARY,
    )
    assert check(context).findings == ()


def test_zorunlu_karsilik_eksikse_kritik_bulgu() -> None:
    context = make_context(
        [make_segment("S-1", source="Kargo ücreti alınmaz", target="Delivery is free")],
        glossary=GLOSSARY,
    )
    outcome = check(context)
    assert codes(outcome.findings) == ["TERM_EKSIK"]
    assert outcome.findings[0].severity.value == "critical"
    assert outcome.findings[0].segment_id == "S-1"
    assert "shipping fee" in outcome.findings[0].message_tr
    assert "Ödeme sayfası" in outcome.findings[0].hint_tr
    assert outcome.checked == 1


def test_yasakli_varyant_uyari_uretir() -> None:
    context = make_context(
        [make_segment("S-1", source="Kargo ücreti alınmaz", target="No cargo fee charged")],
        glossary=GLOSSARY,
    )
    assert codes(check(context).findings) == ["TERM_EKSIK", "TERM_YASAK"]


def test_yalnizca_yasakli_kontrolu_olan_terim() -> None:
    glossary = make_glossary([make_term("marka adı", forbidden=("brand name",))])
    context = make_context(
        [make_segment("S-1", source="Marka adı değişebilir", target="Brand name may change")],
        glossary=glossary,
    )
    assert codes(check(context).findings) == ["TERM_YASAK"]


def test_terim_kaynakta_yoksa_denetlenmez() -> None:
    context = make_context(
        [make_segment("S-1", source="Sadece pamuklu tişört", target="Just a cotton t-shirt")],
        glossary=GLOSSARY,
    )
    outcome = check(context)
    assert outcome.findings == ()
    assert outcome.checked == 0  # kapsam yok → bu kural skoru etkilemez


def test_birden_fazla_terim_ayni_segmentte() -> None:
    context = make_context(
        [make_segment("S-1", source="Şişme mont, yıkanabilir", target="Puffer jacket, machine wash")],
        glossary=GLOSSARY,
    )
    assert codes(check(context).findings) == ["TERM_EKSIK"]


def test_terim_yalnizca_ilgili_segmentte_denetlenir() -> None:
    context = make_context(
        [
            make_segment("S-1", source="Kargo ücreti", target="Shipping fee"),
            make_segment("S-2", source="Yıkanabilir kumaş", target="Fabric"),
        ],
        glossary=GLOSSARY,
    )
    outcome = check(context)
    assert outcome.checked == 2
    assert [finding.segment_id for finding in outcome.findings] == ["S-2"]
