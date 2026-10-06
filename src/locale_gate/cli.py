"""Komut satırı arayüzü.

locale-gate check <katalog> [--glossary ...] [--config ...] [--fail-under 0.95]
locale-gate eval  <altın-set-klasörü>
locale-gate rules                     # kural sözlüğü özeti

Çıkış kodları: 0 geçti · 1 kapı düştü · 2 girdi/kullanım hatası.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from locale_gate import __version__
from locale_gate.catalog import load_catalog
from locale_gate.config import GateConfig
from locale_gate.gate import GateInputError, decide, run_gate
from locale_gate.glossary import load_glossary
from locale_gate.golden import render_golden_text, run_golden
from locale_gate.render import render_markdown, render_report_text
from locale_gate.rules import RULE_LABELS, RULES

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_INPUT_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse tree (one parser, subcommands for each task)."""
    parser = argparse.ArgumentParser(
        prog="locale-gate",
        description="TR↔EN e-ticaret içeriği için deterministik çeviri kalite kapısı.",
    )
    parser.add_argument("--version", action="version", version=f"locale-gate {__version__}")
    sub = parser.add_subparsers(dest="command")

    check = sub.add_parser("check", help="Bir katalogu kural motorundan geçir.")
    check.add_argument("catalog", type=Path, help="Katalog dosyası (JSON veya CSV).")
    check.add_argument("--glossary", type=Path, default=None, help="Sözlük dosyası (YAML veya JSON).")
    check.add_argument("--config", type=Path, default=None, help="Yapılandırma dosyası (TOML veya JSON).")
    check.add_argument("--fail-under", type=float, default=None, help="Skor eşiğini geçici olarak değiştir.")
    check.add_argument("--json", action="store_true", dest="as_json", help="Raporu JSON olarak ver.")
    check.add_argument("--report", type=Path, default=None, help="Raporu bu dosyaya da yaz (JSON).")
    check.add_argument("--max-findings", type=int, default=20, help="Konsolda gösterilecek en fazla bulgu.")
    check.add_argument(
        "--github-summary",
        action="store_true",
        help="Markdown özetini $GITHUB_STEP_SUMMARY dosyasına ekle (Actions iş özeti).",
    )

    evaluation = sub.add_parser("eval", help="Altın set regresyon vakalarını çalıştır.")
    evaluation.add_argument("golden", type=Path, help="golden.json içeren klasör.")
    evaluation.add_argument("--json", action="store_true", dest="as_json", help="Sonucu JSON olarak ver.")

    sub.add_parser("rules", help="Kural listesini ve ağırlıklarını göster.")
    return parser


def cmd_check(args: argparse.Namespace) -> int:
    """Run the gate on one catalog and report the decision."""
    catalog = load_catalog(args.catalog)
    glossary = load_glossary(args.glossary)
    config = GateConfig.load(args.config)
    report = run_gate(catalog, glossary, config, now=datetime.now(tz=UTC))
    passed, reasons = decide(report, config, fail_under=args.fail_under)

    if args.as_json or args.report:
        payload = {
            "version": __version__,
            "generated_at": report.generated_at.isoformat(),
            "source_locale": report.source_locale,
            "target_locale": report.target_locale,
            "segments": report.segments,
            "score": report.score,
            "gate": report.gate if args.fail_under is None else args.fail_under,
            "passed": passed,
            "reasons": reasons,
            "stats": [
                {
                    "rule": stat.rule,
                    "label": stat.label_tr,
                    "checked": stat.checked,
                    "failed": stat.failed,
                    "failed_segments": stat.failed_segments,
                    "score": round(stat.score, 4),
                }
                for stat in report.stats
            ],
            "codes": report.by_code(),
            "findings": [finding.model_dump(mode="json") for finding in report.findings],
        }
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.as_json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))

    if not args.as_json:
        print(
            render_report_text(
                report,
                passed=passed,
                reasons=reasons,
                catalog_path=str(args.catalog),
                max_findings=args.max_findings,
            )
        )

    if args.github_summary:
        target = os.environ.get("GITHUB_STEP_SUMMARY", "").strip()
        if not target:
            print("uyarı: GITHUB_STEP_SUMMARY tanımlı değil, iş özeti yazılmadı.", file=sys.stderr)
        else:
            with Path(target).open("a", encoding="utf-8") as handle:
                handle.write(render_markdown(report, passed=passed, reasons=reasons) + "\n")

    return EXIT_OK if passed else EXIT_FAILED


def cmd_eval(args: argparse.Namespace) -> int:
    """Run the golden set and compare against the expected codes."""
    result = run_golden(args.golden)
    if args.as_json:
        print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    else:
        print(render_golden_text(result))
    return EXIT_OK if result.passed else EXIT_FAILED


def cmd_rules(_args: argparse.Namespace) -> int:
    """Print the rule list with weights and the codes each rule can raise."""
    config = GateConfig()
    weights = config.normalized_weights()
    print(f"locale-gate {__version__} · kural seti")
    width = max(len(label) for label in RULE_LABELS.values())
    for rule, label in RULE_LABELS.items():
        print(f"  {label:<{width}}  ağırlık {weights.get(rule, 0.0):.2f}  ·  {rule}")
    print("")
    print(f"  geçme eşiği: {config.gate:.2f} · kritik bulgu kapıyı düşürür: {config.fail_on_critical}")
    print(f"  en büyük uzama oranı: x{config.max_expansion:.2f}")
    print("  alan sınırları: " + ", ".join(f"{field} {limit}" for field, limit in config.field_limits.items()))
    print(f"  denetlenen kural sayısı: {len(RULES)}")
    return EXIT_OK


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point; maps errors to documented exit codes."""
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_INPUT_ERROR
    handlers = {"check": cmd_check, "eval": cmd_eval, "rules": cmd_rules}
    try:
        return handlers[args.command](args)
    except (GateInputError, ValueError) as exc:
        print(f"girdi hatası: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
    except FileNotFoundError as exc:
        print(f"dosya bulunamadı: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR
