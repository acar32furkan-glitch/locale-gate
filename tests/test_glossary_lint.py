"""Sözlük denetimi (`glossary lint`): bulgu kodları, eşleme semantiği ve kural motoruyla kanıt.

Her test iki şeyi birlikte doğrular: (1) lint doğru kodu ve kayıt numaralarını üretiyor,
(2) iddia edilen sonuç kural motorunda GERÇEKTEN oluyor — "bozuk sözlük sessizce yanlış karar
üretir" cümlesi ölçülmeden belgeye yazılmaz.
"""

from __future__ import annotations

from pathlib import Path

from locale_gate.glossary import Glossary, Term, load_glossary
from locale_gate.glossary_lint import lint_glossary, render_lint_text
from locale_gate.rules.terminology import check
from tests.factories import make_context, make_glossary, make_segment, make_term

REPO_ROOT = Path(__file__).resolve().parents[1]


def _codes(glossary: Glossary) -> list[str]:
    return [finding.code for finding in lint_glossary(glossary).findings]


def test_temiz_sozluk_bulgu_uretmez() -> None:
    glossary = make_glossary(
        [
            make_term("kargo ücreti", target="shipping fee", forbidden=("cargo fee",)),
            make_term("yıkanabilir", target="washable"),
            make_term("marka adı"),  # kısa biçim: karşılık ve yasaklı yok
        ]
    )
    result = lint_glossary(glossary, path="glossary.yaml")
    assert result.findings == ()
    assert result.ok is True
    assert "KARAR: TEMİZ" in render_lint_text(result)


def test_ornek_sozluk_temiz() -> None:
    """Depodaki gerçek sözlük lint'ten geçmeli: kural dosyası kendi örneğini çürütmesin."""
    glossary = load_glossary(REPO_ROOT / "examples" / "data" / "glossary.yaml")
    result = lint_glossary(glossary, path="examples/data/glossary.yaml")
    assert len(glossary.terms) == 8
    assert result.findings == ()


def test_yinelenen_kayit_bildirilir() -> None:
    glossary = make_glossary(
        [
            make_term("kargo ücreti", target="shipping fee"),
            make_term("kargo ücreti", target="shipping fee"),
        ]
    )
    result = lint_glossary(glossary)
    assert [f.code for f in result.findings] == ["SOZLUK_YINELENEN"]
    assert result.findings[0].records == (1, 2)


def test_buyuk_kucuk_harf_farki_yinelenmedir() -> None:
    """Kapı büyük/küçük harfe duyarsız eşler: iki kayıt aynı segmentte iki kez ateşlenir."""
    glossary = make_glossary(
        [
            make_term("Kargo Ücreti", target="shipping fee"),
            make_term("kargo ücreti", target="shipping fee"),
        ]
    )
    assert _codes(glossary) == ["SOZLUK_YINELENEN"]


def test_harf_duyarliligi_farkli_kayitlar_yinelenen_sayilmaz() -> None:
    """Biri `case_sensitive` ise desenler ayrı metinleri yakalar — sahte yinelenen üretilmez."""
    glossary = make_glossary(
        [
            make_term("Kargo", target="cargo", case_sensitive=True),
            make_term("kargo", target="cargo"),
        ]
    )
    assert _codes(glossary) == []


def test_celiskili_hedef_bildirilir() -> None:
    glossary = make_glossary(
        [
            make_term("kargo ücreti", target="shipping fee"),
            make_term("Kargo Ücreti", target="shipping cost"),
        ]
    )
    result = lint_glossary(glossary)
    assert [f.code for f in result.findings] == ["SOZLUK_CELISKILI_HEDEF"]
    message = result.findings[0].message_tr
    assert result.findings[0].records == (1, 2)
    assert "shipping fee" in message
    assert "shipping cost" in message


def test_celiskili_hedef_kural_motorunda_her_ceviriyi_dusurur() -> None:
    """Ölçüm: iki kayıt iki farklı karşılık istiyorsa doğru çeviri bile TERM_EKSIK alır."""
    glossary = make_glossary(
        [
            make_term("kargo ücreti", target="shipping fee"),
            make_term("Kargo Ücreti", target="shipping cost"),
        ]
    )
    for target in ("Shipping fee included", "Shipping cost included"):
        context = make_context([make_segment("S-1", source="Kargo ücreti dahil", target=target)], glossary=glossary)
        codes = [finding.code for finding in check(context).findings]
        assert codes == ["TERM_EKSIK"], target


def test_uc_kayitli_grup_tek_bulgu_uretir() -> None:
    glossary = make_glossary(
        [
            make_term("beden", target="size"),
            make_term("Beden", target="size"),
            make_term("BEDEN", target="stature"),
        ]
    )
    result = lint_glossary(glossary)
    assert [f.code for f in result.findings] == ["SOZLUK_CELISKILI_HEDEF"]
    assert result.findings[0].records == (1, 2, 3)


def test_dort_ayni_kayit_tek_yinelenen_bulgusu() -> None:
    glossary = make_glossary([make_term("beden", target="size") for _ in range(4)])
    result = lint_glossary(glossary)
    assert [f.code for f in result.findings] == ["SOZLUK_YINELENEN"]
    assert result.findings[0].records == (1, 2, 3, 4)


def test_yasakli_listeleri_farkliysa_mesajda_yazar() -> None:
    glossary = make_glossary(
        [
            make_term("beden", target="size", forbidden=("body",)),
            make_term("beden", target="size", forbidden=("body", "stature")),
        ]
    )
    result = lint_glossary(glossary)
    assert [f.code for f in result.findings] == ["SOZLUK_YINELENEN"]
    assert "yasaklı listeleri farklı" in result.findings[0].message_tr


