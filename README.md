# homebank-to-hledger

Konvertiert [Homebank](https://www.gethomebank.org/) `.xhb`-Dateien in
jahresweise [hledger](https://hledger.org/) Journal-Dateien.

## Funktionen

- **Jahresweise Ausgabe** — jedes Kalenderjahr als eigene `.journal`-Datei + `main.journal`
- **Deutsche Kontonamen** — Aktiva / Passiva / Eigenkapital / Erträge / Aufwand
- **Kreditoren & Debitoren** — Ausgaben über `Passiva:Kreditoren:<Payee>`,
  Einnahmen über `Aktiva:Debitoren:<Payee>`
- **Jahreseröffnungsbuchungen** — Salden zum 31.12. als Eröffnungsbilanz am 01.01.
- **Splittransaktionen** — mehrere Kategorien pro Buchung → mehrere Postings
- **Interne Überweisungen** — `kxfer`-Paare werden als einzelne Transaktion ausgegeben
- **hledger-kompatibel** — `hledger check` bestanden (getestet mit 6.279 Transaktionen)

## Voraussetzungen

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (moderner Python-Paketmanager)

## Installation

```bash
git clone <repo-url>
cd homebank-to-hledger
uv sync
```

## Verwendung

```bash
uv run homebank-to-hledger <eingabe.xhb> <ausgabeverzeichnis>
```

### Optionen

| Option | Kurzform | Beschreibung |
|---|---|---|
| `--verbose` | `-v` | Ausführliche Protokollausgabe |
| `--version` | | Versionsnummer anzeigen |
| `--help` | `-h` | Hilfe anzeigen |

### Beispiele

```bash
# Grundaufruf
uv run homebank-to-hledger "Finanzübersicht.xhb" ./journals

# Mit ausführlicher Ausgabe
uv run homebank-to-hledger "Finanzübersicht.xhb" ./journals -v
```

### Beispielausgabe

```
INFO: Parsing abgeschlossen: 20 Konten, 189 Kategorien, 586 Zahlungsempfänger, 6279 Transaktionen
INFO: Schreibe ./journals/2024.journal (1033 Transaktionen)
INFO: Schreibe ./journals/main.journal
14 Journal-Datei(en) mit insgesamt 5432 Buchungen in './journals' erstellt.
```

## Ausgabestruktur

```
journals/
├── main.journal      ← include-Direktiven für alle Jahre
├── 2020.journal
├── 2021.journal
├── ...
└── 2026.journal
```

Jede Jahres-Datei enthält:
- `decimal-mark ,` und `commodity 1.000,00 EUR` (deutsches Format)
- `account`-Deklarationen mit `; type:`-Tags für hledger-Berichte
- `payee`-Deklarationen für alle Zahlungsempfänger
- Eröffnungsbuchung am 01.01. (ab dem zweiten Jahr)
- Alle Buchungen des Jahres, chronologisch sortiert

## Konto-Konventionen

| Homebank-Typ | hledger-Konto | Beispiel |
|---|---|---|
| Bank (type 1) | `Aktiva:Bank:<Name>` | `Aktiva:Bank:Girokonto` |
| Bargeld (type 2) | `Aktiva:Kasse:<Name>` | `Aktiva:Kasse:Bargeld` |
| Sparbuch (type 7) | `Aktiva:Spareinlagen:<Name>` | `Aktiva:Spareinlagen:Sparbuch` |
| Kreditkarte (type 4) | `Passiva:Kreditkarte:<Name>` | `Passiva:Kreditkarte:Mastercard` |
| Darlehen (type 5) | `Passiva:Darlehen:<Name>` | `Passiva:Darlehen:Kredit Haus` |
| Ausgabe-Kategorie | `Aufwand:<Kategorie>` | `Aufwand:Lebensmittel` |
| Einnahme-Kategorie | `Erträge:<Kategorie>` | `Erträge:Lohn & Gehalt` |
| Payee (Ausgabe) | `Passiva:Kreditoren:<Payee>` | `Passiva:Kreditoren:REWE` |
| Payee (Einnahme) | `Aktiva:Debitoren:<Payee>` | `Aktiva:Debitoren:Arbeitgeber GmbH` |
| Jahreseröffnung | `Eigenkapital:Eröffnungsbilanzkonto` | |

## Auswertung mit hledger

```bash
# Kontoübersicht
hledger -f journals/main.journal accounts

# Bilanz (Aktiva / Passiva)
hledger -f journals/main.journal bs

# Gewinn- und Verlustrechnung
hledger -f journals/main.journal incomestatement

# Alle Ausgaben bei REWE
hledger -f journals/main.journal reg payee:REWE

# Kontostand Girokonto
hledger -f journals/main.journal bal "Aktiva:Bank:Girokonto"

# Aufwand nach Kategorie (nur 2024)
hledger -f journals/2024.journal bal type:X
```

## Exit-Codes

| Code | Bedeutung |
|---|---|
| `0` | Erfolgreich |
| `1` | Eingabedatei nicht gefunden oder ungültiges XML |
| `2` | Konvertierungsfehler |
| `3` | Ausgabeverzeichnis konnte nicht erstellt werden |

## Entwicklung

```bash
# Tests ausführen
uv run pytest

# Code formatieren
uv run ruff format .

# Linting
uv run ruff check . --fix

# Typprüfung (strict)
uv run mypy .
```

## Projektstruktur

```
src/
├── exceptions.py   # HomebankParseError, ConversionError
├── models.py       # Datenklassen für Homebank- und hledger-Modelle
├── parser.py       # XHB-XML → HomebankFile
├── converter.py    # HomebankFile → list[HledgerJournal]
├── writer.py       # list[HledgerJournal] → .journal-Dateien
└── main.py         # CLI-Einstiegspunkt (argparse)

tests/
├── test_parser.py       # Parser-Tests
├── test_converter.py    # Konverter-Tests
├── test_writer.py       # Writer-Tests
├── test_integration.py  # End-to-End-Tests (benötigt hledger im PATH)
└── fixtures/
    └── minimal.xhb      # Minimale Test-XHB-Datei
```

## Lizenz

Siehe [LICENSE](LICENSE).
