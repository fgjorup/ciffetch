# -*- coding: utf-8 -*-
"""
Module for an interactive COD search and CIF retrieval dialog. Intended 
to be used as part of other PyQt applications, but can be run as a 
stand-alone application as well.

Searches the Crystallography Open Database using crystallographic filters
and displays matching entries in a sortable table. Users can fetch and
save individual CIF files from the results.

Create a CifFetchDialog() instance and use `fetch_cifs()` for
standard browsing, or `fetch_single_cif()` to auto-close after a single
file is saved. Emits `sigFileFetched(path, cif_content)` when a CIF is
successfully fetched, and `accepted()` in single-file mode.


Made possible by the people behind Crystallograhy Open Database (COD)
https://www.crystallography.net/cod/

All data in the COD and the database itself are dedicated to the public domain
and licensed under the CC0 License . Users of the data should acknowledge the 
original authors of the structural data.

F.H. Gjørup 2026
Aarhus University, Denmark
MAX IV Laboratory, Lund University, Sweden
https://github.com/fgjorup
"""

import re
import sys
import requests
from functools import lru_cache
from PyQt6.QtCore import Qt, QRegularExpression, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QComboBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QFileDialog,
    QStatusBar,
    QMenu,
    QToolButton,
)
from PyQt6.QtGui import QRegularExpressionValidator


COD_URL = "https://www.crystallography.net/cod"
TIMEOUT = 5  # seconds

_IUPAC_PRIORITY = (
    "Rn", "Xe", "Kr", "Ar", "Ne", "He",
    "Fr", "Cs", "Rb", "K", "Na", "Li",
    "Ra", "Ba", "Sr", "Ca", "Mg", "Be",
    "Lr", "Y", "Sc", "La", "Ac", "Hf", "Zr", "Ti", "Ta", "Nb", "V", 
    "W", "Mo", "Cr", "Re", "Tc", "Mn", "Os", "Ru", "Fe", "Ir", "Rh", 
    "Co", "Pt", "Pd", "Ni", "Au", "Ag", "Cu", "Hg", "Cd", "Zn",
    "Tl", "In", "Ga", "Al", "B",
    "Pb", "Sn", "Ge", "Si", "C",
    "Bi", "Sb", "As", "P", "N",
    "H",
    "Po", "Te", "Se", "S",
    "At", "I", "Br", "Cl",
    "O", "F",
)
_PRIORITY_BY_ELEMENT = {
    element: index for index, element in enumerate(_IUPAC_PRIORITY)
}
_UNKNOWN_PRIORITY = len(_IUPAC_PRIORITY)

