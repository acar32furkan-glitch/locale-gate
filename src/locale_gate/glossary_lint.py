"""Sözlük denetimi (`glossary lint`): kural motoru çalışmadan yapılandırma hatasını yakalar.

Sözlük, kapının en yüksek getirili girdisidir ve bozuk bir kayıt **sessizce** yanlış karar üretir:

- `target: ""` hiçbir hedef metinde bulunamaz, yani o terimi içeren her segment KRİTİK `TERM_EKSIK`
  alır ve bunun nedeni sözlükte değil katalogda aranır;
- aynı kaynak terimin iki kaydı tek segmentte iki bulgu üretir ve "kaç bulgu var" sayısını şişirir;
- aynı kaynak iki farklı karşılıkla tanımlıysa hiçbir çeviri doğru olamaz;
- yasaklı varyant zorunlu karşılığın içinde geçiyorsa **doğru** çeviri `TERM_YASAK` yer.

Karşılaştırma kural motorunun kendi semantiğiyle yapılır (`compile_term`): kaynaklar
`casefold` ile değil, gerçekten derlenmiş desenle eşleştirilir — aksi hâlde Türkçe `İ`/`I`
farkı ("İADE" ↔ "iade") yanlış yere "yinelenen" der.
"""

from __future__ import annotations

from collections.abc import Sequence
from itertools import combinations
from typing import Any

from pydantic import BaseModel, ConfigDict

from locale_gate.glossary import Glossary, Term, compile_term

__all__ = ["LintFinding", "LintResult", "lint_glossary", "render_lint_text"]

_CODE_LABELS = {
    "SOZLUK_KAYNAK_BOS": "boş kaynak terim",
    "SOZLUK_HEDEF_BOS": "boş zorunlu karşılık",
    "SOZLUK_YASAK_BOS": "boş yasaklı varyant",
    "SOZLUK_YASAK_TEKRAR": "yinelenen yasaklı varyant",
    "SOZLUK_YASAK_HEDEFLE_CAKISIYOR": "yasaklı varyant zorunlu karşılıkla çakışıyor",
    "SOZLUK_YINELENEN": "yinelenen kayıt",
    "SOZLUK_CELISKILI_HEDEF": "aynı kaynak, farklı karşılık",
}


class LintFinding(BaseModel):
    """Sözlükten gelen tek yapılandırma bulgusu.

    ``records`` 1 tabanlı kayıt numaralarıdır: kullanıcı dosyada ``terms`` listesinin kaçıncı
    elemanına bakacağını doğrudan görsün.
    """

    model_config = ConfigDict(frozen=True)

    code: str
    records: tuple[int, ...] = ()
    source: str = ""
    message_tr: str
    hint_tr: str


class LintResult(BaseModel):
    """Bir sözlük dosyasının denetim sonucu."""

    model_config = ConfigDict(frozen=True)

    path: str
    terms: int
    findings: tuple[LintFinding, ...] = ()

    @property
    def ok(self) -> bool:
        """Sözlük kendi içinde tutarlı mı."""
        return not self.findings

    def codes(self) -> list[str]:
        """Bulgu kodlarını sıralı ve tekrarsız döndür."""
        return sorted({finding.code for finding in self.findings})

    def to_json(self) -> dict[str, Any]:
        """CI'ın okuyacağı sözleşme."""
        return {
            "path": self.path,
            "terms": self.terms,
            "ok": self.ok,
            "codes": self.codes(),
            "findings": [finding.model_dump(mode="json") for finding in self.findings],
        }


def lint_glossary(glossary: Glossary, *, path: str = "") -> LintResult:
    """Sözlüğü kendi içinde denetle (IO yok, saat yok → deterministik)."""
    findings: list[LintFinding] = []
    for index, term in enumerate(glossary.terms, start=1):
        findings.extend(_record_findings(index, term))
    findings.extend(_duplicate_findings(glossary.terms))
    ordered = sorted(findings, key=lambda finding: (finding.records, finding.code))
    return LintResult(path=path, terms=len(glossary.terms), findings=tuple(ordered))


