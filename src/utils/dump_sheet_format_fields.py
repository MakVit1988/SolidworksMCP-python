"""Print the fields of a SolidWorks sheet format (a ``.slddrt`` title block).

``generate_drawing_package`` fills a sheet format's title block through custom
properties, so it needs the property names the format reads ("Обозначение",
"Наименование" and so on). A ``.slddrt`` is a closed binary file; this script
opens it in the running SolidWorks and lists every note on the format with the
property it is linked to, e.g. ``$PRPSHEET:"Наименование"``.

It only reads. It makes a new, empty drawing on the format, edits the sheet
format to read the notes, and closes the drawing without saving.

Usage (SolidWorks must be running)::

    .\\.venv\\Scripts\\python.exe src\\utils\\dump_sheet_format_fields.py `
        "C:\\ProgramData\\SOLIDWORKS\\SOLIDWORKS 2024\\lang\\russian\\sheetformat\\A3-A-1.slddrt"

The list is printed and also written, as UTF-8, to ``sheet_format_fields.txt``
in the current folder (``--out`` changes that); send that file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Make the package importable when this script is invoked directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import win32com.client  # noqa: E402
from win32com.client import dynamic  # noqa: E402

from solidworks_mcp.adapters import sw_type_info  # noqa: E402

# swUserPreferenceStringValue_e: the default drawing template.
_SW_DEFAULT_TEMPLATE_DRAWING = 10
# swDwgPaperSizes_e: user defined; swDwgTemplates_e: custom.
_PAPER_USER_DEFINED = 12
_TEMPLATE_CUSTOM = 12
_DRAWING = 3

#: Most notes read from one format; a guard against a broken note chain.
_MAX_NOTES = 500


def _try(operation, default=None):
    """The operation's result, or ``default`` when COM raises."""
    try:
        return operation()
    except Exception:
        return default


def _connect():
    """The running SolidWorks, with its methods flagged for late binding."""
    try:
        raw = win32com.client.GetActiveObject("SldWorks.Application")
        app = dynamic.Dispatch(raw._oleobj_)
    except Exception:
        print("SolidWorks is not running. Start it and run this again.")
        raise SystemExit(2) from None
    sw_type_info.flag_methods(app, "ISldWorks")
    return app


def _notes(drawing) -> list[dict[str, object]]:
    """Every note of the sheet format being edited: text, link and position."""
    view = _try(lambda: sw_type_info.flagged(drawing.GetFirstView(), "IView"))
    note = _try(lambda: view.GetFirstNote())
    found: list[dict[str, object]] = []
    while note is not None and len(found) < _MAX_NOTES:
        n = sw_type_info.flagged(note, "INote")
        extent = _try(lambda n=n: n.GetExtent())
        x = y = 0.0
        if isinstance(extent, (list, tuple)) and len(extent) >= 6:
            x, y = float(extent[0]), float(extent[1])
        found.append(
            {
                "text": str(_try(lambda n=n: n.GetText(), "") or ""),
                "link": str(_try(lambda n=n: n.PropertyLinkedText, "") or ""),
                "x_mm": round(x * 1000, 1),
                "y_mm": round(y * 1000, 1),
            }
        )
        note = _try(lambda n=n: n.GetNext())
    return found


def dump_fields(sheet_format: Path, width: float, height: float) -> list[str]:
    """Open ``sheet_format`` on a scratch drawing and describe its notes.

    Args:
        sheet_format: The ``.slddrt`` to read.
        width: Sheet width in metres.
        height: Sheet height in metres.

    Returns:
        list[str]: One line per note, top of the sheet first.
    """
    app = _connect()
    template = _try(
        lambda: app.GetUserPreferenceStringValue(_SW_DEFAULT_TEMPLATE_DRAWING)
    )
    if not template:
        print(
            "No default drawing template is set in SolidWorks "
            "(Tools > Options > File Locations > Document Templates)."
        )
        raise SystemExit(2)
    doc = app.NewDocument(template, _PAPER_USER_DEFINED, width, height)
    if doc is None:
        print(f"SolidWorks could not make a drawing from {template}")
        raise SystemExit(2)
    drawing = sw_type_info.flagged(doc, "IDrawingDoc")
    sw_type_info.flag_doc(doc, _DRAWING)
    title = _try(lambda: doc.GetTitle())
    try:
        ok = drawing.SetupSheet5(
            "Sheet1",
            _PAPER_USER_DEFINED,
            _TEMPLATE_CUSTOM,
            1.0,
            1.0,
            True,
            str(sheet_format),
            width,
            height,
            "Default",
            True,
        )
        if not ok:
            print(f"SolidWorks refused the sheet format {sheet_format}")
            raise SystemExit(2)
        drawing.EditTemplate()
        try:
            notes = _notes(drawing)
        finally:
            _try(lambda: drawing.EditSheet())
    finally:
        if title:
            _try(lambda: app.CloseDoc(title))
    notes.sort(key=lambda n: (-float(n["y_mm"]), float(n["x_mm"])))
    lines = [f"{'x mm':>7} {'y mm':>7}  {'linked to':<40} text"]
    for n in notes:
        link = n["link"] or "-"
        lines.append(f"{n['x_mm']:>7} {n['y_mm']:>7}  {link:<40} {n['text']}")
    return lines


def main(argv: list[str] | None = None) -> int:
    """Print and save a sheet format's notes."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("sheet_format", type=Path, help="Path of the .slddrt file")
    parser.add_argument("--width-mm", type=float, default=420.0)
    parser.add_argument("--height-mm", type=float, default=297.0)
    parser.add_argument("--out", type=Path, default=Path("sheet_format_fields.txt"))
    args = parser.parse_args(argv)

    if not args.sheet_format.is_file():
        print(f"ERROR: file not found: {args.sheet_format}")
        return 2
    lines = dump_fields(
        args.sheet_format.resolve(), args.width_mm / 1000, args.height_mm / 1000
    )
    # The console may not show Cyrillic; the file always does.
    sys.stdout.reconfigure(errors="replace")
    print("\n".join(lines))
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8-sig")
    print(f"\nWritten to {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
