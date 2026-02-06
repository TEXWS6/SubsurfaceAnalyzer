"""Curve data CRUD repository. Stores numpy arrays as binary BLOBs."""

import numpy as np
from database.connection import db


class CurveRepository:
    def save_curve(self, well_id: int, mnemonic: str, original_mnemonic: str,
                   unit: str, depth_data: np.ndarray, curve_data: np.ndarray,
                   is_computed: int = 0) -> int:
        conn = db.get_connection()
        valid = ~np.isnan(depth_data)
        depth_min = float(np.nanmin(depth_data)) if valid.any() else None
        depth_max = float(np.nanmax(depth_data)) if valid.any() else None
        cursor = conn.execute(
            """INSERT INTO curves
               (well_id, mnemonic, original_mnemonic, unit, depth_min, depth_max,
                sample_count, data, depth_data, is_computed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (well_id, mnemonic, original_mnemonic, unit, depth_min, depth_max,
             len(curve_data), curve_data.astype(np.float64).tobytes(),
             depth_data.astype(np.float64).tobytes(), is_computed),
        )
        conn.commit()
        return cursor.lastrowid

    def get_curves_for_well(self, well_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            """SELECT id, well_id, mnemonic, original_mnemonic, unit,
                      depth_min, depth_max, sample_count, is_computed
               FROM curves WHERE well_id = ? ORDER BY mnemonic""",
            (well_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_curve_data(self, curve_id: int) -> tuple:
        """Return (depth_array, data_array) for a curve."""
        conn = db.get_connection()
        row = conn.execute(
            "SELECT data, depth_data, sample_count FROM curves WHERE id = ?",
            (curve_id,),
        ).fetchone()
        if not row:
            return None, None
        data = np.frombuffer(row["data"], dtype=np.float64)
        depth = np.frombuffer(row["depth_data"], dtype=np.float64)
        return depth.copy(), data.copy()

    def get_curve_by_mnemonic(self, well_id: int, mnemonic: str) -> dict | None:
        conn = db.get_connection()
        row = conn.execute(
            "SELECT * FROM curves WHERE well_id = ? AND mnemonic = ? LIMIT 1",
            (well_id, mnemonic),
        ).fetchone()
        return dict(row) if row else None

    def get_curve_data_by_mnemonic(self, well_id: int, mnemonic: str) -> tuple:
        """Return (depth_array, data_array) for a curve by mnemonic."""
        info = self.get_curve_by_mnemonic(well_id, mnemonic)
        if not info:
            return None, None
        return self.get_curve_data(info["id"])

    def delete_curve(self, curve_id: int) -> None:
        conn = db.get_connection()
        conn.execute("DELETE FROM curves WHERE id = ?", (curve_id,))
        conn.commit()

    def delete_computed_curves(self, well_id: int) -> None:
        conn = db.get_connection()
        conn.execute(
            "DELETE FROM curves WHERE well_id = ? AND is_computed = 1", (well_id,)
        )
        conn.commit()
