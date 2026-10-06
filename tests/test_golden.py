"""Altın set: örneklerin kendisi, regresyon koşusu ve mutasyon testi."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from locale_gate.golden import load_golden, render_golden_text, run_case, run_golden


@pytest.mark.golden
def test_altin_set_beklenen_davranisi_verir(golden_dir: Path) -> None:
    result = run_golden(golden_dir)
    assert result.passed, render_golden_text(result)
    assert len(result.cases) == 3


@pytest.mark.golden
def test_vaka_dosyalari_mevcut(golden_dir: Path) -> None:
    for case in load_golden(golden_dir):
        assert (golden_dir / case.catalog).exists(), case.catalog
        if case.glossary:
            assert (golden_dir / case.glossary).exists(), case.glossary
        if case.config:
            assert (golden_dir / case.config).exists(), case.config


def test_temiz_vaka_hic_bulgu_uretmez(golden_dir: Path) -> None:
    result = run_golden(golden_dir)
    clean = next(case for case in result.cases if "temiz" in case.name)
    assert clean.gate_passed is True
    assert clean.score == 1.0
    assert clean.missing == {}
    assert clean.unexpected == {}


def test_altin_set_metni_ozet_verir(golden_dir: Path) -> None:
    text = render_golden_text(run_golden(golden_dir))
    assert "ALTIN SET" in text
    assert "3/3 vaka" in text


def test_mutasyon_yakalanir(golden_dir: Path, tmp_path: Path) -> None:
    """Beklenti bilerek yanlış yazılırsa regresyon koşusu kırmızıya dönmeli."""
    (tmp_path / "case").mkdir()
    (tmp_path / "case" / "catalog.json").write_text(
        json.dumps(
            {
                "source_locale": "tr",
                "target_locale": "en",
                "segments": [{"id": "M-1", "field": "title", "source": "Şişme mont", "target": "Puffer jacket"}],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "golden.json").write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "yanlış beklenti",
                        "catalog": "case/catalog.json",
                        "expected": {"M-1": ["TERM_EKSIK"]},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = run_golden(tmp_path)
    assert result.passed is False
    assert result.cases[0].missing["M-1"] == ("TERM_EKSIK",)
    assert "beklenen" in result.cases[0].mismatches[0]


def test_beklenmeyen_bulgu_da_hata(tmp_path: Path) -> None:
    (tmp_path / "case").mkdir()
    (tmp_path / "case" / "catalog.json").write_text(
        json.dumps(
            {
                "source_locale": "tr",
                "target_locale": "en",
                "segments": [
                    {"id": "M-1", "field": "title", "source": "Sipariş {id} yolda", "target": "Order on the way"}
                ],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "golden.json").write_text(
        json.dumps({"cases": [{"name": "fazla bulgu", "catalog": "case/catalog.json", "expected": {"M-1": []}}]}),
        encoding="utf-8",
    )
    result = run_golden(tmp_path)
    assert result.passed is False
    assert result.cases[0].unexpected["M-1"] == ("TOKEN_KAYIP",)


def test_kod_sayisi_beklentisi(tmp_path: Path) -> None:
    (tmp_path / "case").mkdir()
    (tmp_path / "case" / "catalog.json").write_text(
        json.dumps(
            {
                "source_locale": "tr",
                "target_locale": "en",
                "segments": [{"id": "M-1", "field": "title", "source": "Ürün", "target": "Urun"}],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "golden.json").write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "name": "kod sayısı",
                        "catalog": "case/catalog.json",
                        "expected": {"M-1": ["TR_DIAKRITIK"]},
                        "expect_codes": {"TR_DIAKRITIK": 5},
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    result = run_golden(tmp_path)
    assert result.passed is False
    assert any("kod TR_DIAKRITIK" in mismatch for mismatch in result.cases[0].mismatches)


def test_kapi_karari_beklentisi_kontrol_edilir(golden_dir: Path) -> None:
    case = load_golden(golden_dir)[0]
    mutated = case.model_copy(update={"expect_passed": True})
    result = run_case(mutated, golden_dir)
    assert result.passed is False
    assert any("kapı kararı" in mismatch for mismatch in result.mismatches)


def test_olmayan_altin_set_dosyasi(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="altın set dosyası yok"):
        load_golden(tmp_path)


def test_gecersiz_altin_set_dosyasi(tmp_path: Path) -> None:
    path = tmp_path / "golden.json"
    path.write_text(json.dumps({"cases": None}), encoding="utf-8")
    with pytest.raises(ValueError, match="cases"):
        load_golden(tmp_path)
