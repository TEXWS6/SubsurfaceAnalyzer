"""Tests for mnemonic aliasing and constants."""

import pytest
from utils.constants import normalize_mnemonic, get_curve_style


class TestMnemonicAliasing:
    def test_standard_mnemonics(self):
        assert normalize_mnemonic("GR") == "GR"
        assert normalize_mnemonic("ILD") == "ILD"
        assert normalize_mnemonic("RHOB") == "RHOB"

    def test_aliases(self):
        assert normalize_mnemonic("SGR") == "GR"
        assert normalize_mnemonic("CGR") == "GR"
        assert normalize_mnemonic("RILD") == "ILD"
        assert normalize_mnemonic("RHOZ") == "RHOB"
        assert normalize_mnemonic("TNPH") == "NPHI"
        assert normalize_mnemonic("DTC") == "DT"

    def test_case_insensitive(self):
        assert normalize_mnemonic("gr") == "GR"
        assert normalize_mnemonic("Ild") == "ILD"

    def test_unknown_passthrough(self):
        assert normalize_mnemonic("CUSTOM_CURVE") == "CUSTOM_CURVE"
        assert normalize_mnemonic("xyz") == "XYZ"

    def test_whitespace_handling(self):
        assert normalize_mnemonic("  GR  ") == "GR"

    def test_depth_aliases(self):
        assert normalize_mnemonic("DEPT") == "DEPT"
        assert normalize_mnemonic("DEPTH") == "DEPT"
        assert normalize_mnemonic("MD") == "DEPT"


class TestCurveStyle:
    def test_known_curve(self):
        style = get_curve_style("GR")
        assert style["color"] == "green"
        assert style["track"] == 1
        assert style["scale"] == "linear"

    def test_resistivity_log_scale(self):
        style = get_curve_style("ILD")
        assert style["scale"] == "log"
        assert style["track"] == 2

    def test_unknown_fallback(self):
        style = get_curve_style("UNKNOWN")
        assert style["color"] == "black"
        assert style["width"] == 1.0
