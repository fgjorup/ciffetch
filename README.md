# ciffetch

`ciffetch` is a PyQt6 dialog for searching the [Crystallography Open Database
(COD)](https://www.crystallography.net/cod/) and retrieving crystal structure
data as CIF files. It can be run as a standalone application or embedded in
another PyQt application.

Search using chemical formula or required elements, space group, lattice
parameter ranges, text, journal, and publication year. Matching entries appear
in a sortable results table; double-click an entry to choose where to save its
CIF file.

## Requirements

- Python 3
- PyQt6
- requests

Install the dependencies with:

```bash
python -m pip install PyQt6 requests
```

## Run the application

```bash
python ciffetch.py
```

Enter search criteria in the dialog and run the search. Double-click a result
to fetch its CIF file and save it to a chosen location.

## Use from a PyQt application

Create a `QApplication`, instantiate `CifFetchDialog`, and call
`fetch_cifs()`. The `sigFileFetched` signal provides the saved file path and
CIF text when a file has been fetched:

```python
import sys

from PyQt6.QtWidgets import QApplication
from ciffetch import CifFetchDialog

app = QApplication(sys.argv)
dialog = CifFetchDialog()
dialog.sigFileFetched.connect(
    lambda path, cif_content: print(f"Saved {path} ({len(cif_content)} characters)")
)
dialog.fetch_cifs()
sys.exit(app.exec())
```

For single-file selection, call `dialog.fetch_single_cif()` instead.
`CifFetchDialog` also emits the standard `accepted()` signal after a file is
fetched in single-file mode. The `get_latest_saved_file()` method returns the
most recently saved file path.

## Acknowledgment and data

This application is made possible by the people behind the
[Crystallography Open Database](https://www.crystallography.net/cod/). COD data
and the database are dedicated to the public domain under CC0. Users of COD
data should acknowledge the original authors of the structural data and cite
the relevant source information provided with each entry.

## License

The `ciffetch` software is licensed under the
[GNU General Public License, version 3](LICENSE). This software license is
separate from the license and attribution requirements for data retrieved from
COD.
