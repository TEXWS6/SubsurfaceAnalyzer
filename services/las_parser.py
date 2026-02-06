"""LAS file parser using lasio. Extracts well metadata and curve data."""

import os
import numpy as np
import lasio
from utils.constants import normalize_mnemonic


class LASParser:
    def parse(self, file_path: str) -> dict:
        """Parse a LAS file and return well metadata and curves.

        Returns:
            dict with keys:
                - metadata: dict of well header fields
                - curves: list of dicts with mnemonic, unit, data, depth_data
        """
        las = lasio.read(file_path)
        metadata = self._extract_metadata(las, file_path)
        curves = self._extract_curves(las)
        return {"metadata": metadata, "curves": curves}

    def _extract_metadata(self, las, file_path: str) -> dict:
        meta = {
            "name": "",
            "uwi": "",
            "x_coord": None,
            "y_coord": None,
            "kb": None,
            "td": None,
            "las_path": file_path,
        }

        # Try common header fields
        for item in las.well:
            key = item.mnemonic.upper()
            val = item.value

            if key in ("WELL", "WN"):
                meta["name"] = str(val).strip()
            elif key in ("UWI", "API", "UNIQUE WELL ID"):
                meta["uwi"] = str(val).strip()
            elif key in ("XCOORD", "X", "LONG", "LONGITUDE", "EASTING"):
                meta["x_coord"] = self._safe_float(val)
            elif key in ("YCOORD", "Y", "LAT", "LATITUDE", "NORTHING"):
                meta["y_coord"] = self._safe_float(val)
            elif key in ("EKB", "KB", "EKBE"):
                meta["kb"] = self._safe_float(val)
            elif key in ("TD", "TDD", "TOTALDEPTH"):
                meta["td"] = self._safe_float(val)

        # Fallback: use filename as well name if empty
        if not meta["name"]:
            meta["name"] = os.path.splitext(os.path.basename(file_path))[0]

        # Fallback: TD from depth index
        if meta["td"] is None and len(las.index) > 0:
            meta["td"] = float(np.nanmax(las.index))

        return meta

    def _extract_curves(self, las) -> list:
        depth = np.array(las.index, dtype=np.float64)
        curves = []

        for curve in las.curves:
            mnemonic = curve.mnemonic.strip()
            normalized = normalize_mnemonic(mnemonic)

            # Skip the depth curve itself
            if normalized == "DEPT":
                continue

            data = np.array(curve.data, dtype=np.float64)
            curves.append({
                "mnemonic": normalized,
                "original_mnemonic": mnemonic,
                "unit": curve.unit.strip() if curve.unit else "",
                "data": data,
                "depth_data": depth,
            })

        return curves

    def _safe_float(self, value) -> float | None:
        if value is None or str(value).strip() == "":
            return None
        try:
            v = float(value)
            return v if np.isfinite(v) else None
        except (ValueError, TypeError):
            # Try extracting a number from a string like "FT 150.0"
            s = str(value).strip()
            import re
            match = re.search(r"[-+]?\d*\.?\d+", s)
            if match:
                try:
                    v = float(match.group())
                    return v if np.isfinite(v) else None
                except ValueError:
                    pass
            return None

    def parse_from_bytes(self, content: bytes, filename: str) -> dict:
        """Parse LAS content from uploaded bytes."""
        import tempfile
        suffix = os.path.splitext(filename)[1] or ".las"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, mode="wb") as f:
            f.write(content)
            tmp_path = f.name

        try:
            result = self.parse(tmp_path)
            result["metadata"]["las_path"] = filename
            return result
        finally:
            os.unlink(tmp_path)
