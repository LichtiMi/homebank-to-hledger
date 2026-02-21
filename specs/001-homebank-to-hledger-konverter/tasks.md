---
description: "Aufgabenliste: Homebank-zu-hledger Konverter"
---

# Tasks: Homebank-zu-hledger Konverter

**Input**: Design-Dokumente aus `specs/001-homebank-to-hledger-konverter/`
**Prerequisites**: plan.md ✅, research.md ✅, data-model.md ✅, contracts/cli.md ✅, quickstart.md ✅

**Status-Legende**:
- `[x]` Abgeschlossen (implementiert, getestet, alle Gates grün)
- `[ ]` Offen — muss noch implementiert werden

**Hinweis**: Dieses Projekt wurde bereits initial implementiert (Commit `7bb8011`).
Die Tasks spiegeln den Ist-Stand wider. Offene Tasks sind echte Bugs und Lücken,
die beim Ausführen gegen die reale XHB-Datei mit `hledger check` entdeckt wurden.

---

## Format: `[ID] [P?] [Story?] Beschreibung mit Dateipfad`

- **[P]**: Parallel ausführbar (verschiedene Dateien, keine Abhängigkeiten)
- **[Story]**: Welcher User Story die Task zugeordnet ist (US1–US5)

---

## Phase 1: Setup (Projekt-Infrastruktur)

**Zweck**: Projektinitialisierung, Verzeichnisstruktur, Tooling

- [x] T001 Erstelle Verzeichnisstruktur `src/`, `tests/fixtures/` am Repository-Root
- [x] T002 Erstelle `pyproject.toml` mit Python 3.12+, pytest, mypy, ruff (dependency-groups)
- [x] T003 [P] Erstelle `src/__init__.py` und `tests/__init__.py` (leere Pakete)
- [x] T004 [P] Konfiguriere ruff (line-length=88, select E/F/I/UP/B/SIM) in `pyproject.toml`
- [x] T005 [P] Konfiguriere mypy strict mode in `pyproject.toml`
- [x] T006 [P] Konfiguriere pytest (testpaths=["tests"]) in `pyproject.toml`
- [x] T007 [P] Führe `uv sync` aus und bestätige .venv-Erstellung

---

## Phase 2: Foundational (Blocking Prerequisites)

**Zweck**: Gemeinsame Datenmodelle und Ausnahmen, die alle User Stories benötigen

**⚠️ CRITICAL**: Keine User-Story-Implementierung kann beginnen, bevor diese Phase abgeschlossen ist

- [x] T008 Erstelle `src/exceptions.py` mit `HomebankParseError` und `ConversionError`
- [x] T009 Erstelle `src/models.py` mit allen Homebank-Quellmodellen:
  `Currency`, `Group`, `Account`, `Payee`, `Category`, `Split`, `Transaction`, `HomebankFile`
- [x] T010 Erstelle `src/models.py` mit hledger-Ausgabemodellen:
  `HledgerPosting`, `HledgerTransaction`, `HledgerJournal`
- [x] T011 Definiere Konstanten in `src/models.py`:
  `ACCOUNT_TYPE_*`, `AF_CLOSED`, `OF_INCOME`, `OF_SPLIT`, `TXN_STATUS_*`
- [x] T012 Erstelle minimale Test-Fixture `tests/fixtures/minimal.xhb` mit:
  2 Konten, 2 Payees, 2 Kategorien, 1 Normal-, 1 Split-, 1 Überweisungs-Transaktion

**Checkpoint**: Foundation bereit — User Stories können implementiert werden

---

## Phase 3: User Story 1 — Basiskonvertierung (Priority: P1) 🎯 MVP

**Goal**: Eine `.xhb`-Datei wird korrekt geparst und in jahresweise `.journal`-Dateien
konvertiert. Alle Buchungen erscheinen als gültige hledger-Transaktionen mit deutschen
Kontonamen.

