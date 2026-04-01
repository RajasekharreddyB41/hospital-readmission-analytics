import os
import requests

RAW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "raw")
OUTPUT_FILE = os.path.join(RAW_DIR, "readmissions_raw.csv")

CMS_CSV_URL = (
    "https://data.cms.gov/provider-data/sites/default/files/resources/"
    "9n3s-kdb3/Hospital_Readmissions_Reduction_Program.csv"
)

def download_csv():
    print("Downloading CMS Hospital Readmissions dataset...")
    os.makedirs(RAW_DIR, exist_ok=True)
    try:
        response = requests.get(CMS_CSV_URL, timeout=60)
        response.raise_for_status()
        with open(OUTPUT_FILE, "wb") as f:
            f.write(response.content)
        size_kb = os.path.getsize(OUTPUT_FILE) / 1024
        print(f"Download complete! File size: {size_kb:.1f} KB")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Download failed: {e}")
        print("Manual: go to https://data.cms.gov/provider-data/dataset/9n3s-kdb3")
        print(f"Save CSV to: {OUTPUT_FILE}")
        return False

def verify_file():
    import csv
    with open(OUTPUT_FILE, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames or []
        rows = list(reader)
    print(f"\nRows    : {len(rows):,}")
    print(f"Columns : {len(headers)}")
    print("\nColumns found:")
    for h in headers:
        print(f"  {h}")

if __name__ == "__main__":
    success = download_csv()
    if success:
        verify_file()