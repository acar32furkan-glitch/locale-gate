"""Katalog yükleme: JSON, CSV ve bozuk girdi davranışı."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from locale_gate.catalog import load_catalog
from tests.factories import make_catalog, make_segment


def test_json_katalog_yuklenir(tmp_path: Path, catalog_file: Callable[..., Path]) -> None:
    path = catalog_file(
        {
            "source_locale": "tr",
            "target_locale": "en",
            "field_limits": {"title": 60},
            "segments": [
                {"id": "A-1", "field": "title", "source": "Kaynak", "target": "Target", "limit": 70},
                {"id": "A-2", "field": "bullet", "source": "Kaynak 2", "target": "Target 2"},
            ],
        }
    )
    catalog = load_catalog(path)
    assert (catalog.source_locale, catalog.target_locale) == ("tr", "en")
    assert catalog.field_limits == {"title": 60}
    assert [segment.id for segment in catalog.segments] == ["A-1", "A-2"]
    assert catalog.segments[0].limit == 70
    assert catalog.segments[1].limit is None
    assert catalog.fields() == ["bullet", "title"]
    assert catalog.segment_by_id("A-2") is not None
    assert catalog.segment_by_id("yok") is None


def test_csv_katalog_yuklenir(tmp_path: Path) -> None:
    path = tmp_path / "catalog.csv"
    path.write_text(
        "id,field,source,target,limit\n"
        "C-1,title,Kaynak başlık,Target title,70\n"
        "C-2,bullet,Kaynak madde,Target bullet,\n",
        encoding="utf-8",
    )
    catalog = load_catalog(path)
    assert len(catalog.segments) == 2
    assert catalog.segments[0].limit == 70
    assert catalog.segments[1].limit is None


def test_csv_zorunlu_alan_eksikse_hata(tmp_path: Path) -> None:
    path = tmp_path / "catalog.csv"
    path.write_text("id,field,source,target\nC-1,title,,Target\n", encoding="utf-8")
    with pytest.raises(ValueError, match="zorunlu alanlar eksik"):
        load_catalog(path)


def test_csv_limit_sayi_degilse_hata(tmp_path: Path) -> None:
    path = tmp_path / "catalog.csv"
    path.write_text("id,field,source,target,limit\nC-1,title,Kaynak,Hedef,abc\n", encoding="utf-8")
    with pytest.raises(ValueError, match="limit sayı değil"):
        load_catalog(path)


def test_olmayan_dosya_net_hata(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="katalog bulunamadı"):
        load_catalog(tmp_path / "yok.json")


def test_bos_segments_listesi_de_gecerlidir() -> None:
    catalog = make_catalog([])
    assert catalog.segments == ()
    assert catalog.fields() == []


def test_segment_modeli_degismezdir() -> None:
    segment = make_segment("S-1", source="a", target="b")
    with pytest.raises(ValueError, match="frozen"):
        segment.target = "c"
