"""Tests for the drafting-standard profiles (``adapters/solidworks/drawing_profiles.py``)."""

from __future__ import annotations

import pytest

from solidworks_mcp.adapters.solidworks import dimension_layout as lay
from solidworks_mcp.adapters.solidworks import drawing_profiles as prof


class TestEskdScales:
    """The scale series of ГОСТ 2.302."""

    def test_series_is_ordered_largest_first(self) -> None:
        factors = [n / d for n, d in prof.ESKD_SCALES]
        assert factors == sorted(factors, reverse=True)

    @pytest.mark.parametrize(
        "scale", [(2, 1), (2.5, 1), (4, 1), (5, 1), (1, 1), (1, 2), (1, 2.5), (1, 75)]
    )
    def test_gost_scales_are_offered(self, scale) -> None:
        assert scale in prof.ESKD_SCALES

    @pytest.mark.parametrize("scale", [(3, 1), (1.5, 1), (1, 7.5), (1, 12.5), (1, 30)])
    def test_scales_outside_the_gost_series_are_not(self, scale) -> None:
        assert scale not in prof.ESKD_SCALES
        # ...although the ISO profile does use some of them
        assert scale in prof.ISO_SCALES or scale == (1.5, 1)


class TestEskdSheets:
    @pytest.mark.parametrize(
        ("size", "width", "height", "paper"),
        [
            ("A4", 0.210, 0.297, 7),
            ("A3", 0.420, 0.297, 8),
            ("A2", 0.594, 0.420, 9),
            ("A1", 0.841, 0.594, 10),
            ("A0", 1.189, 0.841, 11),
        ],
    )
    def test_paper_sizes(self, size, width, height, paper) -> None:
        sheet = prof.ESKD_PROFILES[size].sheet
        assert (sheet.width, sheet.height, sheet.paper) == (width, height, paper)

    @pytest.mark.parametrize("size", list(prof.ESKD_PROFILES))
    def test_frame_is_20_mm_left_and_5_mm_elsewhere(self, size) -> None:
        p = prof.ESKD_PROFILES[size]
        x0, y0, x1, y1 = p.work_area
        assert x0 == pytest.approx(0.020)
        assert y0 == pytest.approx(0.005)
        assert x1 == pytest.approx(p.sheet.width - 0.005)
        assert y1 == pytest.approx(p.sheet.height - 0.005)

    @pytest.mark.parametrize("size", list(prof.ESKD_PROFILES))
    def test_title_block_is_185_by_55_in_the_frames_lower_right(self, size) -> None:
        p = prof.ESKD_PROFILES[size]
        x0, y0, x1, y1 = p.title_block
        assert (x1 - x0, y1 - y0) == (pytest.approx(0.185), pytest.approx(0.055))
        assert (x1, y0) == (pytest.approx(p.work_area[2]), pytest.approx(0.005))

    @pytest.mark.parametrize("size", list(prof.ESKD_PROFILES))
    def test_notes_and_views_stay_clear_of_the_title_block(self, size) -> None:
        p = prof.ESKD_PROFILES[size]
        assert lay.inside(p.notes_cell, p.work_area)
        assert lay.inside(p.view_zone, p.work_area)
        assert not lay.box_overlap(p.notes_cell, p.title_block, -1e-9)
        assert not lay.box_overlap(p.view_zone, p.title_block, -1e-9)
        assert not lay.box_overlap(p.view_zone, p.notes_cell, -1e-9)

    def test_notes_sit_beside_the_title_block_on_a_wide_sheet(self) -> None:
        p = prof.ESKD_PROFILES["A3"]
        assert p.notes_cell[2] <= p.title_block[0]

    def test_notes_sit_above_the_title_block_on_a4(self) -> None:
        p = prof.ESKD_PROFILES["A4"]
        assert p.notes_cell[1] >= p.title_block[3]

    def test_the_profile_follows_eskd_conventions(self) -> None:
        p = prof.ESKD_PROFILES["A3"]
        assert p.first_angle and p.projection == prof.FIRST_ANGLE
        assert p.captions == {} and p.caption_strip == 0
        assert p.notes_heading == "Технические требования"
        assert not p.material_in_notes and not p.uppercase_notes
        assert p.sheet_format_name == ""
        assert p.date_format == "%d.%m.%Y"
        assert not p.revision_in_number