def render_lint_text(result: LintResult) -> str:
    """Konsol çıktısı: bulgu → çözüm, en sonda tek satır karar."""
    lines = ["SÖZLÜK DENETİMİ"]
    lines.append(f"  dosya: {result.path}  ·  kayıt: {result.terms}  ·  bulgu: {len(result.findings)}")
    lines.append("")
    if result.ok:
        lines.append("Bulgu yok: kayıtlar, karşılıklar ve yasaklı listeler çelişmiyor.")
        lines.append("")
        lines.append("KARAR: TEMİZ")
        return "\n".join(lines)
    for index, finding in enumerate(result.findings, start=1):
        lines.append(f"{index:>3}. [{finding.code}] {_CODE_LABELS.get(finding.code, finding.code)}")
        lines.append(f"      durum  : {finding.message_tr}")
        lines.append(f"      çözüm  : {finding.hint_tr}")
    lines.append("")
    lines.append(f"KARAR: {len(result.findings)} YAPILANDIRMA BULGUSU (kapı düştü)")
    return "\n".join(lines)


def _record_findings(index: int, term: Term) -> list[LintFinding]:
    """Tek kaydın kendi içindeki tutarsızlıkları."""
    findings: list[LintFinding] = []
    if not term.source.strip():
        findings.append(
            LintFinding(
                code="SOZLUK_KAYNAK_BOS",
                records=(index,),
                source=term.source,
                message_tr=f"Kayıt {index}: kaynak terim boş — bu desen hiçbir segmentle eşleşmez.",
                hint_tr="Kaydı silin ya da kaynak terimi yazın; boş kayıt sözlükte ölü ağırlıktır.",
            )
        )

    target_missing = term.target is not None and not term.target.strip()
    if term.target is not None and target_missing:
        findings.append(
            LintFinding(
                code="SOZLUK_HEDEF_BOS",
                records=(index,),
                source=term.source,
                message_tr=(
                    f"Kayıt {index}: “{term.source}” için karşılık boş metin — boş metin hiçbir gerçek "
                    "çeviride bulunmaz (desen yalnızca boş metne uyar), yani bu terimi içeren her segment "
                    "TERM_EKSIK alır."
                ),
                hint_tr=(
                    "Karşılığı yazın ya da `target` alanını tamamen kaldırın (`target: null`): boş metin "
                    "ile alanın yokluğu aynı şey değil — yokluk yalnızca yasaklı varyant denetimi bırakır."
                ),
            )
        )

    seen_variants: dict[str, str] = {}
    for variant in term.forbidden:
        if not variant.strip():
            findings.append(
                LintFinding(
                    code="SOZLUK_YASAK_BOS",
                    records=(index,),
                    source=term.source,
                    message_tr=f"Kayıt {index}: “{term.source}” yasaklı listesinde boş varyant var.",
                    hint_tr="Boş varyantı listeden çıkarın: aranan desen anlamsız ve sonuç öngörülemez.",
                )
            )
            continue
        normalized = _normalize(variant)
        if normalized in seen_variants:
            first_spelling = seen_variants[normalized]
            suffix = f" (ilk yazım: “{first_spelling}”)" if first_spelling != variant else ""
            findings.append(
                LintFinding(
                    code="SOZLUK_YASAK_TEKRAR",
                    records=(index,),
                    source=term.source,
                    message_tr=(
                        f"Kayıt {index}: “{variant}” yasaklı listesinde birden fazla kez geçiyor{suffix} — "
                        "aynı segment için iki TERM_YASAK bulgusu üretilir."
                    ),
                    hint_tr="Yinelenen varyantı silin.",
                )
            )
            continue
        seen_variants[normalized] = variant
        if term.target and term.target.strip():
            requires = compile_term(variant, case_sensitive=term.case_sensitive)
            if not target_missing and requires.search(term.target):
                findings.append(
                    LintFinding(
                        code="SOZLUK_YASAK_HEDEFLE_CAKISIYOR",
                        records=(index,),
                        source=term.source,
                        message_tr=(
                            f"Kayıt {index}: yasaklı “{variant}” zorunlu karşılığın (“{term.target}”) "
                            "içinde geçiyor — sözlüğe uyan çeviri de TERM_YASAK alır."
                        ),
                        hint_tr=(
                            "Yasaklıyı listeden çıkarın ya da zorunlu karşılığı bu ifadeyi içermeyecek "
                            "şekilde değiştirin; aksi hâlde kural kendi kendisiyle çelişir."
                        ),
                    )
                )
    return findings