**Independent Test**:
```bash
uv run homebank-to-hledger tests/fixtures/minimal.xhb /tmp/test-out
ls /tmp/test-out/          # YYYY.journal + main.journal vorhanden
uv run pytest tests/test_parser.py tests/test_converter.py tests/test_writer.py -v
```

### Implementation für User Story 1

- [x] T013 [US1] Implementiere `parse_xhb()` in `src/parser.py`:
  XML-Parsing, Datum (fromordinal), Decimal-Beträge, alle Element-Typen
- [x] T014 [P] [US1] Implementiere `_parse_currency()` in `src/parser.py`
- [x] T015 [P] [US1] Implementiere `_parse_account()` mit type/flags in `src/parser.py`
- [x] T016 [P] [US1] Implementiere `_parse_payee()` und `_parse_category()` in `src/parser.py`
- [x] T017 [US1] Implementiere `_parse_transaction()` mit Status, Flags, kxfer in `src/parser.py`
- [x] T018 [US1] Implementiere `convert()` und `_build_journal()` in `src/converter.py`:
  Jahresgruppierung, Konto-Deklarationen, Payee-Deklarationen
- [x] T019 [US1] Implementiere Konto-Name-Mapping (`hledger_account_name()`,
  `_account_prefix()`) in `src/converter.py`
- [x] T020 [US1] Implementiere `_format_journal()` und `_format_transaction()` in `src/writer.py`:
  deutsches EUR-Format (decimal-mark ,), Konto-/Payee-Deklarationen
- [x] T021 [US1] Implementiere `_format_amount()` mit deutschen Tausenderpunkten in `src/writer.py`
- [x] T022 [US1] Implementiere `write_journals()` und `_format_main_journal()` in `src/writer.py`
- [x] T023 [US1] Implementiere CLI-Einstiegspunkt `main()` in `src/main.py`:
  argparse, Exit-Codes 0–3, Fehler → stderr
- [x] T024 [P] [US1] Schreibe 17 Parser-Tests in `tests/test_parser.py`
- [x] T025 [P] [US1] Schreibe 9 Konverter-Basistests in `tests/test_converter.py`
- [x] T026 [P] [US1] Schreibe 18 Writer-Tests in `tests/test_writer.py`

### Bug-Fix für User Story 1 (entdeckt bei `hledger check`)

- [x] T027 [US1] **BUG-FIX**: Normalisiere mehrfache Leerzeichen in Kontonamen in
  `src/converter.py` → `_sanitize_account_name()`: `re.sub(r' {2,}', ' ', name)`.
  Reproduktionstest in `tests/test_converter.py`:
  `test_doppeltes_leerzeichen_in_payee_name_wird_normalisiert()`
- [x] T028 [US1] **BUG-FIX**: Korrigiere Syntax der `account`-Direktive für geschlossene
  Konten in `src/converter.py` → `_add_account_declarations()`:
  `; type: A  ; geschlossen` → `; type: A, geschlossen: true`.
  Reproduktionstest in `tests/test_converter.py`:
  `test_geschlossenes_konto_hat_valides_type_tag()`

**Checkpoint**: US1 vollständig testbar — `hledger check` auf generierter Ausgabe muss fehlerfrei sein

---

## Phase 4: User Story 2 — Kreditoren/Debitoren-Konten (Priority: P2)

**Goal**: Jeder Zahlungsempfänger erhält eigene `Passiva:Kreditoren:<Name>`-
(Ausgaben) bzw. `Aktiva:Debitoren:<Name>`-Konten (Einnahmen). Salden schließen
in derselben Transaktion auf 0 (4-Posting-Muster).

**Independent Test**:
```bash
uv run pytest tests/test_converter.py::TestConvert::test_ausgabe_erzeugt_kreditoren_konto -v
uv run pytest tests/test_converter.py::TestConvert::test_einnahme_erzeugt_debitoren_konto -v
```