class TestIsoProfile:
    def test_keeps_the_original_a3_values(self) -> None:
        p = prof.ISO_A3
        assert not p.first_angle
        assert (p.sheet.width, p.sheet.height) == (0.420, 0.297)
        assert p.work_area == (0.015, 0.015, 0.405, 0.282)
        assert p.title_block == (0.218, 0.008, 0.412, 0.072)
        assert p.sheet_format_name == "a3 - iso.slddrt"
        assert p.captions["front"] == "FRONT ELEVATION"
        assert p.cells["notes"] == (0.015, 0.015, 0.215, 0.075)


class TestCells:
    def test_third_angle_default_cells(self) -> None:
        zone = prof.ISO_A3.view_zone
        p = prof.DrawingProfile(
            name="X",
            sheet=prof.ISO_A3.sheet,
            projection=prof.THIRD_ANGLE,
            scales=((1, 1),),
            work_area=zone,
            title_block=(0, 0, 0.01, 0.01),
            notes_cell=(0, 0, 0.01, 0.01),
            view_zone=zone,
        )
        cells = p.cells
        assert cells["front"][1] == zone[1] and cells["plan"][3] == zone[3]
        assert cells["notes"] == p.notes_cell

    def test_first_angle_default_cells_put_the_plan_below_the_front(self) -> None:
        p = prof.ESKD_PROFILES["A3"]
        cells = p.cells
        assert cells["front"][1] > cells["plan"][1]
        assert cells["side"][0] > cells["front"][0]
        assert cells["iso"][2] == p.view_zone[2]


class TestGetProfile:
    @pytest.mark.parametrize("name", ["ESKD", "eskd", "ЕСКД", "ГОСТ", "gost", " Eskd "])
    def test_eskd_aliases(self, name) -> None:
        assert prof.get_profile(name, "A3").name == "ESKD"

    @pytest.mark.parametrize("name", ["ISO", "iso", "", None])
    def test_iso_is_the_default(self, name) -> None:
        assert prof.get_profile(name, "A3") is prof.ISO_A3

    def test_sizes_are_case_insensitive_and_default_to_a3(self) -> None:
        assert prof.get_profile("ESKD", "a2").sheet.name == "A2"
        assert prof.get_profile("ESKD", "").sheet.name == "A3"

    def test_iso_only_offers_a3(self) -> None:
        with pytest.raises(ValueError, match="only offers sheet size A3"):
            prof.get_profile("ISO", "A4")

    def test_eskd_rejects_an_unknown_size(self) -> None:
        with pytest.raises(ValueError, match="A4, A3, A2, A1, A0"):
            prof.get_profile("ESKD", "B5")

    def test_unknown_standard(self) -> None:
        with pytest.raises(ValueError, match="Unknown drawing standard 'DIN'"):
            prof.get_profile("DIN")


class TestPropertyNames:
    def test_eskd_defaults(self) -> None:
        names = prof.merge_property_names(prof.ESKD_PROFILES["A3"], None)
        assert names["designation"] == "Обозначение"
        assert names["title"] == "Наименование"

    def test_overrides_replace_and_empty_values_are_ignored(self) -> None:
        names = prof.merge_property_names(
            prof.ESKD_PROFILES["A3"], {"title": "Name", "mass": ""}
        )
        assert names["title"] == "Name"
        assert names["mass"] == "Масса"

    def test_unknown_field_is_named(self) -> None:
        with pytest.raises(ValueError, match="Unknown title-block field.*colour"):
            prof.merge_property_names(prof.ISO_A3, {"colour": "x"})

    def test_fit_fields(self) -> None:
        assert prof.fit_fields(prof.ISO_PROPERTY_NAMES) == {
            "SW-File Name": "drawing number",
            "Description": "title",
        }
        assert prof.fit_fields(prof.ESKD_PROPERTY_NAMES) == {
            "Обозначение": "drawing number",
            "Наименование": "title",
        }
        assert prof.fit_fields({"designation": "Code"}) == {"Code": "drawing number"}
