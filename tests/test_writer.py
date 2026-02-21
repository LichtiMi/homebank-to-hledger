"""Tests für den Journal-Writer."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from src.models import HledgerJournal, HledgerPosting, HledgerTransaction
from src.writer import _add_thousands_separator, _format_amount, write_journals


class TestFormatAmount:
    """Tests für _format_amount()."""

    def test_positiver_betrag(self) -> None:
        """Positive Beträge werden korrekt formatiert."""
        assert _format_amount(Decimal("1234.56"), "EUR") == "1.234,56 EUR"

    def test_negativer_betrag(self) -> None:
        """Negative Beträge erhalten ein Minuszeichen."""
        assert _format_amount(Decimal("-89.34"), "EUR") == "-89,34 EUR"

    def test_betrag_ohne_tausender(self) -> None:
        """Beträge unter 1000 erhalten keinen Tausenderpunkt."""
        assert _format_amount(Decimal("50.00"), "EUR") == "50,00 EUR"

    def test_grosser_betrag_mit_tausender(self) -> None:
        """Beträge über 1000 erhalten Tausenderpunkte."""
        assert _format_amount(Decimal("1000000.00"), "EUR") == "1.000.000,00 EUR"

    def test_fremdwaehrung(self) -> None:
        """Fremdwährungen werden mit ihrem ISO-Code ausgegeben."""
        assert _format_amount(Decimal("100.00"), "USD") == "100,00 USD"

    def test_rundung_auf_zwei_stellen(self) -> None:
        """Beträge werden auf 2 Nachkommastellen gerundet."""
        assert _format_amount(Decimal("1.999"), "EUR") == "2,00 EUR"


class TestAddThousandsSeparator:
    """Tests für _add_thousands_separator()."""

    def test_keine_trenner_unter_1000(self) -> None:
        assert _add_thousands_separator("999") == "999"

    def test_ein_trenner_bei_1000(self) -> None:
        assert _add_thousands_separator("1000") == "1.000"

    def test_mehrere_trenner(self) -> None:
        assert _add_thousands_separator("1000000") == "1.000.000"


class TestWriteJournals:
    """Tests für write_journals()."""

    def _make_journal(self, year: int) -> HledgerJournal:
        """Erstellt ein minimales Testjournal."""
        journal = HledgerJournal(year=year, base_currency_iso="EUR")
        journal.account_declarations.append(
            "account Aktiva:Bank:Girokonto             ; type: C"
        )
        journal.payee_declarations.append("REWE")
        journal.transactions.append(
            HledgerTransaction(
                date=date(year, 3, 15),
                status="*",
                payee="REWE",
                note="Einkauf",
                postings=(
                    HledgerPosting(
                        account="Aufwand:Lebensmittel",
                        amount=Decimal("50.00"),
                        currency="EUR",
                    ),
                    HledgerPosting(
                        account="Passiva:Kreditoren:REWE",
                        amount=Decimal("-50.00"),
                        currency="EUR",
                    ),
                    HledgerPosting(
                        account="Passiva:Kreditoren:REWE",
                        amount=Decimal("50.00"),
                        currency="EUR",
                    ),
                    HledgerPosting(
                        account="Aktiva:Bank:Girokonto",
                        amount=Decimal("-50.00"),
                        currency="EUR",
                    ),
                ),
            )
        )
        return journal

    def test_erstellt_journal_dateien(self, tmp_path: Path) -> None:
        """Für jedes Journal wird eine Datei erstellt."""
        journals = [self._make_journal(2024), self._make_journal(2023)]
        write_journals(journals, tmp_path)
        assert (tmp_path / "2023.journal").exists()
        assert (tmp_path / "2024.journal").exists()

    def test_erstellt_main_journal(self, tmp_path: Path) -> None:
        """Die main.journal-Datei wird erstellt."""
        journals = [self._make_journal(2024)]
        write_journals(journals, tmp_path)
        assert (tmp_path / "main.journal").exists()

    def test_main_journal_enthaelt_includes(self, tmp_path: Path) -> None:
        """Die main.journal enthält include-Direktiven."""
        journals = [self._make_journal(2023), self._make_journal(2024)]
        write_journals(journals, tmp_path)
        content = (tmp_path / "main.journal").read_text(encoding="utf-8")
        assert "include 2023.journal" in content
        assert "include 2024.journal" in content

    def test_journal_enthaelt_decimal_mark(self, tmp_path: Path) -> None:
        """Jede Journal-Datei beginnt mit 'decimal-mark ,'."""
        journals = [self._make_journal(2024)]
        write_journals(journals, tmp_path)
        content = (tmp_path / "2024.journal").read_text(encoding="utf-8")
        assert "decimal-mark ," in content

    def test_journal_enthaelt_commodity(self, tmp_path: Path) -> None:
        """Jede Journal-Datei enthält eine commodity-Deklaration."""
        journals = [self._make_journal(2024)]
        write_journals(journals, tmp_path)
        content = (tmp_path / "2024.journal").read_text(encoding="utf-8")
        assert "commodity" in content
        assert "EUR" in content

    def test_journal_enthaelt_payee_deklaration(self, tmp_path: Path) -> None:
        """Payee-Deklarationen erscheinen im Journal."""
        journals = [self._make_journal(2024)]
        write_journals(journals, tmp_path)
        content = (tmp_path / "2024.journal").read_text(encoding="utf-8")
        assert "payee REWE" in content

    def test_betrag_deutsch_formatiert(self, tmp_path: Path) -> None:
        """Beträge werden im deutschen Format ausgegeben."""
        journals = [self._make_journal(2024)]
        write_journals(journals, tmp_path)
        content = (tmp_path / "2024.journal").read_text(encoding="utf-8")
        assert "50,00 EUR" in content

    def test_erstellt_ausgabeverzeichnis(self, tmp_path: Path) -> None:
        """Das Ausgabeverzeichnis wird erstellt, falls es nicht existiert."""
        output_dir = tmp_path / "neu" / "verzeichnis"
        journals = [self._make_journal(2024)]
        write_journals(journals, output_dir)
        assert output_dir.exists()

    def test_transaktion_mit_status_stern(self, tmp_path: Path) -> None:
        """Abgestimmte Transaktionen erhalten '*' in der Ausgabe."""
        journals = [self._make_journal(2024)]
        write_journals(journals, tmp_path)
        content = (tmp_path / "2024.journal").read_text(encoding="utf-8")
        assert "2024-03-15 * REWE" in content

    def test_payee_pipe_note_format(self, tmp_path: Path) -> None:
        """Transaktionen mit Payee und Notiz werden als 'Payee | Notiz' ausgegeben."""
        journals = [self._make_journal(2024)]
        write_journals(journals, tmp_path)
        content = (tmp_path / "2024.journal").read_text(encoding="utf-8")
        assert "REWE | Einkauf" in content
