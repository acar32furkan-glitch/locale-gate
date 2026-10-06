"""Kural motoru orkestrasyonu: kural kaydı, etiketler ve determinizm sözleşmesi."""

from __future__ import annotations

from locale_gate.catalog import Catalog
from locale_gate.config import DEFAULT_WEIGHTS, GateConfig
from locale_gate.glossary import Glossary
from locale_gate.rules import RULE_LABELS, RULES
from locale_gate.rules.context import RuleContext, RuleOutcome

EMPTY_CONTEXT = RuleContext(catalog=Catalog(segments=()), glossary=Glossary(), config=GateConfig())


def test_dort_kural_kayitli() -> None:
    assert list(RULES) == ["terminology", "tokens", "turkish", "length"]


def test_her_kuralin_etiketi_var() -> None:
    assert set(RULES) == set(RULE_LABELS)


def test_varsayilan_agirliklar_kurallarla_uyumlu() -> None:
    assert set(DEFAULT_WEIGHTS) == set(RULES)


def test_bos_katalogda_hicbir_kural_bulgu_uretmez() -> None:
    for rule, check in RULES.items():
        outcome = check(EMPTY_CONTEXT)
        assert isinstance(outcome, RuleOutcome)
        assert outcome.rule == rule
        assert outcome.findings == ()
        assert outcome.checked == 0


def test_kurallar_saf_fonksiyondur_ayni_girdi_ayni_cikti() -> None:
    for check in RULES.values():
        assert check(EMPTY_CONTEXT) == check(EMPTY_CONTEXT)
