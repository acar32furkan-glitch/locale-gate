"""CLI sözleşmesi: çıkış kodları, JSON çıktısı, rapor dosyası ve iş özeti."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest

from locale_gate.cli import main

CLEAN = "temiz/catalog.json"
CLEAN_GLOSSARY = "temiz/glossary.yaml"
CLEAN_CONFIG = "temiz/config.toml"
DIRTY = "tr_en_temel/catalog.json"
DIRTY_GLOSSARY = "tr_en_temel/glossary.yaml"


def test_temiz_katalog_gecer(capsys: pytest.CaptureFixture[str], golden_dir: Path) -> None:
    code = main(
        [
            "check",
            str(golden_dir / CLEAN),
            "--glossary",
            str(golden_dir / CLEAN_GLOSSARY),
            "--config",
            str(golden_dir / CLEAN_CONFIG),
        ]
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "KARAR: GEÇTİ" in out
    assert "skor: 1.000" in out


def test_kusurlu_katalog_kapiyi_dusurur(capsys: pytest.CaptureFixture[str], golden_dir: Path) -> None:
    code = main(["check", str(golden_dir / DIRTY), "--glossary", str(golden_dir / DIRTY_GLOSSARY)])
    out = capsys.readouterr().out
    assert code == 1
    assert "KARAR: KALDI" in out
    assert "TERM_EKSIK" in out


def test_json_cikti_sozlesmesi(capsys: pytest.CaptureFixture[str], golden_dir: Path) -> None:
    main(
        [
            "check",
            str(golden_dir / DIRTY),
            "--glossary",
            str(golden_dir / DIRTY_GLOSSARY),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) >= {
        "version",
        "score",
        "passed",
        "findings",
        "stats",
        "codes",
        "source_locale",
        "target_locale",
    }
    assert payload["passed"] is False
    assert any(item["code"] == "TERM_EKSIK" for item in payload["findings"])
    assert all("message_tr" in item for item in payload["findings"])


def test_rapor_dosyasi_yazilir(tmp_path: Path, golden_dir: Path) -> None:
    target = tmp_path / "out" / "report.json"
    main(
        [
            "check",
            str(golden_dir / CLEAN),
            "--glossary",
            str(golden_dir / CLEAN_GLOSSARY),
            "--report",
            str(target),
            "--json",
        ]
    )
    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["passed"] is True


def test_github_ozeti_yazilir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, golden_dir: Path) -> None:
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    main(
        [
            "check",
            str(golden_dir / DIRTY),
            "--glossary",
            str(golden_dir / DIRTY_GLOSSARY),
            "--github-summary",
        ]
    )
    text = summary.read_text(encoding="utf-8")
    assert "### Çeviri kalite kapısı" in text
    assert "KALDI" in text


def test_github_ozeti_ortam_degiskeni_yoksa_uyari(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], golden_dir: Path
) -> None:
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    main(["check", str(golden_dir / CLEAN), "--github-summary"])
    assert "GITHUB_STEP_SUMMARY tanımlı değil" in capsys.readouterr().err


def test_fail_under_ile_kapi_gecilebilir(golden_dir: Path) -> None:
    assert main(["check", str(golden_dir / DIRTY), "--glossary", str(golden_dir / DIRTY_GLOSSARY)]) == 1
    code = main(
        [
            "check",
            str(golden_dir / DIRTY),
            "--glossary",
            str(golden_dir / DIRTY_GLOSSARY),
            "--fail-under",
            "0.1",
        ]
    )
    assert code == 1  # kritik bulgu hâlâ var


def test_max_findings_siniri(capsys: pytest.CaptureFixture[str], golden_dir: Path) -> None:
    main(
        [
            "check",
            str(golden_dir / DIRTY),
            "--glossary",
            str(golden_dir / DIRTY_GLOSSARY),
            "--max-findings",
            "1",
        ]
    )
    out = capsys.readouterr().out
    assert "bugu daha var" in out or "bulgu daha var" in out


def test_olmayan_katalog_girdi_hatasi(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    code = main(["check", str(tmp_path / "yok.json")])
    assert code == 2
    assert "dosya bulunamadı" in capsys.readouterr().err


def test_ayni_dil_cifti_girdi_hatasi(capsys: pytest.CaptureFixture[str], catalog_file: Callable[..., Path]) -> None:
    path = catalog_file(
        {
            "source_locale": "tr",
            "target_locale": "tr",
            "segments": [{"id": "A", "field": "title", "source": "a", "target": "a"}],
        }
    )
    assert main(["check", str(path)]) == 2
    assert "girdi hatası" in capsys.readouterr().err


def test_komut_yoksa_yardim_ve_hata_kodu(capsys: pytest.CaptureFixture[str]) -> None:
    code = main([])
    assert code == 2
    assert "locale-gate" in capsys.readouterr().out


def test_rules_komutu(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["rules"]) == 0
    out = capsys.readouterr().out
    assert "Sözlük uyumu" in out
    assert "denetlenen kural sayısı: 4" in out


def test_eval_komutu_basarili(golden_dir: Path) -> None:
    assert main(["eval", str(golden_dir)]) == 0


def test_eval_komutu_json(capsys: pytest.CaptureFixture[str], golden_dir: Path) -> None:
    assert main(["eval", str(golden_dir), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["cases"]) == 3


def test_eval_komutu_basarisiz_olabilir(tmp_path: Path) -> None:
    (tmp_path / "case").mkdir()
    (tmp_path / "case" / "catalog.json").write_text(
        json.dumps(
            {
                "source_locale": "tr",
                "target_locale": "en",
                "segments": [{"id": "M-1", "field": "title", "source": "Ürün", "target": "Product"}],
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "golden.json").write_text(
        json.dumps(
            {"cases": [{"name": "hatalı", "catalog": "case/catalog.json", "expected": {"M-1": ["TERM_EKSIK"]}}]}
        ),
        encoding="utf-8",
    )
    assert main(["eval", str(tmp_path)]) == 1


def test_surum_bayragi(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
    assert "locale-gate" in capsys.readouterr().out
