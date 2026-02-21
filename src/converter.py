"""
Konvertierungslogik: Homebank-Datenmodell → hledger-Journale.

Buchungsmodell:
- Ausgaben:  Aufwand:Kategorie  /  Passiva:Kreditoren:Payee  ↔  Aktiva:Konto
- Einnahmen: Aktiva:Debitoren:Payee  /  Erträge:Kategorie  ↔  Aktiva:Konto
- Intern:    Aktiva:KontoA  ↔  Aktiva:KontoB  (kxfer-Duplikat unterdrückt)
- Split:     je Split-Eintrag ein Aufwand/Ertrags-Posting + Kreditoren/Debitoren-Konto
"""

import logging
import re
from collections import defaultdict
from datetime import date
from decimal import Decimal

from src.exceptions import ConversionError
from src.models import (
    ACCOUNT_TYPE_BANK,
    ACCOUNT_TYPE_CASH,
    ACCOUNT_TYPE_CREDITCARD,
    ACCOUNT_TYPE_LIABILITY,
    ACCOUNT_TYPE_NONE,
    ACCOUNT_TYPE_SAVINGS,
    TXN_STATUS_CLEARED,
    TXN_STATUS_RECONCILED,
    Account,
    Category,
    HledgerJournal,
    HledgerPosting,
    HledgerTransaction,
    HomebankFile,
    Payee,
    Transaction,
)

logger = logging.getLogger(__name__)

# Konten ohne Payee-Buchung (interne Überweisungen erhalten keinen Kreditoren-Eintrag)
_INTERNAL_TRANSFER_PAYMODE = 5


# ---------------------------------------------------------------------------
# Konto-Name-Mapping
# ---------------------------------------------------------------------------


def _sanitize_account_name(name: str) -> str:
    """
    Bereinigt einen Kontonamen für hledger.

    - Ersetzt ':' durch '-' (hledger nutzt ':' als Hierarchie-Trenner)
    - Normalisiert mehrfache Leerzeichen zu einem (hledger nutzt 2+ Leerzeichen
      als Trennzeichen zwischen Kontoname und Betrag in account-Direktiven)
    - Entfernt führende/nachfolgende Leerzeichen
    """
    sanitized = name.replace(":", "-")
    sanitized = re.sub(r" {2,}", " ", sanitized)
    return sanitized.strip()


def _account_prefix(account_type: int) -> str:
    """Gibt den hledger-Kontopräfix für einen Homebank-Kontotyp zurück."""
    mapping = {
        ACCOUNT_TYPE_NONE: "Aktiva",
        ACCOUNT_TYPE_BANK: "Aktiva:Bank",
        ACCOUNT_TYPE_CASH: "Aktiva:Kasse",
        3: "Aktiva:Vermögen",  # ACCOUNT_TYPE_ASSET
        ACCOUNT_TYPE_CREDITCARD: "Passiva:Kreditkarte",
        ACCOUNT_TYPE_LIABILITY: "Passiva:Darlehen",
        ACCOUNT_TYPE_SAVINGS: "Aktiva:Spareinlagen",
    }
    return mapping.get(account_type, "Aktiva")


def hledger_account_name(account: Account) -> str:
    """Erstellt den vollständigen hledger-Kontonamen für ein Homebank-Konto."""
    prefix = _account_prefix(account.account_type)
    safe_name = _sanitize_account_name(account.name)
    return f"{prefix}:{safe_name}"


def hledger_account_type_tag(account_type: int) -> str:
    """Gibt das hledger-Typ-Tag für einen Kontotyp zurück."""
    mapping = {
        ACCOUNT_TYPE_NONE: "A",
        ACCOUNT_TYPE_BANK: "C",
        ACCOUNT_TYPE_CASH: "C",
        3: "A",  # ACCOUNT_TYPE_ASSET
        ACCOUNT_TYPE_CREDITCARD: "L",
        ACCOUNT_TYPE_LIABILITY: "L",
        ACCOUNT_TYPE_SAVINGS: "A",
    }
    return mapping.get(account_type, "A")