### Implementation für User Story 2

- [x] T029 [US2] Implementiere `_payee_account()` in `src/converter.py`:
  amount < 0 → `Passiva:Kreditoren:<Payee>`, amount ≥ 0 → `Aktiva:Debitoren:<Payee>`
- [x] T030 [US2] Implementiere 4-Posting-Buchungsmuster für Ausgaben mit Payee in
  `_convert_normal_transaction()` in `src/converter.py`
- [x] T031 [US2] Implementiere 4-Posting-Buchungsmuster für Einnahmen mit Payee in
  `_convert_normal_transaction()` in `src/converter.py`
- [x] T032 [US2] Implementiere 2-Posting-Fallback ohne Payee (Aufwand/Ertrag ↔ Konto)
  in `_convert_normal_transaction()` in `src/converter.py`
- [x] T033 [P] [US2] Schreibe Tests für Kreditoren/Debitoren in `tests/test_converter.py`:
  `test_ausgabe_erzeugt_kreditoren_konto()`, `test_einnahme_erzeugt_debitoren_konto()`

**Checkpoint**: US2 vollständig — Kreditoren/Debitoren-Konten erscheinen korrekt im Journal

---

## Phase 5: User Story 3 — Jahreseröffnungsbuchungen (Priority: P3)

**Goal**: Jedes Journal (außer dem ersten) beginnt mit einer korrekten
`Eröffnungsbilanz`-Transaktion, die die Salden zum 31.12. des Vorjahres enthält.
Gegenkonto ist `Eigenkapital:Eröffnungsbilanzkonto`.

**Independent Test**:
```bash
uv run pytest tests/test_converter.py::TestConvert::test_eroeffnungsbuchung_ab_zweitem_jahr -v
uv run pytest tests/test_converter.py::TestCalculateBalances -v
```

### Implementation für User Story 3

- [x] T034 [US3] Implementiere `calculate_balances_up_to()` in `src/converter.py`:
  Anfangssalden + alle Transaktionen bis Stichtag aufsummieren
- [x] T035 [US3] Implementiere `_build_opening_balance()` in `src/converter.py`:
  Buchung am 01.01., `Eigenkapital:Eröffnungsbilanzkonto` als inferiertes Gegenkonto
- [x] T036 [US3] Integriere Eröffnungsbuchung in `_build_journal()` in `src/converter.py`
  (nur wenn Jahr > erstes Jahr mit Transaktionen)
- [x] T037 [P] [US3] Schreibe Tests in `tests/test_converter.py`:
  `test_eroeffnungsbuchung_ab_zweitem_jahr()`,
  `test_nur_anfangssaldo_ohne_transaktionen()`,
  `test_saldo_nach_allen_transaktionen()`

**Checkpoint**: US3 vollständig — jede Jahres-Datei ist eigenständig bilanzierbar

---

## Phase 6: User Story 4 — Splittransaktionen (Priority: P4)

**Goal**: Transaktionen mit `flags & 256` (OF_SPLIT) werden als Mehrfach-Posting-
Transaktion ausgegeben. Jeder Split-Eintrag (`scat`/`samt`/`smem`) erzeugt
ein eigenes Aufwand/Ertrags-Posting.

**Independent Test**:
```bash
uv run pytest tests/test_parser.py::TestParseXhb::test_split_transaktion_wird_erkannt -v
uv run pytest tests/test_converter.py::TestConvert::test_split_transaktion_mehrere_postings -v
```

### Implementation für User Story 4

- [x] T038 [US4] Implementiere `_parse_splits()` in `src/parser.py`:
  `||`-getrennte `scat`/`samt`/`smem` → `tuple[Split, ...]`
- [x] T039 [US4] Integriere Split-Parsing in `_parse_transaction()` in `src/parser.py`
  (nur wenn `flags & OF_SPLIT`)
