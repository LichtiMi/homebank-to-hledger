"""Tests für den XHB-Parser."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from src.exceptions import HomebankParseError
from src.models import (
    ACCOUNT_TYPE_BANK,
    ACCOUNT_TYPE_CASH,
    TXN_STATUS_CLEARED,
    TXN_STATUS_RECONCILED,
)
from src.parser import parse_xhb

FIXTURES = Path(__file__).parent / "fixtures"


class TestParseXhb:
    """Tests für parse_xhb()."""

    def test_parst_minimale_datei(self) -> None:
        """parse_xhb() liest eine minimale XHB-Datei ohne Fehler."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        assert hb.base_currency_key == 1

    def test_waehrung_wird_geparst(self) -> None:
        """Währungen werden korrekt geparst."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        assert 1 in hb.currencies
        eur = hb.currencies[1]
        assert eur.iso == "EUR"
        assert eur.symbol == "€"
        assert eur.fraction == 2

    def test_konten_werden_geparst(self) -> None:
        """Konten werden korrekt geparst."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        assert len(hb.accounts) == 2
        girokonto = hb.accounts[1]
        assert girokonto.name == "Girokonto"
        assert girokonto.account_type == ACCOUNT_TYPE_BANK
        assert girokonto.initial_balance == Decimal("1000.00")
        kasse = hb.accounts[2]
        assert kasse.account_type == ACCOUNT_TYPE_CASH

    def test_datum_wird_korrekt_dekodiert(self) -> None:
        """GLib Julian Day wird korrekt in Python-Datum umgewandelt."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        # date="738521" soll ein gültiges Datum ergeben
        assert hb.transactions[0].date == date.fromordinal(738521)

    def test_betrag_ist_decimal_kein_float(self) -> None:
        """Beträge werden als Decimal geparst, nicht als float."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        assert isinstance(hb.transactions[0].amount, Decimal)
        assert hb.transactions[0].amount == Decimal("-50.00")

    def test_transaktionen_chronologisch_sortiert(self) -> None:
        """Transaktionen sind nach Datum sortiert."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        dates = [t.date for t in hb.transactions]
        assert dates == sorted(dates)

    def test_status_reconciled(self) -> None:
        """st=2 wird als TXN_STATUS_RECONCILED erkannt."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        # Erste Transaktion hat st=2
        assert hb.transactions[0].status == TXN_STATUS_RECONCILED

    def test_status_cleared(self) -> None:
        """st=1 wird als TXN_STATUS_CLEARED erkannt."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        # Dritte Transaktion (split) hat st=1
        split_txn = next(t for t in hb.transactions if t.is_split)
        assert split_txn.status == TXN_STATUS_CLEARED

    def test_split_transaktion_wird_erkannt(self) -> None:
        """Splittransaktionen mit flags=256 werden korrekt geparst."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        split_txns = [t for t in hb.transactions if t.is_split]
        assert len(split_txns) == 1
        split = split_txns[0]
        assert len(split.splits) == 1
        assert split.splits[0].amount == Decimal("-89.34")
        assert split.splits[0].memo == "Wocheneinkauf"

    def test_interne_ueberweisung_wird_erkannt(self) -> None:
        """Interne Überweisungen (kxfer) werden korrekt geparst."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        internal = [t for t in hb.transactions if t.is_internal_transfer]
        # Beide Seiten der Überweisung
        assert len(internal) == 2
        assert all(t.kxfer == 1 for t in internal)

    def test_payees_werden_geparst(self) -> None:
        """Zahlungsempfänger werden korrekt geparst."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        assert len(hb.payees) == 2
        assert hb.payees[1].name == "REWE"
        assert hb.payees[2].name == "Arbeitgeber GmbH"

    def test_kategorien_werden_geparst(self) -> None:
        """Kategorien werden korrekt geparst."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        assert len(hb.categories) == 2
        assert not hb.categories[1].is_income  # Lebensmittel = Aufwand
        assert hb.categories[2].is_income  # Gehalt = Ertrag

    def test_datei_nicht_gefunden(self) -> None:
        """FileNotFoundError wird geworfen, wenn Datei nicht existiert."""
        with pytest.raises(FileNotFoundError):
            parse_xhb(Path("/nicht/vorhanden.xhb"))

    def test_ungueltige_xml_datei(self, tmp_path: Path) -> None:
        """HomebankParseError wird bei ungültigem XML geworfen."""
        bad_file = tmp_path / "bad.xhb"
        bad_file.write_text("das ist kein XML", encoding="utf-8")
        with pytest.raises(HomebankParseError, match="XML-Parsing-Fehler"):
            parse_xhb(bad_file)

    def test_falsches_root_element(self, tmp_path: Path) -> None:
        """HomebankParseError wird bei falschem Root-Element geworfen."""
        bad_file = tmp_path / "bad.xhb"
        bad_file.write_text('<?xml version="1.0"?><root/>', encoding="utf-8")
        with pytest.raises(HomebankParseError, match="Root-Element"):
            parse_xhb(bad_file)

    def test_basiswaehrung_aus_properties(self) -> None:
        """Die Basiswährung wird aus dem <properties>-Element gelesen."""
        hb = parse_xhb(FIXTURES / "minimal.xhb")
        assert hb.base_currency_key == 1
        base = hb.base_currency()
        assert base.iso == "EUR"
