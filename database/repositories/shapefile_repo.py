"""Repository for shapefile layers and features."""

import json
from database.connection import db


class ShapefileRepository:
    def create_layer(self, project_id: int, name: str, geometry_type: str,
                     feature_count: int = 0, bounds_json: str = "",
                     crs_wkt: str = "", attribute_columns_json: str = "[]") -> int:
        conn = db.get_connection()
        cursor = conn.execute(
            """INSERT INTO shapefile_layers
               (project_id, name, geometry_type, feature_count,
                bounds_json, crs_wkt, attribute_columns_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (project_id, name, geometry_type, feature_count,
             bounds_json, crs_wkt, attribute_columns_json),
        )
        conn.commit()
        return cursor.lastrowid

    def bulk_create_features(self, records: list):
        """Insert features in bulk.

        records: list of (layer_id, geometry_json, attributes_json, label) tuples.
        """
        conn = db.get_connection()
        conn.executemany(
            """INSERT INTO shapefile_features
               (layer_id, geometry_json, attributes_json, label)
               VALUES (?, ?, ?, ?)""",
            records,
        )
        conn.commit()

    def get_layers_by_project(self, project_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM shapefile_layers WHERE project_id = ? ORDER BY name",
            (project_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_layer_by_id(self, layer_id: int) -> dict | None:
        conn = db.get_connection()
        row = conn.execute(
            "SELECT * FROM shapefile_layers WHERE id = ?", (layer_id,),
        ).fetchone()
        return dict(row) if row else None

    def get_features_by_layer(self, layer_id: int) -> list:
        conn = db.get_connection()
        rows = conn.execute(
            "SELECT * FROM shapefile_features WHERE layer_id = ?",
            (layer_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def update_layer_style(self, layer_id: int, **kwargs):
        """Update style columns on a layer.

        Accepted kwargs: line_color, line_width, fill_color, fill_opacity, label_field.
        """
        allowed = {"line_color", "line_width", "fill_color", "fill_opacity", "label_field"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        set_clause = ", ".join(f"{k} = ?" for k in updates)
        values = list(updates.values()) + [layer_id]
        conn = db.get_connection()
        conn.execute(
            f"UPDATE shapefile_layers SET {set_clause} WHERE id = ?", values,
        )
        conn.commit()

    def delete_layer(self, layer_id: int):
        """Delete a layer and its features (cascade)."""
        conn = db.get_connection()
        conn.execute("DELETE FROM shapefile_layers WHERE id = ?", (layer_id,))
        conn.commit()