# A complete lookup dictionary for all 230 space groups
SPACE_GROUPS = {
    # Triclinic (1-2)
    1: "P 1", 2: "P -1",
    # Monoclinic (3-15)
     3: "P 2",       4: "P 2_1",    5: "C 2",    6: "P m",    7: "P c",      8: "C m", 9: "C c",
    10: "P 2/m",    11: "P 2_1/m", 12: "C 2/m", 13: "P 2/c", 14: "P 2_1/c", 15: "C 2/c",
    # Orthorhombic (16-74)
    16: "P 222",   17: "P 222_1", 18: "P 2_12_12", 19: "P 2_12_12_1", 20: "C 222_1",
    21: "C 222",   22: "F 222",   23: "I 222",     24: "I 2_12_12_1", 25: "P mm2",
    26: "P mc2_1", 27: "P cc2",   28: "P ma2",     29: "P ca2_1",     30: "P nc2",
    31: "P mn2_1", 32: "P ba2",   33: "P na2_1",   34: "P nn2",       35: "C mm2",
    36: "C mc2_1", 37: "C cc2",   38: "A mm2",     39: "A em2",       40: "A ma2",
    41: "A ea2",   42: "F mm2",   43: "F dd2",     44: "I mm2",       45: "I ba2",
    46: "I ma2",   47: "P mmm",   48: "P nnn",     49: "P ccm",       50: "P ban",
    51: "P mma",   52: "P nna",   53: "P mna",     54: "P cca",       55: "P bam",
    56: "P ccn",   57: "P bcm",   58: "P nnm",     59: "P mmn",       60: "P bcn",
    61: "P bca",   62: "P nma",   63: "C mcm",     64: "C mce",       65: "C mmm",
    66: "C ccm",   67: "C mme",   68: "C cce",     69: "F mmm",       70: "F ddd",
    71: "I mmm",   72: "I bam",   73: "I bca",     74: "I mma",
    # Tetragonal (75-142)
     75: "P 4",        76: "P 4_1",       77: "P 4_2",      78: "P 4_3",      79: "I 4",        80: "I 4_1",
     81: "P -4",       82: "I -4",        83: "P 4/m",      84: "P 4_2/m",    85: "P 4/n",      86: "P 4_2/n",
     87: "I 4/m",      88: "I 4_1/a",     89: "P 422",      90: "P 42_12",    91: "P 4_122",    92: "P 4_12_12",
     93: "P 4_222",    94: "P 4_22_12",   95: "P 4_322",    96: "P 4_32_12",  97: "I 422",      98: "I 4_122",
     99: "P 4mm",     100: "P 4bm",      101: "P 4_2cm",   102: "P 4_2nm",   103: "P 4cc",     104: "P 4nc",
    105: "P 4_2mc",   106: "P 4_2bc",    107: "I 4mm",     108: "I 4cm",     109: "I 4_1md",   110: "I 4_1cd",
    111: "P -42m",    112: "P -42c",     113: "P -42_1m",  114: "P -42_1c",  115: "P -4m2",    116: "P -4c2",
    117: "P -4b2",    118: "P -4n2",     119: "I -4m2",    120: "I -4c2",    121: "I -42m",    122: "I -42d",
    123: "P 4/mmm",   124: "P 4/mcc",    125: "P 4/nbm",   126: "P 4/nnc",   127: "P 4/mbm",   128: "P 4/mnc",
    129: "P 4/nmm",   130: "P 4/ncc",    131: "P 4_2/mmc", 132: "P 4_2/mcm", 133: "P 4_2/nbc", 134: "P 4_2/nnm",
    135: "P 4_2/mbc", 136: "P 4_2/mnm",  137: "P 4_2/nmc", 138: "P 4_2/ncm", 139: "I 4/mmm",   140: "I 4/mcm",
    141: "I 4_1/amd", 142: "I 4_1/acd",
    # Trigonal (143-167)
    143: "P 3", 144: "P3_1", 145: "P3_2", 146: "R3", 147: "P-3", 148: "R-3",
    149: "P 312", 150: "P321", 151: "P3_112", 152: "P3_121", 153: "P3_212", 154: "P3_221",
    155: "R 32", 156: "P3m1", 157: "P31m", 158: "P3c1", 159: "P31c", 160: "R3m",
    161: "R 3c", 162: "P-31m", 163: "P-31c", 164: "P-3m1", 165: "P-3c1", 166: "R-3m",
    167: "R -3c",
    # Hexagonal (168-194)
    168: "P 6",     169: "P 6_1",     170: "P 6_5",    171: "P 6_2",  172: "P 6_4",   173: "P 6_3",
    174: "P -6",    175: "P 6/m",     176: "P 6_3/m",  177: "P 622",  178: "P 6_122", 179: "P 6_522",
    180: "P 6_222", 181: "P 6_422",   182: "P 6_322",  183: "P 6mm",  184: "P 6cc",   185: "P 6_3cm",
    186: "P 6_3mc", 187: "P -6m2",    188: "P -6c2",   189: "P -62m", 190: "P -62c",  191: "P 6/mmm",
    192: "P 6/mcc", 193: "P 6_3/mcm", 194: "P 6_3/mmc",
    # Cubic (195-230)
    195: "P 23",    196: "F 23",    197: "I 23",   198: "P 2_13",  199: "I 2_13", 200: "P m-3",
    201: "P n-3",   202: "F m-3",   203: "F d-3",  204: "I m-3",   205: "P a-3",  206: "I a-3",
    207: "P 432",   208: "P 4_232", 209: "F 432",  210: "F 4_132", 211: "I 432",  212: "P 4_332",
    213: "P 4_132", 214: "I 4_132", 215: "P -43m", 216: "F -43m",  217: "I -43m", 218: "P -43n",
    219: "F -43c",  220: "I -43d",  221: "P m-3m", 222: "P n-3n",  223: "P m-3n", 224: "P n-3m",
    225: "F m-3m",  226: "F m-3c",  227: "F d-3m", 228: "F d-3c",  229: "I m-3m", 230: "I a-3d"
}

