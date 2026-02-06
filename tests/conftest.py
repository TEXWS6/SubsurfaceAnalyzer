"""Pytest fixtures and sample LAS data."""

import os
import sys
import tempfile
import pytest
import numpy as np

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Override DB path for tests
import config
config.DB_PATH = os.path.join(tempfile.mkdtemp(), "test_subsurface.db")

from database.schema import init_db
from database.connection import db


SAMPLE_LAS_20 = """\
~VERSION INFORMATION
 VERS.                 2.0 :   CWLS LOG ASCII STANDARD -VERSION 2.0
 WRAP.                  NO :   ONE LINE PER DEPTH STEP
~WELL INFORMATION
 WELL.                TEST WELL 1  :
 UWI .                1234567890   :
 XCOORD.              500000.0     :
 YCOORD.              6000000.0    :
 EKB .FT              150.0        :
 TD  .FT              5000.0       :
~CURVE INFORMATION
 DEPT.FT                           : DEPTH
 GR  .GAPI                        : GAMMA RAY
 ILD .OHMM                        : DEEP INDUCTION
 RHOB.G/C3                        : BULK DENSITY
 NPHI.V/V                         : NEUTRON POROSITY
 DT  .US/F                        : SONIC
~A  DEPTH         GR         ILD       RHOB       NPHI        DT
 1000.0000    30.0000     5.0000     2.5500     0.1500    80.0000
 1000.5000    32.0000     4.8000     2.5600     0.1480    79.5000
 1001.0000    35.0000     4.5000     2.5700     0.1450    79.0000
 1001.5000    45.0000     3.0000     2.5200     0.1600    82.0000
 1002.0000    55.0000     2.5000     2.4800     0.1800    85.0000
 1002.5000    80.0000     1.5000     2.4000     0.2200    92.0000
 1003.0000    95.0000     1.2000     2.3500     0.2500    98.0000
 1003.5000   110.0000     1.0000     2.3000     0.2800   105.0000
 1004.0000    85.0000     1.8000     2.4200     0.2000    88.0000
 1004.5000    40.0000     6.0000     2.5400     0.1520    80.5000
 1005.0000    28.0000    10.0000     2.5800     0.1400    78.0000
 1005.5000    25.0000    15.0000     2.6000     0.1200    76.0000
 1006.0000    22.0000    20.0000     2.6100     0.1100    75.0000
 1006.5000    20.0000    25.0000     2.6200     0.1000    74.0000
 1007.0000    18.0000    30.0000     2.6300     0.0900    73.0000
"""


@pytest.fixture(autouse=True)
def setup_db():
    """Initialize a fresh test database for each test."""
    # Close any existing connection
    db.close()
    # Point to a brand new DB file
    config.DB_PATH = os.path.join(tempfile.mkdtemp(), f"test_{id(object())}.db")
    # Force the singleton to create a new connection by clearing thread-local
    if hasattr(db._local, "connection"):
        db._local.connection = None
    init_db()
    yield
    db.close()
    if hasattr(db._local, "connection"):
        db._local.connection = None


@pytest.fixture
def sample_las_file():
    """Create a temporary LAS file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".las", delete=False) as f:
        f.write(SAMPLE_LAS_20)
        return f.name


@pytest.fixture
def sample_arrays():
    """Return sample numpy arrays for testing."""
    depth = np.arange(1000, 1007.5, 0.5)
    gr = np.array([30, 32, 35, 45, 55, 80, 95, 110, 85, 40, 28, 25, 22, 20, 18], dtype=float)
    rhob = np.array([2.55, 2.56, 2.57, 2.52, 2.48, 2.40, 2.35, 2.30, 2.42, 2.54,
                     2.58, 2.60, 2.61, 2.62, 2.63], dtype=float)
    nphi = np.array([0.15, 0.148, 0.145, 0.16, 0.18, 0.22, 0.25, 0.28, 0.20, 0.152,
                     0.14, 0.12, 0.11, 0.10, 0.09], dtype=float)
    rt = np.array([5, 4.8, 4.5, 3.0, 2.5, 1.5, 1.2, 1.0, 1.8, 6.0,
                   10, 15, 20, 25, 30], dtype=float)
    return depth, gr, rhob, nphi, rt
