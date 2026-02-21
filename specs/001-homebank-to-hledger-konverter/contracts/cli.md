# CLI-Vertrag: homebank-to-hledger

**Version**: 0.1.0
**Typ**: Kommandozeilen-Tool

---

## Aufruf

```
homebank-to-hledger [OPTIONEN] <eingabe.xhb> <ausgabeverzeichnis>
```

## Pflichtargumente

| Argument | Typ | Beschreibung |
|---|---|---|
| `eingabe.xhb` | Dateipfad | Homebank-Exportdatei (.xhb) |
| `ausgabeverzeichnis` | Verzeichnispfad | Zielverzeichnis für Journal-Dateien |

## Optionen

| Option | Kurzform | Standard | Beschreibung |
|---|---|---|---|
| `--verbose` | `-v` | False | Ausführliche Protokollausgabe (auf stderr) |
| `--version` | — | — | Versionsnummer anzeigen und beenden |
| `--help` | `-h` | — | Hilfe anzeigen und beenden |

## Exit-Codes

| Code | Bedeutung |
|---|---|
| `0` | Erfolgreich |
| `1` | Eingabedatei nicht gefunden oder ungültiges XML |
| `2` | Konvertierungsfehler |
| `3` | Ausgabeverzeichnis konnte nicht erstellt werden |

## Stdout / Stderr

- **stdout**: leer (kein Ausgabepfad auf stdout)
- **stderr**: Fortschritts- und Fehlermeldungen
- **Abschlussmeldung** (stderr, Exit 0):
  ```
  14 Journal-Datei(en) mit insgesamt 5432 Buchungen in './journals' erstellt.
  ```

## Ausgabestruktur

```
<ausgabeverzeichnis>/
├── main.journal          # include-Direktiven für alle Jahre
├── 2020.journal
├── 2021.journal
├── ...
└── 2026.journal
```

## Journal-Dateiformat

Jede `YYYY.journal`-Datei hat folgende Struktur:

```journal
; ============================================================
; hledger Journal YYYY
; Generiert von homebank-to-hledger
; ============================================================

decimal-mark ,

commodity 1.000,00 EUR

; --- Konto-Deklarationen ---
account Aktiva                                  ; type: A
account Aktiva:Bank                             ; type: C
...

; --- Zahlungsempfänger ---
payee REWE
payee Arbeitgeber GmbH
...

; --- Buchungen ---
YYYY-01-01 * Eröffnungsbilanz | YYYY
    Aktiva:Bank:Girokonto    1.234,56 EUR
    ...
    Eigenkapital:Eröffnungsbilanzkonto

YYYY-MM-DD [*|!] Payee | Notiz
    Aufwand:Kategorie        50,00 EUR
    Passiva:Kreditoren:Payee -50,00 EUR
    Passiva:Kreditoren:Payee  50,00 EUR
    Aktiva:Bank:Konto        -50,00 EUR
```

## Unveränderliche Garantien (Vertragsbestandteil)

1. **Determinismus:** Gleiche Eingabe → Byte-identische Ausgabe
2. **Kein Netzwerkzugriff** zur Laufzeit
3. **Fehlerausgabe ausschließlich auf stderr**
4. **Beträge** immer mit deutschem Dezimalkomma: `1.234,56 EUR`
5. **Kein `float`** intern für Geldbeträge
