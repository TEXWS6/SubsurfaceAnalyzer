"""Export service for formation tops CSV export."""

import csv
import io


class ExportService:
    @staticmethod
    def tops_to_csv(tops_data: list) -> str:
        """Convert formation tops data to CSV string.

        tops_data: list of dicts from TopsRepository.
        """
        output = io.StringIO()
        fieldnames = ["well_name", "formation", "md_top", "md_base",
                       "confidence", "source"]
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in tops_data:
            writer.writerow(row)
        return output.getvalue()
