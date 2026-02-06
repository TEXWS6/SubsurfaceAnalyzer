"""IHS .297/.298 fixed-width format parser.

Follows the LASParser pattern — parse file → return structured data.
Column positions based on standard IHS/PI-Dwights export format.
"""

import re
from typing import Optional


# .297 well header field definitions: (name, start, length)
HEADER_297_FIELDS = [
    ("uwi", 0, 14),
    ("well_name", 14, 40),
    ("operator", 54, 32),
    ("field_name", 86, 20),
    ("state", 106, 2),
    ("county", 108, 22),
    ("latitude", 130, 10),
    ("longitude", 140, 14),
    ("kb_elev", 154, 6),
    ("td", 160, 5),
    ("status", 165, 5),
    ("completion_date", 170, 8),
    ("formation", 178, 20),
]

# .297 completion/perforation record fields: (name, start, length)
COMPLETION_297_FIELDS = [
    ("uwi", 0, 14),
    ("perf_top", 14, 7),
    ("perf_base", 21, 7),
    ("completion_date", 28, 8),
    ("treatment_type", 36, 20),
]

# .298 production record fields: (name, start, length)
PRODUCTION_298_FIELDS = [
    ("uwi", 0, 14),
    ("date", 14, 6),       # YYYYMM
    ("oil_vol", 20, 8),
    ("gas_vol", 28, 14),
    ("water_vol", 42, 7),
    ("days_produced", 49, 5),
]


def _parse_fixed_width(line: str, field_defs: list) -> dict:
    """Parse a fixed-width line into a dict using field definitions."""
    result = {}
    for name, start, length in field_defs:
        end = start + length
        raw = line[start:end].strip() if len(line) > start else ""
        result[name] = raw
    return result


def _safe_float(value: str) -> Optional[float]:
    """Safely convert string to float, handling common formatting."""
    if not value:
        return None
    # Remove commas and extra whitespace
    cleaned = value.replace(",", "").strip()
    if not cleaned or cleaned == "-":
        return None
    try:
        return float(cleaned)
    except ValueError:
        # Regex fallback to extract first number
        match = re.search(r"[-+]?\d*\.?\d+", cleaned)
        return float(match.group()) if match else None


def _clean_header_record(record: dict) -> dict:
    """Clean and convert a parsed .297 header record."""
    return {
        "uwi": record.get("uwi", "").strip(),
        "well_name": record.get("well_name", "").strip(),
        "operator": record.get("operator", "").strip(),
        "field_name": record.get("field_name", "").strip(),
        "state": record.get("state", "").strip(),
        "county": record.get("county", "").strip(),
        "latitude": _safe_float(record.get("latitude", "")),
        "longitude": _safe_float(record.get("longitude", "")),
        "kb_elev": _safe_float(record.get("kb_elev", "")),
        "td": _safe_float(record.get("td", "")),
        "status": record.get("status", "").strip(),
        "completion_date": record.get("completion_date", "").strip(),
        "formation": record.get("formation", "").strip(),
    }


def _clean_production_record(record: dict) -> dict:
    """Clean and convert a parsed .298 production record."""
    # Convert YYYYMM to YYYY-MM
    raw_date = record.get("date", "").strip()
    if len(raw_date) == 6 and raw_date.isdigit():
        date_str = f"{raw_date[:4]}-{raw_date[4:6]}"
    else:
        date_str = raw_date

    return {
        "uwi": record.get("uwi", "").strip(),
        "date": date_str,
        "oil_vol": _safe_float(record.get("oil_vol", "")) or 0.0,
        "gas_vol": _safe_float(record.get("gas_vol", "")) or 0.0,
        "water_vol": _safe_float(record.get("water_vol", "")) or 0.0,
        "days_produced": _safe_float(record.get("days_produced", "")) or 0.0,
    }


class IHSParser:
    @staticmethod
    def parse_297(file_path_or_content: str) -> list:
        """Parse IHS .297 file for well header data.

        Args:
            file_path_or_content: file path or raw file content string.

        Returns:
            List of cleaned well header dicts.
        """
        lines = IHSParser._read_lines(file_path_or_content)
        wells = []
        for line in lines:
            if not line.strip() or line.startswith("#"):
                continue
            record = _parse_fixed_width(line, HEADER_297_FIELDS)
            cleaned = _clean_header_record(record)
            if cleaned["uwi"]:
                wells.append(cleaned)
        return wells

    @staticmethod
    def parse_298(file_path_or_content: str) -> list:
        """Parse IHS .298 file for monthly production data.

        Args:
            file_path_or_content: file path or raw file content string.

        Returns:
            List of cleaned production record dicts.
        """
        lines = IHSParser._read_lines(file_path_or_content)
        records = []
        for line in lines:
            if not line.strip() or line.startswith("#"):
                continue
            record = _parse_fixed_width(line, PRODUCTION_298_FIELDS)
            cleaned = _clean_production_record(record)
            if cleaned["uwi"] and cleaned["date"]:
                records.append(cleaned)
        return records

    @staticmethod
    def parse_297_completions(file_path_or_content: str) -> list:
        """Parse completion/perforation records from .297 extended data.

        Returns list of completion dicts with uwi, perf_top, perf_base, etc.
        """
        lines = IHSParser._read_lines(file_path_or_content)
        completions = []
        for line in lines:
            if not line.strip() or line.startswith("#"):
                continue
            record = _parse_fixed_width(line, COMPLETION_297_FIELDS)
            cleaned = {
                "uwi": record.get("uwi", "").strip(),
                "perf_top": _safe_float(record.get("perf_top", "")),
                "perf_base": _safe_float(record.get("perf_base", "")),
                "completion_date": record.get("completion_date", "").strip(),
                "treatment_type": record.get("treatment_type", "").strip(),
            }
            if cleaned["uwi"] and (cleaned["perf_top"] is not None
                                    or cleaned["perf_base"] is not None):
                completions.append(cleaned)
        return completions

    @staticmethod
    def import_297_to_project(wells_data: list, project_id: int,
                              well_repo) -> dict:
        """Save parsed .297 wells to database, deduplicating by UWI.

        Returns counts dict: {created, skipped, total}.
        """
        created = 0
        skipped = 0
        for w in wells_data:
            uwi = w.get("uwi", "")
            if not uwi:
                skipped += 1
                continue
            existing = well_repo.get_by_uwi(project_id, uwi)
            if existing:
                skipped += 1
                continue
            well_repo.create(
                project_id=project_id,
                name=w.get("well_name", uwi),
                uwi=uwi,
                x_coord=w.get("longitude"),
                y_coord=w.get("latitude"),
                kb=w.get("kb_elev"),
                td=w.get("td"),
            )
            created += 1
        return {"created": created, "skipped": skipped, "total": len(wells_data)}

    @staticmethod
    def _read_lines(file_path_or_content: str) -> list:
        """Read lines from file path or content string."""
        if "\n" in file_path_or_content or len(file_path_or_content) > 260:
            return file_path_or_content.splitlines()
        try:
            with open(file_path_or_content, "r", encoding="utf-8", errors="replace") as f:
                return f.readlines()
        except (OSError, FileNotFoundError):
            return file_path_or_content.splitlines()
