"""Drafting-standard profiles for the standard drawing generator.

A :class:`DrawingProfile` holds everything that differs between drafting
standards: the sheet and its frame, the title-block area, the projection
method, the permitted scales, view captions and the standard notes. The
generator in ``drawing_standard.py`` reads these values instead of module
constants, so one code path serves every standard.

Two standards are defined:

* ``ISO`` - the original A3 sheet, third-angle projection, SolidWorks'
  ``a3 - iso`` sheet format.
* ``ESKD`` - the Russian unified system for design documentation (ЕСКД):

  - sheet sizes A4-A0 (ГОСТ 2.301) with a frame 20 mm from the left edge
    and 5 mm from the others;
  - the first-angle projection method (ГОСТ 2.305);
  - the scale series of ГОСТ 2.302;
  - the form 1 title block of ГОСТ 2.104, 185 x 55 mm in the lower right
    corner of the frame;
  - a "Технические требования" block (ГОСТ 2.316).

All lengths are metres, as in the SolidWorks API. Boxes are
``(x0, y0, x1, y1)`` from the sheet's lower-left corner.
"""

from __future__ import annotations

from dataclasses import dataclass, field

Box = tuple[float, float, float, float]

FIRST_ANGLE = "first_angle"
THIRD_ANGLE = "third_angle"

#: Logical title-block fields a profile maps onto SolidWorks property names.
FIELD_KEYS = (
    "title",
    "designation",
    "material",
    "mass",
    "author",
    "date",
    "revision",
    "company",
)

#: Fields that live on the drawing; the others are written into the model.
DRAWING_FIELD_KEYS = ("author", "date", "revision", "company")

# swDwgPaperSizes_e (swconst.tlb)
_PAPER_A4_VERTICAL = 7
_PAPER_A3 = 8
_PAPER_A2 = 9
_PAPER_A1 = 10
_PAPER_A0 = 11


@dataclass(frozen=True)
class SheetSpec:
    """One paper size.

    Attributes:
        name: ``"A3"`` etc.
        paper: ``swDwgPaperSizes_e`` value for ``SetupSheet5``.
        width: Sheet width in metres.
        height: Sheet height in metres.
    """

    name: str
    paper: int
    width: float
    height: float


@dataclass(frozen=True)
class DrawingProfile:
    """Everything the generator takes from the drafting standard.

    Attributes:
        name: ``"ISO"`` or ``"ESKD"``.
        sheet: The paper size.
        projection: ``"first_angle"`` or ``"third_angle"``.
        scales: Permitted sheet scales as ``(num, den)``, largest first.
        work_area: Where views and dimensions may go (inside the frame).
        title_block: The title block's area.
        notes_cell: The cell for the notes block.
        view_zone: The area the four view cells share.
        captions: Role -> view caption; a role without one is not captioned.
        caption_strip: Height reserved under a view for its caption.
        notes_heading: First line of the notes block.
        standard_notes: Lines every drawing gets, after the material line.
        material_in_notes: Whether the material is the first note line.
        uppercase_notes: Whether note lines are shown in capitals.
        sheet_format_name: Default sheet format file, or ``""`` when the
            caller must name one. ЕСКД follows SolidWorks' Russian formats:
            ``A3-A-1.slddrt`` is A3, landscape (А), form 1 (first sheet).
        property_names: Logical field -> SolidWorks custom property name.
        date_format: ``strftime`` pattern for the drawn date.
        revision_in_number: Whether the default drawing number carries the
            revision (``MODEL-RevA-01``) or is just the model name.
        fixed_cells: Cells to use as they are when nothing fits; the four
            quarters of ``view_zone`` when empty.
    """

    name: str
    sheet: SheetSpec
    projection: str
    scales: tuple[tuple[float, float], ...]
    work_area: Box
    title_block: Box
    notes_cell: Box
    view_zone: Box
    captions: dict[str, str] = field(default_factory=dict)
    caption_strip: float = 0.0
    notes_heading: str = "NOTES"
    standard_notes: tuple[str, ...] = ()
    material_in_notes: bool = True
    uppercase_notes: bool = True
    sheet_format_name: str = ""
    property_names: dict[str, str] = field(default_factory=dict)
    date_format: str = "%d %b %Y"
    revision_in_number: bool = True
    fixed_cells: dict[str, Box] = field(default_factory=dict)

    @property
    def first_angle(self) -> bool:
        """Whether the profile uses first-angle projection."""
        return self.projection == FIRST_ANGLE

    @property
    def cells(self) -> dict[str, Box]:
        """The default cell of each role, used when nothing fits."""
        if self.fixed_cells:
            return dict(self.fixed_cells)
        zx0, zy0, zx1, zy1 = self.view_zone
        xm, ym = (zx0 + zx1) / 2, (zy0 + zy1) / 2
        if self.first_angle:
            grid = {
                "front": (zx0, ym, xm, zy1),
                "side": (xm, ym, zx1, zy1),
                "plan": (zx0, zy0, xm, ym),
                "iso": (xm, zy0, zx1, ym),
            }
        else:
            grid = {
                "front": (zx0, zy0, xm, ym),
                "side": (xm, zy0, zx1, ym),
                "plan": (zx0, ym, xm, zy1),
                "iso": (xm, ym, zx1, zy1),
            }
        return {**grid, "notes": self.notes_cell}


