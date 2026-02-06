"""Project CRUD repository."""

from database.connection import db


class ProjectRepository:
    def create(self, name: str, description: str = "") -> int:
        conn = db.get_connection()
        cursor = conn.execute(
            "INSERT INTO projects (name, description) VALUES (?, ?)",
            (name, description),
        )
        conn.commit()
        return cursor.lastrowid

    def get_all(self) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM projects ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    def get_by_id(self, project_id: int) -> dict | None:
        conn = db.get_connection()
        row = conn.execute(
            "SELECT * FROM projects WHERE id = ?", (project_id,)
        ).fetchone()
        return dict(row) if row else None

    def update(self, project_id: int, name: str, description: str = "") -> None:
        conn = db.get_connection()
        conn.execute(
            "UPDATE projects SET name = ?, description = ? WHERE id = ?",
            (name, description, project_id),
        )
        conn.commit()

    def delete(self, project_id: int) -> None:
        conn = db.get_connection()
        conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
