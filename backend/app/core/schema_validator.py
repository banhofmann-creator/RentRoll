from app.parsers.base import ParseMetadata

EXPECTED_COLUMN_COUNT = 61

EXPECTED_HEADERS = [
    "Fonds", "Immobilie Numer", "Immobilie Bezeichnung", "GARBE Niederlassung", "",
    "Mieteinheit", "Art", "Stockwerk", "Anzahl Stellplätze", "Fläche", "",
    "Lease ID", "Mietername", "Mietbeginn", "vereinbartes Vertragsende",
    "Vertragsende (Kündigung)", "tatsächliches Vertragsende",
    "Sonderkündigung Frist", "Sonderkündigung zum", "Kündigung Frist",
    "Kündigung zum", "Laufzeit Option", "Frist Optionsziehung",
    "MV-Ende nach Optionsziehung", "Anzahl weiterer Optionen",
    "maximale Mietlaufzeit", "WAULT", "WAULB", "WAULE", "",
    "Jahresnettomiete", "Nettomiete", "Investitionsmiete",
    "Ende mietfreie Zeit", "Betrag mietfreie Zeit", "Marktmiete", "AM-ERV",
    "Potenzial", "Nettomiete", "Marktmiete", "AM-ERV", "",
    "NKVZ", "NK-Pauschale", "NKVZ", "NK-Pauschale",
    "Gesamtnettomiete", "Gesamtnettomiete", "Mieter UST-pflichtig", "",
    "proz. Mieterhöhung", "Erhöhungs-Prozentsatz", "nächste Erhöhung",
    "Erhöhungszyklen", "", "Indexmieterhöhung", "Wertsicherung Art",
    "Schwellwert", "Datum", "Weitergabe", "Green Lease",
]


def validate_schema(metadata: ParseMetadata) -> list[str]:
    warnings = []
    headers = metadata.column_headers

    if len(headers) != EXPECTED_COLUMN_COUNT:
        warnings.append(
            f"Column count mismatch: expected {EXPECTED_COLUMN_COUNT}, got {len(headers)}"
        )

    diffs = []
    for i in range(min(len(headers), len(EXPECTED_HEADERS))):
        actual = headers[i].strip()
        expected = EXPECTED_HEADERS[i].strip()
        if actual != expected and not (actual == "" and expected == ""):
            diffs.append(f"  col[{i}]: expected {expected!r}, got {actual!r}")

    if diffs:
        warnings.append("Column header differences:\n" + "\n".join(diffs))

    return warnings