#: ГОСТ 2.302: natural size, enlargement and reduction scales, largest first.
ESKD_SCALES: tuple[tuple[float, float], ...] = (
    (100, 1), (50, 1), (40, 1), (20, 1), (10, 1), (5, 1), (4, 1), (2.5, 1),
    (2, 1), (1, 1),
    (1, 2), (1, 2.5), (1, 4), (1, 5), (1, 10), (1, 15), (1, 20), (1, 25),
    (1, 40), (1, 50), (1, 75), (1, 100), (1, 200), (1, 400), (1, 500),
    (1, 800), (1, 1000),
)  # fmt: skip

#: Scales of the original ISO A3 profile, largest first.
ISO_SCALES: tuple[tuple[float, float], ...] = (
    (5, 1), (4, 1), (3, 1), (2.5, 1), (2, 1), (1.5, 1), (1, 1),
    (1, 2), (1, 2.5), (1, 4), (1, 5), (1, 7.5), (1, 10), (1, 12.5),
    (1, 15), (1, 20), (1, 25), (1, 30), (1, 40), (1, 50), (1, 60),
    (1, 75), (1, 100),
)  # fmt: skip

ISO_PROPERTY_NAMES = {
    "title": "Description",
    "material": "Material",
    "mass": "Weight",
    "author": "DrawnBy",
    "date": "DrawnDate",
    "revision": "Revision",
    "company": "COMPANYNAME",
}

#: Property names Russian sheet formats usually read. A format that names
#: them differently is mapped with the ``title_block_fields`` argument.
ESKD_PROPERTY_NAMES = {
    "title": "Наименование",
    "designation": "Обозначение",
    "material": "Материал",
    "mass": "Масса",
    "author": "Разработал",
    "date": "Дата",
    "revision": "Изм.",
    "company": "Организация",
}

ISO_A3 = DrawingProfile(
    name="ISO",
    sheet=SheetSpec("A3", _PAPER_A3, 0.420, 0.297),
    projection=THIRD_ANGLE,
    scales=ISO_SCALES,
    work_area=(0.015, 0.015, 0.405, 0.282),
    title_block=(0.218, 0.008, 0.412, 0.072),
    notes_cell=(0.015, 0.015, 0.215, 0.075),
    view_zone=(0.015, 0.075, 0.405, 0.282),
    captions={
        "front": "FRONT ELEVATION",
        "plan": "PLAN",
        "side": "SIDE ELEVATION",
        "iso": "ISOMETRIC",
    },
    caption_strip=0.009,
    notes_heading="NOTES",
    standard_notes=(
        "ALL DIMENSIONS IN MILLIMETRES",
        "THIRD ANGLE PROJECTION",
        "REMOVE ALL BURRS AND SHARP EDGES",
    ),
    material_in_notes=True,
    uppercase_notes=True,
    sheet_format_name="a3 - iso.slddrt",
    property_names=ISO_PROPERTY_NAMES,
    fixed_cells={
        "front": (0.015, 0.075, 0.215, 0.178),
        "side": (0.215, 0.075, 0.405, 0.178),
        "plan": (0.015, 0.178, 0.215, 0.282),
        "iso": (0.215, 0.178, 0.405, 0.282),
        "notes": (0.015, 0.015, 0.215, 0.075),
    },
)

# ГОСТ 2.104 form 1: 185 x 55 mm, lower right corner of the frame.
_FRAME_LEFT = 0.020
_FRAME_OTHER = 0.005
_TITLE_W = 0.185
_TITLE_H = 0.055
_ZONE_GAP = 0.002
#: Narrowest notes cell worth placing beside the title block.
_MIN_NOTES_W = 0.080
_NOTES_ABOVE_H = 0.040

#: ГОСТ 2.316 technical requirements. A reviewer should confirm these suit
#: the product; callers add their own lines with ``notes``.
ESKD_STANDARD_NOTES = (
    "Неуказанные предельные отклонения размеров по ГОСТ 30893.1-m.",
    "Острые кромки притупить.",
)

ESKD_SHEETS: dict[str, SheetSpec] = {
    "A4": SheetSpec("A4", _PAPER_A4_VERTICAL, 0.210, 0.297),
    "A3": SheetSpec("A3", _PAPER_A3, 0.420, 0.297),
    "A2": SheetSpec("A2", _PAPER_A2, 0.594, 0.420),
    "A1": SheetSpec("A1", _PAPER_A1, 0.841, 0.594),
    "A0": SheetSpec("A0", _PAPER_A0, 1.189, 0.841),
}