def test_karsiligi_olmayan_yinelenen_kayit() -> None:
    glossary = make_glossary([make_term("beden", target="size"), make_term("beden")])
    result = lint_glossary(glossary)
    assert [f.code for f in result.findings] == ["SOZLUK_YINELENEN"]
    assert "bazı kayıtlarda karşılık yok" in result.findings[0].message_tr


def test_bos_hedef_bildirilir_ve_gercekten_dusurur() -> None:
    """`target: ""` katalogda değil sözlükte hata: doğru çeviri bile TERM_EKSIK alıyor."""
    glossary = make_glossary([make_term("beden", target="")])
    result = lint_glossary(glossary)
    assert [f.code for f in result.findings] == ["SOZLUK_HEDEF_BOS"]
    context = make_context([make_segment("S-1", source="Beden tablosu", target="Size chart")], glossary=glossary)
    assert [finding.code for finding in check(context).findings] == ["TERM_EKSIK"]


def test_bos_kaynak_bildirilir_ve_yinelenen_uretmez() -> None:
    glossary = make_glossary([make_term(""), make_term("  ", target="size")])
    result = lint_glossary(glossary)
    assert [f.code for f in result.findings] == ["SOZLUK_KAYNAK_BOS", "SOZLUK_KAYNAK_BOS"]
    assert result.findings[0].records == (1,)
    assert result.findings[1].records == (2,)


def test_bos_yasakli_varyant_bildirilir() -> None:
    glossary = make_glossary([make_term("beden", target="size", forbidden=("",))])
    assert _codes(glossary) == ["SOZLUK_YASAK_BOS"]


def test_yinelenen_yasakli_varyant_bildirilir() -> None:
    glossary = make_glossary([make_term("beden", target="size", forbidden=("body", "Body"))])
    result = lint_glossary(glossary)
    assert [f.code for f in result.findings] == ["SOZLUK_YASAK_TEKRAR"]
    assert "body" in result.findings[0].message_tr


def test_yasakli_zorunlu_karsilikla_cakisirsa_dogru_ceviri_duser() -> None:
    glossary = make_glossary([make_term("su itici", target="water repellent", forbidden=("water repellent",))])
    result = lint_glossary(glossary)
    assert [f.code for f in result.findings] == ["SOZLUK_YASAK_HEDEFLE_CAKISIYOR"]
    context = make_context(
        [make_segment("S-1", source="Su itici kumaş", target="Water repellent fabric")], glossary=glossary
    )
    assert [finding.code for finding in check(context).findings] == ["TERM_YASAK"]


def test_yasakli_karsiligi_iceren_varyant_cakisma_sayilir() -> None:
    """“shipping” yasaklı, karşılık “shipping fee” → yasaklı karşılığın İÇİNDE geçiyor."""
    glossary = make_glossary([make_term("kargo ücreti", target="shipping fee", forbidden=("shipping",))])
    assert _codes(glossary) == ["SOZLUK_YASAK_HEDEFLE_CAKISIYOR"]


def test_hedef_yoklugu_bulgu_degil() -> None:
    """`target: null` meşru kısa biçimdir (yalnızca yasaklı varyant denetlenir)."""
    assert _codes(make_glossary([make_term("beden")])) == []


def test_bulgu_sirasi_kayit_numarasina_gore() -> None:
    glossary = make_glossary(
        [
            make_term("beden", target=""),
            make_term("kargo ücreti", target="shipping fee"),
            make_term("Kargo ücreti", target="shipping cost"),
            make_term(""),
        ]
    )
    records = [finding.records for finding in lint_glossary(glossary).findings]
    assert records == [(1,), (2, 3), (4,)]


def test_render_kayit_numaralarini_yazar() -> None:
    glossary = make_glossary([make_term("beden", target="size"), make_term("Beden", target="size")])
    text = render_lint_text(lint_glossary(glossary, path="g.yaml"))
    assert "SÖZLÜK DENETİMİ" in text
    assert "kayıt: 2  ·  bulgu: 1" in text
    assert "Kayıt 1 ve 2" in text
    assert "KARAR: 1 YAPILANDIRMA BULGUSU" in text


def test_json_sozlesmesi() -> None:
    glossary = Glossary(
        terms=(
            Term(source="beden", target=""),
            Term(source="kargo ücreti", target="shipping fee"),
            Term(source="Kargo Ücreti", target="shipping cost"),
        )
    )
    payload = lint_glossary(glossary, path="g.yaml").to_json()
    assert payload["path"] == "g.yaml"
    assert payload["terms"] == 3
    assert payload["ok"] is False
    assert payload["codes"] == ["SOZLUK_CELISKILI_HEDEF", "SOZLUK_HEDEF_BOS"]
    assert [finding["records"] for finding in payload["findings"]] == [[1], [2, 3]]
    assert set(payload["findings"][0]) == {"code", "records", "source", "message_tr", "hint_tr"}


def test_hatali_ornek_dosya_belgelenen_uc_bulgu() -> None:
    """README'de gösterilen çıktı bu dosyadan gelir: belge ile davranış ayrışmasın."""
    glossary = load_glossary(REPO_ROOT / "examples" / "data" / "glossary-hatali.yaml")
    result = lint_glossary(glossary, path="examples/data/glossary-hatali.yaml")
    assert [finding.code for finding in result.findings] == [
        "SOZLUK_YASAK_TEKRAR",
        "SOZLUK_CELISKILI_HEDEF",
        "SOZLUK_HEDEF_BOS",
    ]
    assert [finding.records for finding in result.findings] == [(1,), (1, 2), (3,)]
    assert "kayıt: 3  ·  bulgu: 3" in render_lint_text(result)
