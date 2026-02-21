"""Datenmodelle für die Homebank-zu-hledger-Konvertierung."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

# ---------------------------------------------------------------------------
# Homebank-Quellmodelle (aus XHB-XML)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Currency:
    """Eine in Homebank definierte Währung."""

    key: int
    iso: str  # ISO 4217, z.B. "EUR"
    name: str
    symbol: str
    decimal_char: str  # Dezimaltrennzeichen in Homebank
    group_char: str  # Tausendertrennzeichen in Homebank
    fraction: int  # Nachkommastellen
    rate: Decimal  # Wechselkurs gegenüber Basiswährung (0 = Basiswährung)


@dataclass(frozen=True)
class Group:
    """Eine Kontengruppe in Homebank."""

    key: int
    name: str


# Account-Typ-Enum (aus hb-account.h)
ACCOUNT_TYPE_NONE = 0
ACCOUNT_TYPE_BANK = 1
ACCOUNT_TYPE_CASH = 2
ACCOUNT_TYPE_ASSET = 3
ACCOUNT_TYPE_CREDITCARD = 4
ACCOUNT_TYPE_LIABILITY = 5

# Account-Flag-Bits (aus hb-account.h)
AF_CLOSED = 1 << 1  # Konto geschlossen/archiviert


@dataclass(frozen=True)
class Account:
    """Ein Konto in Homebank."""

    key: int
    name: str
    account_type: int  # Siehe ACCOUNT_TYPE_* Konstanten
    currency_key: int
    initial_balance: Decimal
    flags: int
    number: str = ""
    bank_name: str = ""
    notes: str = ""
    group_key: int | None = None

    @property
    def is_closed(self) -> bool:
        """Gibt True zurück, wenn das Konto geschlossen ist."""
        return bool(self.flags & AF_CLOSED)


@dataclass(frozen=True)
class Payee:
    """Ein Zahlungsempfänger/-auftraggeber in Homebank."""

    key: int
    name: str
    default_category_key: int | None = None
    default_paymode: int | None = None


@dataclass(frozen=True)
class Category:
    """Eine Buchungskategorie in Homebank."""

    key: int
    name: str  # Nur der Blattname, nicht der vollständige Pfad
    flags: int
    parent_key: int | None = None  # None = Hauptkategorie

    # Kategorie-Flag-Bits (aus hb-category.h)
    GF_SUB = 1 << 0  # Subkategorie
    GF_INCOME = 1 << 1  # Einnahme-Kategorie

    @property
    def is_income(self) -> bool:
        """Gibt True zurück, wenn dies eine Einnahme-Kategorie ist."""
        return bool(self.flags & Category.GF_INCOME)

    @property
    def is_subcategory(self) -> bool:
        """Gibt True zurück, wenn dies eine Subkategorie ist."""
        return self.parent_key is not None


@dataclass(frozen=True)
class Split:
    """Eine Teilbuchung innerhalb einer Splittransaktion."""

    amount: Decimal
    category_key: int | None
    memo: str


# Transaktions-Flag-Bits (aus hb-transaction.h)
OF_INCOME = 1 << 1  # Einnahme
OF_SPLIT = 1 << 8  # Splittransaktion

# Transaktions-Status
TXN_STATUS_NONE = 0
TXN_STATUS_CLEARED = 1
TXN_STATUS_RECONCILED = 2
TXN_STATUS_REMIND = 3


@dataclass(frozen=True)
class Transaction:
    """Eine Transaktion (Buchung) in Homebank."""

    date: date
    amount: Decimal
    account_key: int
    flags: int
    status: int  # Siehe TXN_STATUS_* Konstanten
    paymode: int  # Zahlungsart
    payee_key: int | None = None
    category_key: int | None = None
    wording: str = ""  # Buchungstext / Memo
    info: str = ""  # Referenz / Info
    tags: tuple[str, ...] = field(default_factory=tuple)
    kxfer: int | None = None  # Interne Überweisungs-Paarkennzeichen
    dst_account_key: int | None = None  # Zielkonto bei interner Überweisung
    splits: tuple[Split, ...] = field(default_factory=tuple)

    @property
    def is_split(self) -> bool:
        """Gibt True zurück, wenn dies eine Splittransaktion ist."""
        return bool(self.flags & OF_SPLIT)

    @property
    def is_internal_transfer(self) -> bool:
        """Gibt True zurück, wenn dies eine interne Überweisung ist."""
        return self.kxfer is not None and self.dst_account_key is not None


@dataclass
class HomebankFile:
    """Der vollständige Inhalt einer Homebank-XHB-Datei."""

    base_currency_key: int
    currencies: dict[int, Currency] = field(default_factory=dict)
    groups: dict[int, Group] = field(default_factory=dict)
    accounts: dict[int, Account] = field(default_factory=dict)
    payees: dict[int, Payee] = field(default_factory=dict)
    categories: dict[int, Category] = field(default_factory=dict)
    transactions: list[Transaction] = field(default_factory=list)

    def base_currency(self) -> Currency:
        """Gibt die Basiswährung zurück."""
        return self.currencies[self.base_currency_key]


# ---------------------------------------------------------------------------
# hledger-Ausgabemodelle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HledgerPosting:
    """Eine Buchungszeile in einer hledger-Transaktion."""

    account: str
    amount: Decimal | None  # None = Betrag wird von hledger inferiert
    currency: str
    comment: str = ""


@dataclass(frozen=True)
class HledgerTransaction:
    """Eine vollständige hledger-Transaktion."""

    date: date
    status: str  # "" | "!" | "*"
    payee: str
    note: str
    postings: tuple[HledgerPosting, ...]
    comment: str = ""


@dataclass
class HledgerJournal:
    """Ein hledger-Journal für ein Kalenderjahr."""

    year: int
    base_currency_iso: str
    account_declarations: list[str] = field(default_factory=list)
    payee_declarations: list[str] = field(default_factory=list)
    transactions: list[HledgerTransaction] = field(default_factory=list)