- [x] T040 [US4] Implementiere `_convert_split_transaction()` in `src/converter.py`:
  je Split ein Aufwand/Ertrag-Posting + Kreditoren/Debitoren, dann Konto-Abschluss
- [x] T041 [P] [US4] Schreibe Tests in `tests/test_parser.py`:
  `test_split_transaktion_wird_erkannt()` (Anzahl Splits, Betrag, Memo)
- [x] T042 [P] [US4] Schreibe Tests in `tests/test_converter.py`:
  `test_split_transaktion_mehrere_postings()` (>2 Postings)

**Checkpoint**: US4 vollständig — Splittransaktionen erzeugen korrekte Mehrfach-Postings

---

## Phase 7: User Story 5 — Interne Überweisungen (Priority: P5)

**Goal**: `kxfer`-Paare (zwei `<ope>`-Einträge mit gleichem Wert) werden als
einzelne 2-Posting-Transaktion ausgegeben. Die zweite Seite wird unterdrückt.

**Independent Test**:
```bash
uv run pytest tests/test_parser.py::TestParseXhb::test_interne_ueberweisung_wird_erkannt -v
uv run pytest tests/test_converter.py::TestConvert::test_kein_doppeltes_kxfer -v
```

### Implementation für User Story 5

- [x] T043 [US5] Implementiere kxfer-Erkennung in `_parse_transaction()` in `src/parser.py`:
  `kxfer`- und `dst_account`-Attribute → `Transaction.is_internal_transfer`
- [x] T044 [US5] Implementiere `_convert_internal_transfer()` in `src/converter.py`:
  Quell- ↔ Zielkonto als 2-Posting, Beschreibung als `Interne Überweisung`
- [x] T045 [US5] Implementiere kxfer-Deduplizierung via `seen_kxfer: set[int]` in
  `_convert_single_transaction()` in `src/converter.py`
- [x] T046 [P] [US5] Schreibe Tests in `tests/test_parser.py`:
  `test_interne_ueberweisung_wird_erkannt()` (beide Seiten mit kxfer=1)
- [x] T047 [P] [US5] Schreibe Tests in `tests/test_converter.py`:
  `test_kein_doppeltes_kxfer()` (nur 1 Transaktion für das Paar)

**Checkpoint**: US5 vollständig — alle User Stories implementiert und testbar

---

## Phase 8: Polish & Cross-Cutting Concerns

**Zweck**: Qualitätssicherung, End-to-End-Validierung, Konto-Typ-Vollständigkeit.
Alle vier Verfassungsprinzipien werden auf die Gesamtimplementierung angewendet.

- [x] T048 [P] **[Code Quality]** Ergänze Konto-Typ 7 (Sparbuch/Savings) in `src/models.py`
  als `ACCOUNT_TYPE_SAVINGS = 7` und in `src/converter.py` → `_account_prefix()`:
  type 7 → `Aktiva:Spareinlagen`
- [x] T049 [P] **[Testing Standards]** Erstelle `tests/test_integration.py` mit
  End-to-End-Test: XHB parsen → konvertieren → schreiben → `hledger check` auf Output.
  Nur ausführen wenn `hledger` im PATH vorhanden (via `shutil.which("hledger")`)
- [x] T050 **[UX Consistency]** Aktualisiere `README.md` mit vollständiger Verwendungsdokumentation:
  Installation, Beispielaufruf, Konventions-Tabelle, Exit-Codes
- [x] T051 **[Testing Standards]** Führe `uv run pytest` aus — bestätige 0 Fehler,
  validiere alle Repro-Tests für T027 und T028 schlagen vor dem Fix fehl
- [x] T052 **[Code Quality]** Führe `uv run ruff format . && uv run ruff check . --fix` aus
- [x] T053 **[Code Quality]** Führe `uv run mypy .` aus — bestätige 0 Fehler (strict)
- [x] T054 **[Performance]** Validiere Quickstart (`specs/001-homebank-to-hledger-konverter/quickstart.md`):
  Konvertierung der echten XHB-Datei in <10s, Ausgabe in <256 MB RAM
  (Ergebnis: 0,54s Laufzeit, 37 MB RAM — weit unter den Grenzwerten)

