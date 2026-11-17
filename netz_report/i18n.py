"""Einfache Übersetzung von Netz-Report (Deutsch / Englisch).

Die Texte im Code sind deutsch. Ist QGIS nicht auf Deutsch eingestellt,
wird die englische Übersetzung aus EN verwendet.
"""
EN = {
    # Dialog
    "Netz-Report – Netzstatistik und Bericht": "Netz-Report – Network statistics and report",
    "Leitungslayer:": "Line layer:",
    "Nur ausgewählte Objekte": "Selected features only",
    "Filter (Ausdruck, optional):": "Filter (expression, optional):",
    "Feld Werkstoff:": "Material field:",
    "Feld Nennweite (DN, mm):": "Diameter field (DN, mm):",
    "Feld Baujahr / Datum:": "Install year / date field:",
    "Feld Gebiet (optional):": "Area field (optional):",
    "Bezugsjahr:": "Reference year:",
    "Altersklassen (Jahre):": "Age classes (years):",
    "Nennweitenklassen (mm):": "Diameter classes (mm):",
    "Weitere Felder für Datenqualität:": "Additional fields for data quality:",
    "Werte, die als leer gelten:": "Values treated as empty:",
    "Bericht erstellen": "Create report",
    "Excel exportieren…": "Export Excel…",
    "PDF exportieren…": "Export PDF…",
    "Schließen": "Close",
    # Tabellen
    "Kennzahlen": "Key figures", "Werkstoff": "Material", "Alter": "Age", "Nennweite": "Diameter",
    "Gebiet": "Area", "Datenqualität": "Data quality", "Kennzahl": "Key figure", "Wert": "Value",
    "Klasse": "Class", "Abschnitte": "Sections", "Länge (km)": "Length (km)", "Anteil (%)": "Share (%)",
    "Feld": "Field", "Soll (%)": "Target (%)", "Ist (%)": "Actual (%)",
    "Leitungen (km)": "Pipes (km)", "Leitungen (Abschnitte)": "Pipes (sections)",
    "Mittleres Baujahr (längengewichtet)": "Mean install year (length-weighted)",
    "Bezugsjahr": "Reference year",
    "unbekannt": "unknown",
    "unter {a} Jahre": "< {a} years", "{a}–{b} Jahre": "{a}–{b} years", "{a} Jahre und älter": ">= {a} years",
    "bis DN {a}": "up to DN {a}", "DN {a}–{b}": "DN {a}–{b}", "über DN {a}": "over DN {a}",
    # Meldungen
    "Bitte zuerst einen Leitungslayer auswählen.": "Please select a line layer first.",
    "Keine Objekte gefunden (Filter prüfen).": "No features found (check the filter).",
    "Filterausdruck ungültig: {msg}": "Invalid filter expression: {msg}",
    "Bitte zuerst einen Bericht erstellen.": "Please create a report first.",
    "{n} Abschnitte, {km} km ausgewertet.": "{n} sections, {km} km evaluated.",
    "Gespeichert: {path}": "Saved: {path}",
    "Speichern fehlgeschlagen: {msg}": "Saving failed: {msg}",
    "Excel-Datei (*.xlsx)": "Excel file (*.xlsx)", "PDF-Datei (*.pdf)": "PDF file (*.pdf)",
    # Bericht
    "Netzbericht": "Network report", "Layer": "Layer", "Filter": "Filter", "Erstellt am": "Created on",
    "Kurzfassung": "Summary", "keiner": "none",
    "Anteil der Netzlänge mit gültigem Wert (Soll 100 %).":
        "Share of network length with a valid value (target 100 %).",
    "Erstellt mit dem QGIS-Plugin Netz-Report.": "Created with the QGIS plugin Netz-Report.",
    "Das Netz hat {km} km Leitungen in {n} Abschnitten.": "The network has {km} km of pipes in {n} sections.",
    "Häufigster Werkstoff ist {m} ({s} % der Länge).": "The most common material is {m} ({s} % of length).",
    "Mittleres Baujahr (längengewichtet): {y}; {km} km ({s} %) sind {lab}.":
        "Mean install year (length-weighted): {y}; {km} km ({s} %) are {lab}.",
    "Am wenigsten vollständig ist das Feld {f} ({s} % der Länge mit Wert).":
        "The least complete field is {f} ({s} % of length with a value).",
}


def is_german():
    from qgis.core import QgsSettings
    loc = QgsSettings().value("locale/userLocale", "") or ""
    if not loc:
        from qgis.PyQt.QtCore import QLocale
        loc = QLocale.system().name()
    return str(loc).lower().startswith("de")


def tr(text, **kwargs):
    """Text übersetzen und Platzhalter wie {n} ausfüllen."""
    if not is_german():
        text = EN.get(text, text)
    return text.format(**kwargs) if kwargs else text
