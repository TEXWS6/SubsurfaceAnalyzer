"""Production data CRUD repository."""

from database.connection import db


class ProductionRepository:
    def create(self, well_id: int, date: str, oil_vol: float = 0,
               gas_vol: float = 0, water_vol: float = 0,
               days_produced: float = 0) -> int:
        conn = db.get_connection()
        cursor = conn.execute(
            """INSERT INTO production_data
               (well_id, date, oil_vol, gas_vol, water_vol, days_produced)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (well_id, date, oil_vol, gas_vol, water_vol, days_produced),
        )
        conn.commit()
        return cursor.lastrowid

    def bulk_create(self, records: list) -> int:
        """Insert multiple production records at once.

        records: list of tuples (well_id, date, oil_vol, gas_vol, water_vol, days_produced)
        Returns number of rows inserted.
        """
        if not records:
            return 0
        conn = db.get_connection()
        conn.executemany(
            """INSERT INTO production_data
               (well_id, date, oil_vol, gas_vol, water_vol, days_produced)
               VALUES (?, ?, ?, ?, ?, ?)""",
            records,
        )
        conn.commit()
        return len(records)

    def get_by_well(self, well_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM production_data WHERE well_id = ? ORDER BY date",
            (well_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_by_date_range(self, well_id: int, start_date: str, end_date: str) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            """SELECT * FROM production_data
               WHERE well_id = ? AND date >= ? AND date <= ?
               ORDER BY date""",
            (well_id, start_date, end_date),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_cumulative(self, well_id: int) -> dict:
        """Return cumulative production sums for a well."""
        conn = db.get_connection()
        row = conn.execute(
            """SELECT
                COALESCE(SUM(oil_vol), 0) as cum_oil,
                COALESCE(SUM(gas_vol), 0) as cum_gas,
                COALESCE(SUM(water_vol), 0) as cum_water,
                COALESCE(SUM(days_produced), 0) as cum_days
               FROM production_data WHERE well_id = ?""",
            (well_id,),
        ).fetchone()
        return dict(row) if row else {
            "cum_oil": 0, "cum_gas": 0, "cum_water": 0, "cum_days": 0
        }

    def get_cumulative_by_project(self, project_id: int) -> list:
        """Return cumulative production per well for a project."""
        conn = db.get_connection()
        rows = conn.execute(
            """SELECT w.id as well_id, w.name as well_name,
                COALESCE(SUM(p.oil_vol), 0) as cum_oil,
                COALESCE(SUM(p.gas_vol), 0) as cum_gas,
                COALESCE(SUM(p.water_vol), 0) as cum_water
               FROM wells w
               LEFT JOIN production_data p ON w.id = p.well_id
               WHERE w.project_id = ?
               GROUP BY w.id, w.name
               ORDER BY w.name""",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def delete_by_well(self, well_id: int) -> None:
        conn = db.get_connection()
        conn.execute("DELETE FROM production_data WHERE well_id = ?", (well_id,))
        conn.commit()
