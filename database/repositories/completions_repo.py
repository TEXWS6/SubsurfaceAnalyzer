"""Completions CRUD repository."""

from database.connection import db


class CompletionsRepository:
    def create(self, well_id: int, perf_top: float = None,
               perf_base: float = None, completion_date: str = None,
               treatment_type: str = "") -> int:
        conn = db.get_connection()
        cursor = conn.execute(
            """INSERT INTO completions
               (well_id, perf_top, perf_base, completion_date, treatment_type)
               VALUES (?, ?, ?, ?, ?)""",
            (well_id, perf_top, perf_base, completion_date, treatment_type),
        )
        conn.commit()
        return cursor.lastrowid

    def bulk_create(self, records: list) -> int:
        """Insert multiple completion records at once.

        records: list of tuples (well_id, perf_top, perf_base, completion_date, treatment_type)
        Returns number of rows inserted.
        """
        if not records:
            return 0
        conn = db.get_connection()
        conn.executemany(
            """INSERT INTO completions
               (well_id, perf_top, perf_base, completion_date, treatment_type)
               VALUES (?, ?, ?, ?, ?)""",
            records,
        )
        conn.commit()
        return len(records)

    def get_by_well(self, well_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM completions WHERE well_id = ? ORDER BY perf_top",
            (well_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, completion_id: int) -> None:
        conn = db.get_connection()
        conn.execute("DELETE FROM completions WHERE id = ?", (completion_id,))
        conn.commit()

    def delete_by_well(self, well_id: int) -> None:
        conn = db.get_connection()
        conn.execute("DELETE FROM completions WHERE well_id = ?", (well_id,))
        conn.commit()
