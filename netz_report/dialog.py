"""Dialogfenster von Netz-Report (ohne .ui-Datei, damit alles in Python nachvollziehbar ist)."""
import datetime
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QCheckBox, QPushButton, QLabel, QLineEdit, QSpinBox,
    QTableWidget, QTableWidgetItem, QHBoxLayout, QHeaderView, QTabWidget, QAbstractItemView,
)
from qgis.gui import QgsMapLayerComboBox, QgsFieldComboBox, QgsFieldExpressionWidget, QgsCheckableComboBox
from qgis.core import QgsMapLayerProxyModel, QgsSettings

from .i18n import tr

try:  # QGIS >= 3.34
    from qgis.core import Qgis
    LINE_FILTER = Qgis.LayerFilter.LineLayer
except AttributeError:
    LINE_FILTER = QgsMapLayerProxyModel.LineLayer
try:
    NO_EDIT = QAbstractItemView.EditTrigger.NoEditTriggers
    STRETCH = QHeaderView.ResizeMode.Stretch
    TO_CONTENTS = QHeaderView.ResizeMode.ResizeToContents
except AttributeError:
    NO_EDIT = QAbstractItemView.NoEditTriggers
    STRETCH = QHeaderView.Stretch
    TO_CONTENTS = QHeaderView.ResizeToContents

S = "netz_report/"


class NetzReportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("Netz-Report – Netzstatistik und Bericht"))
        self.resize(760, 720)
        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.layer_combo = QgsMapLayerComboBox()
        self.layer_combo.setFilters(LINE_FILTER)
        form.addRow(tr("Leitungslayer:"), self.layer_combo)
        self.chk_selected = QCheckBox(tr("Nur ausgewählte Objekte"))
        form.addRow(self.chk_selected)
        self.filter_expr = QgsFieldExpressionWidget()
        form.addRow(tr("Filter (Ausdruck, optional):"), self.filter_expr)

        self.f_material = QgsFieldComboBox()
        self.f_dn = QgsFieldComboBox()
        self.f_year = QgsFieldComboBox()
        self.f_group = QgsFieldComboBox()
        for cb in (self.f_material, self.f_dn, self.f_year, self.f_group):
            cb.setAllowEmptyFieldName(True)
        form.addRow(tr("Feld Werkstoff:"), self.f_material)
        form.addRow(tr("Feld Nennweite (DN, mm):"), self.f_dn)
        form.addRow(tr("Feld Baujahr / Datum:"), self.f_year)
        form.addRow(tr("Feld Gebiet (optional):"), self.f_group)

        self.ref_year = QSpinBox()
        self.ref_year.setRange(1900, 2200)
        self.ref_year.setValue(datetime.date.today().year)
        form.addRow(tr("Bezugsjahr:"), self.ref_year)
        self.age_bounds = QLineEdit("20, 40, 60")
        form.addRow(tr("Altersklassen (Jahre):"), self.age_bounds)
        self.dn_bounds = QLineEdit("50, 100, 150, 300")
        form.addRow(tr("Nennweitenklassen (mm):"), self.dn_bounds)
        self.quality_fields = QgsCheckableComboBox()
        form.addRow(tr("Weitere Felder für Datenqualität:"), self.quality_fields)
        self.empty_values = QLineEdit("NYD, NOT YET DEFINED, Unassigned, unbekannt, unknown")
        form.addRow(tr("Werte, die als leer gelten:"), self.empty_values)
        layout.addLayout(form)

        buttons = QHBoxLayout()
        self.run_button = QPushButton(tr("Bericht erstellen"))
        self.xlsx_button = QPushButton(tr("Excel exportieren…"))
        self.pdf_button = QPushButton(tr("PDF exportieren…"))
        close_button = QPushButton(tr("Schließen"))
        close_button.clicked.connect(self.close)
        for b in (self.run_button, self.xlsx_button, self.pdf_button, close_button):
            buttons.addWidget(b)
        layout.addLayout(buttons)

        self.status = QLabel("")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        self.layer_combo.layerChanged.connect(self.update_fields)
        self.load_settings()
        self.update_fields(self.layer_combo.currentLayer())

    def update_fields(self, layer):
        for cb in (self.f_material, self.f_dn, self.f_year, self.f_group):
            cb.setLayer(layer)
        self.filter_expr.setLayer(layer)
        self.quality_fields.clear()
        if layer is not None:
            self.quality_fields.addItems([f.name() for f in layer.fields()])
            s = QgsSettings()
            combos = ((self.f_material, "material"), (self.f_dn, "dn"),
                      (self.f_year, "year"), (self.f_group, "group"))
            for cb, key in combos:
                name = s.value(S + key, "")
                if name and layer.fields().indexOf(name) >= 0:
                    cb.setField(name)
            checked = s.value(S + "quality_fields", "") or ""
            self.quality_fields.setCheckedItems([n for n in str(checked).split("|") if n])

    def load_settings(self):
        s = QgsSettings()
        self.age_bounds.setText(s.value(S + "age_bounds", self.age_bounds.text()))
        self.dn_bounds.setText(s.value(S + "dn_bounds", self.dn_bounds.text()))
        self.empty_values.setText(s.value(S + "empty_values", self.empty_values.text()))
        self.filter_expr.setExpression(s.value(S + "filter", "") or "")

    def save_settings(self):
        s = QgsSettings()
        s.setValue(S + "material", self.f_material.currentField())
        s.setValue(S + "dn", self.f_dn.currentField())
        s.setValue(S + "year", self.f_year.currentField())
        s.setValue(S + "group", self.f_group.currentField())
        s.setValue(S + "age_bounds", self.age_bounds.text())
        s.setValue(S + "dn_bounds", self.dn_bounds.text())
        s.setValue(S + "empty_values", self.empty_values.text())
        s.setValue(S + "filter", self.filter_expr.expression())
        s.setValue(S + "quality_fields", "|".join(self.quality_fields.checkedItems()))

    def show_tables(self, tables):
        """tables: Liste von (Titel, Kopfzeile, Zeilen)."""
        self.tabs.clear()
        for title, header, rows in tables:
            t = QTableWidget(len(rows), len(header))
            t.setHorizontalHeaderLabels(header)
            t.setEditTriggers(NO_EDIT)
            t.verticalHeader().setVisible(False)
            for i, row in enumerate(rows):
                for j, v in enumerate(row):
                    t.setItem(i, j, QTableWidgetItem(str(v)))
            t.horizontalHeader().setSectionResizeMode(0, STRETCH)
            for j in range(1, len(header)):
                t.horizontalHeader().setSectionResizeMode(j, TO_CONTENTS)
            self.tabs.addTab(t, title)
