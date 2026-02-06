"""Shapefile parser using geopandas.

Follows the LASParser/IHSParser pattern — parse file → return structured data.
Expects .zip uploads containing .shp/.shx/.dbf (and optionally .prj).
"""

import json
import os
import tempfile
import zipfile
from typing import Optional


class ShapefileParser:
    @staticmethod
    def parse_from_zip(content_bytes: bytes, filename: str = "upload.zip") -> dict:
        """Parse a shapefile from uploaded zip bytes.

        Returns structured dict with metadata and features.
        """
        tmp_dir = tempfile.mkdtemp()
        zip_path = os.path.join(tmp_dir, filename)
        with open(zip_path, "wb") as f:
            f.write(content_bytes)

        # Extract zip
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_dir)

        # Find the .shp file inside extracted contents
        shp_path = None
        for root, dirs, files in os.walk(tmp_dir):
            for fname in files:
                if fname.lower().endswith(".shp"):
                    shp_path = os.path.join(root, fname)
                    break
            if shp_path:
                break

        if not shp_path:
            raise ValueError("No .shp file found in the uploaded zip archive.")

        return ShapefileParser.parse(shp_path)

    @staticmethod
    def parse(file_path: str) -> dict:
        """Parse a shapefile from disk (.shp or .zip).

        Returns:
            {
                "metadata": {
                    "name": str,
                    "geometry_type": str,
                    "feature_count": int,
                    "crs_wkt": str,
                    "bounds": [xmin, ymin, xmax, ymax],
                    "attribute_columns": [str, ...],
                },
                "features": [
                    {
                        "geometry_json": str (GeoJSON geometry),
                        "attributes": dict,
                        "label": str,
                    },
                    ...
                ]
            }
        """
        import geopandas as gpd

        if file_path.lower().endswith(".zip"):
            gdf = gpd.read_file(f"zip://{file_path}")
        else:
            gdf = gpd.read_file(file_path)

        if gdf.empty:
            raise ValueError("Shapefile contains no features.")

        # Determine geometry type from first non-null geometry
        geom_types = gdf.geometry.geom_type.dropna().unique()
        primary_type = geom_types[0] if len(geom_types) > 0 else "Unknown"

        # CRS info
        crs_wkt = gdf.crs.to_wkt() if gdf.crs else ""

        # Bounds
        bounds = list(gdf.total_bounds)  # [xmin, ymin, xmax, ymax]

        # Attribute columns (exclude geometry)
        attr_cols = [c for c in gdf.columns if c != gdf.geometry.name]

        # Detect best label field
        label_field = ShapefileParser._detect_label_field(gdf, attr_cols)

        # Build layer name from filename
        name = os.path.splitext(os.path.basename(file_path))[0]

        # Build features list
        features = []
        for _, row in gdf.iterrows():
            geom = row.geometry
            if geom is None:
                continue

            geom_json = json.dumps(geom.__geo_interface__)

            # Collect attributes (convert numpy types to native Python)
            attrs = {}
            for col in attr_cols:
                val = row[col]
                if hasattr(val, "item"):
                    val = val.item()  # numpy scalar → python scalar
                if val != val:  # NaN check
                    val = None
                attrs[col] = val

            label = str(attrs.get(label_field, "")) if label_field else ""

            features.append({
                "geometry_json": geom_json,
                "attributes": attrs,
                "label": label,
            })

        return {
            "metadata": {
                "name": name,
                "geometry_type": primary_type,
                "feature_count": len(features),
                "crs_wkt": crs_wkt,
                "bounds": bounds,
                "attribute_columns": attr_cols,
            },
            "features": features,
        }

    @staticmethod
    def _detect_label_field(gdf, attr_cols: list) -> Optional[str]:
        """Heuristic: pick a column likely to be a good label.

        Checks for columns containing 'name', 'label', 'id', 'lease'.
        Falls back to the first string/object column.
        """
        name_hints = ["name", "label", "id", "lease", "well", "field"]
        lower_cols = {c.lower(): c for c in attr_cols}

        # First pass: exact substring match in column name
        for hint in name_hints:
            for lc, orig in lower_cols.items():
                if hint in lc:
                    return orig

        # Fallback: first object/string column
        for col in attr_cols:
            if gdf[col].dtype == object:
                return col

        return attr_cols[0] if attr_cols else None

    @staticmethod
    def import_to_project(parsed: dict, project_id: int,
                          shapefile_repo, label_field: str = None) -> dict:
        """Save parsed shapefile data to database.

        Returns: {"layer_id": int, "feature_count": int}
        """
        meta = parsed["metadata"]

        # Override label field if specified
        if label_field and label_field in meta["attribute_columns"]:
            effective_label = label_field
        else:
            effective_label = None
            # Try to find the auto-detected label from features
            for feat in parsed["features"]:
                if feat.get("label"):
                    # The parser already picked a label field
                    effective_label = None  # use what's already there
                    break

        layer_id = shapefile_repo.create_layer(
            project_id=project_id,
            name=meta["name"],
            geometry_type=meta["geometry_type"],
            feature_count=meta["feature_count"],
            bounds_json=json.dumps(meta["bounds"]),
            crs_wkt=meta["crs_wkt"],
            attribute_columns_json=json.dumps(meta["attribute_columns"]),
        )

        # Build feature records
        records = []
        for feat in parsed["features"]:
            label = feat["label"]
            if label_field and label_field in feat["attributes"]:
                label = str(feat["attributes"].get(label_field, ""))

            records.append((
                layer_id,
                feat["geometry_json"],
                json.dumps(feat["attributes"]),
                label,
            ))

        if records:
            shapefile_repo.bulk_create_features(records)

        # Update label_field on the layer
        if label_field:
            shapefile_repo.update_layer_style(layer_id, label_field=label_field)

        return {"layer_id": layer_id, "feature_count": len(records)}
