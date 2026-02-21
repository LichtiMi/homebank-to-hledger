"""Parser für Homebank XHB-Dateien (XML-Format)."""

import logging
import xml.etree.ElementTree as ET
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from src.exceptions import HomebankParseError
from src.models import (
    ACCOUNT_TYPE_NONE,
    OF_SPLIT,
    Account,
    Category,
    Currency,
    Group,
    HomebankFile,
    Payee,
    Split,
    Transaction,
)

logger = logging.getLogger(__name__)


def _require_attr(element: ET.Element, attr: str) -> str:
    """Gibt ein Pflichtattribut zurück oder wirft HomebankParseError."""
    value = element.get(attr)
    if value is None:
        raise HomebankParseError(
            f"Pflichtattribut '{attr}' fehlt in Element <{element.tag}>"
        )
    return value


def _int_attr(element: ET.Element, attr: str, default: int = 0) -> int:
    """Liest ein Integer-Attribut mit optionalem Standardwert."""
    raw = element.get(attr)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise HomebankParseError(
            f"Ungültiger Integer-Wert '{raw}' für Attribut '{attr}' "
            f"in Element <{element.tag}>"
        ) from exc


def _decimal_attr(
    element: ET.Element, attr: str, default: Decimal = Decimal(0)
) -> Decimal:
    """Liest einen Dezimalbetrag direkt aus dem XML-String (kein float-Umweg)."""
    raw = element.get(attr)
    if raw is None:
        return default
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise HomebankParseError(
            f"Ungültiger Dezimalwert '{raw}' für Attribut '{attr}' "
            f"in Element <{element.tag}>"
        ) from exc


def _parse_hb_date(value: str, element: ET.Element) -> date:
    """
    Konvertiert einen Homebank-Datumswert (GLib Julian Day = Python-Ordinalzahl).

    GLib Julian Day Number entspricht exakt Python datetime.date.fromordinal().
    Epoch: 1. Januar 1 AD = 1 (identisch mit Python).
    """
    try:
        ordinal = int(value)
        return date.fromordinal(ordinal)
    except (ValueError, OverflowError) as exc:
        raise HomebankParseError(
            f"Ungültiger Datumswert '{value}' in Element <{element.tag}>"
        ) from exc


def _parse_splits(
    scat: str, samt: str, smem: str, element: ET.Element
) -> tuple[Split, ...]:
    """Parst die Split-Attribute einer Transaktion."""
    cats = scat.split("||")
    amts = samt.split("||")
    mems = smem.split("||") if smem else [""] * len(cats)

    if len(cats) != len(amts):
        raise HomebankParseError(
            f"Inkonsistente Split-Listen in <{element.tag}>: "
            f"scat hat {len(cats)} Einträge, samt hat {len(amts)}"
        )

    splits: list[Split] = []
    for cat_str, amt_str, mem in zip(cats, amts, mems, strict=False):
        cat_key: int | None = int(cat_str) if cat_str.strip() else None
        try:
            amount = Decimal(amt_str)
        except InvalidOperation as exc:
            raise HomebankParseError(
                f"Ungültiger Split-Betrag '{amt_str}' in <{element.tag}>"
            ) from exc
        splits.append(Split(amount=amount, category_key=cat_key, memo=mem))

    return tuple(splits)


def _parse_currency(element: ET.Element) -> Currency:
    """Parst ein <cur>-Element."""
    key = _int_attr(element, "key")
    if key == 0:
        raise HomebankParseError("Währung mit key=0 ist ungültig")
    return Currency(
        key=key,
        iso=element.get("iso", ""),
        name=element.get("name", ""),
        symbol=element.get("symb", ""),
        decimal_char=element.get("dchar", "."),
        group_char=element.get("gchar", ","),
        fraction=_int_attr(element, "frac", 2),
        rate=_decimal_attr(element, "rate"),
    )


def _parse_group(element: ET.Element) -> Group:
    """Parst ein <grp>-Element."""
    return Group(
        key=_int_attr(element, "key"),
        name=element.get("name", ""),
    )


def _parse_account(element: ET.Element) -> Account:
    """Parst ein <account>-Element."""
    key = _int_attr(element, "key")
    if key == 0:
        raise HomebankParseError("Konto mit key=0 ist ungültig")
    type_raw = element.get("type")
    account_type = int(type_raw) if type_raw is not None else ACCOUNT_TYPE_NONE
    grp_raw = element.get("grp")
    return Account(
        key=key,
        name=element.get("name", ""),
        account_type=account_type,
        currency_key=_int_attr(element, "curr", 0),
        initial_balance=_decimal_attr(element, "initial"),
        flags=_int_attr(element, "flags", 0),
        number=element.get("number", ""),
        bank_name=element.get("bankname", ""),
        notes=element.get("notes", ""),
        group_key=int(grp_raw) if grp_raw is not None else None,
    )