def _category_path(cat_key: int, categories: dict[int, Category]) -> str:
    """Erstellt den vollständigen Kategoriepfad (Eltern:Kind)."""
    cat = categories.get(cat_key)
    if cat is None:
        return "Unbekannt"
    safe_name = _sanitize_account_name(cat.name)
    if cat.parent_key is not None:
        parent = categories.get(cat.parent_key)
        if parent is not None:
            safe_parent = _sanitize_account_name(parent.name)
            return f"{safe_parent}:{safe_name}"
    return safe_name


def _category_account(
    cat_key: int | None,
    amount: Decimal,
    categories: dict[int, Category],
) -> str:
    """Gibt den hledger-Kontonamen für eine Kategorie zurück."""
    if cat_key is None:
        # Vorzeichen bestimmt Einnahme/Ausgabe
        return (
            "Erträge:Nicht kategorisiert"
            if amount >= 0
            else "Aufwand:Nicht kategorisiert"
        )

    cat = categories.get(cat_key)
    if cat is None:
        return (
            "Erträge:Nicht kategorisiert"
            if amount >= 0
            else "Aufwand:Nicht kategorisiert"
        )

    path = _category_path(cat_key, categories)
    prefix = "Erträge" if cat.is_income else "Aufwand"
    return f"{prefix}:{path}"


def _payee_account(payee_name: str, amount: Decimal) -> str:
    """
    Gibt den hledger-Kontonamen für einen Zahlungsempfänger zurück.

    Ausgaben → Passiva:Kreditoren:<Payee>
    Einnahmen → Aktiva:Debitoren:<Payee>
    """
    safe_name = _sanitize_account_name(payee_name)
    if amount < 0:
        return f"Passiva:Kreditoren:{safe_name}"
    return f"Aktiva:Debitoren:{safe_name}"


# ---------------------------------------------------------------------------
# Transaktions-Status → hledger-Markierung
# ---------------------------------------------------------------------------


def _status_mark(status: int) -> str:
    """Gibt die hledger-Statusmarkierung zurück."""
    if status == TXN_STATUS_RECONCILED:
        return "*"
    if status == TXN_STATUS_CLEARED:
        return "!"
    return ""


# ---------------------------------------------------------------------------
# Beschreibungszeile
# ---------------------------------------------------------------------------


def _build_description(txn: Transaction, payees: dict[int, Payee]) -> tuple[str, str]:
    """
    Erstellt Payee- und Notiz-Teil der Transaktionsbeschreibung.

    Returns:
        (payee_str, note_str)
    """
    payee_name = ""
    if txn.payee_key is not None:
        p = payees.get(txn.payee_key)
        if p:
            payee_name = p.name

    parts: list[str] = []
    if txn.wording:
        parts.append(txn.wording)
    if txn.info:
        parts.append(txn.info)
    note = " – ".join(parts) if parts else ""

    return payee_name, note


# ---------------------------------------------------------------------------
# Hauptkonvertierung: einzelne Transaktion
# ---------------------------------------------------------------------------


