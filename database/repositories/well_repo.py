"""Well CRUD repository."""

from database.connection import db


class WellRepository:
    def create(self, project_id: int, name: str, uwi: str = "",
               x_coord: float = None, y_coord: float = None,
               kb: float = None, td: float = None, las_path: str = None) -> int:
        conn = db.get_connection()
        cursor = conn.execute(
            """INSERT INTO wells (project_id, name, uwi, x_coord, y_coord, kb, td, las_path)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, name, uwi, x_coord, y_coord, kb, td, las_path),
        )
        conn.commit()
        return cursor.lastrowid

    def get_by_project(self, project_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM wells WHERE project_id = ? ORDER BY name", (project_id,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_by_id(self, well_id: int) -> dict | None:
        conn = db.get_connection()
        row = conn.execute("SELECT * FROM wells WHERE id = ?", (well_id,)).fetchone()
        return dict(row) if row else None

    def update(self, well_id: int, **kwargs) -> None:
        if not kwargs:
            return
        fields = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [well_id]
        conn = db.get_connection()
        conn.execute(f"UPDATE wells SET {fields} WHERE id = ?", values)
        conn.commit()

    def get_by_uwi(self, project_id: int, uwi: str) -> dict | None:
        """Find a well by UWI within a project."""
        conn = db.get_connection()
        row = conn.execute(
            "SELECT * FROM wells WHERE project_id = ? AND uwi = ?",
            (project_id, uwi),
        ).fetchone()
        return dict(row) if row else None

    def delete(self, well_id: int) -> None:
        conn = db.get_connection()
        conn.execute("DELETE FROM wells WHERE id = ?", (well_id,))
        conn.commit()
