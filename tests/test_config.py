"""Yapılandırma: varsayılanlar, dosyadan okuma ve ağırlık normalizasyonu."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from locale_gate.config import DEFAULT_FIELD_LIMITS, DEFAULT_WEIGHTS, GateConfig


def test_varsayilanlar() -> None:
    config = GateConfig()
    assert config.gate == 0.95
    assert config.fail_on_critical is True
    assert config.max_expansion == 1.6
    assert config.field_limits == DEFAULT_FIELD_LIMITS
    assert config.locales == ("tr", "en")


def test_toml_okuma(tmp_path: Path) -> None:
    path = tmp_path / "locale-gate.toml"
    path.write_text(
        "gate = 0.8\nmax_expansion = 1.3\n\n[field_limits]\ntitle = 50\n\n[weights]\nterminology = 1\n",
        encoding="utf-8",
    )
    config = GateConfig.from_file(path)
    assert config.gate == 0.8
    assert config.max_expansion == 1.3
    assert config.field_limits == {"title": 50}
    assert config.weights == {"terminology": 1.0}


def test_pyproject_icindeki_bolum_okunur(tmp_path: Path) -> None:
    path = tmp_path / "pyproject.toml"
    path.write_text("[tool.locale-gate]\ngate = 0.7\n", encoding="utf-8")
    assert GateConfig.from_file(path).gate == 0.7


def test_json_config_okuma(tmp_path: Path) -> None:
    path = tmp_path / "gate.json"
    path.write_text(json.dumps({"gate": 0.5}), encoding="utf-8")
    assert GateConfig.from_file(path).gate == 0.5


def test_bilinmeyen_alan_reddedilir(tmp_path: Path) -> None:
    path = tmp_path / "gate.toml"
    path.write_text("gat = 0.5\n", encoding="utf-8")  # yazım hatası
    with pytest.raises(ValueError, match="gat"):
        GateConfig.from_file(path)


@pytest.mark.parametrize(("gate", "valid"), [(0.0, True), (1.0, True), (-0.1, False), (1.2, False)])
def test_gate_araligi(tmp_path: Path, gate: float, valid: bool) -> None:
    if valid:
        assert GateConfig(gate=gate).gate == gate
    else:
        with pytest.raises(ValueError, match="should be"):
            GateConfig(gate=gate)


def test_agirlik_normalizasyonu() -> None:
    config = GateConfig(weights={"tokens": 3, "length": 1})
    normalized = config.normalized_weights()
    assert normalized["tokens"] == pytest.approx(0.75)
    assert normalized["length"] == pytest.approx(0.25)


def test_sifir_agirlik_hatasi() -> None:
    with pytest.raises(ValueError, match="weights toplamı sıfır"):
        GateConfig(weights={"tokens": 0}).normalized_weights()


def test_limit_for_segment_limiti_oncesl_gecer() -> None:
    config = GateConfig(field_limits={"title": 60})
    assert config.limit_for("title", 99) == 99  # segment kendi sınırını getirmişse o geçerli
    assert config.limit_for("title", None) == 60
    assert config.limit_for("bilinmeyen", None) is None


def test_varsayilan_agirliklar_toplami_bir() -> None:
    assert sum(DEFAULT_WEIGHTS.values()) == pytest.approx(1.0)
