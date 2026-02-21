# Quickstart: Homebank-zu-hledger Konverter

## Voraussetzungen

- Python 3.12+
- `uv` (https://docs.astral.sh/uv/)

## Installation

```bash
# Abhängigkeiten installieren
uv sync

# Werkzeug testen
uv run homebank-to-hledger --version
```

## Verwendung

```bash
# Grundaufruf
uv run homebank-to-hledger "Meine Finanzen.xhb" ./journals

# Mit ausführlicher Ausgabe
uv run homebank-to-hledger "Meine Finanzen.xhb" ./journals -v
```

## Beispielausgabe

```
INFO: Parsing abgeschlossen: 20 Konten, 189 Kategorien, 586 Zahlungsempfänger, 6279 Transaktionen
INFO: Schreibe ./journals/2024.journal (1033 Transaktionen)
...
14 Journal-Datei(en) mit insgesamt 5432 Buchungen in './journals' erstellt.
```

## Ausgabe mit hledger auswerten

```bash
# Kontoübersicht
hledger -f journals/main.journal accounts

# Bilanz
hledger -f journals/main.journal bs

# Aufwand nach Kategorie (2024)
hledger -f journals/2024.journal incomestatement

# Ausgaben bei einem bestimmten Payee
hledger -f journals/main.journal reg payee:REWE

# Kontostand Girokonto
hledger -f journals/main.journal bal "Aktiva:Bank:Bankkonto Michi"
```

## Entwicklung

```bash
# Tests ausführen
uv run pytest

# Code formatieren
uv run ruff format .

# Linting
uv run ruff check . --fix

# Typprüfung
uv run mypy .
```

## Konventionen der generierten Journale

| Homebank-Konzept | hledger-Konto |
|---|---|
| Bank-Konto | `Aktiva:Bank:<Name>` |
| Bargeld | `Aktiva:Kasse:<Name>` |
| Kreditkarte | `Passiva:Kreditkarte:<Name>` |
| Darlehen | `Passiva:Darlehen:<Name>` |
| Ausgabe-Kategorie | `Aufwand:<Kategorie>` |
| Einnahme-Kategorie | `Erträge:<Kategorie>` |
| Payee (Ausgabe) | `Passiva:Kreditoren:<Payee>` |
| Payee (Einnahme) | `Aktiva:Debitoren:<Payee>` |
| Jahreseröffnung | `Eigenkapital:Eröffnungsbilanzkonto` |