def eskd_format_name(sheet: SheetSpec) -> str:
    """The Russian sheet format for a paper size, form 1: ``A3-A-1.slddrt``.

    SolidWorks' Russian ``sheetformat`` folder names its formats
    ``<size>-<А|P>-<form>.slddrt``: А is landscape, P portrait (A4 is only
    portrait), form 1 is the first sheet's title block.
    """
    orientation = "A" if sheet.width > sheet.height else "P"
    return f"{sheet.name}-{orientation}-1.slddrt"


def _eskd(sheet: SheetSpec) -> DrawingProfile:
    """The ЕСКД profile for one paper size (form 1 title block, ГОСТ 2.104)."""
    w, h = sheet.width, sheet.height
    right = w - _FRAME_OTHER
    work = (_FRAME_LEFT, _FRAME_OTHER, right, h - _FRAME_OTHER)
    title = (right - _TITLE_W, _FRAME_OTHER, right, _FRAME_OTHER + _TITLE_H)
    beside = title[0] - _FRAME_OTHER - _FRAME_LEFT
    if beside >= _MIN_NOTES_W:
        notes = (
            _FRAME_LEFT,
            _FRAME_OTHER,
            title[0] - _FRAME_OTHER,
            title[3] + _ZONE_GAP,
        )
        zone_y0 = notes[3]
    else:  # A4: the title block spans the frame, so the notes sit above it
        notes = (
            _FRAME_LEFT,
            title[3] + _ZONE_GAP,
            right,
            title[3] + _ZONE_GAP + _NOTES_ABOVE_H,
        )
        zone_y0 = notes[3]
    return DrawingProfile(
        name="ESKD",
        sheet=sheet,
        projection=FIRST_ANGLE,
        scales=ESKD_SCALES,
        work_area=work,
        title_block=title,
        notes_cell=notes,
        view_zone=(work[0], zone_y0, work[2], work[3]),
        captions={},
        caption_strip=0.0,
        notes_heading="Технические требования",
        standard_notes=ESKD_STANDARD_NOTES,
        material_in_notes=False,
        uppercase_notes=False,
        sheet_format_name=eskd_format_name(sheet),
        property_names=ESKD_PROPERTY_NAMES,
        date_format="%d.%m.%Y",
        revision_in_number=False,
    )


ESKD_PROFILES: dict[str, DrawingProfile] = {
    name: _eskd(sheet) for name, sheet in ESKD_SHEETS.items()
}

_STANDARD_ALIASES = {
    "ISO": "ISO",
    "ESKD": "ESKD",
    "ЕСКД": "ESKD",
    "GOST": "ESKD",
    "ГОСТ": "ESKD",
}


def standard_name(standard: str) -> str:
    """Canonical standard name (``"ISO"`` or ``"ESKD"``).

    Raises:
        ValueError: The standard is not one of the known names.
    """
    key = (standard or "ISO").strip().upper()
    try:
        return _STANDARD_ALIASES[key]
    except KeyError:
        raise ValueError(
            f"Unknown drawing standard '{standard}'; use ISO or ESKD (ЕСКД)"
        ) from None


def get_profile(standard: str = "ISO", sheet_size: str = "A3") -> DrawingProfile:
    """The profile for a standard and paper size.

    Args:
        standard: ``ISO`` or ``ESKD`` (``ЕСКД``, ``GOST`` and ``ГОСТ`` also work).
        sheet_size: ``A3`` for ISO; ``A4``-``A0`` for ESKD.

    Raises:
        ValueError: Unknown standard, or a size the standard does not offer.
    """
    name = standard_name(standard)
    size = (sheet_size or "A3").strip().upper()
    if name == "ISO":
        if size != "A3":
            raise ValueError("The ISO profile only offers sheet size A3")
        return ISO_A3
    if size not in ESKD_PROFILES:
        raise ValueError(
            f"Sheet size '{sheet_size}' is not available for ESKD; "
            f"use one of {', '.join(ESKD_PROFILES)}"
        )
    return ESKD_PROFILES[size]


def merge_property_names(
    profile: DrawingProfile, overrides: dict[str, str] | None
) -> dict[str, str]:
    """The profile's property names with the caller's overrides applied.

    Args:
        profile: The drafting profile.
        overrides: Logical field -> the property name the caller's sheet
            format reads, for example ``{"title": "Name"}``.

    Raises:
        ValueError: An override names a field that does not exist.
    """
    unknown = sorted(set(overrides or {}) - set(FIELD_KEYS))
    if unknown:
        raise ValueError(
            f"Unknown title-block field(s) {', '.join(unknown)}; "
            f"use {', '.join(FIELD_KEYS)}"
        )
    return {
        **profile.property_names,
        **{k: v for k, v in (overrides or {}).items() if v},
    }


def fit_fields(names: dict[str, str]) -> dict[str, str]:
    """Title-block fields shrunk to fit their boxes: property name -> label.

    The drawing number and the title are the two that can run over a box.
    ISO shows the drawing number through ``SW-File Name``; a profile with a
    ``designation`` property shows that instead.
    """
    number = names.get("designation", "SW-File Name")
    fields = {number: "drawing number"}
    if "title" in names:
        fields[names["title"]] = "title"
    return fields
