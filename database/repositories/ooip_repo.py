"""OOIP/OGIP results CRUD repository."""

import json
from database.connection import db


class OOIPRepository:
    def save(self, well_id: int = None, project_id: int = None,
             formation: str = "", method: str = "deterministic",
             ooip: float = None, ogip: float = None,
             parameters: dict = None) -> int:
        conn = db.get_connection()
        params_json = json.dumps(parameters or {})
        cursor = conn.execute(
            """INSERT INTO ooip_results
               (well_id, project_id, formation, method, ooip, ogip, parameters_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (well_id, project_id, formation, method, ooip, ogip, params_json),
        )
        conn.commit()
        return cursor.lastrowid

    def get_by_well(self, well_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM ooip_results WHERE well_id = ? ORDER BY created_at DESC",
            (well_id,),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["parameters"] = json.loads(d.get("parameters_json", "{}"))
            results.append(d)
        return results

    def get_by_project(self, project_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM ooip_results WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["parameters"] = json.loads(d.get("parameters_json", "{}"))
            results.append(d)
        return results

    def get_by_id(self, result_id: int) -> dict | None:
        conn = db.get_connection()
        row = conn.execute(
            "SELECT * FROM ooip_results WHERE id = ?", (result_id,)
        ).fetchone()
        if not row:
            return None
        d = dict(row)
        d["parameters"] = json.loads(d.get("parameters_json", "{}"))
        return d

    def delete(self, result_id: int) -> None:
        conn = db.get_connection()
        conn.execute("DELETE FROM ooip_results WHERE id = ?", (result_id,))
        conn.commit()
