
import csv
import json
import math

from pathlib import Path
from datetime import datetime, timezone

import pyarrow.parquet as pq


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

PROJECT_DIR = Path(__file__).resolve().parent

PARQUET_FILE = Path(
    "/home/laxma/mp_datasets/build/collections/summary/"
    "version=2026-09-28/"
    "group-1-ff975e74-part-0.zstd.parquet"
)

OUTPUT_DIR = PROJECT_DIR / "dataset" / "first_tester"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FIELDS = [
    "material_id",
    "formula_pretty",
    "density",
    "band_gap",
    "formation_energy_per_atom",
    "energy_above_hull",
    "volume",
]

PROPERTIES = FIELDS[2:]

UNITS = {
    "density": "g/cm^3",
    "band_gap": "eV",
    "formation_energy_per_atom": "eV/atom",
    "energy_above_hull": "eV/atom",
    "volume": "angstrom^3",
}


# --------------------------------------------------
# 2. MISSING VALUE DETECTION
# --------------------------------------------------

def is_missing(value):

    if value is None:
        return True

    try:
        return math.isnan(value)
    except (TypeError, ValueError):
        return False


# --------------------------------------------------
# 3. COLLECTION
# --------------------------------------------------

def collect_data():

    print("=" * 60)
    print("CAEMITE — MATERIALS PROJECT DATA COLLECTION")
    print("=" * 60)

    if not PARQUET_FILE.exists():
        raise FileNotFoundError(PARQUET_FILE)

    parquet = pq.ParquetFile(PARQUET_FILE)

    total = parquet.metadata.num_rows

    print(f"\nDataset records: {total:,}")
    print("Reading existing Parquet dataset...")
    
    materials_file = OUTPUT_DIR / "materials.csv"
    missing_file = OUTPUT_DIR / "missing_materials.csv"
    summary_file = OUTPUT_DIR / "missing_summary.csv"
    metadata_file = OUTPUT_DIR / "metadata.json"

    missing_counts = {
        prop: 0 for prop in PROPERTIES
    }

    materials_missing = 0
    processed = 0

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

        for batch in parquet.iter_batches(
            batch_size=5000,
            columns=FIELDS,
        ):

            columns = batch.to_pydict()

            for i in range(batch.num_rows):

                row = {
                    field: columns[field][i]
                    for field in FIELDS
                }

                missing_properties = []

                for prop in PROPERTIES:

                    if is_missing(row[prop]):
                        missing_properties.append(prop)
                        missing_counts[prop] += 1

                material_writer.writerow(row)

                if missing_properties:

                    materials_missing += 1

                    missing_writer.writerow({
                        "material_id": row["material_id"],
                        "formula_pretty": row["formula_pretty"],
                        "missing_properties": ";".join(
                            missing_properties
                        ),
                    })

            processed += batch.num_rows

            print(
                f"Processed {processed:,} / {total:,}",
                flush=True,
            )

    # --------------------------------------------------
    # 4. MISSING VALUE SUMMARY
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

        for prop in PROPERTIES:

            missing = missing_counts[prop]
            available = total - missing

            percentage = (
                missing / total * 100
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
    # 5. METADATA
    # --------------------------------------------------

    metadata = {
        "source": "Materials Project",
        "endpoint": "materials.summary",
        "dataset_version": "2026-09-28",
        "retrieved_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "total_material_records": total,
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

        json.dump(metadata, file, indent=4)

    # --------------------------------------------------
    # 6. FINAL REPORT
    # --------------------------------------------------

    print("\n" + "=" * 60)
    print("COLLECTION COMPLETED")
    print("=" * 60)

    print(f"\nTotal materials: {total:,}")

    for prop in PROPERTIES:

        missing = missing_counts[prop]

        print(
            f"{prop:30s} "
            f"Available: {total - missing:>9,} | "
            f"Missing: {missing:>9,}"
        )

    print(
        f"\nMaterials with missing properties: "
        f"{materials_missing:,}"
    )

    print("\nOUTPUT FILES")

    for path in [
        materials_file,
        missing_file,
        summary_file,
        metadata_file,
    ]:
        print(path)


# --------------------------------------------------
# 7. MAIN
# --------------------------------------------------

if __name__ == "__main__":
    collect_data()

