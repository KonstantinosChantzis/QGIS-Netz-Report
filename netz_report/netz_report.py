"""Hauptklasse des Plugins: Menüeintrag, Werkzeugleisten-Knopf, Auswertung und Export."""
import os
import datetime

from qgis.PyQt.QtGui import QIcon, QTextDocument
from qgis.PyQt.QtWidgets import QAction, QFileDialog
from qgis.core import QgsFeatureRequest, QgsExpression, QgsDistanceArea, QgsProject

from . import core
from .core import fmt
from .dialog import NetzReportDialog
from .i18n import tr


def is_null(v):
    if v is None:
        return True
    if hasattr(v, "isNull"):
        try:
            return bool(v.isNull())
        except TypeError:
            return False
    return str(v).strip() in ("", "NULL")


def to_year(v):
    """Jahr aus Zahl, Text ('1975' oder '1975-01-01'), QDate, QDateTime oder datetime."""
    if is_null(v):
        return None
    if hasattr(v, "date") and callable(v.date):   # QDateTime
        v = v.date()
    y = getattr(v, "year", None)
    if y is not None:
        y = y() if callable(y) else y
        return int(y) if 1000 < int(y) < 3000 else None
    try:
        y = int(float(str(v)[:4]))
    except ValueError:
        return None
    return y if 1000 < y < 3000 else None


def to_float(v):
    if is_null(v):
        return None
    try:
        return float(str(v).replace(",", "."))
    except ValueError:
        return None


class NetzReportPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.action = None
        self.dialog = None
        self.result = None
        self.meta = {}

    def initGui(self):
        icon = QIcon(os.path.join(os.path.dirname(__file__), "icon.png"))
        self.action = QAction(icon, "Netz-Report", self.iface.mainWindow())
        self.action.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToVectorMenu("&Netz-Report", self.action)

    def unload(self):
        self.iface.removeToolBarIcon(self.action)
        self.iface.removePluginVectorMenu("&Netz-Report", self.action)

    def run(self):
        if self.dialog is None:
            self.dialog = NetzReportDialog(self.iface.mainWindow())
            self.dialog.run_button.clicked.connect(self.create_report)
            self.dialog.xlsx_button.clicked.connect(self.export_xlsx)
            self.dialog.pdf_button.clicked.connect(self.export_pdf)
        self.dialog.show()
        self.dialog.raise_()

    # --- Auswertung ---
    def create_report(self):
        d = self.dialog
        layer = d.layer_combo.currentLayer()
        if layer is None:
            d.status.setText(tr("Bitte zuerst einen Leitungslayer auswählen."))
            return
        d.save_settings()
        expr = d.filter_expr.expression().strip()
        request = QgsFeatureRequest()
        if expr:
            e = QgsExpression(expr)
            if e.hasParserError():
                d.status.setText(tr("Filterausdruck ungültig: {msg}", msg=e.parserErrorString()))
                return
            request.setFilterExpression(expr)
        feats = layer.getSelectedFeatures(request) if d.chk_selected.isChecked() else layer.getFeatures(request)

        empty = {v.strip().lower() for v in d.empty_values.text().split(",") if v.strip()}
        f_mat, f_dn, f_year, f_grp = (d.f_material.currentField(), d.f_dn.currentField(),
                                      d.f_year.currentField(), d.f_group.currentField())
        q_fields = [f for f in (f_mat, f_dn, f_year, f_grp) if f]
        q_fields += [f for f in d.quality_fields.checkedItems() if f not in q_fields]

        da = QgsDistanceArea()
        da.setSourceCrs(layer.crs(), QgsProject.instance().transformContext())
        geographic = layer.crs().isGeographic()
        if geographic:
            da.setEllipsoid(QgsProject.instance().ellipsoid() or "EPSG:7030")

        def text(v):
            if is_null(v):
                return None
            s = str(v).strip()
            return None if s.lower() in empty else s

        records = []
        for f in feats:
            g = f.geometry()
            if g is None or g.isEmpty():
                continue
            length = da.measureLength(g) if geographic else g.length()
            mat = text(f[f_mat]) if f_mat else None
            dn = to_float(f[f_dn]) if f_dn else None
            year = to_year(f[f_year]) if f_year else None
            grp = text(f[f_grp]) if f_grp else None
            filled = {}
            for q in q_fields:
                if q == f_dn:
                    filled[q] = dn is not None and dn > 1
                elif q == f_year:
                    filled[q] = year is not None
                else:
                    filled[q] = text(f[q]) is not None
            records.append({"length_m": length, "material": mat, "dn": dn, "year": year,
                            "group": grp, "filled": filled})
        if not records:
            d.status.setText(tr("Keine Objekte gefunden (Filter prüfen)."))
            return

        age_b = core.parse_bounds(d.age_bounds.text(), (20, 40, 60))
        dn_b = core.parse_bounds(d.dn_bounds.text(), (50, 100, 150, 300))
        self.result = core.summarize(records, d.ref_year.value(), age_b, dn_b, q_fields)
        self.meta = {"layer": layer.name(), "filter": expr or tr("keiner"),
                     "date": datetime.date.today().strftime("%d.%m.%Y"),
                     "with_dn": bool(f_dn), "with_year": bool(f_year), "with_mat": bool(f_mat)}
        d.show_tables(self.tables())
        d.status.setText(tr("{n} Abschnitte, {km} km ausgewertet.", n=fmt(self.result["count"], 0),
                            km=fmt(self.result["total_km"])))

    def tables(self):
        r = self.result
        head = [tr("Klasse"), tr("Abschnitte"), tr("Länge (km)"), tr("Anteil (%)")]

        def rows(t):
            return [[k, fmt(n, 0), fmt(km, 2), fmt(s, 1)] for k, n, km, s in t]
        kz = [[tr("Leitungen (Abschnitte)"), fmt(r["count"], 0)], [tr("Leitungen (km)"), fmt(r["total_km"], 1)],
              [tr("Bezugsjahr"), str(r["ref_year"])]]
        if r["mean_year"]:
            kz.append([tr("Mittleres Baujahr (längengewichtet)"), str(int(round(r["mean_year"])))])
        out = [(tr("Kennzahlen"), [tr("Kennzahl"), tr("Wert")], kz)]
        if self.meta.get("with_mat"):
            out.append((tr("Werkstoff"), head, rows(r["material"])))
        if self.meta.get("with_year"):
            out.append((tr("Alter"), head, rows(r["age"])))
        if self.meta.get("with_dn"):
            out.append((tr("Nennweite"), head, rows(r["dn"])))
        if r["group"]:
            out.append((tr("Gebiet"), head, rows(r["group"])))
        out.append((tr("Datenqualität"), [tr("Feld"), tr("Soll (%)"), tr("Ist (%)")],
                    [[f, fmt(s, 0), fmt(i, 1)] for f, s, i in r["quality"]]))
        return out

    def raw_tables(self):
        """Same tables as tables(), but with plain numbers (for Excel)."""
        r = self.result
        head = [tr("Klasse"), tr("Abschnitte"), tr("Länge (km)"), tr("Anteil (%)")]

        def rows(t):
            return [[k, int(n), round(km, 2), round(s, 1)] for k, n, km, s in t]
        kz = [[tr("Leitungen (Abschnitte)"), int(r["count"])], [tr("Leitungen (km)"), round(r["total_km"], 1)],
              [tr("Bezugsjahr"), int(r["ref_year"])]]
        if r["mean_year"]:
            kz.append([tr("Mittleres Baujahr (längengewichtet)"), int(round(r["mean_year"]))])
        out = [(tr("Kennzahlen"), [tr("Kennzahl"), tr("Wert")], kz)]
        if self.meta.get("with_mat"):
            out.append((tr("Werkstoff"), head, rows(r["material"])))
        if self.meta.get("with_year"):
            out.append((tr("Alter"), head, rows(r["age"])))
        if self.meta.get("with_dn"):
            out.append((tr("Nennweite"), head, rows(r["dn"])))
        if r["group"]:
            out.append((tr("Gebiet"), head, rows(r["group"])))
        out.append((tr("Datenqualität"), [tr("Feld"), tr("Soll (%)"), tr("Ist (%)")],
                    [[f, round(s, 1), round(i, 1)] for f, s, i in r["quality"]]))
        return out

    # --- Export ---
    def _ask_path(self, title, filt, ext):
        path, _ = QFileDialog.getSaveFileName(self.dialog, title, "", filt)
        if path and not path.lower().endswith(ext):
            path += ext
        return path

    def export_xlsx(self):
        if not self.result:
            self.dialog.status.setText(tr("Bitte zuerst einen Bericht erstellen."))
            return
        path = self._ask_path(tr("Excel exportieren…"), tr("Excel-Datei (*.xlsx)"), ".xlsx")
        if not path:
            return
        from osgeo import ogr
        drv = ogr.GetDriverByName("XLSX")
        if os.path.exists(path):
            drv.DeleteDataSource(path)
        ds = drv.CreateDataSource(path)
        if ds is None:
            self.dialog.status.setText(tr("Speichern fehlgeschlagen: {msg}", msg=path))
            return
        for title, header, rows in self.raw_tables():
            lyr = ds.CreateLayer(title[:31], geom_type=ogr.wkbNone)
            for j, h in enumerate(header):
                if j == 0:
                    ftype = ogr.OFTString
                else:
                    vals = [row[j] for row in rows]
                    ftype = ogr.OFTInteger if vals and all(isinstance(v, int) for v in vals) else ogr.OFTReal
                lyr.CreateField(ogr.FieldDefn(h, ftype))
            for row in rows:
                feat = ogr.Feature(lyr.GetLayerDefn())
                for j, v in enumerate(row):
                    feat.SetField(j, v if j else str(v))
                lyr.CreateFeature(feat)
        ds = None
        self.dialog.status.setText(tr("Gespeichert: {path}", path=path))

    def html(self):
        r, m = self.result, self.meta
        css = ("body{font-family:Arial;font-size:9pt;} h1{font-size:16pt;color:#1F3864;} "
               "h2{font-size:11pt;color:#1F3864;margin-top:12px;} table{border-collapse:collapse;} "
               "th{background:#E8ECF4;text-align:left;} td,th{border:1px solid #bbb;padding:3px 6px;}")
        parts = [f"<html><head><style>{css}</style></head><body>",
                 f"<h1>{tr('Netzbericht')} – {m['layer']}</h1>",
                 f"<p>{tr('Layer')}: {m['layer']} &nbsp;|&nbsp; {tr('Filter')}: {m['filter']} &nbsp;|&nbsp; "
                 f"{tr('Erstellt am')}: {m['date']}</p>",
                 f"<h2>{tr('Kurzfassung')}</h2><p>{core.summary_text(r)}</p>"]
        for title, header, rows in self.tables():
            head_html = "".join(f"<th>{h}</th>" for h in header)
            parts.append(f"<h2>{title}</h2><table width='100%'><thead><tr>{head_html}</tr></thead><tbody>")
            for row in rows:
                parts.append("<tr>" + "".join(f"<td>{v}</td>" if j == 0 else f"<td align='right'>{v}</td>"
                                              for j, v in enumerate(row)) + "</tr>")
            parts.append("</tbody></table>")
            if title == tr("Datenqualität"):
                parts.append(f"<p>{tr('Anteil der Netzlänge mit gültigem Wert (Soll 100 %).')}</p>")
        parts.append(f"<p style='color:#777'>{tr('Erstellt mit dem QGIS-Plugin Netz-Report.')}</p></body></html>")
        return "".join(parts)

    def export_pdf(self):
        if not self.result:
            self.dialog.status.setText(tr("Bitte zuerst einen Bericht erstellen."))
            return
        path = self._ask_path(tr("PDF exportieren…"), tr("PDF-Datei (*.pdf)"), ".pdf")
        if not path:
            return
        from qgis.PyQt.QtPrintSupport import QPrinter
        try:
            printer = QPrinter(QPrinter.PrinterMode.HighResolution)
            printer.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
        except AttributeError:
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(path)
        doc = QTextDocument()
        doc.setHtml(self.html())
        if hasattr(doc, "print_"):
            doc.print_(printer)
        else:
            doc.print(printer)
        self.dialog.status.setText(tr("Gespeichert: {path}", path=path))
