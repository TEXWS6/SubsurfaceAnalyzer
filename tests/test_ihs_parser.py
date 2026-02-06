"""Tests for IHS .297/.298 parser."""

import pytest
from services.ihs_parser import IHSParser, _safe_float, _parse_fixed_width


# Sample .297 content (fixed-width, 195+ chars per line)
SAMPLE_297 = """\
42-123-45678  TEST WELL ONE                           ACME OIL CO                     PERMIAN BASIN       TX ECTOR                  31.95000  -102.10000  3200  8500 COMP 20200115 WOLFCAMP
42-123-99999  TEST WELL TWO                           BETA ENERGY INC                 DELAWARE BASIN      TX REEVES                 31.80000  -103.50000  3450  9200 DRIL 20210601 BONE SPRING
"""

# Sample .298 content (fixed-width)
SAMPLE_298 = """\
42-123-45678  202001   15000    25000000     8000  30
42-123-45678  202002   14500    24000000     7500  29
42-123-45678  202003   13800    23000000     7200  31
42-123-99999  202001   12000    20000000     5000  30
"""

# Sample .297 completions
SAMPLE_297_COMP = """\
42-123-45678  7800   8100   20200115 ACID FRAC
42-123-45678  8100   8400   20200115 PLUG AND PERF
42-123-99999  8500   8900   20210601 SLIDING SLEEVE
"""


class TestParse297:
    def test_parse_wells(self):
        wells = IHSParser.parse_297(SAMPLE_297)
        assert len(wells) == 2
        assert wells[0]["uwi"] == "42-123-45678"
        assert wells[0]["well_name"] == "TEST WELL ONE"
        assert wells[0]["state"] == "TX"

    def test_parse_coordinates(self):
        wells = IHSParser.parse_297(SAMPLE_297)
        assert wells[0]["latitude"] == pytest.approx(31.95, abs=0.01)
        assert wells[0]["longitude"] == pytest.approx(-102.1, abs=0.01)

    def test_parse_kb_td(self):
        wells = IHSParser.parse_297(SAMPLE_297)
        assert wells[0]["kb_elev"] == pytest.approx(3200, abs=1)
        assert wells[0]["td"] == pytest.approx(8500, abs=1)

    def test_parse_empty(self):
        wells = IHSParser.parse_297("")
        assert wells == []

    def test_skip_comments(self):
        content = "# Comment line\n" + SAMPLE_297
        wells = IHSParser.parse_297(content)
        assert len(wells) == 2


class TestParse298:
    def test_parse_production(self):
        records = IHSParser.parse_298(SAMPLE_298)
        assert len(records) == 4

    def test_date_format(self):
        records = IHSParser.parse_298(SAMPLE_298)
        assert records[0]["date"] == "2020-01"

    def test_volumes(self):
        records = IHSParser.parse_298(SAMPLE_298)
        assert records[0]["oil_vol"] == pytest.approx(15000, abs=1)
        assert records[0]["gas_vol"] == pytest.approx(25000000, abs=1)
        assert records[0]["water_vol"] == pytest.approx(8000, abs=1)
        assert records[0]["days_produced"] == pytest.approx(30, abs=1)

    def test_uwi_match(self):
        records = IHSParser.parse_298(SAMPLE_298)
        uwis = set(r["uwi"] for r in records)
        assert "42-123-45678" in uwis
        assert "42-123-99999" in uwis

    def test_parse_empty(self):
        assert IHSParser.parse_298("") == []


class TestParse297Completions:
    def test_parse_completions(self):
        completions = IHSParser.parse_297_completions(SAMPLE_297_COMP)
        assert len(completions) == 3

    def test_perf_depths(self):
        completions = IHSParser.parse_297_completions(SAMPLE_297_COMP)
        assert completions[0]["perf_top"] == pytest.approx(7800, abs=1)
        assert completions[0]["perf_base"] == pytest.approx(8100, abs=1)

    def test_treatment_type(self):
        completions = IHSParser.parse_297_completions(SAMPLE_297_COMP)
        assert "ACID FRAC" in completions[0]["treatment_type"]


class TestImport297ToProject:
    def test_import_creates_wells(self):
        from database.repositories import WellRepository, ProjectRepository
        proj_repo = ProjectRepository()
        well_repo = WellRepository()

        pid = proj_repo.create("Test IHS Project")
        wells_data = IHSParser.parse_297(SAMPLE_297)
        result = IHSParser.import_297_to_project(wells_data, pid, well_repo)

        assert result["created"] == 2
        assert result["skipped"] == 0

    def test_import_deduplicates(self):
        from database.repositories import WellRepository, ProjectRepository
        proj_repo = ProjectRepository()
        well_repo = WellRepository()

        pid = proj_repo.create("Test Dedup")
        wells_data = IHSParser.parse_297(SAMPLE_297)
        IHSParser.import_297_to_project(wells_data, pid, well_repo)
        result = IHSParser.import_297_to_project(wells_data, pid, well_repo)

        assert result["created"] == 0
        assert result["skipped"] == 2


class TestSafeFloat:
    def test_valid(self):
        assert _safe_float("123.45") == pytest.approx(123.45)

    def test_with_commas(self):
        assert _safe_float("1,234.5") == pytest.approx(1234.5)

    def test_empty(self):
        assert _safe_float("") is None

    def test_dash(self):
        assert _safe_float("-") is None

    def test_embedded_number(self):
        assert _safe_float("FT 150.0") == pytest.approx(150.0)
