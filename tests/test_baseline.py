"""Taban çizgisi: bilinen borç kapıya girmemeli, yeni bulgu girmeli."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from locale_gate.baseline import Baseline, BaselineError, apply_baseline, load_baseline
from locale_gate.catalog import load_catalog
from locale_gate.cli import main
from locale_gate.config import GateConfig
from locale_gate.gate import run_gate
from locale_gate.glossary import load_glossary
from locale_gate.models import Report

# Örnek borç kataloğu: 12 segment, 12 bulgu (5 kritik), ham skor 0.529.
BORCLU = ("data", "catalog.json")
BORCLU_SOZLUK = ("data", "glossary.yaml")


def _ornek(golden_dir: Path, parts: tuple[str, str]) -> Path:
    """``examples/`` altındaki yolu kur (golden_dir = examples/golden)."""
    return golden_dir.parent.joinpath(*parts)


def _taban_yaz(tmp_path: Path, catalog: Path, glossary: Path) -> Path:
    """Gerçek CLI ile taban raporu üret (kusurlu katalogda çıkış kodu 1, rapor yine yazılır)."""
    path = tmp_path / "taban.json"
    code = main(["check", str(catalog), "--glossary", str(glossary), "--report", str(path)])
    assert code == 1
    return path


def _katalog_yeni_bulgu(tmp_path: Path, catalog: Path) -> Path:
    """Borca dokunmadan tek bir YENİ ihlal ekle (yer tutucu düşen açıklama)."""
    payload = json.loads(catalog.read_text(encoding="utf-8"))
    payload["segments"].append(
        {
            "id": "YENI-1-description",
            "field": "description",
            "source": "Sipariş {order_id} ile 3 gün içinde kargoda.",
            "target": "Order shipped within 3 days.",
        }
    )
    path = tmp_path / "katalog-yeni.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


@pytest.fixture
def borclu_katalog(golden_dir: Path) -> Path:
    return _ornek(golden_dir, BORCLU)


@pytest.fixture
def borclu_sozluk(golden_dir: Path) -> Path:
    return _ornek(golden_dir, BORCLU_SOZLUK)


@pytest.fixture
def kusurlu_rapor(borclu_katalog: Path, borclu_sozluk: Path) -> Report:
    """Ham (tabansız) rapor."""
    return run_gate(load_catalog(borclu_katalog), load_glossary(borclu_sozluk))


def test_borc_devralinir_ve_skor_yeniden_hesaplanir(kusurlu_rapor: Report) -> None:
    """Yalnızca TERM_EKSIK bulguları tabanda olsun: kalan bulgular skora girer."""
    keys = frozenset(
        (finding.code, finding.segment_id, finding.field)
        for finding in kusurlu_rapor.findings
        if finding.code == "TERM_EKSIK"
    )
    taban = Baseline(path=Path("taban.json"), source_locale="tr", target_locale="en", keys=keys, entries=len(keys))

    filtreli, ozet = apply_baseline(kusurlu_rapor, taban, GateConfig().normalized_weights())

    assert len(kusurlu_rapor.findings) == 12
    assert ozet.suppressed == 3
    assert ozet.new == 9
    assert ozet.stale == 0
    assert ozet.raw_score == pytest.approx(0.5292)

    terminology = filtreli.stat_for("terminology")
    assert terminology is not None
    # Kalan üç bulgu üç ayrı segmentte: skor 1 − 3/7.
    assert (terminology.checked, terminology.failed, terminology.failed_segments) == (7, 3, 3)
    # Sözlük 4/7, korunan ifadeler 1/3, yazım 10/12, uzunluk 11/12 (ağırlıklar .35/.35/.15/.15)
    beklenen = 0.35 * (4 / 7) + 0.35 * (1 / 3) + 0.15 * (10 / 12) + 0.15 * (11 / 12)
    assert filtreli.score == pytest.approx(beklenen, abs=1e-4)
    assert filtreli.score == pytest.approx(0.5792)
    assert (kusurlu_rapor.critical_count, filtreli.critical_count) == (5, 2)
    assert all(finding.code != "TERM_EKSIK" for finding in filtreli.findings)


def test_ayni_kod_farkli_alan_esanmaz(kusurlu_rapor: Report) -> None:
    """Kimlik (code, segment, alan) üçlüsüdür: alan yanlışsa bulgu yeni sayılır."""
    ilk = kusurlu_rapor.findings[0]
    taban = Baseline(
        path=Path("taban.json"),
        source_locale=None,
        target_locale=None,
        keys=frozenset({(ilk.code, ilk.segment_id, "baska-alan")}),
        entries=1,
    )

    filtreli, ozet = apply_baseline(kusurlu_rapor, taban, GateConfig().normalized_weights())

    assert ozet.suppressed == 0
    assert ozet.stale == 1
    assert len(filtreli.findings) == len(kusurlu_rapor.findings)


def test_yon_uyusmazligi_reddedilir(kusurlu_rapor: Report) -> None:
    """Ters yönün raporu borcu 'tanır' görünür ve kapı hiçbir şeyi denetlemez."""
    taban = Baseline(
        path=Path("taban.json"),
        source_locale="en",
        target_locale="tr",
        keys=frozenset({("TERM_EKSIK", "G-102-title", "title")}),
        entries=1,
    )

    with pytest.raises(BaselineError, match="farklı bir dil çiftinden"):
        apply_baseline(kusurlu_rapor, taban, GateConfig().normalized_weights())


@pytest.mark.parametrize(
    ("icerik", "beklenen"),
    [
        ("{bozuk", "geçersiz JSON"),
        ("[]", "kök bir nesne"),
        ('{"source_locale": "tr"}', "'findings' listesi yok"),
        ('{"findings": [42]}', r"findings\[0\] bir nesne değil"),
        ('{"findings": [{"code": "X", "segment_id": "Y"}]}', "geçerli 'field' yok"),
    ],
)
def test_bozuk_taban_dosyasi_sessizce_yutulmaz(tmp_path: Path, icerik: str, beklenen: str) -> None:
    path = tmp_path / "taban.json"
    path.write_text(icerik, encoding="utf-8")

    with pytest.raises(BaselineError, match=beklenen):
        load_baseline(path)


def test_taban_dosyasi_yok(tmp_path: Path) -> None:
    with pytest.raises(BaselineError, match="bulunamadı"):
        load_baseline(tmp_path / "yok.json")


def test_alinan_kimlikler_dosyadan_okunur(tmp_path: Path, kusurlu_rapor: Report) -> None:
    """Diskten okunan taban, rapordaki bulguları gerçekten eşler."""
    path = tmp_path / "taban.json"
    path.write_text(
        json.dumps(
            {
                "source_locale": "tr",
                "target_locale": "en",
                "findings": [
                    {
                        "code": finding.code,
                        "segment_id": finding.segment_id,
                        "field": finding.field,
                        "severity": finding.severity.value,
                        "rule": finding.rule,
                        "message_tr": finding.message_tr,
                        "detail_tr": finding.detail_tr,
                        "hint_tr": finding.hint_tr,
                    }
                    for finding in kusurlu_rapor.findings[:4]
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    taban = load_baseline(path)
    filtreli, ozet = apply_baseline(kusurlu_rapor, taban, GateConfig().normalized_weights())

    assert taban.entries == 4
    assert len(taban.keys) == 4
    assert ozet.suppressed == 4
    assert ozet.new == 8
    assert filtreli.critical_count <= kusurlu_rapor.critical_count


def test_cli_taban_borcu_kapiya_sokmaz(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], borclu_katalog: Path, borclu_sozluk: Path
) -> None:
    taban = _taban_yaz(tmp_path, borclu_katalog, borclu_sozluk)
    capsys.readouterr()

    code = main(["check", str(borclu_katalog), "--glossary", str(borclu_sozluk), "--baseline", str(taban)])
    out = capsys.readouterr().out

    assert code == 0
    assert "KARAR: GEÇTİ" in out
    assert "12 bilinen bulgu devralındı" in out
    assert "0 yeni" in out
    assert "Yeni bulgu yok; 12 bilinen bulgu tabanda devralındı." in out


def test_cli_taban_yeni_bulguyu_yakalar(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], borclu_katalog: Path, borclu_sozluk: Path
) -> None:
    taban = _taban_yaz(tmp_path, borclu_katalog, borclu_sozluk)
    capsys.readouterr()

    katalog = _katalog_yeni_bulgu(tmp_path, borclu_katalog)
    code = main(["check", str(katalog), "--glossary", str(borclu_sozluk), "--baseline", str(taban)])
    out = capsys.readouterr().out

    assert code == 1
    assert "YENİ BULGULAR" in out
    assert "1 yeni" in out
    assert "TOKEN_KAYIP" in out
    assert "YENI-1-description" in out
    assert "KARAR: KALDI" in out


def test_cli_json_bloku(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], borclu_katalog: Path, borclu_sozluk: Path
) -> None:
    taban = _taban_yaz(tmp_path, borclu_katalog, borclu_sozluk)
    capsys.readouterr()

    code = main(
        [
            "check",
            str(borclu_katalog),
            "--glossary",
            str(borclu_sozluk),
            "--baseline",
            str(taban),
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["passed"] is True
    assert payload["score"] == pytest.approx(1.0)
    assert payload["findings"] == []
    assert payload["baseline"]["suppressed"] == 12
    assert payload["baseline"]["new"] == 0
    assert payload["baseline"]["raw_score"] == pytest.approx(0.5292)


def test_cli_kapanan_bulgu_sayilir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], borclu_katalog: Path, borclu_sozluk: Path
) -> None:
    """Tabanda duran ama artık üretilmeyen bulgu 'kapanmış' sayılır."""
    taban = _taban_yaz(tmp_path, borclu_katalog, borclu_sozluk)
    payload = json.loads(taban.read_text(encoding="utf-8"))
    payload["findings"].append(
        {
            "severity": "critical",
            "code": "TERM_EKSIK",
            "rule": "terminology",
            "segment_id": "ARTIK-YOK",
            "field": "title",
            "message_tr": "eski",
            "detail_tr": "eski",
            "hint_tr": "eski",
        }
    )
    taban.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    capsys.readouterr()

    code = main(
        [
            "check",
            str(borclu_katalog),
            "--glossary",
            str(borclu_sozluk),
            "--baseline",
            str(taban),
            "--json",
        ]
    )
    sonuc = json.loads(capsys.readouterr().out)

    assert code == 0
    assert sonuc["baseline"]["stale"] == 1
    assert sonuc["baseline"]["entries"] == 13
    assert sonuc["baseline"]["suppressed"] == 12


def test_cli_taban_ve_rapor_birlikte_reddedilir(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], borclu_katalog: Path, borclu_sozluk: Path
) -> None:
    taban = _taban_yaz(tmp_path, borclu_katalog, borclu_sozluk)
    capsys.readouterr()

    code = main(
        [
            "check",
            str(borclu_katalog),
            "--glossary",
            str(borclu_sozluk),
            "--baseline",
            str(taban),
            "--report",
            str(tmp_path / "yeni.json"),
        ]
    )

    assert code == 2
    assert "--baseline ile --report birlikte kullanılamaz" in capsys.readouterr().err
    assert not (tmp_path / "yeni.json").exists()


def test_cli_yon_uyusmazligi_girdi_hatasi(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], borclu_katalog: Path, borclu_sozluk: Path
) -> None:
    taban = _taban_yaz(tmp_path, borclu_katalog, borclu_sozluk)
    payload = json.loads(taban.read_text(encoding="utf-8"))
    payload["source_locale"], payload["target_locale"] = "en", "tr"
    taban.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    capsys.readouterr()

    code = main(["check", str(borclu_katalog), "--glossary", str(borclu_sozluk), "--baseline", str(taban)])

    assert code == 2
    assert "farklı bir dil çiftinden" in capsys.readouterr().err


def test_cli_github_ozeti_tabani_yazar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, borclu_katalog: Path, borclu_sozluk: Path
) -> None:
    taban = _taban_yaz(tmp_path, borclu_katalog, borclu_sozluk)
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    main(
        [
            "check",
            str(borclu_katalog),
            "--glossary",
            str(borclu_sozluk),
            "--baseline",
            str(taban),
            "--github-summary",
        ]
    )

    text = summary.read_text(encoding="utf-8")
    assert "- taban: 12 bilinen bulgu devralındı · 0 yeni · 0 kapanmış" in text
    assert "GEÇTİ" in text
