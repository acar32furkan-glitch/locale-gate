"""Kapı: skor matematiği, karar mantığı ve girdi doğrulaması."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from locale_gate.catalog import Catalog
from locale_gate.config import GateConfig
from locale_gate.gate import GateInputError, decide, run_gate
from locale_gate.models import Severity
from tests.factories import make_catalog, make_glossary, make_segment, make_term

NOW = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)


def failing_catalog() -> Catalog:
    """Bir kritik (yer tutucu kaybı), bir uyarı (uzun başlık) ve bir temiz segment."""
    return make_catalog(
        [
            make_segment("S-1", source="Sipariş {order_id} yolda", target="Your order is on the way"),
            make_segment("S-2", source="Kısa kaynak", target="x" * 200),
            make_segment("S-3", source="Pamuklu tişört", target="Cotton t-shirt"),
        ],
        field_limits={"title": 70},
    )


def test_bulgu_yoksa_skor_bir() -> None:
    report = run_gate(
        make_catalog([make_segment("S-1", source="Pamuklu tişört", target="Cotton t-shirt")]),
        now=NOW,
    )
    assert report.score == 1.0
    assert report.findings == ()
    assert report.segments == 1
    assert report.generated_at == NOW


def test_bulgular_onem_sirasina_gore_siralanir() -> None:
    report = run_gate(failing_catalog(), now=NOW)
    severities = [finding.severity for finding in report.findings]
    assert severities == sorted(severities, key=lambda s: {"critical": 0, "warning": 1, "info": 2}[s.value])
    assert report.critical_count == 1


def test_skor_segment_basari_orani_uzerinden_hesaplanir() -> None:
    """Tek segmentte üç bulgu olsa bile kural en fazla o segment kadar cezalanır, skor negatife düşmez."""
    catalog = make_catalog(
        [
            make_segment(
                "S-1",
                source="Ürün {a} {b} 45 x 30 cm",
                target="Product details and measurements of this item in detail",
            )
        ],
        field_limits={"title": 200},
    )
    report = run_gate(catalog, now=NOW)
    assert len(report.findings) == 3  # {a}, {b} ve 45 x 30 cm
    assert 0.0 <= report.score <= 1.0
    tokens = report.stat_for("tokens")
    assert tokens is not None
    assert tokens.failed == 3
    assert tokens.failed_segments == 1
    assert tokens.score == 0.0  # eski formülle burada skor -2.0 çıkardı


def test_kapsami_olmayan_kural_skoru_etkilemez() -> None:
    """Sözlük boşsa terminology kuralı ne skora ne karara girer."""
    report = run_gate(
        make_catalog([make_segment("S-1", source="Temiz metin", target="Clean text")]),
        now=NOW,
    )
    terminology = report.stat_for("terminology")
    assert terminology is not None
    assert terminology.checked == 0
    assert terminology.score == 1.0


def test_bilgi_bulgu_kapiyi_dusurmez_ama_skoru_etkiler() -> None:
    catalog = make_catalog(
        [make_segment("S-1", source="Weight is here", target="Ağırlık 2.5 kg", field="bullet")],
        source_locale="en",
        target_locale="tr",
    )
    report = run_gate(catalog, now=NOW)
    assert report.count(Severity.INFO) == 1
    assert report.critical_count == 0
    passed, reasons = decide(report, GateConfig(gate=0.99))
    assert passed is False
    assert "eşik" in reasons[0]
    passed_low, _ = decide(report, GateConfig(gate=0.4))
    assert passed_low is True
    assert report.score < 0.99  # bilgi bulgusu skoru düşürür ama kapıyı tek başına düşürmez


def test_kritik_bulgu_tek_basina_kapiyi_dusurur() -> None:
    config = GateConfig(gate=0.0, fail_on_critical=True)
    report = run_gate(failing_catalog(), config=config, now=NOW)
    passed, reasons = decide(report, config)
    assert passed is False
    assert any("kritik" in reason for reason in reasons)


def test_fail_on_critical_kapatilabilir() -> None:
    config = GateConfig(gate=0.0, fail_on_critical=False)
    report = run_gate(failing_catalog(), config=config, now=NOW)
    passed, reasons = decide(report, config)
    assert passed is True
    assert reasons == []


def test_fail_under_esigi_gecici_olarak_degistirir() -> None:
    report = run_gate(failing_catalog(), now=NOW)
    assert decide(report, GateConfig())[0] is False
    assert decide(report, GateConfig(), fail_under=0.01)[0] is False  # kritik bulgu hâlâ var
    ok, _ = decide(report, GateConfig(fail_on_critical=False), fail_under=0.01)
    assert ok is True


def test_ayni_dil_cifti_reddedilir() -> None:
    catalog = make_catalog([make_segment("S-1", source="a", target="b")], source_locale="tr", target_locale="tr")
    with pytest.raises(GateInputError, match="aynı"):
        run_gate(catalog, now=NOW)


def test_desteklenmeyen_dil_reddedilir() -> None:
    catalog = make_catalog([make_segment("S-1", source="a", target="b")], target_locale="de")
    with pytest.raises(GateInputError, match="desteklenmeyen dil"):
        run_gate(catalog, now=NOW)


def test_sozluk_dil_cifti_uyusmuyorsa_hata() -> None:
    glossary = make_glossary([make_term("kargo", target="shipping")], source_locale="tr", target_locale="de")
    with pytest.raises(GateInputError, match="dil çifti"):
        run_gate(make_catalog([make_segment("S-1", source="kargo", target="shipping")]), glossary, now=NOW)


def test_ayni_girdi_ayni_cikti() -> None:
    first = run_gate(failing_catalog(), now=NOW)
    second = run_gate(failing_catalog(), now=NOW)
    assert first.findings == second.findings
    assert first.score == second.score
    assert first.stats == second.stats


def test_rapor_yardimcilari() -> None:
    report = run_gate(failing_catalog(), now=NOW)
    assert report.by_code().get("TOKEN_KAYIP") == 1
    assert report.stat_for("tokens") is not None
    assert report.stat_for("yok") is None
    assert report.count(Severity.WARNING) >= 1


def test_bos_katalog_sifir_bolme_hatasi_vermez() -> None:
    report = run_gate(make_catalog([]), now=NOW)
    assert report.score == 1.0
    assert report.segments == 0
