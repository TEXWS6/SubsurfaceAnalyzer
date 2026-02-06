"""Tests for CompletionsRepository."""

import pytest
from database.repositories import CompletionsRepository, ProjectRepository, WellRepository


@pytest.fixture
def repos():
    proj = ProjectRepository()
    well = WellRepository()
    comp = CompletionsRepository()
    pid = proj.create("Test Comp Project")
    wid = well.create(pid, "Well 1", uwi="COMP-001")
    return comp, wid


class TestCompletionsRepository:
    def test_create(self, repos):
        comp, wid = repos
        cid = comp.create(wid, perf_top=7800, perf_base=8100,
                          completion_date="2020-01-15",
                          treatment_type="ACID FRAC")
        assert cid > 0

    def test_bulk_create(self, repos):
        comp, wid = repos
        records = [
            (wid, 7800, 8100, "2020-01-15", "ACID FRAC"),
            (wid, 8100, 8400, "2020-01-15", "PLUG AND PERF"),
            (wid, 8400, 8700, "2020-01-20", "SLIDING SLEEVE"),
        ]
        count = comp.bulk_create(records)
        assert count == 3

    def test_bulk_create_empty(self, repos):
        comp, _ = repos
        assert comp.bulk_create([]) == 0

    def test_get_by_well(self, repos):
        comp, wid = repos
        comp.create(wid, perf_top=7800, perf_base=8100)
        comp.create(wid, perf_top=8100, perf_base=8400)
        records = comp.get_by_well(wid)
        assert len(records) == 2
        # Should be ordered by perf_top
        assert records[0]["perf_top"] == pytest.approx(7800)
        assert records[1]["perf_top"] == pytest.approx(8100)

    def test_delete(self, repos):
        comp, wid = repos
        cid = comp.create(wid, perf_top=7800, perf_base=8100)
        comp.delete(cid)
        assert comp.get_by_well(wid) == []

    def test_delete_by_well(self, repos):
        comp, wid = repos
        comp.create(wid, perf_top=7800, perf_base=8100)
        comp.create(wid, perf_top=8100, perf_base=8400)
        comp.delete_by_well(wid)
        assert comp.get_by_well(wid) == []