---

## Dependencies & Execution Order

### Phase-Abhängigkeiten

- **Setup (Phase 1)**: Keine Abhängigkeiten — sofort startbar
- **Foundational (Phase 2)**: Hängt von Phase 1 ab — blockiert alle User Stories
- **User Stories (Phase 3–7)**: Alle hängen von Phase 2 ab
  - US1 (P1) zuerst — alle anderen bauen darauf auf
  - US2–US5 können nach US1-Fertigstellung parallel implementiert werden
- **Polish (Phase 8)**: Hängt von allen User Stories ab

### User Story Abhängigkeiten

- **US1 (P1)**: Keine Abhängigkeit — kann nach Foundational starten; **MUSS zuerst fertig sein**
- **US2 (P2)**: Hängt von US1-Modellen (parser.py, models.py) ab — kann danach parallel
- **US3 (P3)**: Hängt von US1-Modellen ab — kann parallel zu US2 laufen
- **US4 (P4)**: Hängt von US1-Parser (split-Parsing) ab — kann parallel zu US2/US3
- **US5 (P5)**: Hängt von US1-Parser (kxfer-Parsing) ab — kann parallel zu US2/US3/US4

### Innerhalb jeder User Story

- Modelle vor Services
- Parser vor Converter
- Converter vor Writer
- Implementierung vor Tests (Ist-Stand: Tests wurden co-located geschrieben)
- Bug-Fix-Tests müssen VOR dem Fix fehlschlagen (T027, T028)

### Parallele Möglichkeiten

```bash
# Offene Bug-Fixes können parallel gestartet werden (verschiedene Funktionen):
Task: "T027 — _sanitize_account_name() in src/converter.py"
Task: "T028 — _add_account_declarations() in src/converter.py"

# Polish-Tasks parallel:
Task: "T048 — Typ-7-Mapping in src/models.py + src/converter.py"
Task: "T049 — tests/test_integration.py erstellen"
Task: "T050 — README.md aktualisieren"
```

---

## Implementation Strategy

### MVP (bereits erreicht — US1 vollständig)

1. ✅ Phase 1: Setup abgeschlossen
2. ✅ Phase 2: Foundation abgeschlossen
3. ✅ Phase 3 (US1): Basiskonvertierung implementiert und getestet
4. **NÄCHSTE AKTION**: T027 + T028 (kritische Bug-Fixes) vor allem anderen

### Sofortige Priorität (kritische Bugs)

1. T027 — Doppeltes-Leerzeichen-Bug: Repro-Test → Fix → `hledger check` grün
2. T028 — Geschlossenes-Konto-Tag-Bug: Repro-Test → Fix → `hledger check` grün
3. T051–T053 — Quality Gates bestätigen

### Inkrementelle Lieferung (verbleibend)

1. T027 + T028 → `hledger check` fehlerfrei ✓
2. T048 → Typ-7-Konten korrekt gemappt ✓
3. T049 → Integrations-Test mit echtem hledger ✓
4. T050 → README vollständig ✓
5. T054 → Performance-Benchmark bestätigt ✓

---

## Notes

- `[x]` Tasks sind bereits implementiert (Commit `7bb8011`) — nicht nochmals anfassen
- `[ ]` Tasks sind offen — die Bug-Fixes (T027, T028) haben höchste Priorität
- T027 und T028 sind unabhängig voneinander (verschiedene Funktionen) — parallel ausführbar
- `[P]` Tasks = verschiedene Dateien, keine Abhängigkeiten untereinander
- Alle `[ ]`-Tasks müssen durch `uv run ruff format .`, `uv run ruff check .`,
  `uv run mypy .` und `uv run pytest` validiert werden
