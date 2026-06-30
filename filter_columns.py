"""
Filtra un CSV de AppsFlyer dejando solo las columnas necesarias para la app.
Uso: python3 filter_columns.py archivo.csv
Genera: archivo_filtered.csv (~20MB en vez de ~600MB)
"""
import csv
import sys
import os

COLUMNS = [
    "AppsFlyer ID",
    "Media Source",
    "Attributed Touch Time",
    "Install Time",
    "Contributor 1 Media Source",
    "Contributor 1 Touch Time",
    "Contributor 2 Media Source",
    "Contributor 2 Touch Time",
    "Contributor 3 Media Source",
    "Contributor 3 Touch Time",
]

def filter_csv(input_path):
    base, ext = os.path.splitext(input_path)
    output_path = f"{base}_filtered{ext}"

    with open(input_path, encoding="utf-8-sig") as fin, \
         open(output_path, "w", newline="", encoding="utf-8") as fout:

        reader = csv.DictReader(fin)
        missing = [c for c in COLUMNS if c not in reader.fieldnames]
        if missing:
            print(f"Advertencia: columnas no encontradas: {missing}")

        cols = [c for c in COLUMNS if c in reader.fieldnames]
        writer = csv.DictWriter(fout, fieldnames=cols)
        writer.writeheader()

        for i, row in enumerate(reader):
            writer.writerow({c: row[c] for c in cols})
            if i % 100_000 == 0 and i > 0:
                print(f"  {i:,} filas procesadas...")

    size_mb = os.path.getsize(output_path) / 1_048_576
    print(f"\nListo: {output_path}")
    print(f"Tamaño: {size_mb:.1f} MB")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 filter_columns.py archivo.csv")
        sys.exit(1)
    filter_csv(sys.argv[1])
