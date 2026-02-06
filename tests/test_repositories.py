"""Tests for database repositories."""

import numpy as np
import pytest
from database.repositories import (
    ProjectRepository, WellRepository, CurveRepository,
    TopsRepository, MapConfigRepository, PetroParamsRepository,
)


class TestProjectRepository:
    def setup_method(self):
        self.repo = ProjectRepository()

    def test_create_and_get(self):
        pid = self.repo.create("Test Project", "Description")
        assert pid > 0
        project = self.repo.get_by_id(pid)
        assert project["name"] == "Test Project"
        assert project["description"] == "Description"

    def test_get_all(self):
        self.repo.create("Project A")
        self.repo.create("Project B")
        projects = self.repo.get_all()
        assert len(projects) >= 2

    def test_update(self):
        pid = self.repo.create("Old Name")
        self.repo.update(pid, "New Name", "New Desc")
        project = self.repo.get_by_id(pid)
        assert project["name"] == "New Name"

    def test_delete(self):
        pid = self.repo.create("To Delete")
        self.repo.delete(pid)
        assert self.repo.get_by_id(pid) is None


class TestWellRepository:
    def setup_method(self):
        self.project_repo = ProjectRepository()
        self.repo = WellRepository()

    def test_create_and_get(self):
        pid = self.project_repo.create("Test Project")
        wid = self.repo.create(pid, "Well-1", uwi="123", x_coord=100, y_coord=200)
        well = self.repo.get_by_id(wid)
        assert well["name"] == "Well-1"
        assert well["x_coord"] == 100.0
        assert well["y_coord"] == 200.0

    def test_get_by_project(self):
        pid = self.project_repo.create("Test Project")
        self.repo.create(pid, "Well-A")
        self.repo.create(pid, "Well-B")
        wells = self.repo.get_by_project(pid)
        assert len(wells) == 2

    def test_update(self):
        pid = self.project_repo.create("Test Project")
        wid = self.repo.create(pid, "Well-1")
        self.repo.update(wid, x_coord=500, y_coord=600)
        well = self.repo.get_by_id(wid)
        assert well["x_coord"] == 500.0

    def test_cascade_delete(self):
        pid = self.project_repo.create("Test Project")
        wid = self.repo.create(pid, "Well-1")
        self.project_repo.delete(pid)
        assert self.repo.get_by_id(wid) is None


class TestCurveRepository:
    def setup_method(self):
        self.project_repo = ProjectRepository()
        self.well_repo = WellRepository()
        self.repo = CurveRepository()

    def test_save_and_retrieve(self):
        pid = self.project_repo.create("Test")
        wid = self.well_repo.create(pid, "Well")
        depth = np.arange(1000, 1010, 0.5)
        data = np.random.rand(len(depth))

        cid = self.repo.save_curve(wid, "GR", "GR", "GAPI", depth, data)
        assert cid > 0

        ret_depth, ret_data = self.repo.get_curve_data(cid)
        np.testing.assert_array_almost_equal(ret_depth, depth)
        np.testing.assert_array_almost_equal(ret_data, data)

    def test_get_by_mnemonic(self):
        pid = self.project_repo.create("Test")
        wid = self.well_repo.create(pid, "Well")
        depth = np.arange(100, 200, 1.0)
        data = np.random.rand(len(depth))
        self.repo.save_curve(wid, "GR", "GR", "GAPI", depth, data)

        info = self.repo.get_curve_by_mnemonic(wid, "GR")
        assert info is not None
        assert info["mnemonic"] == "GR"

    def test_list_curves(self):
        pid = self.project_repo.create("Test")
        wid = self.well_repo.create(pid, "Well")
        depth = np.arange(100, 200, 1.0)
        self.repo.save_curve(wid, "GR", "GR", "GAPI", depth, np.random.rand(100))
        self.repo.save_curve(wid, "ILD", "ILD", "OHMM", depth, np.random.rand(100))

        curves = self.repo.get_curves_for_well(wid)
        assert len(curves) == 2

    def test_delete_computed(self):
        pid = self.project_repo.create("Test")
        wid = self.well_repo.create(pid, "Well")
        depth = np.arange(100, 200, 1.0)
        self.repo.save_curve(wid, "GR", "GR", "GAPI", depth, np.random.rand(100), is_computed=0)
        self.repo.save_curve(wid, "VSHALE", "VSHALE", "V/V", depth, np.random.rand(100), is_computed=1)

        self.repo.delete_computed_curves(wid)
        curves = self.repo.get_curves_for_well(wid)
        assert len(curves) == 1
        assert curves[0]["mnemonic"] == "GR"


class TestTopsRepository:
    def setup_method(self):
        self.project_repo = ProjectRepository()
        self.well_repo = WellRepository()
        self.repo = TopsRepository()

    def test_create_and_get(self):
        pid = self.project_repo.create("Test")
        wid = self.well_repo.create(pid, "Well")
        tid = self.repo.create(wid, "Top Cretaceous", 1500.0, 1600.0)
        tops = self.repo.get_by_well(wid)
        assert len(tops) == 1
        assert tops[0]["formation"] == "Top Cretaceous"
        assert tops[0]["md_top"] == 1500.0

    def test_get_formations_in_project(self):
        pid = self.project_repo.create("Test")
        w1 = self.well_repo.create(pid, "Well-1")
        w2 = self.well_repo.create(pid, "Well-2")
        self.repo.create(w1, "Formation A", 1000)
        self.repo.create(w1, "Formation B", 1500)
        self.repo.create(w2, "Formation A", 1100)

        formations = self.repo.get_formations_in_project(pid)
        assert "Formation A" in formations
        assert "Formation B" in formations

    def test_get_by_formation(self):
        pid = self.project_repo.create("Test")
        w1 = self.well_repo.create(pid, "Well-1", x_coord=100, y_coord=200)
        w2 = self.well_repo.create(pid, "Well-2", x_coord=300, y_coord=400)
        self.repo.create(w1, "Top Sand", 1000)
        self.repo.create(w2, "Top Sand", 1100)

        data = self.repo.get_by_formation(pid, "Top Sand")
        assert len(data) == 2
        assert data[0]["x_coord"] is not None


class TestPetroParamsRepository:
    def setup_method(self):
        self.project_repo = ProjectRepository()
        self.well_repo = WellRepository()
        self.repo = PetroParamsRepository()

    def test_save_and_get(self):
        pid = self.project_repo.create("Test")
        wid = self.well_repo.create(pid, "Well")
        self.repo.save(wid, "default", gr_clean=25.0, gr_shale=100.0)

        params = self.repo.get(wid, "default")
        assert params is not None
        assert params["gr_clean"] == 25.0
        assert params["gr_shale"] == 100.0

    def test_update_existing(self):
        pid = self.project_repo.create("Test")
        wid = self.well_repo.create(pid, "Well")
        self.repo.save(wid, "default", gr_clean=25.0)
        self.repo.save(wid, "default", gr_clean=30.0)

        params = self.repo.get(wid, "default")
        assert params["gr_clean"] == 30.0
