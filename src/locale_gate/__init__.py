"""locale-gate — TR↔EN e-ticaret içeriği için deterministik çeviri kalite kapısı.

Tasarım ilkesi: **hiçbir ölçüm LLM'e bağlı değildir.** Aynı girdi her zaman aynı skoru ve aynı
bulguları üretir; bu yüzden kapı CI'da güvenle kullanılabilir (bkz. `docs/adr/0001-deterministic-gate.md`).
"""

from __future__ import annotations

__version__ = "0.1.0"
__all__ = ["__version__"]
