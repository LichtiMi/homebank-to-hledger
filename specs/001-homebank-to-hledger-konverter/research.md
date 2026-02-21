# Research: Homebank-zu-hledger Konverter

**Feature Branch**: `001-homebank-to-hledger-konverter`
**Datum**: 2026-02-21

---

## 1. Homebank XHB Dateiformat

### 1.1 Datumsformat
- **Entscheidung:** GLib Julian Day Number = Python `datetime.date.toordinal()`
- **Konvertierung:** `datetime.date.fromordinal(N)` — kein Offset nötig
- **Belegt:** `date="735233"` → `date.fromordinal(735233)` → `2013-12-31` ✓

### 1.2 Betragsformat
- **Entscheidung:** XML-Attributwert direkt via `Decimal(raw_string)` lesen — kein float-Umweg
- **Rationale:** `Decimal("8851.5")` ist exakt; `Decimal(float("8851.5"))` ergibt Noise

### 1.3 Account-Typen (aus `hb-account.h`)

| type | Bedeutung | hledger-Mapping |
|---|---|---|
| 0 | Keine Angabe | `Aktiva` |
| 1 | Bank | `Aktiva:Bank` |
| 2 | Bargeld | `Aktiva:Kasse` |
| 3 | Vermögenswert | `Aktiva:Vermögen` |
| 4 | Kreditkarte | `Passiva:Kreditkarte` |
| 5 | Verbindlichkeit | `Passiva:Darlehen` |

### 1.4 Transaktions-Flags
- `OF_INCOME` = bit 1 (2): Einnahme (informativ; Vorzeichen von `amount` ist maßgeblich)
- `OF_SPLIT` = bit 8 (256): Splittransaktion mit `scat`/`samt`/`smem`-Attributen
- `AF_CLOSED` = bit 1 (2) auf Account: Konto geschlossen

### 1.5 Splittransaktionen
- `scat`, `samt`, `smem` sind `||`-getrennte Parallellisten
- Jeder Split-Eintrag → eigene hledger-Posting-Zeile

### 1.6 Interne Überweisungen
- Zwei `<ope>`-Einträge mit gleichem `kxfer`-Wert
- Duplikat erkannt und unterdrückt (nur erste Seite ausgegeben)
- `dst_account` zeigt auf das Gegenkonto

### 1.7 Kategorien-Flags
- `GF_INCOME` = bit 1 (2): Einnahme-Kategorie → Präfix `Erträge:`
- Ohne dieses Flag: Ausgabe-Kategorie → Präfix `Aufwand:`
- Subkategorien: `parent`-Attribut vorhanden; Pfad = `Eltern:Kind`

---

## 2. hledger Journal-Format

### 2.1 Konto-Hierarchie mit deutschen Namen
- `account`-Direktive mit `; type: X` Tag erforderlich (hledger erkennt sonst nur englische Namen)
- Typen: `A` (Aktiva), `L` (Passiva), `E` (Eigenkapital), `R` (Erträge), `X` (Aufwand), `C` (Kasse/Bank)

### 2.2 Jahresweise Journale
- Eine Datei pro Kalenderjahr: `2024.journal`
- `main.journal` mit `include`-Direktiven
- Eröffnungsbuchung am 01.01. mit Salden vom 31.12. des Vorjahres

### 2.3 Währungsformatierung
- `decimal-mark ,` (deutsches Format)
- `commodity 1.000,00 EUR`

### 2.4 Beschreibungszeile
- Format: `Payee | Notiz` (hledger-Payee/Note-Trenner)

---

## 3. Buchungsmodell für Zahlungsempfänger

**Gewählte Lösung (Option B — Kreditoren/Debitoren-Konten):**

- Debitoren (Einnahmen) → `Aktiva:Debitoren:<Payee-Name>` (unter Aktiva)
- Kreditoren (Ausgaben) → `Passiva:Kreditoren:<Payee-Name>` (unter Passiva)

Da Homebank-Buchungen sofort beglichen sind, schließt jeder Kreditoren/Debitoren-Saldo
in einer Transaktion auf 0 — das 4-Posting-Muster wird verwendet:

```journal
; Ausgabe mit Payee REWE:
2024-03-15 * REWE | Wocheneinkauf
    Aufwand:Lebensmittel             50,00 EUR
    Passiva:Kreditoren:REWE         -50,00 EUR
    Passiva:Kreditoren:REWE          50,00 EUR
    Aktiva:Bank:Bankkonto Michi     -50,00 EUR
```

---

## 4. Datei der echten XHB-Datei (Statistik)

| Kennzahl | Wert |
|---|---|
| Konten | 20 |
| Kategorien | 189 |
| Zahlungsempfänger | 586 |
| Transaktionen gesamt | 6.279 |
| Jahre mit Buchungen | 2013–2026 (aktiv ab 2020) |
| Basiswährung | EUR |
| Fremdwährungskonten | eToro (USD) |
