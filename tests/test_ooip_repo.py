"""Tests for OOIPRepository."""

import json
import pytest
from database.repositories import OOIPRepository, ProjectRepository, WellRepository


@pytest.fixture
def repos():
    proj = ProjectRepository()
    well = WellRepository()
    ooip = OOIPRepository()
    pid = proj.create("Test OOIP Project")
    wid = well.create(pid, "Well 1", uwi="OOIP-001")
    return ooip, wid, pid


class TestOOIPRepository:
    def test_save_deterministic(self, repos):
        ooip, wid, pid = repos
        rid = ooip.save(
            well_id=wid, project_id=pid,
            formation="WOLFCAMP", method="deterministic",
            ooip=500000, ogip=None,
            parameters={"area": 40, "h": 20, "phi": 0.15},
        )
        assert rid > 0

    def test_save_monte_carlo(self, repos):
        ooip, wid, pid = repos
        rid = ooip.save(
            well_id=wid, project_id=pid,
            formation="WOLFCAMP", method="monte_carlo",
            ooip=600000,
            parameters={"p10": 300000, "p50": 600000, "p90": 900000},
        )
        assert rid > 0

    def test_get_by_well(self, repos):
        ooip, wid, pid = repos
        ooip.save(well_id=wid, project_id=pid, formation="A", ooip=100)
        ooip.save(well_id=wid, project_id=pid, formation="B", ooip=200)
        results = ooip.get_by_well(wid)
        assert len(results) == 2

    def test_get_by_project(self, repos):
        ooip, wid, pid = repos
        ooip.save(well_id=wid, project_id=pid, formation="A", ooip=100)
        results = ooip.get_by_project(pid)
        assert len(results) == 1

    def test_get_by_id(self, repos):
        ooip, wid, pid = repos
        rid = ooip.save(
            well_id=wid, project_id=pid,
            formation="WOLF", method="deterministic",
            ooip=500000,
            parameters={"area": 40},
        )
        result = ooip.get_by_id(rid)
        assert result is not None
        assert result["formation"] == "WOLF"
        assert result["ooip"] == pytest.approx(500000)
        assert result["parameters"]["area"] == 40

    def test_get_by_id_not_found(self, repos):
        ooip, _, _ = repos
        assert ooip.get_by_id(99999) is None

    def test_delete(self, repos):
        ooip, wid, pid = repos
        rid = ooip.save(well_id=wid, project_id=pid, ooip=100)
        ooip.delete(rid)
        assert ooip.get_by_id(rid) is None

    def test_json_parameters_roundtrip(self, repos):
        ooip, wid, pid = repos
        params = {
            "area": 40, "h": 20, "phi": 0.15,
            "sw": 0.3, "bo": 1.2, "rf": 0.3,
        }
        rid = ooip.save(
            well_id=wid, project_id=pid,
            formation="TEST", parameters=params,
        )
        result = ooip.get_by_id(rid)
        assert result["parameters"] == params