def _convert_normal_transaction(
    txn: Transaction,
    hb: HomebankFile,
    currency_iso: str,
) -> HledgerTransaction:
    """Konvertiert eine einfache (nicht-split, nicht-intern) Transaktion."""
    account = hb.accounts.get(txn.account_key)
    if account is None:
        raise ConversionError(
            f"Konto {txn.account_key} nicht gefunden für Transaktion am {txn.date}"
        )

    payee_name, note = _build_description(txn, hb.payees)
    status = _status_mark(txn.status)
    acc_name = hledger_account_name(account)
    cat_acc = _category_account(txn.category_key, txn.amount, hb.categories)
    amount = txn.amount

    # Buchungsrichtung:
    # Ausgabe (< 0): Aufwand +abs / Kreditoren -abs → Kreditoren +abs / Aktiva -abs
    # Einnahme (amount > 0): Debitoren +amt / Erträge -amt → Aktiva +amt / Deb. -amt
    postings_list: list[HledgerPosting] = []
    if payee_name:
        payee_acc = _payee_account(payee_name, amount)
        abs_amount = abs(amount)

        if amount < 0:
            # Ausgabe
            postings_list = [
                HledgerPosting(
                    account=cat_acc, amount=abs_amount, currency=currency_iso
                ),
                HledgerPosting(
                    account=payee_acc, amount=-abs_amount, currency=currency_iso
                ),
                HledgerPosting(
                    account=payee_acc, amount=abs_amount, currency=currency_iso
                ),
                HledgerPosting(
                    account=acc_name, amount=-abs_amount, currency=currency_iso
                ),
            ]
        else:
            # Einnahme
            postings_list = [
                HledgerPosting(
                    account=payee_acc, amount=abs_amount, currency=currency_iso
                ),
                HledgerPosting(
                    account=cat_acc, amount=-abs_amount, currency=currency_iso
                ),
                HledgerPosting(
                    account=acc_name, amount=abs_amount, currency=currency_iso
                ),
                HledgerPosting(
                    account=payee_acc, amount=-abs_amount, currency=currency_iso
                ),
            ]
    else:
        # Kein Payee: direkte Buchung ohne Kreditoren/Debitoren-Zwischenkonto
        if amount < 0:
            postings_list = [
                HledgerPosting(
                    account=cat_acc, amount=abs(amount), currency=currency_iso
                ),
                HledgerPosting(account=acc_name, amount=amount, currency=currency_iso),
            ]
        else:
            postings_list = [
                HledgerPosting(account=acc_name, amount=amount, currency=currency_iso),
                HledgerPosting(account=cat_acc, amount=-amount, currency=currency_iso),
            ]

    return HledgerTransaction(
        date=txn.date,
        status=status,
        payee=payee_name,
        note=note,
        postings=tuple(postings_list),
    )


def _convert_internal_transfer(
    txn: Transaction,
    hb: HomebankFile,
    currency_iso: str,
) -> HledgerTransaction:
    """Konvertiert eine interne Überweisung (kxfer-Transaktion)."""
    src_account = hb.accounts.get(txn.account_key)
    if src_account is None:
        raise ConversionError(
            f"Quellkonto {txn.account_key} nicht gefunden "
            f"für interne Überweisung am {txn.date}"
        )
    dst_account = hb.accounts.get(txn.dst_account_key)  # type: ignore[arg-type]
    if dst_account is None:
        raise ConversionError(
            f"Zielkonto {txn.dst_account_key} nicht gefunden "
            f"für interne Überweisung am {txn.date}"
        )

    payee_name, note = _build_description(txn, hb.payees)
    status = _status_mark(txn.status)
    src_name = hledger_account_name(src_account)
    dst_name = hledger_account_name(dst_account)
    amount = txn.amount

    postings = (
        HledgerPosting(account=src_name, amount=amount, currency=currency_iso),
        HledgerPosting(account=dst_name, amount=-amount, currency=currency_iso),
    )

    description = payee_name or "Interne Überweisung"
    return HledgerTransaction(
        date=txn.date,
        status=status,
        payee=description,
        note=note,
        postings=postings,
    )


