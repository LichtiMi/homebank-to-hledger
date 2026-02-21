# Implementation Plan: Homebank-zu-hledger Konverter

**Branch**: `001-homebank-to-hledger-konverter` | **Date**: 2026-02-21 | **Spec**: research.md
**Input**: Benutzeranforderung: Homebank XHB-Dateien in jahresweise hledger-Journale konvertieren

## Summary

Konvertiert `.xhb`-Dateien (Homebank-XML-Format) in jahresweise hledger-Journaldateien mit
deutschen Kontonamen (Aktiva/Passiva/Eigenkapital/Erträge/Aufwand). Zahlungsempfänger werden
als Kreditoren- (Ausgaben) bzw. Debitoren-Konten (Einnahmen) geführt. Jedes Jahr erhält eine
eigene Datei mit Eröffnungsbuchung aus den Vorjahres-Salden. Splittransaktionen und interne
Überweisungen werden korrekt behandelt.

## Technical Context

**Language/Version**: Python 3.12+
**Primary Dependencies**: Nur stdlib — `xml.etree.ElementTree`, `decimal`, `pathlib`, `datetime`, `argparse`, `logging`
**Storage**: Eingabe: `.xhb`-Datei; Ausgabe: `.journal`-Dateien im Zielverzeichnis
**Testing**: pytest
**Target Platform**: Linux/macOS/Windows (plattformunabhängig, reine Stdlib)
**Project Type**: CLI-Tool
**Performance Goals**: ≤50.000 Transaktionen in <10 Sekunden, <256 MB RAM
**Constraints**: Offline-only, kein Netzwerkzugriff, `Decimal` für alle Geldbeträge
**Scale/Scope**: Realistische Haushalts-XHB-Dateien (getestet: 6.279 Transaktionen, 586 Payees)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Verify compliance with all four constitution principles before proceeding:

| Principle | Check | Status |
|-----------|-------|--------|
| I. Code Quality | Alle Funktionen typisiert; `Decimal` für Geld; `pathlib.Path` für Pfade; kein bare `except`; kein `print()` für Diagnose; `HomebankParseError` und `ConversionError` definiert | ✅ |
| II. Testing Standards | 53 Tests geschrieben (parser, converter, writer); `uv run pytest` → 53/53 passed; Tests spiegeln `src/`-Struktur | ✅ |
| III. User Experience Consistency | Fehler → `stderr`; Exit-Codes 0–3 dokumentiert; deterministisch; POSIX-Flags (`-v`, `--verbose`) | ✅ |
| IV. Performance Requirements | Reale Datei (6.279 Transaktionen) konvertiert in <2s; keine Netzwerkaufrufe | ✅ |

**Quality Gates** (all MUST pass before "done"):
1. `uv run ruff format .` — ✅ zero diff
2. `uv run ruff check . --fix` — ✅ zero violations
3. `uv run mypy .` — ✅ zero errors
4. `uv run pytest` — ✅ 53/53 passed

## Project Structure

### Documentation (this feature)

```text
specs/001-homebank-to-hledger-konverter/
├── plan.md              # Dieses Dokument
├── research.md          # XHB- und hledger-Format-Analyse
├── data-model.md        # Datenmodell-Dokumentation
├── quickstart.md        # Schnellstart-Anleitung
└── contracts/
    └── cli.md           # CLI-Schnittstellenvertrag
```

### Source Code

```text
src/
├── __init__.py
├── exceptions.py        # HomebankParseError, ConversionError
├── models.py            # Datenklassen (HomebankFile, Transaction, HledgerJournal, …)
├── parser.py            # XHB-XML → HomebankFile
├── converter.py         # HomebankFile → list[HledgerJournal]
├── writer.py            # list[HledgerJournal] → .journal-Dateien
└── main.py              # CLI-Einstiegspunkt (argparse)

tests/
├── __init__.py
├── test_parser.py       # 17 Tests für parse_xhb()
├── test_converter.py    # 18 Tests für convert() und hledger_account_name()
├── test_writer.py       # 18 Tests für write_journals() und Formatierungsfunktionen
└── fixtures/
    └── minimal.xhb      # Minimale Test-XHB-Datei
```

**Structure Decision**: Single-project-Layout (CLI-Tool ohne Web-Frontend).
Reine Funktionsaufteilung: Parser → Converter → Writer, I/O nur in `main.py` und `writer.py`.

## Complexity Tracking

> Keine Verfassungsverstöße — alle Checks bestanden.
