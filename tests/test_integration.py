"""
End-to-End-Integrationstest: XHB parsen → konvertieren → schreiben → hledger check.

Dieser Test wird nur ausgeführt, wenn `hledger` im PATH verfügbar ist.
Er validiert, dass die gesamte Konvertierungspipeline hledger-kompatible
Journal-Dateien erzeugt, die `hledger check` ohne Fehler passieren.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

from src.converter import convert
from src.parser import parse_xhb
from src.writer import write_journals

FIXTURES = Path(__file__).parent / "fixtures"

# Test überspringen wenn hledger nicht installiert ist
hledger_available = shutil.which("hledger") is not None
skip_without_hledger = pytest.mark.skipif(
    not hledger_available,
    reason="hledger ist nicht im PATH installiert",
)


@skip_without_hledger
class TestHledgerIntegration:
    """End-to-End-Tests gegen echtes hledger."""

    def test_generierte_journale_bestehen_hledger_check(self, tmp_path: Path) -> None:
        """
        T049: Die vollständige Konvertierungspipeline erzeugt Journale, die
        `hledger check` ohne Fehler passieren.

        Testet:
        - Konto-Deklarationen (account ... ; type: X) sind syntaktisch korrekt
        - Buchungen sind korrekt bilanziert (Summe = 0)
        - Keine fehlerhaften Payee/Konto-Namen (Doppelleerzeichen etc.)
        """
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        write_journals(journals, tmp_path)

        main_journal = tmp_path / "main.journal"
        assert main_journal.exists(), "main.journal wurde nicht erstellt"

        result = subprocess.run(
            ["hledger", "-f", str(main_journal), "check"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"hledger check schlug fehl:\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )

    def test_hledger_accounts_listet_alle_konten(self, tmp_path: Path) -> None:
        """
        `hledger accounts` gibt alle deklarierten Konten zurück.
        Stellt sicher, dass account-Direktiven korrekt geparst werden.
        """
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        write_journals(journals, tmp_path)

        result = subprocess.run(
            ["hledger", "-f", str(tmp_path / "main.journal"), "accounts"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"hledger accounts fehlgeschlagen: {result.stderr}"
        )
        accounts = result.stdout.strip().splitlines()
        assert len(accounts) > 0, "Keine Konten in der Ausgabe"

        # Kern-Konten müssen vorhanden sein
        account_set = set(accounts)
        assert any("Aktiva" in a for a in account_set)
        assert any("Aufwand" in a for a in account_set)
        assert any("Erträge" in a for a in account_set)

    def test_hledger_payees_listet_alle_zahlungsempfaenger(
        self, tmp_path: Path
    ) -> None:
        """
        `hledger payees` gibt alle deklarierten Zahlungsempfänger zurück.
        """
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        write_journals(journals, tmp_path)

        result = subprocess.run(
            ["hledger", "-f", str(tmp_path / "main.journal"), "payees"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"hledger payees fehlgeschlagen: {result.stderr}"
        payees = result.stdout.strip().splitlines()
        assert "REWE" in payees
        assert "Arbeitgeber GmbH" in payees

    def test_hledger_balance_ist_ausgeglichen(self, tmp_path: Path) -> None:
        """
        `hledger balance` darf keinen Gesamtfehler anzeigen.
        Alle Buchungen müssen auf 0 aufgehen.
        """
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        write_journals(journals, tmp_path)

        result = subprocess.run(
            [
                "hledger",
                "-f",
                str(tmp_path / "main.journal"),
                "balance",
                "--no-total",
            ],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, (
            f"hledger balance fehlgeschlagen:\n{result.stderr}"
        )
