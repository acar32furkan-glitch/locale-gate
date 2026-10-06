"""Kural 4 (length): alan sınırı ve uzama oranı sınır davranışları."""

from __future__ import annotations

from locale_gate.config import GateConfig
from locale_gate.rules.length import MIN_EXPANSION_SOURCE_LEN, check
from tests.factories import codes, make_context, make_segment

SOURCE = "Bu ürünün kumaşı nefes alır ve kolayca kırışmaz"  # 46 karakter


def test_sinir_tam_kenarinda_bulgu_uretmez() -> None:
    context = make_context([make_segment("S-1", source=SOURCE, target="x" * 70)], field_limits={"title": 70})
    assert check(context).findings == ()


def test_sinir_asan_hedef_uyari_uretir() -> None:
    context = make_context([make_segment("S-1", source=SOURCE, target="x" * 71)], field_limits={"title": 70})
    findings = check(context).findings
    assert codes(findings) == ["LENGTH_SINIR"]
    assert "71/70" in findings[0].message_tr


def test_segment_kendi_limitini_getirirse_o_kullanilir() -> None:
    context = make_context(
        [make_segment("S-1", source=SOURCE, target="x" * 40, limit=30)],
        field_limits={"title": 70},
    )
    assert codes(check(context).findings) == ["LENGTH_SINIR"]


def test_uzama_orani_asilirsa_uyari() -> None:
    long_target = "x" * 80
    context = make_context(
        [make_segment("S-1", source=SOURCE, target=long_target)],
        config=GateConfig(max_expansion=1.2, field_limits={"title": 500}),
        field_limits={"title": 500},
    )
    assert codes(check(context).findings) == ["LENGTH_UZAMA"]


def test_kisa_kaynakta_uzama_olculmez() -> None:
    context = make_context(
        [make_segment("S-1", source="Deri Cüzdan", target="Genuine Leather Wallet with RFID Protection")],
        field_limits={"title": 200},
    )
    assert check(context).findings == ()


def test_uzama_kurali_alt_siniri() -> None:
    assert MIN_EXPANSION_SOURCE_LEN == 25
    context = make_context(
        [make_segment("S-1", source="u" * 24, target="t" * 200)],
        config=GateConfig(max_expansion=1.1, field_limits={"title": 500}),
    )
    assert check(context).findings == ()


def test_limit_yoksa_ve_kaynak_boss_denetlenmez() -> None:
    context = make_context(
        [make_segment("S-1", source="", target="")],
        config=GateConfig(field_limits={}),
    )
    outcome = check(context)
    assert outcome.findings == ()
    assert outcome.checked == 0


def test_kapsam_limiti_olan_segmentleri_sayar() -> None:
    context = make_context(
        [
            make_segment("S-1", source="kaynak metin", target="target text"),
            make_segment("S-2", field="bilinmeyen", source="kaynak", target="target"),
        ],
        field_limits={"title": 70},
    )
    assert check(context).checked == 2  # ikisi de kaynak vermiş, sınır yoksa da uzama ölçülür
