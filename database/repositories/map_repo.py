"""Map configuration CRUD repository."""

from database.connection import db


class MapConfigRepository:
    def create(self, project_id: int, name: str, map_type: str = "structure",
               formation_top: str = None, formation_base: str = None,
               interpolation_method: str = "cubic", grid_resolution: int = 100,
               colorscale: str = "Viridis", kriging_model: str = "spherical",
               kriging_sill: float = None, kriging_range: float = None,
               kriging_nugget: float = None, idw_power: float = 2.0,
               extra_config_json: str = "{}") -> int:
        conn = db.get_connection()
        cursor = conn.execute(
            """INSERT INTO map_configs
               (project_id, name, map_type, formation_top, formation_base,
                interpolation_method, grid_resolution, colorscale,
                kriging_model, kriging_sill, kriging_range, kriging_nugget,
                idw_power, extra_config_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (project_id, name, map_type, formation_top, formation_base,
             interpolation_method, grid_resolution, colorscale,
             kriging_model, kriging_sill, kriging_range, kriging_nugget,
             idw_power, extra_config_json),
        )
        conn.commit()
        return cursor.lastrowid

    def get_by_project(self, project_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM map_configs WHERE project_id = ? ORDER BY name",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_by_id(self, config_id: int) -> dict | None:
        conn = db.get_connection()
        row = conn.execute(
            "SELECT * FROM map_configs WHERE id = ?", (config_id,)
        ).fetchone()
        return dict(row) if row else None

    def delete(self, config_id: int) -> None:
        conn = db.get_connection()
        conn.execute("DELETE FROM map_configs WHERE id = ?", (config_id,))
        conn.commit()
