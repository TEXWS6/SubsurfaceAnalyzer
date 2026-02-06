"""Formation tops CRUD repository."""

from database.connection import db


class TopsRepository:
    def create(self, well_id: int, formation: str, md_top: float,
               md_base: float = None, confidence: str = "medium",
               source: str = "manual") -> int:
        conn = db.get_connection()
        cursor = conn.execute(
            """INSERT INTO formation_tops (well_id, formation, md_top, md_base, confidence, source)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (well_id, formation, md_top, md_base, confidence, source),
        )
        conn.commit()
        return cursor.lastrowid

    def get_by_well(self, well_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM formation_tops WHERE well_id = ? ORDER BY md_top",
            (well_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_by_project(self, project_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            """SELECT ft.*, w.name as well_name
               FROM formation_tops ft
               JOIN wells w ON ft.well_id = w.id
               WHERE w.project_id = ?
               ORDER BY w.name, ft.md_top""",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_by_formation(self, project_id: int, formation: str) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            """SELECT ft.*, w.name as well_name, w.x_coord, w.y_coord, w.kb
               FROM formation_tops ft
               JOIN wells w ON ft.well_id = w.id
               WHERE w.project_id = ? AND ft.formation = ?
               ORDER BY w.name""",
            (project_id, formation),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_formations_in_project(self, project_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            """SELECT DISTINCT ft.formation
               FROM formation_tops ft
               JOIN wells w ON ft.well_id = w.id
               WHERE w.project_id = ?
               ORDER BY ft.formation""",
            (project_id,),
        ).fetchall()
        return [r["formation"] for r in rows]

    def update(self, top_id: int, **kwargs) -> None:
        if not kwargs:
            return
        fields = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [top_id]
        conn = db.get_connection()
        conn.execute(f"UPDATE formation_tops SET {fields} WHERE id = ?", values)
        conn.commit()

    def delete(self, top_id: int) -> None:
        conn = db.get_connection()
        conn.execute("DELETE FROM formation_tops WHERE id = ?", (top_id,))
        conn.commit()
