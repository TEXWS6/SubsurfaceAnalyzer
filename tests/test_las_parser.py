"""Tests for LAS parser service."""

import os
import pytest
from services.las_parser import LASParser


class TestLASParser:
    def setup_method(self):
        self.parser = LASParser()

    def test_parse_las_20(self, sample_las_file):
        result = self.parser.parse(sample_las_file)

        assert "metadata" in result
        assert "curves" in result

        meta = result["metadata"]
        assert meta["name"] == "TEST WELL 1"
        assert meta["uwi"] == "1234567890"
        assert meta["x_coord"] == 500000.0
        assert meta["y_coord"] == 6000000.0
        assert meta["kb"] == 150.0
        assert meta["td"] == 5000.0

    def test_parse_curves(self, sample_las_file):
        result = self.parser.parse(sample_las_file)
        curves = result["curves"]

        mnemonics = [c["mnemonic"] for c in curves]
        assert "GR" in mnemonics
        assert "ILD" in mnemonics
        assert "RHOB" in mnemonics
        assert "NPHI" in mnemonics
        assert "DT" in mnemonics

        # Check DEPT is not in curves (it's the index)
        assert "DEPT" not in mnemonics

        # Check data length
        for c in curves:
            assert len(c["data"]) == 15
            assert len(c["depth_data"]) == 15

    def test_parse_from_bytes(self, sample_las_file):
        with open(sample_las_file, "rb") as f:
            content = f.read()

        result = self.parser.parse_from_bytes(content, "test.las")
        assert result["metadata"]["name"] == "TEST WELL 1"
        assert len(result["curves"]) == 5

    def test_mnemonic_normalization(self, sample_las_file):
        result = self.parser.parse(sample_las_file)
        curves = result["curves"]

        # ILD should be normalized to ILD
        ild_curves = [c for c in curves if c["mnemonic"] == "ILD"]
        assert len(ild_curves) == 1
        assert ild_curves[0]["original_mnemonic"] == "ILD"

        os.unlink(sample_las_file)
