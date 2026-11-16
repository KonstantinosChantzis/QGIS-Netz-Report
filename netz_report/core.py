"""Berechnung der Kennzahlen von Netz-Report (ohne QGIS-Abhängigkeit, damit testbar)."""
from .i18n import tr


def parse_bounds(text, default):
    """Text wie '20, 40, 60' in eine sortierte Liste von Zahlen umwandeln."""
    try:
        values = sorted({float(v.strip()) for v in str(text).replace(";", ",").split(",") if v.strip()})
    except ValueError:
        return list(default)
    return values or list(default)


def _num(x):
    return int(x) if float(x).is_integer() else x


def age_labels(bounds):
    labels = [tr("unter {a} Jahre", a=_num(bounds[0]))]
    for lo, hi in zip(bounds[:-1], bounds[1:]):
        labels.append(tr("{a}–{b} Jahre", a=_num(lo), b=_num(hi) - 1))
    labels.append(tr("{a} Jahre und älter", a=_num(bounds[-1])))
    return labels + [tr("unbekannt")]


def dn_labels(bounds):
    labels = [tr("bis DN {a}", a=_num(bounds[0]))]
    for lo, hi in zip(bounds[:-1], bounds[1:]):
        labels.append(tr("DN {a}–{b}", a=_num(lo) + 1, b=_num(hi)))
    labels.append(tr("über DN {a}", a=_num(bounds[-1])))
    return labels + [tr("unbekannt")]


def age_class(year, ref_year, bounds, labels):
    if year is None:
        return labels[-1]
    age = ref_year - year
    for i, b in enumerate(bounds):
        if age < b:
            return labels[i]
    return labels[len(bounds)]


def dn_class(dn, bounds, labels):
    if dn is None or dn <= 1:
        return labels[-1]
    for i, b in enumerate(bounds):
        if dn <= b:
            return labels[i]
    return labels[len(bounds)]


def summarize(records, ref_year, age_bounds=(20, 40, 60), dn_bounds=(50, 100, 150, 300), quality_fields=()):
    """records: Liste von dicts mit den Schlüsseln
    length_m, material, dn, year, group (alle außer length_m dürfen None sein)
    und filled (dict Feldname -> True/False für die Datenqualität).
    Gibt ein dict mit Tabellen (Liste von Zeilen) und Kennzahlen zurück."""
    a_lab = age_labels(age_bounds)
    d_lab = dn_labels(dn_bounds)
    unknown = tr("unbekannt")
    total = sum(r["length_m"] for r in records) / 1000.0

    def table(key_func, order=None):
        acc = {}
        for r in records:
            k = key_func(r)
            n, km = acc.get(k, (0, 0.0))
            acc[k] = (n + 1, km + r["length_m"] / 1000.0)
        if order:
            keys = [k for k in order if k in acc]
        else:
            keys = sorted((k for k in acc if k != unknown), key=lambda k: -acc[k][1])
            if unknown in acc:
                keys.append(unknown)
        return [(k, acc[k][0], acc[k][1], 100.0 * acc[k][1] / total if total else 0.0) for k in keys]

    t_mat = table(lambda r: r["material"] or unknown)
    t_age = table(lambda r: age_class(r["year"], ref_year, age_bounds, a_lab), a_lab)
    t_dn = table(lambda r: dn_class(r["dn"], dn_bounds, d_lab), d_lab)
    t_grp = table(lambda r: r["group"] or unknown) if any(r["group"] is not None for r in records) else []

    quality = []
    for f in quality_fields:
        km = sum(r["length_m"] for r in records if r["filled"].get(f)) / 1000.0
        quality.append((f, 100.0, 100.0 * km / total if total else 0.0))

    with_year = [r for r in records if r["year"] is not None]
    yl = sum(r["length_m"] for r in with_year)
    mean_year = sum(r["year"] * r["length_m"] for r in with_year) / yl if yl else None
    oldest = a_lab[len(age_bounds)]
    old_km = next((row[2] for row in t_age if row[0] == oldest), 0.0)
    return {
        "total_km": total, "count": len(records), "mean_year": mean_year, "ref_year": ref_year,
        "oldest_label": oldest, "old_km": old_km, "old_share": 100.0 * old_km / total if total else 0.0,
        "material": t_mat, "age": t_age, "dn": t_dn, "group": t_grp, "quality": quality,
    }


def summary_text(res):
    """Kurzfassung in 2–3 Sätzen."""
    parts = [tr("Das Netz hat {km} km Leitungen in {n} Abschnitten.", km=fmt(res["total_km"]), n=fmt(res["count"], 0))]
    known = [r for r in res["material"] if r[0] != tr("unbekannt")]
    if known:
        parts.append(tr("Häufigster Werkstoff ist {m} ({s} % der Länge).", m=known[0][0], s=fmt(known[0][3])))
    if res["mean_year"]:
        parts.append(tr("Mittleres Baujahr (längengewichtet): {y}; {km} km ({s} %) sind {lab}.",
                        y=int(round(res["mean_year"])), km=fmt(res["old_km"]), s=fmt(res["old_share"]),
                        lab=res["oldest_label"]))
    if res["quality"]:
        worst = min(res["quality"], key=lambda q: q[2])
        parts.append(tr("Am wenigsten vollständig ist das Feld {f} ({s} % der Länge mit Wert).",
                        f=worst[0], s=fmt(worst[2])))
    return " ".join(parts)


def fmt(x, d=1):
    """Zahl im deutschen oder englischen Format."""
    from .i18n import is_german
    s = f"{x:,.{d}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".") if is_german() else s
