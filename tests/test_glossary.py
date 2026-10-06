"""Sözlük: dosya biçimleri, kelime sınırı davranışı ve Türkçe harf duyarlılığı."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from locale_gate.glossary import Glossary, compile_term, load_glossary
from tests.factories import make_glossary, make_term


def test_yaml_sozluk_yuklenir(tmp_path: Path) -> None:
    path = tmp_path / "glossary.yaml"
    path.write_text(
        "source_locale: tr\ntarget_locale: en\n"
        "terms:\n"
        "  - source: kargo ücreti\n    target: shipping fee\n    forbidden: [cargo fee]\n"
        "  - source: yalnız kaynak\n",
        encoding="utf-8",
    )
    glossary = load_glossary(path)
    assert len(glossary.terms) == 2
    assert glossary.terms[0].forbidden == ("cargo fee",)
    assert glossary.terms[1].target is None


def test_json_sozluk_yuklenir(tmp_path: Path) -> None:
    path = tmp_path / "glossary.json"
    path.write_text(
        json.dumps({"terms": [{"source": "beden", "target": "size", "forbidden": ["body"]}]}),
        encoding="utf-8",
    )
    glossary = load_glossary(path)
    assert glossary.terms[0].target == "size"


def test_sozluk_yoksa_bos_sozluk() -> None:
    assert load_glossary(None).terms == ()
    assert Glossary().terms == ()


def test_olmayan_sozluk_dosyasi(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="sözlük bulunamadı"):
        load_glossary(tmp_path / "yok.yaml")


def test_gecersiz_sozluk_kaydi() -> None:
    with pytest.raises(ValueError, match="valid dictionary"):
        Glossary.model_validate({"terms": [123]})


def test_kelime_siniri_tam_kelime_ister() -> None:
    pattern = compile_term("beden", case_sensitive=False)
    assert pattern.search("bu beden büyük")
    assert pattern.search("BEDEN TABLOSU")
    assert not pattern.search("bedenler")  # çoğul ek ayrı kelimedir
    assert not pattern.search("badende")


def test_turkce_harfler_kelime_sinirinda_sayilir() -> None:
    pattern = compile_term("ürün", case_sensitive=False)
    assert pattern.search("ürün açıklaması")
    assert pattern.search("ÜRÜN ÖZELLİKLERİ")
    assert not pattern.search("ürünlerimiz")
    assert not pattern.search("gürün")


def test_sembolle_baslayan_terim_eslesir() -> None:
    pattern = compile_term("%100 pamuk", case_sensitive=False)
    assert pattern.search("bu %100 pamuk bir tişört")
    assert not pattern.search("bu %100 pamuklular")


def test_buyuk_kucuk_harf_duyarliligi_secilebilir() -> None:
    sensitive = compile_term("Bedford", case_sensitive=True)
    assert sensitive.search("Bedford marka")
    assert not sensitive.search("bedford marka")
    loose = compile_term("Bedford", case_sensitive=False)
    assert loose.search("bedford marka")


def test_kaynak_metindeki_terimler_bulunur() -> None:
    glossary = make_glossary([make_term("kargo ücreti", target="shipping fee"), make_term("iade", target="return")])
    found = glossary.terms_in("Kargo ücreti ve iade koşulları")
    assert [term.source for term in found] == ["kargo ücreti", "iade"]
    assert glossary.terms_in("alakasız cümle") == []


def test_sozluk_hedef_karsiligi_olmayan_terim() -> None:
    term = make_term("marka adı", forbidden=("brand name",))
    assert term.target_pattern() is None
    assert [variant for variant, _ in term.forbidden_patterns()] == ["brand name"]
