"""CLI-Einstiegspunkt für den Homebank-zu-hledger-Konverter."""

import argparse
import logging
import sys
from pathlib import Path

from src.converter import convert
from src.exceptions import ConversionError, HomebankParseError
from src.parser import parse_xhb
from src.writer import write_journals

__version__ = "0.1.0"

logger = logging.getLogger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Erstellt den Argument-Parser."""
    parser = argparse.ArgumentParser(
        prog="homebank-to-hledger",
        description=(
            "Konvertiert Homebank (.xhb) Dateien in hledger Journal-Dateien. "
            "Für jedes Kalenderjahr wird eine eigene .journal-Datei erstellt."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Beispiel:\n"
            "  homebank-to-hledger finanzen.xhb ./journals\n\n"
            "Ausgabestruktur:\n"
            "  ./journals/2023.journal\n"
            "  ./journals/2024.journal\n"
            "  ./journals/main.journal  (include-Direktiven)\n\n"
            "Exit-Codes:\n"
            "  0  Erfolgreich\n"
            "  1  Eingabedatei nicht gefunden oder ungültig\n"
            "  2  Konvertierungsfehler\n"
            "  3  Ausgabeverzeichnis konnte nicht erstellt werden\n"
        ),
    )

    parser.add_argument(
        "eingabe",
        type=Path,
        metavar="eingabe.xhb",
        help="Homebank-Exportdatei (.xhb)",
    )
    parser.add_argument(
        "ausgabe",
        type=Path,
        metavar="ausgabeverzeichnis",
        help="Verzeichnis für die generierten Journal-Dateien",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=False,
        help="Ausführliche Protokollausgabe",
    )

    return parser


def _configure_logging(verbose: bool) -> None:
    """Konfiguriert das Logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        stream=sys.stderr,
    )


def main() -> None:
    """Hauptfunktion des CLI-Tools."""
    parser = _build_parser()
    args = parser.parse_args()

    _configure_logging(args.verbose)

    # Schritt 1: XHB-Datei parsen
    try:
        hb_file = parse_xhb(args.eingabe)
    except FileNotFoundError as exc:
        print(f"Fehler: {exc}", file=sys.stderr)
        sys.exit(1)
    except HomebankParseError as exc:
        print(f"Fehler beim Lesen der XHB-Datei: {exc}", file=sys.stderr)
        sys.exit(1)

    # Schritt 2: Konvertierung
    try:
        journals = convert(hb_file)
    except ConversionError as exc:
        print(f"Konvertierungsfehler: {exc}", file=sys.stderr)
        sys.exit(2)

    if not journals:
        print(
            "Warnung: Keine Transaktionen gefunden — keine Journaldateien erstellt.",
            file=sys.stderr,
        )
        sys.exit(0)

    # Schritt 3: Journale schreiben
    try:
        write_journals(journals, args.ausgabe)
    except OSError as exc:
        print(f"Fehler beim Schreiben der Ausgabedateien: {exc}", file=sys.stderr)
        sys.exit(3)

    total_txns = sum(len(j.transactions) for j in journals)
    print(
        f"{len(journals)} Journal-Datei(en) mit insgesamt {total_txns} "
        f"Buchungen in '{args.ausgabe}' erstellt.",
        file=sys.stderr,
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
