# locale-gate

[![CI](https://github.com/acar32furkan-glitch/locale-gate/actions/workflows/ci.yml/badge.svg)](https://github.com/acar32furkan-glitch/locale-gate/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Ruff](https://img.shields.io/badge/lint-ruff-261230)](https://docs.astral.sh/ruff/)
[![Checked with mypy](https://img.shields.io/badge/mypy-strict-2f6f9f)](https://mypy-lang.org/)

[Türkçe](README.md) · **English**

**A deterministic translation quality gate for Turkish ↔ English e-commerce content.** It checks
marketplace listing translations for glossary compliance, protected fragments (placeholders,
measurements, model numbers), Turkish spelling, and length budgets — and returns a single score plus
a **pass/fail decision** your CI can trust.

No setup, see it in 30 seconds:

```bash
git clone https://github.com/acar32furkan-glitch/locale-gate && cd locale-gate
uv sync --all-extras --dev
uv run locale-gate check examples/data/catalog.json --glossary examples/data/glossary.yaml
```

![locale-gate demo output](docs/assets/demo.svg)

> Rule messages and docs are Turkish on purpose: the people reading the report are the Turkish
> content team. Code, field names and rule identifiers are English.

---

## Why

Translation quality breaks in two ways. A translator ignores the glossary ("cargo fee" instead of
"shipping fee"), or technical fragments silently change: the `{order_id}` placeholder drops out of a
sentence, "780 gram" becomes "0.78 kg", half of "45 x 30 cm" disappears. These look normal on the
page; the customer finds them first.

locale-gate makes them **catchable in CI**: the same input always produces the same score and the
same findings — no measurement depends on an LLM or the network (see
[ADR-0001](docs/adr/0001-deterministic-gate.md)) — and a translation whose score falls under
`--fail-under` cannot be merged.

## Four rules

| Rule | What it checks | Example mistake it catches |
|------|----------------|----------------------------|
| `terminology` | Required glossary targets and forbidden variants | "cargo fee" used where the glossary says "shipping fee" |
| `tokens` | Placeholders, HTML tags, links, measurements, model numbers | `{order_id}` lost in translation · 780 gram → 0.78 kg |
| `turkish` | Diacritics, the `i/İ` casing rule, untranslated segments | "Urun Ozellikleri" · "ISTANBUL" (should be "İSTANBUL") |
| `length` | Field character limits and expansion ratio | 85 characters in a 70-character title field |

Rule codes, thresholds and their rationale: **[docs/rules.md](docs/rules.md)** (Turkish).

```bash
uv run locale-gate rules                                      # rule set + weights
uv run locale-gate check examples/data/catalog.json --json     # the JSON contract for agents/CI
uv run locale-gate eval examples/golden                        # golden set regression
```

## Using it in CI

```yaml
- name: Translation quality gate
  run: uv run locale-gate check content/catalog.json --glossary content/glossary.yaml --github-summary
```

`--github-summary` appends a Markdown report to the Actions job summary; the command exits **1**
when the gate fails, breaking the PR. Catalogs can be JSON or CSV (`id,field,source,target,limit`).

## Your own thresholds

```toml
# locale-gate.toml
gate = 0.98
fail_on_critical = true
max_expansion = 1.4

[field_limits]
title = 60
bullet = 120
```

```bash
uv run locale-gate check catalog.json --glossary glossary.yaml --config locale-gate.toml --fail-under 0.9
```

## Architecture

```text
catalog.json ─┐
glossary.yaml ├─→ rules/ (terminology · tokens · turkish · length) ─→ gate.py ─→ Report ─→ cli/render
config.toml  ─┘        (pure functions)                              (score + decision)
```

- Every rule is a pure function: no IO, no clock, no randomness.
- Each rule reports its own **coverage**; a rule that was never exercised cannot inflate the score.
- The score is the weighted mean of rule scores; the pass decision additionally looks at the number
  of critical findings.
- Details: [docs/architecture.md](docs/architecture.md) · decisions: [docs/adr/](docs/adr/)

## Quality

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy                              # strict
uv run pytest --cov=locale_gate
uv run locale-gate eval examples/golden   # the behaviour contract of the rules
```

## Limits

- **No LLM:** it does not judge meaning or fluency, only mechanical and glossary-based mistakes.
  Creative translation quality needs human review (an optional LLM judge is on the roadmap).
- **Two locale pairs:** `tr→en` and `en→tr`. Other languages are added by writing a rule module,
  not by configuration.
- **Turkish rules reason, they do not guess:** the diacritics rule only fires when the source text
  contains the correct spelling, so it never flags the word that was actually right.

## Contributing

[CONTRIBUTING.md](CONTRIBUTING.md) · [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) ·
[SECURITY.md](SECURITY.md) · changes: [CHANGELOG.md](CHANGELOG.md)

## License

[MIT](LICENSE) © 2026 Furkan Acar (acar32furkan-glitch)
