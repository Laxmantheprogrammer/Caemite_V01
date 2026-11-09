
"""
Caemite — Materials Project Data Collector
============================================

Retrieves all available material records from the
Materials Project Summary endpoint.

Collects:
    - material_id
    - formula_pretty
    - density
    - band_gap
    - formation_energy_per_atom
    - energy_above_hull
    - volume

Outputs:
    dataset/first_tester/materials.csv
    dataset/first_tester/missing_materials.csv
    dataset/first_tester/missing_summary.csv
    dataset/first_tester/metadata.json

Missing values are recorded as missing.
Zero is ALWAYS treated as a valid numerical value.
"""

import os
import csv
import json
import math

from pathlib import Path
from datetime import datetime, timezone

from mp_api.client import MPRester


# --------------------------------------------------
# 1. PATHS AND CONFIGURATION
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent
ENV_FILE = PROJECT_DIR / ".env"

OUTPUT_DIR = PROJECT_DIR / "dataset" / "first_tester"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------
# 2. LOAD API KEY
# --------------------------------------------------

def load_env_file(path):
    """Load simple KEY=VALUE entries from .env."""

    if not path.exists():
        return

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line or line.startswith("#"):
                continue

            if line.startswith("export "):
                line = line[7:].strip()

            if "=" not in line:
                continue

            key, value = line.split("=", 1)

            key = key.strip()
            value = value.strip().strip("\"'")

            os.environ.setdefault(key, value)


load_env_file(ENV_FILE)

API_KEY = os.environ.get("MP_API_KEY")

if not API_KEY:
    raise RuntimeError(
        "MP_API_KEY was not found. "
        "Check your project's .env file."
    )


# --------------------------------------------------
# 3. PROPERTY DEFINITIONS
# --------------------------------------------------

FIELDS = [
    "material_id",
    "formula_pretty",
    "density",
    "band_gap",
    "formation_energy_per_atom",
    "energy_above_hull",
    "volume",
]

PROPERTIES = [
    "density",
    "band_gap",
    "formation_energy_per_atom",
    "energy_above_hull",
    "volume",
]

UNITS = {
    "density": "g/cm^3",
    "band_gap": "eV",
    "formation_energy_per_atom": "eV/atom",
    "energy_above_hull": "eV/atom",
    "volume": "angstrom^3",
}


# --------------------------------------------------
# 4. MISSING VALUE DETECTION
# --------------------------------------------------

def is_missing(value):
    """
    Only missing values are classified as missing.

    None = missing
    NaN = missing
    0 = VALID
    0.0 = VALID
    """

    if value is None:
        return True

    if isinstance(value, float) and math.isnan(value):
        return True

    return False


# --------------------------------------------------
# 5. DATA COLLECTION
# --------------------------------------------------

def collect_data():

    print("=" * 60)
    print("CAEMITE — MATERIALS PROJECT DATA COLLECTION")
    print("=" * 60)

    print("\nConnecting to Materials Project...")

    with MPRester(
        API_KEY,
        use_document_model=False,
    ) as mpr:

        print("Connected.")
        print("Requesting all Summary endpoint records...")
        print("This may take some time.\n")

        docs = mpr.materials.summary.search(
            fields=FIELDS,
            num_chunks=None,
            chunk_size=1000,
        )

    print(f"Retrieved {len(docs):,} material records.")

    return docs


# --------------------------------------------------
# 6. DATA PROCESSING AND EXPORT
# --------------------------------------------------

def process_data(docs):

    materials_file = OUTPUT_DIR / "materials.csv"
    missing_file = OUTPUT_DIR / "missing_materials.csv"
    summary_file = OUTPUT_DIR / "missing_summary.csv"
    metadata_file = OUTPUT_DIR / "metadata.json"

    missing_counts = {
        prop: 0 for prop in PROPERTIES
    }

    materials_missing = 0

    print("\nProcessing records...")

    with (
        materials_file.open(
            "w", newline="", encoding="utf-8"
        ) as material_handle,

        missing_file.open(
            "w", newline="", encoding="utf-8"
        ) as missing_handle,
    ):

        material_writer = csv.DictWriter(
            material_handle,
            fieldnames=FIELDS,
        )

        missing_writer = csv.DictWriter(
            missing_handle,
            fieldnames=[
                "material_id",
                "formula_pretty",
                "missing_properties",
            ],
        )

        material_writer.writeheader()
        missing_writer.writeheader()

        for index, doc in enumerate(docs, start=1):

            # All requested fields are returned as dictionaries.
            row = {
                field: doc.get(field)
                for field in FIELDS
            }

            missing_properties = []

            for prop in PROPERTIES:

                value = row[prop]

                if is_missing(value):
                    missing_properties.append(prop)
                    missing_counts[prop] += 1

            # Write the complete material record.
            material_writer.writerow(row)

            # Record materials with missing properties.
            if missing_properties:

                materials_missing += 1

                missing_writer.writerow({
                    "material_id": row["material_id"],
                    "formula_pretty": row["formula_pretty"],
                    "missing_properties": ";".join(
                        missing_properties
                    ),
                })

            if index % 10000 == 0:
                print(
                    f"Processed {index:,} / {len(docs):,}"
                )

    # --------------------------------------------------
    # 7. MISSING VALUE SUMMARY
    # --------------------------------------------------

    with summary_file.open(
        "w", newline="", encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "property",
                "unit",
                "missing_count",
                "available_count",
                "missing_percentage",
            ],
        )

        writer.writeheader()

        total = len(docs)

        for prop in PROPERTIES:

            missing = missing_counts[prop]
            available = total - missing

            percentage = (
                (missing / total) * 100
                if total else 0
            )

            writer.writerow({
                "property": prop,
                "unit": UNITS[prop],
                "missing_count": missing,
                "available_count": available,
                "missing_percentage": round(
                    percentage, 4
                ),
            })

    # --------------------------------------------------
    # 8. METADATA
    # --------------------------------------------------

    metadata = {
        "source": "Materials Project",
        "endpoint": "materials.summary",
        "retrieved_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "total_material_records": len(docs),

        "properties": PROPERTIES,
        "units": UNITS,

        "missing_records": materials_missing,

        "missing_property_counts": missing_counts,

        "missing_values_policy": (
            "None and NaN are missing. "
            "Zero is a valid numerical value."
        ),
    }

    with metadata_file.open(
        "w", encoding="utf-8"
    ) as file:

        json.dump(
            metadata,
            file,
            indent=4,
        )

    # --------------------------------------------------
    # 9. FINAL REPORT
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("COLLECTION COMPLETED")
    print("=" * 60)

    print(f"\nTotal materials: {len(docs):,}")

    print("\nPROPERTY AVAILABILITY:")

    for prop in PROPERTIES:

        missing = missing_counts[prop]
        available = len(docs) - missing

        print(
            f"{prop:30s} "
            f"Available: {available:>9,} | "
            f"Missing: {missing:>9,}"
        )

    print(
        f"\nMaterials with at least one missing "
        f"property: {materials_missing:,}"
    )

    print("\nOUTPUT FILES:")

    print(f"Materials: {materials_file}")
    print(f"Missing records: {missing_file}")
    print(f"Missing summary: {summary_file}")
    print(f"Metadata: {metadata_file}")

    print("\nCaemite data collection finished.")


# --------------------------------------------------
# 10. MAIN
# --------------------------------------------------

def main():

    docs = collect_data()

    process_data(docs)


if __name__ == "__main__":
    main()

