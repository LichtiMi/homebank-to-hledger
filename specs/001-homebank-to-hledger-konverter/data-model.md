# Datenmodell: Homebank-zu-hledger Konverter

**Feature Branch**: `001-homebank-to-hledger-konverter`
**Datum**: 2026-02-21

---

## 1. Homebank-Quellmodelle (aus XHB-XML)

### Currency (Währung)
| Feld | Typ | Quelle |
|---|---|---|
| `key` | `int` | `<cur key>` |
| `iso` | `str` | `<cur iso>` |
| `name` | `str` | `<cur name>` |
| `symbol` | `str` | `<cur symb>` |
| `decimal_char` | `str` | `<cur dchar>` |
| `group_char` | `str` | `<cur gchar>` |
| `fraction` | `int` | `<cur frac>` |
| `rate` | `Decimal` | `<cur rate>` |

### Account (Konto)
| Feld | Typ | Quelle |
|---|---|---|
| `key` | `int` | `<account key>` |
| `name` | `str` | `<account name>` |
| `account_type` | `int` | `<account type>` (0–5) |
| `currency_key` | `int` | `<account curr>` |
| `initial_balance` | `Decimal` | `<account initial>` |
| `flags` | `int` | `<account flags>` |
| `number` | `str` | `<account number>` |
| `bank_name` | `str` | `<account bankname>` |
| `group_key` | `int \| None` | `<account grp>` |

Abgeleitete Eigenschaft: `is_closed` → `flags & AF_CLOSED` (bit 1)

### Payee (Zahlungsempfänger)
| Feld | Typ | Quelle |
|---|---|---|
| `key` | `int` | `<pay key>` |
| `name` | `str` | `<pay name>` |
| `default_category_key` | `int \| None` | `<pay category>` |

### Category (Kategorie)
| Feld | Typ | Quelle |
|---|---|---|
| `key` | `int` | `<cat key>` |
| `name` | `str` | `<cat name>` |
| `flags` | `int` | `<cat flags>` |
| `parent_key` | `int \| None` | `<cat parent>` |

Abgeleitete Eigenschaften:
- `is_income` → `flags & GF_INCOME` (bit 1)
- `is_subcategory` → `parent_key is not None`

### Split (Teilbuchung)
| Feld | Typ | Quelle |
|---|---|---|
| `amount` | `Decimal` | `<ope samt>` (||–getrennt) |
| `category_key` | `int \| None` | `<ope scat>` (||–getrennt) |
| `memo` | `str` | `<ope smem>` (||–getrennt) |

### Transaction (Transaktion)
| Feld | Typ | Quelle |
|---|---|---|
| `date` | `date` | `<ope date>` (fromordinal) |
| `amount` | `Decimal` | `<ope amount>` |
| `account_key` | `int` | `<ope account>` |
| `flags` | `int` | `<ope flags>` |
| `status` | `int` | `<ope st>` |
| `paymode` | `int` | `<ope paymode>` |
| `payee_key` | `int \| None` | `<ope payee>` |
| `category_key` | `int \| None` | `<ope category>` |
| `wording` | `str` | `<ope wording>` |
| `info` | `str` | `<ope info>` |
| `kxfer` | `int \| None` | `<ope kxfer>` |
| `dst_account_key` | `int \| None` | `<ope dst_account>` |
| `splits` | `tuple[Split, ...]` | `scat/samt/smem` |

---

## 2. hledger-Ausgabemodelle

### HledgerPosting (Buchungszeile)
| Feld | Typ | Bedeutung |
|---|---|---|
| `account` | `str` | Vollständiger Kontoname |
| `amount` | `Decimal \| None` | Betrag (None = von hledger inferiert) |
| `currency` | `str` | ISO-Währungscode |
| `comment` | `str` | Optionaler Kommentar |

### HledgerTransaction (Transaktion)
| Feld | Typ | Bedeutung |
|---|---|---|
| `date` | `date` | Buchungsdatum |
| `status` | `str` | `""`, `"!"` oder `"*"` |
| `payee` | `str` | Payee-Teil der Beschreibung |
| `note` | `str` | Notiz-Teil der Beschreibung |
| `postings` | `tuple[HledgerPosting, ...]` | Buchungszeilen |
| `comment` | `str` | Transaktionskommentar |

### HledgerJournal (Jahresjournal)
| Feld | Typ | Bedeutung |
|---|---|---|
| `year` | `int` | Kalenderjahr |
| `base_currency_iso` | `str` | ISO-Code der Basiswährung |
| `account_declarations` | `list[str]` | `account X ; type: Y`-Zeilen |
| `payee_declarations` | `list[str]` | Payee-Namen |
| `transactions` | `list[HledgerTransaction]` | Sortierte Buchungen |

---

## 3. Konto-Name-Mapping

### Homebank-Kontotyp → hledger-Präfix

| type | Präfix | hledger type-Tag |
|---|---|---|
| 0 (none) | `Aktiva` | `A` |
| 1 (Bank) | `Aktiva:Bank` | `C` |
| 2 (Cash) | `Aktiva:Kasse` | `C` |
| 3 (Asset) | `Aktiva:Vermögen` | `A` |
| 4 (Kreditkarte) | `Passiva:Kreditkarte` | `L` |
| 5 (Liability) | `Passiva:Darlehen` | `L` |
| 7 (Savings) | `Aktiva:Spareinlagen` | `A` |

Vollständiger Kontoname: `<Präfix>:<bereinigter-Kontoname>`
Bereinigung: `:` → `-`, führende/nachfolgende Leerzeichen entfernt.

### Kategorie → hledger-Konto

- `GF_INCOME` gesetzt: `Erträge:<Kategoriepfad>`
- `GF_INCOME` nicht gesetzt: `Aufwand:<Kategoriepfad>`
- Subkategorie-Pfad: `<Elternname>:<Kindname>`
- Ohne Kategorie + negativer Betrag: `Aufwand:Nicht kategorisiert`
- Ohne Kategorie + positiver Betrag: `Erträge:Nicht kategorisiert`

### Payee → hledger-Durchlauf-Konto

- Ausgabe (amount < 0): `Passiva:Kreditoren:<Payee-Name>`
- Einnahme (amount ≥ 0): `Aktiva:Debitoren:<Payee-Name>`