def _convert_split_transaction(
    txn: Transaction,
    hb: HomebankFile,
    currency_iso: str,
) -> HledgerTransaction:
    """Konvertiert eine Splittransaktion (mehrere Kategorien)."""
    account = hb.accounts.get(txn.account_key)
    if account is None:
        raise ConversionError(
            f"Konto {txn.account_key} nicht gefunden für Splittransaktion am {txn.date}"
        )
    if not txn.splits:
        raise ConversionError(
            f"Splittransaktion am {txn.date} hat keine Split-Einträge"
        )

    payee_name, note = _build_description(txn, hb.payees)
    status = _status_mark(txn.status)
    acc_name = hledger_account_name(account)
    total_amount = txn.amount

    postings_list: list[HledgerPosting] = []

    if payee_name:
        payee_acc = _payee_account(payee_name, total_amount)
        abs_total = abs(total_amount)

        # Schritt 1: Aufwand/Ertrag ↔ Kreditoren/Debitoren für jeden Split
        for split in txn.splits:
            split_abs = abs(split.amount)
            cat_acc = _category_account(split.category_key, split.amount, hb.categories)
            comment = split.memo if split.memo else ""

            if total_amount < 0:
                # Ausgabe
                postings_list.append(
                    HledgerPosting(
                        account=cat_acc,
                        amount=split_abs,
                        currency=currency_iso,
                        comment=comment,
                    )
                )
                postings_list.append(
                    HledgerPosting(
                        account=payee_acc, amount=-split_abs, currency=currency_iso
                    )
                )
            else:
                # Einnahme
                postings_list.append(
                    HledgerPosting(
                        account=payee_acc,
                        amount=split_abs,
                        currency=currency_iso,
                        comment=comment,
                    )
                )
                postings_list.append(
                    HledgerPosting(
                        account=cat_acc, amount=-split_abs, currency=currency_iso
                    )
                )

        # Schritt 2: Kreditoren/Debitoren ↔ Konto
        if total_amount < 0:
            postings_list.append(
                HledgerPosting(
                    account=payee_acc, amount=abs_total, currency=currency_iso
                )
            )
            postings_list.append(
                HledgerPosting(
                    account=acc_name, amount=-abs_total, currency=currency_iso
                )
            )
        else:
            postings_list.append(
                HledgerPosting(
                    account=acc_name, amount=abs_total, currency=currency_iso
                )
            )
            postings_list.append(
                HledgerPosting(
                    account=payee_acc, amount=-abs_total, currency=currency_iso
                )
            )
    else:
        # Kein Payee: direkte Buchung ohne Durchlaufkonto
        for split in txn.splits:
            cat_acc = _category_account(split.category_key, split.amount, hb.categories)
            comment = split.memo if split.memo else ""
            postings_list.append(
                HledgerPosting(
                    account=cat_acc,
                    amount=abs(split.amount),
                    currency=currency_iso,
                    comment=comment,
                )
            )
        postings_list.append(
            HledgerPosting(account=acc_name, amount=total_amount, currency=currency_iso)
        )

    return HledgerTransaction(
        date=txn.date,
        status=status,
        payee=payee_name,
        note=note,
        postings=tuple(postings_list),
    )


# ---------------------------------------------------------------------------
# Eröffnungsbuchung
# ---------------------------------------------------------------------------


def _build_opening_balance(
    year: int,
    balances: dict[int, Decimal],
    hb: HomebankFile,
    base_currency_iso: str,
) -> HledgerTransaction | None:
    """
    Erstellt die Eröffnungsbuchung für ein Jahr.

    Salden sind die berechneten Kontostände zum 31.12. des Vorjahres.
    """
    non_zero = {k: v for k, v in balances.items() if v != Decimal(0)}
    if not non_zero:
        return None

    postings_list: list[HledgerPosting] = []
    for acc_key, balance in sorted(non_zero.items()):
        account = hb.accounts.get(acc_key)
        if account is None:
            continue
        acc_name = hledger_account_name(account)
        # Währung des Kontos
        currency = hb.currencies.get(account.currency_key)
        iso = currency.iso if currency else base_currency_iso
        postings_list.append(
            HledgerPosting(account=acc_name, amount=balance, currency=iso)
        )

    if not postings_list:
        return None

    # Eigenkapital-Gegenkonto (inferiert — kein Betrag angegeben)
    postings_list.append(
        HledgerPosting(
            account="Eigenkapital:Eröffnungsbilanzkonto",
            amount=None,
            currency=base_currency_iso,
        )
    )

    return HledgerTransaction(
        date=date(year, 1, 1),
        status="*",
        payee="Eröffnungsbilanz",
        note=f"{year}",
        postings=tuple(postings_list),
    )


