"""Tests for ProductionRepository."""

import pytest
from database.repositories import ProductionRepository, ProjectRepository, WellRepository


@pytest.fixture
def repos():
    proj = ProjectRepository()
    well = WellRepository()
    prod = ProductionRepository()
    pid = proj.create("Test Prod Project")
    wid = well.create(pid, "Well 1", uwi="TEST-001")
    return prod, wid, pid


class TestProductionRepository:
    def test_create(self, repos):
        prod, wid, _ = repos
        rid = prod.create(wid, "2020-01", 1000, 5000000, 500, 30)
        assert rid > 0

    def test_bulk_create(self, repos):
        prod, wid, _ = repos
        records = [
            (wid, "2020-01", 1000, 5000000, 500, 30),
            (wid, "2020-02", 950, 4800000, 520, 29),
            (wid, "2020-03", 900, 4500000, 480, 31),
        ]
        count = prod.bulk_create(records)
        assert count == 3

    def test_bulk_create_empty(self, repos):
        prod, _, _ = repos
        assert prod.bulk_create([]) == 0

    def test_get_by_well(self, repos):
        prod, wid, _ = repos
        prod.create(wid, "2020-01", 1000, 5000000, 500, 30)
        prod.create(wid, "2020-02", 950, 4800000, 520, 29)
        records = prod.get_by_well(wid)
        assert len(records) == 2
        assert records[0]["date"] == "2020-01"

    def test_get_by_date_range(self, repos):
        prod, wid, _ = repos
        prod.create(wid, "2020-01", 1000, 5000000, 500, 30)
        prod.create(wid, "2020-06", 800, 4000000, 400, 30)
        prod.create(wid, "2020-12", 600, 3000000, 300, 31)
        records = prod.get_by_date_range(wid, "2020-01", "2020-06")
        assert len(records) == 2

    def test_get_cumulative(self, repos):
        prod, wid, _ = repos
        prod.create(wid, "2020-01", 1000, 5000000, 500, 30)
        prod.create(wid, "2020-02", 900, 4000000, 400, 28)
        cum = prod.get_cumulative(wid)
        assert cum["cum_oil"] == pytest.approx(1900)
        assert cum["cum_gas"] == pytest.approx(9000000)
        assert cum["cum_water"] == pytest.approx(900)
        assert cum["cum_days"] == pytest.approx(58)

    def test_get_cumulative_empty(self, repos):
        prod, wid, _ = repos
        cum = prod.get_cumulative(wid)
        assert cum["cum_oil"] == 0

    def test_get_cumulative_by_project(self, repos):
        prod, wid, pid = repos
        prod.create(wid, "2020-01", 1000, 5000000, 500, 30)
        results = prod.get_cumulative_by_project(pid)
        assert len(results) >= 1
        assert results[0]["cum_oil"] == pytest.approx(1000)

    def test_delete_by_well(self, repos):
        prod, wid, _ = repos
        prod.create(wid, "2020-01", 1000, 5000000, 500, 30)
        prod.delete_by_well(wid)
        assert prod.get_by_well(wid) == []