def _duplicate_findings(terms: Sequence[Term]) -> list[LintFinding]:
    """Aynı kaynak desenini tanımlayan kayıt grupları."""
    findings: list[LintFinding] = []
    for members in _pattern_groups(terms):
        records = tuple(index + 1 for index in members)
        first = terms[members[0]]
        required = [term.target for term in (terms[index] for index in members) if term.target and term.target.strip()]
        distinct = {_normalize(value) for value in required} if required else set()
        listesi = _records_tr(records)
        if len(distinct) > 1:
            variants = " · ".join(f"“{value}”" for value in required)
            findings.append(
                LintFinding(
                    code="SOZLUK_CELISKILI_HEDEF",
                    records=records,
                    source=first.source,
                    message_tr=(
                        f"Kayıt {listesi} aynı kaynak terimi farklı karşılıklarla tanımlıyor: {variants}. "
                        "Aynı anda iki karşılık arandığı için her çeviri en az bir TERM_EKSIK alır."
                    ),
                    hint_tr="Tek kayıt bırakın ve geçerli karşılığı seçin; diğer kaydı silin.",
                )
            )
            continue
        notes: list[str] = []
        if any(term.target is None for term in (terms[index] for index in members)):
            notes.append("bazı kayıtlarda karşılık yok")
        if len({tuple(sorted(term.forbidden)) for term in (terms[index] for index in members)}) > 1:
            notes.append("yasaklı listeleri farklı (birleşim uygulanır)")
        suffix = f" ({'; '.join(notes)})" if notes else ""
        findings.append(
            LintFinding(
                code="SOZLUK_YINELENEN",
                records=records,
                source=first.source,
                message_tr=(
                    f"Kayıt {listesi} aynı kaynak terimi tanımlıyor: “{first.source}”{suffix}. "
                    "Aynı segment iki kez denetlenir ve bulgu sayısı çiftlenir."
                ),
                hint_tr="Kayıtlardan birini silin; yasaklı listeleri farklıysa tek kayıtta birleştirin.",
            )
        )
    return findings


def _pattern_groups(terms: Sequence[Term]) -> list[list[int]]:
    """Desen eşitliğine göre bağlı bileşenler (union-find, deterministik sıra)."""
    parent = list(range(len(terms)))

    def find(index: int) -> int:
        while parent[index] != index:
            parent[index] = parent[parent[index]]
            index = parent[index]
        return index

    for left, right in combinations(range(len(terms)), 2):
        if not _ayni_desen(terms[left], terms[right]):
            continue
        first, second = find(left), find(right)
        if first != second:
            parent[max(first, second)] = min(first, second)

    buckets: dict[int, list[int]] = {}
    for index in range(len(terms)):
        buckets.setdefault(find(index), []).append(index)
    return [members for members in buckets.values() if len(members) > 1]


def _ayni_desen(left: Term, right: Term) -> bool:
    """İki kayıt, kural motorunun eşlemesinde aynı metni yakalıyor mu."""
    if not left.source.strip() or not right.source.strip():
        return False
    return (
        left.source_pattern().fullmatch(right.source) is not None
        and right.source_pattern().fullmatch(left.source) is not None
    )


def _normalize(text: str) -> str:
    """Karşılıkları karşılaştırmak için boşluk ve büyük/küçük harf farkını sil."""
    return " ".join(text.split()).casefold()


def _records_tr(records: tuple[int, ...]) -> str:
    """``(1, 2, 3)`` → ``"1, 2 ve 3"`` (Türkçe bağlaç; yalnızca en az iki kayıtlık gruplar için)."""
    return f"{', '.join(str(item) for item in records[:-1])} ve {records[-1]}"