# ---------------------------------------------------------------------------
# Hauptkonvertierung: HomebankFile → liste von HledgerJournalen
# ---------------------------------------------------------------------------


def calculate_balances_up_to(
    hb: HomebankFile,
    up_to_date: date,
) -> dict[int, Decimal]:
    """
    Berechnet die Kontostände aller Konten bis einschließlich up_to_date.

    Berücksichtigt Anfangssalden und alle Transaktionen bis zum Stichtag.
    """
    balances: dict[int, Decimal] = {}

    # Anfangssalden aller Konten
    for acc_key, account in hb.accounts.items():
        balances[acc_key] = account.initial_balance

    # Transaktionen bis Stichtag aufsummieren
    for txn in hb.transactions:
        if txn.date > up_to_date:
            break
        balances[txn.account_key] = (
            balances.get(txn.account_key, Decimal(0)) + txn.amount
        )

    return balances


def convert(hb: HomebankFile) -> list[HledgerJournal]:
    """
    Konvertiert ein HomebankFile in eine Liste von HledgerJournalen (eines pro Jahr).

    Returns:
        Sortierte Liste von HledgerJournal-Objekten (ältestes zuerst)
    """
    base_currency = hb.base_currency()
    base_iso = base_currency.iso

    # Alle Jahre mit Transaktionen ermitteln
    if not hb.transactions:
        logger.warning(
            "Keine Transaktionen gefunden — leere Journalliste wird zurückgegeben"
        )
        return []

    years = sorted({txn.date.year for txn in hb.transactions})
    logger.info("Gefundene Jahre: %s", years)

    # Transaktionen nach Jahr gruppieren
    txns_by_year: dict[int, list[Transaction]] = defaultdict(list)
    for txn in hb.transactions:
        txns_by_year[txn.date.year].append(txn)

    # kxfer-Paare: immer nur die erste Seite (kleinerer account_key) ausgeben
    # Wir sammeln alle gesehenen kxfer-Werte global
    seen_kxfer: set[int] = set()

    journals: list[HledgerJournal] = []

    for year in years:
        journal = _build_journal(
            year=year,
            transactions=txns_by_year[year],
            hb=hb,
            base_iso=base_iso,
            seen_kxfer=seen_kxfer,
        )
        journals.append(journal)

    return journals


def _build_journal(
    year: int,
    transactions: list[Transaction],
    hb: HomebankFile,
    base_iso: str,
    seen_kxfer: set[int],
) -> HledgerJournal:
    """Erstellt ein HledgerJournal für ein einzelnes Jahr."""
    journal = HledgerJournal(year=year, base_currency_iso=base_iso)

    # --- Konto-Deklarationen ---
    _add_account_declarations(journal, hb, base_iso)

    # --- Payee-Deklarationen ---
    for payee in sorted(hb.payees.values(), key=lambda p: p.name):
        safe_name = _sanitize_account_name(payee.name)
        if safe_name:
            journal.payee_declarations.append(safe_name)

    # --- Eröffnungsbuchung ---
    if year > min(txn.date.year for txn in hb.transactions):
        prev_year_end = date(year - 1, 12, 31)
        balances = calculate_balances_up_to(hb, prev_year_end)
        opening = _build_opening_balance(year, balances, hb, base_iso)
        if opening is not None:
            journal.transactions.append(opening)

    # --- Transaktionen konvertieren ---
    for txn in sorted(transactions, key=lambda t: t.date):
        try:
            hledger_txn = _convert_single_transaction(txn, hb, base_iso, seen_kxfer)
        except ConversionError as exc:
            logger.warning("Transaktion übersprungen: %s", exc)
            continue
        if hledger_txn is not None:
            journal.transactions.append(hledger_txn)

    return journal


