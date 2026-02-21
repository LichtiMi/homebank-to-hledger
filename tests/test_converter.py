"""Tests für die Konvertierungslogik."""

from datetime import date
from decimal import Decimal
from pathlib import Path

from src.converter import (
    calculate_balances_up_to,
    convert,
    hledger_account_name,
)
from src.models import (
    ACCOUNT_TYPE_BANK,
    ACCOUNT_TYPE_CASH,
    ACCOUNT_TYPE_CREDITCARD,
    Account,
    HomebankFile,
)
from src.parser import parse_xhb

FIXTURES = Path(__file__).parent / "fixtures"


class TestHledgerAccountName:
    """Tests für hledger_account_name()."""

    def test_bank_konto(self) -> None:
        """Bank-Konten erhalten das Präfix 'Aktiva:Bank'."""
        acc = Account(
            key=1,
            name="Girokonto",
            account_type=ACCOUNT_TYPE_BANK,
            currency_key=1,
            initial_balance=Decimal("0"),
            flags=0,
        )
        assert hledger_account_name(acc) == "Aktiva:Bank:Girokonto"

    def test_kasse_konto(self) -> None:
        """Bargeld-Konten erhalten das Präfix 'Aktiva:Kasse'."""
        acc = Account(
            key=2,
            name="Bargeld",
            account_type=ACCOUNT_TYPE_CASH,
            currency_key=1,
            initial_balance=Decimal("0"),
            flags=0,
        )
        assert hledger_account_name(acc) == "Aktiva:Kasse:Bargeld"

    def test_kreditkarte_konto(self) -> None:
        """Kreditkartenkonten erhalten das Präfix 'Passiva:Kreditkarte'."""
        acc = Account(
            key=3,
            name="Visa",
            account_type=ACCOUNT_TYPE_CREDITCARD,
            currency_key=1,
            initial_balance=Decimal("0"),
            flags=0,
        )
        assert hledger_account_name(acc) == "Passiva:Kreditkarte:Visa"

    def test_doppelpunkt_in_name_wird_ersetzt(self) -> None:
        """Doppelpunkte im Kontonamen werden durch '-' ersetzt."""
        acc = Account(
            key=4,
            name="Konto:Spar",
            account_type=ACCOUNT_TYPE_BANK,
            currency_key=1,
            initial_balance=Decimal("0"),
            flags=0,
        )
        assert hledger_account_name(acc) == "Aktiva:Bank:Konto-Spar"


class TestConvert:
    """Integrationstests für convert()."""

    def test_konvertiert_minimale_datei(self) -> None:
        """convert() erzeugt Journale für eine minimale XHB-Datei."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        assert len(journals) >= 1

    def test_ein_journal_pro_jahr(self) -> None:
        """Für jedes Jahr mit Transaktionen wird ein Journal erstellt."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        years = {j.year for j in journals}
        expected_years = {t.date.year for t in hb.transactions}
        assert years == expected_years

    def test_kein_doppeltes_kxfer(self) -> None:
        """Interne Überweisungen werden nur einmal gebucht (kein kxfer-Duplikat)."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        all_txns = [t for j in journals for t in j.transactions]
        # Zwei Seiten der internen Überweisung (kxfer=1) → nur eine Transaktion
        # Eröffnungsbuchung = 'Eröffnungsbilanz', Überweisung = 'Interne Überweisung'
        transfer_txns = [
            t
            for t in all_txns
            if any("Aktiva:Kasse" in p.account for p in t.postings)
            and any("Aktiva:Bank" in p.account for p in t.postings)
        ]
        assert len(transfer_txns) == 1

    def test_ausgabe_erzeugt_kreditoren_konto(self) -> None:
        """Ausgaben mit Payee erzeugen ein Passiva:Kreditoren-Konto."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        all_postings = [p for j in journals for t in j.transactions for p in t.postings]
        kreditoren = [p for p in all_postings if "Passiva:Kreditoren:REWE" in p.account]
        assert len(kreditoren) > 0

    def test_einnahme_erzeugt_debitoren_konto(self) -> None:
        """Einnahmen mit Payee erzeugen ein Aktiva:Debitoren-Konto."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        all_postings = [p for j in journals for t in j.transactions for p in t.postings]
        debitoren = [
            p for p in all_postings if "Aktiva:Debitoren:Arbeitgeber GmbH" in p.account
        ]
        assert len(debitoren) > 0

    def test_split_transaktion_mehrere_postings(self) -> None:
        """Splittransaktionen erzeugen mehrere Posting-Zeilen."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        all_txns = [t for j in journals for t in j.transactions]
        # Splittransaktion hat mehr als 2 Postings
        split_txns = [t for t in all_txns if len(t.postings) > 2]
        assert len(split_txns) >= 1

    def test_eroeffnungsbuchung_ab_zweitem_jahr(self) -> None:
        """Ab dem zweiten Jahr gibt es eine Eröffnungsbuchung."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        if len(journals) > 1:
            second_year = sorted(journals, key=lambda j: j.year)[1]
            opening = [
                t for t in second_year.transactions if t.payee == "Eröffnungsbilanz"
            ]
            assert len(opening) == 1

    def test_journal_hat_konto_deklarationen(self) -> None:
        """Jedes Journal enthält Konto-Deklarationen."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        for j in journals:
            assert len(j.account_declarations) > 0

    def test_journal_hat_payee_deklarationen(self) -> None:
        """Jedes Journal enthält Payee-Deklarationen."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        for j in journals:
            assert len(j.payee_declarations) > 0

    def test_leere_transaktionsliste(self) -> None:
        """convert() gibt leere Liste zurück, wenn keine Transaktionen vorhanden."""
        hb = HomebankFile(base_currency_key=1)
        hb.currencies[1] = parse_xhb(FIXTURES / "minimal.xhb").currencies[1]
        journals = convert(hb)
        assert journals == []

    def test_transaktion_status_reconciled(self) -> None:
        """Abgestimmte Transaktionen erhalten den Status '*'."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        all_txns = [t for j in journals for t in j.transactions]
        reconciled = [
            t for t in all_txns if t.status == "*" and t.payee != "Eröffnungsbilanz"
        ]
        assert len(reconciled) > 0

    def test_transaktion_status_cleared(self) -> None:
        """Geprüfte Transaktionen erhalten den Status '!'."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        journals = convert(hb)
        all_txns = [t for j in journals for t in j.transactions]
        cleared = [t for t in all_txns if t.status == "!"]
        assert len(cleared) > 0


class TestCalculateBalances:
    """Tests für calculate_balances_up_to()."""

    def test_nur_anfangssaldo_ohne_transaktionen(self) -> None:
        """Ohne Transaktionen entspricht der Saldo dem Anfangssaldo."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        # Datum vor allen Transaktionen
        early_date = date(2000, 1, 1)
        balances = calculate_balances_up_to(hb, early_date)
        assert balances[1] == Decimal("1000.00")  # Girokonto
        assert balances[2] == Decimal("100.00")  # Kasse

    def test_saldo_nach_allen_transaktionen(self) -> None:
        """Nach allen Transaktionen ist der Saldo korrekt berechnet."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        future_date = date(2099, 12, 31)
        balances = calculate_balances_up_to(hb, future_date)
        # Girokonto: 1000 - 50 + 2500 - 89.34 - 200 = 3160.66
        assert balances[1] == Decimal("1000.00") + Decimal("-50.00") + Decimal(
            "2500.00"
        ) + Decimal("-89.34") + Decimal("-200.00")
        # Kasse: 100 + 200 (interne Überweisung)
        assert balances[2] == Decimal("100.00") + Decimal("200.00")