def _parse_payee(element: ET.Element) -> Payee:
    """Parst ein <pay>-Element."""
    cat_raw = element.get("category")
    mode_raw = element.get("paymode")
    return Payee(
        key=_int_attr(element, "key"),
        name=element.get("name", ""),
        default_category_key=int(cat_raw) if cat_raw is not None else None,
        default_paymode=int(mode_raw) if mode_raw is not None else None,
    )


def _parse_category(element: ET.Element) -> Category:
    """Parst ein <cat>-Element."""
    parent_raw = element.get("parent")
    return Category(
        key=_int_attr(element, "key"),
        name=element.get("name", ""),
        flags=_int_attr(element, "flags", 0),
        parent_key=int(parent_raw) if parent_raw is not None else None,
    )


def _parse_transaction(element: ET.Element) -> Transaction:
    """Parst ein <ope>-Element (Transaktion)."""
    date_raw = _require_attr(element, "date")
    txn_date = _parse_hb_date(date_raw, element)

    amount = _decimal_attr(element, "amount")
    account_key = _int_attr(element, "account")
    flags = _int_attr(element, "flags", 0)
    status = _int_attr(element, "st", 0)
    paymode = _int_attr(element, "paymode", 0)

    payee_raw = element.get("payee")
    cat_raw = element.get("category")
    kxfer_raw = element.get("kxfer")
    dst_raw = element.get("dst_account")

    tags_raw = element.get("tags", "")
    tags = tuple(t for t in tags_raw.split(" ") if t) if tags_raw else ()

    # Splits parsen (nur wenn OF_SPLIT-Flag gesetzt)
    splits: tuple[Split, ...] = ()
    if flags & OF_SPLIT:
        scat = element.get("scat", "")
        samt = element.get("samt", "")
        smem = element.get("smem", "")
        if scat and samt:
            splits = _parse_splits(scat, samt, smem, element)

    return Transaction(
        date=txn_date,
        amount=amount,
        account_key=account_key,
        flags=flags,
        status=status,
        paymode=paymode,
        payee_key=int(payee_raw) if payee_raw is not None else None,
        category_key=int(cat_raw) if cat_raw is not None else None,
        wording=element.get("wording", ""),
        info=element.get("info", ""),
        tags=tags,
        kxfer=int(kxfer_raw) if kxfer_raw is not None else None,
        dst_account_key=int(dst_raw) if dst_raw is not None else None,
        splits=splits,
    )


def parse_xhb(path: Path) -> HomebankFile:
    """
    Liest und parst eine Homebank XHB-Datei.

    Args:
        path: Pfad zur .xhb-Datei

    Returns:
        HomebankFile mit allen geparsten Daten

    Raises:
        HomebankParseError: Bei ungültigem XML oder fehlenden Pflichtfeldern
        FileNotFoundError: Wenn die Datei nicht existiert
    """
    if not path.exists():
        raise FileNotFoundError(f"XHB-Datei nicht gefunden: {path}")
    if not path.is_file():
        raise HomebankParseError(f"Pfad ist keine Datei: {path}")

    logger.info("Lese XHB-Datei: %s", path)

    try:
        tree = ET.parse(path)  # noqa: S314 - lokale Datei, kein Netzwerk
    except ET.ParseError as exc:
        raise HomebankParseError(f"XML-Parsing-Fehler in '{path}': {exc}") from exc

    root = tree.getroot()
    if root.tag != "homebank":
        raise HomebankParseError(
            f"Unerwartetes Root-Element: <{root.tag}> (erwartet: <homebank>)"
        )

    # Basiswährung aus <properties>
    props = root.find("properties")
    if props is None:
        raise HomebankParseError("Pflicht-Element <properties> fehlt in der XHB-Datei")
    base_currency_key = _int_attr(props, "curr", 1)

    hb_file = HomebankFile(base_currency_key=base_currency_key)

    for element in root:
        tag = element.tag
        try:
            if tag == "cur":
                cur = _parse_currency(element)
                hb_file.currencies[cur.key] = cur
            elif tag == "grp":
                grp = _parse_group(element)
                hb_file.groups[grp.key] = grp
            elif tag == "account":
                acc = _parse_account(element)
                hb_file.accounts[acc.key] = acc
            elif tag == "pay":
                pay = _parse_payee(element)
                hb_file.payees[pay.key] = pay
            elif tag == "cat":
                cat = _parse_category(element)
                hb_file.categories[cat.key] = cat
            elif tag == "ope":
                txn = _parse_transaction(element)
                hb_file.transactions.append(txn)
        except HomebankParseError:
            raise
        except Exception as exc:
            raise HomebankParseError(
                f"Unerwarteter Fehler beim Parsen von <{tag}>: {exc}"
            ) from exc

    # Transaktionen chronologisch sortieren
    hb_file.transactions.sort(key=lambda t: t.date)

    logger.info(
        "Parsing abgeschlossen: %d Konten, %d Kategorien, "
        "%d Zahlungsempfänger, %d Transaktionen",
        len(hb_file.accounts),
        len(hb_file.categories),
        len(hb_file.payees),
        len(hb_file.transactions),
    )

    return hb_file