def _add_account_declarations(
    journal: HledgerJournal,
    hb: HomebankFile,
    base_iso: str,
) -> None:
    """Fügt alle Konto-Deklarationen mit type-Tags zum Journal hinzu."""
    # Feste Hauptkonten
    journal.account_declarations.extend(
        [
            "account Aktiva                                  ; type: A",
            "account Aktiva:Bank                             ; type: C",
            "account Aktiva:Kasse                            ; type: C",
            "account Aktiva:Vermögen                         ; type: A",
            "account Aktiva:Spareinlagen                     ; type: A",
            "account Aktiva:Debitoren                        ; type: A",
            "account Passiva                                 ; type: L",
            "account Passiva:Kreditkarte                     ; type: L",
            "account Passiva:Darlehen                        ; type: L",
            "account Passiva:Kreditoren                      ; type: L",
            "account Eigenkapital                            ; type: E",
            "account Eigenkapital:Eröffnungsbilanzkonto      ; type: E",
            "account Erträge                                 ; type: R",
            "account Aufwand                                 ; type: X",
        ]
    )

    # Individuelle Konten
    for account in sorted(hb.accounts.values(), key=lambda a: a.name):
        acc_name = hledger_account_name(account)
        type_tag = hledger_account_type_tag(account.account_type)
        # Geschlossene Konten: Kommentar als Comma-Tag im selben Semikolon.
        # Zweites ';' würde hledger dazu verleiten, 'C  ; ...' als type-Code zu parsen.
        if account.is_closed:
            entry = f"account {acc_name:<55} ; type: {type_tag}, geschlossen: true"
        else:
            entry = f"account {acc_name:<55} ; type: {type_tag}"
        journal.account_declarations.append(entry)

    # Debitoren-Konten für Payees (Einnahmen)
    for payee in sorted(hb.payees.values(), key=lambda p: p.name):
        safe_name = _sanitize_account_name(payee.name)
        if safe_name:
            journal.account_declarations.append(
                f"account Aktiva:Debitoren:{safe_name:<44} ; type: A"
            )
            journal.account_declarations.append(
                f"account Passiva:Kreditoren:{safe_name:<42} ; type: L"
            )

    # Kategorie-Konten
    for cat in sorted(hb.categories.values(), key=lambda c: c.name):
        path = _category_path(cat.key, hb.categories)
        prefix = "Erträge" if cat.is_income else "Aufwand"
        acc_name = f"{prefix}:{path}"
        type_tag = "R" if cat.is_income else "X"
        journal.account_declarations.append(
            f"account {acc_name:<55} ; type: {type_tag}"
        )


def _convert_single_transaction(
    txn: Transaction,
    hb: HomebankFile,
    base_iso: str,
    seen_kxfer: set[int],
) -> HledgerTransaction | None:
    """
    Konvertiert eine einzelne Transaktion.

    Returns:
        HledgerTransaction oder None (wenn Duplikat einer internen Überweisung)
    """
    # Interne Überweisung: kxfer-Duplikat unterdrücken
    if txn.is_internal_transfer:
        assert txn.kxfer is not None
        if txn.kxfer in seen_kxfer:
            return None
        seen_kxfer.add(txn.kxfer)

        # Währung des Quellkontos
        account = hb.accounts.get(txn.account_key)
        currency = hb.currencies.get(account.currency_key) if account else None
        iso = currency.iso if currency else base_iso

        return _convert_internal_transfer(txn, hb, iso)

    # Währung des Kontos bestimmen
    account = hb.accounts.get(txn.account_key)
    currency = hb.currencies.get(account.currency_key) if account else None
    iso = currency.iso if currency else base_iso

    if txn.is_split:
        return _convert_split_transaction(txn, hb, iso)

    return _convert_normal_transaction(txn, hb, iso)