def lookup_space_group(sg_number: int) -> str:
    """Returns the Hermann-Mauguin symbol for an International Tables number (1-230)."""
    return SPACE_GROUPS.get(sg_number, f"Error: {sg_number} is not a valid space group number (1-230).")


@lru_cache(maxsize=4096)
def parse_formula(elements: str) -> str:
    """"Parse a list of elements into a more human-readable form."""
    if not elements:
        return ""
    elements_list = elements.split()
    elements_list.sort(
        key=lambda element: _PRIORITY_BY_ELEMENT.get(
            re.sub(r"[^A-Za-z]", "", element),
            _UNKNOWN_PRIORITY,
        )
    )
    return "".join(elements_list)

class RangeEdit(QLineEdit):
    """A QLineEdit that accepts a range of numbers in the form "min-max"."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("min-max")
        self.setValidator(QRegularExpressionValidator(QRegularExpression(r"^\s*(\d*\.?\d*)\s*-\s*(\d*\.?\d*)\s*$"), self))

    def value(self):
        text = self.text().strip()
        if not text:
            return None, None
        match = re.match(r"^\s*(\d*\.?\d*)\s*-\s*(\d*\.?\d*)\s*$", text)
        if not match:
            raise ValueError(f"Invalid range: {text}")
        min_value = float(match.group(1)) if match.group(1) else None
        max_value = float(match.group(2)) if match.group(2) else None
        return min_value, max_value


class CifFetchDialog(QDialog):
    """Interactive COD search and CIF retrieval dialog.

    Searches the Crystallography Open Database using crystallographic filters
    and displays matching entries in a sortable table. Users can fetch and
    save individual CIF files from the results. Use `fetch_cifs()` for
    standard browsing, or `fetch_single_cif()` to auto-close after a single
    file is saved. Emits `sigFileFetched(path, cif_content)` when a CIF is
    successfully fetched, and `accepted()` in single-file mode.

    Made possible by the people behind Crystallograhy Open Database (COD)
    https://www.crystallography.net/cod/

    All data in the COD and the database itself are dedicated to the public domain
    and licensed under the CC0 License . Users of the data should acknowledge the 
    original authors of the structural data.
    """
    sigFileFetched = pyqtSignal(str,str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("CIF search")
        self.resize(900, 600)
        self.single_cif = False
        self.latest_file = None

        self.tabs = QTabWidget(self)
        self.search_tab = self._build_search_tab()
        self.results_tab = self._build_results_tab()
        self.tabs.addTab(self.search_tab, "Search")
        self.tabs.addTab(self.results_tab, "Results")
        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        self.status_bar = QStatusBar(self)
        self.status_bar.showMessage("Crystallography Open Database: https://www.crystallography.net/cod/")
        layout.addWidget(self.status_bar)
        self.search_and_show_button.setDefault(True)

    def _build_search_tab(self):
        tab = QWidget()
        form = QFormLayout()

        self.formula_input = QLineEdit()
        self.formula_input.setPlaceholderText("e.g. Al2O3")
        self.elements_input = QLineEdit()
        self.elements_input.setPlaceholderText("e.g. Al O (up to 8)")
        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Title, mineral, or other text e.g. corundum")
        self.journal_input = QLineEdit()

        self.spacegroup_input = QComboBox()
        sgs = [SPACE_GROUPS[key] for key in sorted(list(SPACE_GROUPS.keys()))]
        self.spacegroup_input.addItems(sgs)
        for i,cat in [(0,"Triclinic"), (3,"Monoclinic"), (17,"Orthorhombic"), (77,"Tetragonal"), (146,"Trigonal"), (172,"Hexagonal"), (200,"Cubic")]:
            self.spacegroup_input.insertItem(i,cat)
            self.spacegroup_input.model().item(i).setEnabled(False)
        self.spacegroup_input.insertItem(0,"Any")
        self.spacegroup_input.setCurrentIndex(0)
        self.spacegroup_input.currentTextChanged.connect(self._update_spacegroup_from_name)

        # self.spacegroup_input.editingFinished.connect(self._update_spacegroup_from_name)
        # self.spacegroup_input = QLineEdit()
        # self.spacegroup_input.setPlaceholderText("e.g. P 63/m")
        # self.spacegroup_input.editingFinished.connect(self._update_spacegroup_from_name)
        
        self.space_group_number_input = QSpinBox()
        self.space_group_number_input.setRange(0, 230)
        self.space_group_number_input.setSpecialValueText("Any")
        self.space_group_number_input.setWrapping(True)
        self.space_group_number_input.valueChanged.connect(self._update_spacegroup_from_number)

        self.a_range_input = RangeEdit()
        self.b_range_input = RangeEdit()
        self.c_range_input = RangeEdit()
        self.alpha_range_input = RangeEdit()
        self.beta_range_input = RangeEdit()
        self.gamma_range_input = RangeEdit()

        self.year_input = QSpinBox()
        self.year_input.setRange(1900, 2100)
        self.year_input.setSpecialValueText("Any")
        self.year_input.setWrapping(True)
        self.n_elements_input = QSpinBox()
        self.n_elements_input.setRange(0, 8)
        self.n_elements_input.setSpecialValueText("Any")
        self.limit_input = QSpinBox()
        self.limit_input.setRange(1, 1000)
        self.limit_input.setValue(100)

        form.addRow("Formula:", self.formula_input)
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.elements_input)
        hlayout.addWidget(QLabel("Number of elements:"))
        hlayout.addWidget(self.n_elements_input)
        form.addRow("Elements:", hlayout)
  
        hlayout = QHBoxLayout()
        hlayout.addWidget(self.spacegroup_input)
        hlayout.addWidget(QLabel("Space group number:"))
        hlayout.addWidget(self.space_group_number_input)
        form.addRow("Space group:", hlayout)
        # form.addRow("Space group number:", self.space_group_number_input)
        hlayout = QHBoxLayout()
        hlayout.addWidget(QLabel("a:"))
        hlayout.addWidget(self.a_range_input)
        hlayout.addWidget(QLabel("b:"))
        hlayout.addWidget(self.b_range_input)
        hlayout.addWidget(QLabel("c:"))
        hlayout.addWidget(self.c_range_input)
        hlayout.addWidget(QLabel("\u03b1:"))
        hlayout.addWidget(self.alpha_range_input)
        hlayout.addWidget(QLabel("\u03b2:"))
        hlayout.addWidget(self.beta_range_input)
        hlayout.addWidget(QLabel("\u03b3:"))
        hlayout.addWidget(self.gamma_range_input)
        form.addRow("Lattice parameters:", hlayout)
        form.addRow("Text:", self.text_input)
        form.addRow("Journal:", self.journal_input)
        form.addRow("Publication year:", self.year_input)
        form.addRow("Maximum displayed results:", self.limit_input)

        self.clear_search_button = QPushButton("Clear search")
        self.clear_search_button.clicked.connect(self.clear_search)
        self.search_button = QPushButton("Run search")
        self.search_button.clicked.connect(self.run_search)
        self.search_and_show_button = QPushButton("Run search and show results")
        self.search_and_show_button.clicked.connect(self.run_search_and_show_results)
        
        layout = QVBoxLayout(tab)
        layout.addLayout(form)
        search_buttons_layout = QHBoxLayout()
        search_buttons_layout.addWidget(self.clear_search_button)
        search_buttons_layout.addStretch()
        search_buttons_layout.addWidget(self.search_button)
        search_buttons_layout.addWidget(self.search_and_show_button)
        layout.addLayout(search_buttons_layout)
        layout.addStretch()
        return tab

    def _build_results_tab(self):

        self.entry_fields = [
            ("file", "COD ID"),
            ("sg", "Space group"),
            ("formula", "Formula"),
            ("a", "a (Å)"),
            ("b", " b (Å)"),
            ("c", " c (Å)"),
            ("alpha", " \u03b1 (\u00b0)"),
            ("beta", " \u03b2 (\u00b0)"),
            ("gamma", " \u03b3 (\u00b0)"),
            ("vol", "Volume (Å\u00b3)"),
            ("Z", "Z"),
            ("diffrtemp", "Temperature (K)"),
            ("diffrpressure", "Pressure (kPa)"),
            ("celltemp", "Cell temperature (K)"),
            ("cellpressure", "Cell pressure (kPa)"),
            ("commonname", "Common name"),
            ("chemname", "Chemical name"),
            ("mineral", "Mineral"),
            # ("Rall", "Rall"),
            # ("Robs", "Robs"),
            # ("Rref", "Rref"),
            # ("wRall", "wRall"),
            # ("wRobs", "wRobs"),
            # ("wRref", "wRref"),
            # ("RFsqd", "RFsqd"),
            # ("RI", "RI"),
            # ("gofall", "gofall"),
            # ("gofobs", "gofobs"),
            # ("gofgt", "gofgt"),
            # ("gofref", "gofref"),
            ("authors", "Authors"),
            ("title", "Title"),
            ("year", "Year"),
            ("journal", "Journal"),
            # ("volume", "Volume"), # journal volume
            # ("issue", "Issue"),
            # ("firstpage", "First page"),
            # ("lastpage", "Last page"),
            ("doi", "DOI"),
        ]

        tab = QWidget()
        self.results_table = QTableWidget(0, len(self.entry_fields), tab)
        self.results_table.setHorizontalHeaderLabels([label for field, label in self.entry_fields])
        self.results_table.setSortingEnabled(True)
        self.results_table.setWordWrap(False)
        self.results_table.horizontalHeader().setStretchLastSection(True)
        self.results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.results_table.resizeColumnsToContents()

        self.results_table.cellDoubleClicked.connect(self.table_double_clicked)


        default_fields = [0,1,2,3,4,5,6,7,8,9,11,12,18,19,20]
        menu = QMenu(self)
        for column, (field, label) in enumerate(self.entry_fields):
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(column in default_fields)
            self.results_table.setColumnHidden(column, column not in default_fields)
            action.toggled.connect(
                lambda visible, column=column:
                    self.results_table.setColumnHidden(column, not visible)
            )

        button = QToolButton()
        button.setText("Fields")
        button.setMenu(menu)
        button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)


        layout = QVBoxLayout(tab)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.results_table)
        return tab

    def _search_parameters(self):
        params = {"format": "json"}
        # for key, value in (
        #     ("formula", self.formula_input.text()),
        #     ("text", self.text_input.text()),
        #     ("journal", self.journal_input.text()),
        #     ("spacegroup", self.spacegroup_input.currentText()),
        # ):
        #     if value.strip():
        #         params[key] = value.strip()

        elements = self.elements_input.text().replace(",", " ").split()
        if len(elements) > 8:
            raise ValueError("COD search supports at most 8 required elements.")
        for index, element in enumerate(elements, start=1):
            params[f"el{index}"] = element

        if self.year_input.text() != self.year_input.specialValueText():
            params["year"] = self.year_input.value()

        if self.formula_input.text().strip():
            formula = self.formula_input.text().strip()
            formula = [part for part in re.split(r"(?=[A-Z])", formula) if part]
            formula = " ".join(sorted(formula))
            params["formula"] = formula

        if self.a_range_input.text().strip():
            amin, amax = self.a_range_input.value()
            if amin is not None:
                params["amin"] = amin
            if amax is not None:
                params["amax"] = amax

        if self.b_range_input.text().strip():
            bmin, bmax = self.b_range_input.value()
            if bmin is not None:
                params["bmin"] = bmin
            if bmax is not None:
                params["bmax"] = bmax

        if self.c_range_input.text().strip():
            cmin, cmax = self.c_range_input.value()
            if cmin is not None:
                params["cmin"] = cmin
            if cmax is not None:
                params["cmax"] = cmax

        if self.alpha_range_input.text().strip():
            alpmin, alpmax = self.alpha_range_input.value()
            if alpmin is not None:
                params["alpmin"] = alpmin
            if alpmax is not None:
                params["alpmax"] = alpmax

        if self.beta_range_input.text().strip():
            betmin, betmax = self.beta_range_input.value()
            if betmin is not None:
                params["betmin"] = betmin
            if betmax is not None:
                params["betmax"] = betmax

        if self.gamma_range_input.text().strip():
            gamin, gamax = self.gamma_range_input.value()
            if gamin is not None:
                params["gamin"] = gamin
            if gamax is not None:
                params["gamax"] = gamax
        
        # if self.spacegroup_input.text().strip():
        #     sg = self.spacegroup_input.text().strip()
        #     sg = sg.replace(" ", "")
        #     sg = sg[0]+' '+ sg[1:] if len(sg) > 1 else sg
        #     params["spacegroup"] = sg
                            
        if self.space_group_number_input.text() != self.space_group_number_input.specialValueText():
            params["space_group_number"] = self.space_group_number_input.value()

        if self.n_elements_input.text() != self.n_elements_input.specialValueText():
            n_elements = self.n_elements_input.value()
            params["strictmin"] = n_elements
            params["strictmax"] = n_elements
        return params

    def run_search(self):
        success = False
        self.search_button.setEnabled(False)
        self.status_bar.showMessage("Searching COD…")
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            params = self._search_parameters()
            response = requests.get(
                COD_URL+'/result', params=params, timeout=TIMEOUT
            )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict):
                payload = payload.get("data", payload.get("results", []))
            if not isinstance(payload, list):
                raise ValueError("The server returned an unexpected response.")
            result_count = len(payload)
            self._show_entries(payload[: self.limit_input.value()])
            if result_count > self.limit_input.value():
                self.status_bar.showMessage(
                    f"Found {result_count} entries; displaying the first "
                    f"{self.limit_input.value()}."
                )
            else:
                self.status_bar.showMessage(f"Found {result_count} entries.")
            # self.tabs.setCurrentWidget(self.results_tab)
            success = True
        except (requests.RequestException, ValueError) as error:
            self.status_bar.showMessage(f"Search failed: {error}")
        finally:
            QApplication.restoreOverrideCursor()
            self.search_button.setEnabled(True)
        return success

    def run_search_and_show_results(self):
        if self.run_search():
            self.tabs.setCurrentWidget(self.results_tab)

    @staticmethod
    def _value(entry, *keys):
        for key in keys:
            value = entry.get(key)
            if value is not None:
                if key in ("a", "b", "c", "alpha", "beta", "gamma"):
                    try:
                        return f"{float(value):.4f}"
                    except (ValueError, TypeError):
                        pass
                if key == "formula":
                    elements = value.replace("-", "")
                    return parse_formula(elements)
                return str(value)
        return ""

    def _show_entries(self, entries):
        self.results_table.setSortingEnabled(False)
        self.results_table.setRowCount(len(entries))
        for row, entry in enumerate(entries):
            if not isinstance(entry, dict):
                entry = {"value": entry}
            values = tuple(self._value(entry, key) for key in [field for field, label in self.entry_fields])
            for column, value in enumerate(values):
                item = QTableWidgetItem()
                if re.match(r"^-?\d+\.\d+$", value): # check if float
                    item.setData(Qt.ItemDataRole.DisplayRole,float(value))
                elif value.strip().isdigit():
                    item.setData(Qt.ItemDataRole.DisplayRole,int(value))
                else:
                    item.setText(value)

                self.results_table.setItem(row, column, item)
        self.results_table.setSortingEnabled(True)
        # self.results_table.resizeColumnsToContents()

    def _update_spacegroup_from_number(self, value):
        self.spacegroup_input.blockSignals(True)
        # self.spacegroup_input.setStyleSheet("")
        self.status_bar.showMessage("")
        if value == 0:
            # self.spacegroup_input.clear()
            self.spacegroup_input.setCurrentText("Any")
        else:
            sg_symbol = lookup_space_group(value)
            # index = self.spacegroup_input.findText(sg_symbol)
            self.spacegroup_input.setCurrentText(sg_symbol)
        self.spacegroup_input.blockSignals(False)

    def _update_spacegroup_from_name(self, sg_name):
        # sg_name = self.spacegroup_input.text().strip()
        self.space_group_number_input.blockSignals(True)
        if not sg_name:
            self.space_group_number_input.setValue(0)
            self.space_group_number_input.blockSignals(False)
            return
        for number, name in SPACE_GROUPS.items():
            if name.replace(" ", "") == sg_name.replace(" ", "").lower().capitalize():
                self.space_group_number_input.setValue(number)
                # self.spacegroup_input.setText(name)
                self.space_group_number_input.blockSignals(False)
                # self.spacegroup_input.setStyleSheet("")
                return
        self.space_group_number_input.blockSignals(False)
        # print(sg_name.replace(" ", "").title())
        # self.status_bar.showMessage(f"Warning: '{sg_name}' is not a recognized space group symbol.")
        # self.spacegroup_input.setStyleSheet("color: red;")

    def clear_search(self):
        self.formula_input.clear()
        self.elements_input.clear()
        self.text_input.clear()
        self.journal_input.clear()
        self.spacegroup_input.clear()
        self.space_group_number_input.setValue(self.space_group_number_input.minimum())
        self.year_input.setValue(self.year_input.minimum())
        self.n_elements_input.setValue(self.n_elements_input.minimum())
        self.limit_input.setValue(100)
        self.status_bar.showMessage("Crystallography Open Database: https://www.crystallography.net/cod/")

    def clear_results(self):
        self.results_table.clearContents()

    def clear(self):
        self.clear_search()
        self.clear_results()
        self.tabs.setCurrentIndex(0)
        self.latest_file = None

    def table_double_clicked(self, row, column):
        item = self.results_table.item(row, 0)
        if item:
            entry_id = item.text()
            print(f"Entry id: {entry_id}")
            filename, ok = QFileDialog.getSaveFileName(self, "Save CIF file", f"{entry_id}.cif", "CIF files (*.cif);;All files (*)")
            if ok:
                try:
                    cif_content = self._fetch_cif(entry_id)
                    if not cif_content:
                        raise ValueError(f"No CIF content returned for entry {entry_id}.")
                    self._save_cif_to_file(filename, cif_content)
                    self.status_bar.showMessage(f"Saved CIF file for entry {entry_id} to {filename}.")
                    self.latest_file = filename
                    self.sigFileFetched.emit(filename,cif_content)
                    if self.single_cif:
                        self.done(QDialog.DialogCode.Accepted)
                except Exception as e:
                    self.status_bar.showMessage(f"Failed to fetch or save CIF file for entry {entry_id}: {e}")


    def _fetch_cif(self,cod_id: str) -> str:
        if not cod_id.isdigit():
            raise ValueError("COD ID must contain digits only")

        response = requests.get(f"{COD_URL}/{cod_id}.cif", timeout=10)
        response.raise_for_status()
        return response.text

    def _save_cif_to_file(self, filename: str, cif_content: str):
        with open(filename, "w") as f:
            f.write(cif_content)

    def get_latest_saved_file(self):
        """Return the full path to the latest fetched file"""
        return self.latest_file

    def fetch_cifs(self, modal=True, clear_previous=True):
        """
        Open the fetch dialog (modal or modeless (False)).
        Connect to the sigFileFetched signal to get the file path and content
        whenever a file is fetched or connect to the accepted() signal and 
        get the latest file with the get_latest_file() method.
        """
        if clear_previous:
            self.clear()
        if modal:
            self.open()
        else:
            self.show()

    def fetch_single_cif(self, clear_previous=True):
        """
        Open the dialog to fetch a single cif file (modal dialog) and hide
        the dialog after fetching a file.
        Connect to the sigFileFetched signal to get the file path and content
        whenever a file is fetched or connect to the accepted() signal and 
        get the latest file with the get_latest_file() method.
        """
        self.single_cif = True
        if clear_previous:
            self.clear()
        self.open()
 
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    dialog = CifFetchDialog()
    dialog.fetch_cifs()
    sys.exit(app.exec())


### Notes for developers (and llm's) ###

# Available search parameters:
#     id - a string containing one or more COD IDs separated by a comma (",") or a new line ("\n") symbol. The percent ("%") wild card symbol can be used to specify a range of IDs.
#     smarts - a substructure query in SMILES arbitrary target specification.
#     text - a keyword that must be contained in the metadata of the entry. The metadata search covers data such as the bibliographic information of the associated publication, common and systematic name of the sample compound and the name of the sample mineral.
#     format - the format in which the results will be returned. Supported formats:
#     html - a html web page displaying the list of COD entries.
#     csv - a csv file containing information about the COD entries. The provided information matches the one provided by the COD MySQL database.
#     json - a json file containing information about the COD entries. The provided information matches the one provided by the COD MySQL database.
#     lst - a txt file containing a list of COD IDs.
#     urls - a txt file containing a list of URLs pointing to the COD CIF files.
#     zip - a zip archive containing CIF files. Please note that there is a limit of how many entries can be returned using this format. In case this limit is reached, a html page with an error message is returned instead.
#     count - the number of COD entries that match the search criteria.
#     formula - the empirical chemical formula of the crystal. Chemical element symbols in the formula must be ordered according to the Hill notation and separated by a space symbol, e.g. "C8 H10 N4 O2".
#     el1, el2, ..., el8 - chemical element symbols that must appear in the chemical formula.
#     nel1, nel2, ..., nel4 - chemical element symbols that must not appear in the chemical formula.
#     strictmin, strictmax - the minimum/maximum number of distinct chemical elements that must appear in the chemical formula.
#     spacegroup - the Hermann-Mauguin space group symbol or the superspace group symbol.
#     space_group_number - the space group number as assigned in the International Tables for Crystallography Vol. A.
#     amin, amax - the minimum/maximum value of the lattice parameter a.
#     bmin, bmax - the minimum/maximum value of the lattice parameter b.
#     cmin, cmax - the minimum/maximum value of the lattice parameter c.
#     alpmin, alpmax - the minimum/maximum value of the lattice parameter alpha.
#     betmin, betmax - the minimum/maximum value of the lattice parameter beta.
#     gamin, gamax - the minimum/maximum value of the lattice parameter gamma.
#     vmin, vmax - the minimum/maximum volume of the lattice.
#     minZ, maxZ - the minimum/maximum Z value of the lattice.
#     minZprime, maxZprime - the minimum/maximum Z' value of the lattice.
#     journal - the name of the journal in which the scientific paper describing the crystal structure was published.
#     year - the year of publication of the crystal structure.
#     volume - the volume of the journal where the scientific paper describing the crystal structure was published.
#     issue - the issue of the journal where the scientific paper describing the crystal structure was published.
#     doi - the DOI that links to the online paper in which the crystal structure was published.
#     has_fobs - flag value denoting that entries must have an associated X-ray reflection files (Fobs or Iobs data) in the COD which contain the original reflection intensities used to determine the structures.
#     include_duplicates - flag value denoting that entries that are marked as duplicates of other entries in the COD should not be excluded.
#     include_errors - flag value denoting that entries that are marked as having errors should not be excluded.
#     include_theoretical - flag value denoting that entries that are marked as theoretical should not be excluded.

# Available entry fields:
#     'file', 
#     'a', 'siga', 'b', 'sigb', 'c', 'sigc', 
#     'alpha', 'sigalpha', 'beta', 'sigbeta', 'gamma', 'siggamma', 
#     'vol', 'sigvol', 'celltemp', 'sigcelltemp', 'diffrtemp', 'sigdiffrtemp',
#     'cellpressure', 'sigcellpressure', 'diffrpressure', 'sigdiffrpressure',
#     'thermalhist', 'pressurehist', 'compoundsource', 'nel', 'sg', 'sgHall',
#     'sgNumber', 'commonname', 'chemname', 'mineral', 'formula', 'calcformula',
#     'cellformula', 'Z', 'Zprime', 'acce_code', 'authors', 'title', 'journal', 
#     'year', 'volume', 'issue', 'firstpage', 'lastpage', 'doi', 'method', 
#     'radiation', 'wavelength', 'radType', 'radSymbol', 'Rall', 'Robs', 'Rref',
#     'wRall', 'wRobs', 'wRref', 'RFsqd', 'RI', 'gofall', 'gofobs', 'gofgt', 
#     'gofref', 'duplicateof', 'optimal', 'status', 'flags', 'svnrevision', 
#     'date', 'time', 'onhold'