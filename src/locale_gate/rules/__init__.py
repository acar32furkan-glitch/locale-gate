"""Kural motoru: her kural saf bir fonksiyondur, aynı girdiye aynı çıktıyı verir.

Kurallar birbirinden bağımsızdır ve her biri kendi **kapsamını** (`checked`) bildirir: örneğin
sözlük kuralı yalnızca sözlükteki bir terimi içeren segmentleri sayar. Skor, sayılan segmentler
üzerinden hesaplandığı için "hiç denenmemiş" bir kural skoru yapay olarak yükseltemez.
"""

from __future__ import annotations

from locale_gate.rules.context import RuleContext, RuleFn, RuleOutcome
from locale_gate.rules.length import check as check_length
from locale_gate.rules.terminology import check as check_terminology
from locale_gate.rules.tokens import check as check_tokens
from locale_gate.rules.turkish import check as check_turkish

RULES: dict[str, RuleFn] = {
    "terminology": check_terminology,
    "tokens": check_tokens,
    "turkish": check_turkish,
    "length": check_length,
}

RULE_LABELS: dict[str, str] = {
    "terminology": "Sözlük uyumu",
    "tokens": "Korunan ifadeler",
    "turkish": "Türkçe yazım",
    "length": "Uzunluk bütçesi",
}

__all__ = ["RULES", "RULE_LABELS", "RuleContext", "RuleFn", "RuleOutcome"]
