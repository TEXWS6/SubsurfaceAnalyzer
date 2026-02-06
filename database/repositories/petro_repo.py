"""Petrophysical parameters CRUD repository."""

from database.connection import db


class PetroParamsRepository:
    def save(self, well_id: int, name: str = "default", **params) -> int:
        conn = db.get_connection()
        existing = conn.execute(
            "SELECT id FROM petro_params WHERE well_id = ? AND name = ?",
            (well_id, name),
        ).fetchone()

        columns = [
            "vshale_method", "gr_clean", "gr_shale", "rho_matrix", "rho_fluid",
            "nphi_matrix", "archie_a", "archie_m", "archie_n", "rw",
            "phi_cutoff", "sw_cutoff", "vshale_cutoff",
        ]
        filtered = {k: v for k, v in params.items() if k in columns}

        if existing:
            if filtered:
                fields = ", ".join(f"{k} = ?" for k in filtered)
                values = list(filtered.values()) + [existing["id"]]
                conn.execute(f"UPDATE petro_params SET {fields} WHERE id = ?", values)
                conn.commit()
            return existing["id"]

        cols = ["well_id", "name"] + list(filtered.keys())
        placeholders = ", ".join("?" for _ in cols)
        values = [well_id, name] + list(filtered.values())
        cursor = conn.execute(
            f"INSERT INTO petro_params ({', '.join(cols)}) VALUES ({placeholders})",
            values,
        )
        conn.commit()
        return cursor.lastrowid

    def get(self, well_id: int, name: str = "default") -> dict | None:
        conn = db.get_connection()
        row = conn.execute(
            "SELECT * FROM petro_params WHERE well_id = ? AND name = ?",
            (well_id, name),
        ).fetchone()
        return dict(row) if row else None

    def get_by_well(self, well_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM petro_params WHERE well_id = ? ORDER BY name",
            (well_id,),
        ).fetchall()
        return [dict(r) for r in rows]
