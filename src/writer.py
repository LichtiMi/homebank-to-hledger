"""Ausgabe der hledger-Journaldateien."""

import logging
from decimal import Decimal
from pathlib import Path

from src.models import HledgerJournal, HledgerPosting, HledgerTransaction

logger = logging.getLogger(__name__)

_INDENT = "    "  # 4 Leerzeichen Einrückung für Postings


def _format_amount(amount: Decimal, currency: str) -> str:
    """
    Formatiert einen Betrag im deutschen Format (Komma als Dezimaltrennzeichen).

    Beispiele:
        Decimal("1234.56") → "1.234,56 EUR"
        Decimal("-89.34") → "-89,34 EUR"
    """
    # Auf 2 Nachkommastellen runden
    rounded = round(amount, 2)
    # Vorzeichenbehandlung
    negative = rounded < 0
    abs_val = abs(rounded)

    # In String mit 2 Nachkommastellen umwandeln (Python nutzt intern Punkt)
    raw = f"{abs_val:.2f}"
    integer_part, frac_part = raw.split(".")

    # Tausenderpunkte einfügen
    int_with_sep = _add_thousands_separator(integer_part)

    # Deutsch: Komma als Dezimaltrennzeichen
    formatted = f"{int_with_sep},{frac_part}"
    if negative:
        formatted = f"-{formatted}"

    return f"{formatted} {currency}"


def _add_thousands_separator(integer_str: str) -> str:
    """Fügt Tausenderpunkte ein: '1234567' → '1.234.567'."""
    result: list[str] = []
    for i, digit in enumerate(reversed(integer_str)):
        if i > 0 and i % 3 == 0:
            result.append(".")
        result.append(digit)
    return "".join(reversed(result))


def _format_posting(posting: HledgerPosting) -> str:
    """Formatiert eine Buchungszeile."""
    if posting.amount is None:
        # Betrag wird von hledger inferiert
        line = f"{_INDENT}{posting.account}"
    else:
        amount_str = _format_amount(posting.amount, posting.currency)
        # Ausrichtung: Kontoname (40 Zeichen) + Abstand + Betrag
        line = f"{_INDENT}{posting.account:<48}  {amount_str}"

    if posting.comment:
        line = f"{line}  ; {posting.comment}"

    return line


def _format_transaction(txn: HledgerTransaction) -> list[str]:
    """Formatiert eine vollständige Transaktion als Liste von Zeilen."""
    lines: list[str] = []

    # Beschreibungszeile: DATUM [STATUS] PAYEE | NOTIZ
    date_str = txn.date.strftime("%Y-%m-%d")
    status_part = f" {txn.status}" if txn.status else ""

    if txn.payee and txn.note:
        desc = f"{txn.payee} | {txn.note}"
    elif txn.payee:
        desc = txn.payee
    elif txn.note:
        desc = txn.note
    else:
        desc = "(keine Beschreibung)"

    header = f"{date_str}{status_part} {desc}"
    if txn.comment:
        header = f"{header}  ; {txn.comment}"
    lines.append(header)

    # Buchungszeilen
    for posting in txn.postings:
        lines.append(_format_posting(posting))

    return lines


def _format_journal(journal: HledgerJournal) -> str:
    """Formatiert ein HledgerJournal als vollständigen Journal-Text."""
    sections: list[str] = []

    # --- Datei-Header ---
    sections.append(
        f"; ============================================================\n"
        f"; hledger Journal {journal.year}\n"
        f"; Generiert von homebank-to-hledger\n"
        f"; ============================================================\n"
    )

    # --- Währungsdirektiven ---
    sections.append("decimal-mark ,\n")
    sections.append(f"commodity 1.000,00 {journal.base_currency_iso}\n")

    # --- Konto-Deklarationen ---
    if journal.account_declarations:
        sections.append("; --- Konto-Deklarationen ---")
        for decl in journal.account_declarations:
            sections.append(decl)
        sections.append("")

    # --- Payee-Deklarationen ---
    if journal.payee_declarations:
        sections.append("; --- Zahlungsempfänger ---")
        for payee in journal.payee_declarations:
            sections.append(f"payee {payee}")
        sections.append("")

    # --- Transaktionen ---
    if journal.transactions:
        sections.append("; --- Buchungen ---")
        for txn in journal.transactions:
            txn_lines = _format_transaction(txn)
            sections.append("\n".join(txn_lines))
            sections.append("")

    return "\n".join(sections)


def _format_main_journal(years: list[int]) -> str:
    """Erstellt die main.journal-Datei mit include-Direktiven."""
    lines = [
        "; ============================================================",
        "; hledger Hauptjournal",
        "; Alle Jahresjournale werden über include eingebunden.",
        "; ============================================================",
        "",
    ]
    for year in sorted(years):
        lines.append(f"include {year}.journal")
    lines.append("")
    return "\n".join(lines)


def write_journals(journals: list[HledgerJournal], output_dir: Path) -> None:
    """
    Schreibt alle Journaldateien in das Ausgabeverzeichnis.

    Erstellt außerdem eine main.journal mit include-Direktiven.

    Args:
        journals:    Liste der zu schreibenden Journale
        output_dir:  Zielverzeichnis (wird erstellt, wenn nicht vorhanden)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    years: list[int] = []
    for journal in sorted(journals, key=lambda j: j.year):
        filename = f"{journal.year}.journal"
        filepath = output_dir / filename
        content = _format_journal(journal)
        filepath.write_text(content, encoding="utf-8")
        logger.info(
            "Schreibe %s (%d Transaktionen)", filepath, len(journal.transactions)
        )
        years.append(journal.year)

    # main.journal
    main_path = output_dir / "main.journal"
    main_path.write_text(_format_main_journal(years), encoding="utf-8")
    logger.info("Schreibe %s", main_path)
