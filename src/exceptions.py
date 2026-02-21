"""Domänenspezifische Ausnahmen für den Homebank-zu-hledger-Konverter."""


class HomebankParseError(Exception):
    """Wird ausgelöst, wenn die XHB-Datei nicht geparst werden kann."""


class ConversionError(Exception):
    """Wird ausgelöst, wenn eine Transaktion nicht konvertiert werden kann."""
