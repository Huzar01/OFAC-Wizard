#!/usr/bin/env python3
"""
A Python program to download and search the OFAC SDN List.
This updated version searches all fields whose header contains "name" to
ensure that user input is matched in a case‑insensitive and partial manner.

NOTE: Before using or modifying this script, check the OFAC/Treasury website
for the latest file URLs and any usage restrictions.
"""

import csv
import requests
import sys
from io import StringIO

# URL for the OFAC SDN list in CSV format.
# (Make sure this URL is current; if not, update it accordingly.)
SDN_LIST_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"

def download_sdn_list(url=SDN_LIST_URL):
    """Download the SDN list CSV data from the given URL."""
    print("Downloading OFAC SDN list from:")
    print("  ", url)
    try:
        response = requests.get(url)
        response.raise_for_status()
    except Exception as err:
        print("Error downloading SDN list:", err)
        sys.exit(1)
    response.encoding = "utf-8"
    return response.text

def parse_sdn_list(csv_text):
    """
    Parse the CSV text using Python's CSV module.
    Uses a CSV sniffer to try to detect the file's formatting.
    """
    try:
        sample = csv_text.splitlines()[0]
        dialect = csv.Sniffer().sniff(sample)
    except csv.Error:
        dialect = csv.excel  # fallback to default if detection fails
    reader = csv.DictReader(StringIO(csv_text), dialect=dialect)
    records = list(reader)
    print(f"Downloaded and parsed {len(records)} record(s).")
    return records

def search_sdn_list(records, query, category=None):
    """
    Search for records where any field with "name" in its header
    contains the query string (case-insensitive and partial match).

    If a category filter is provided (e.g. "entity", "vessel", etc.), then
    only records whose 'Type' (or 'Entity Type') field contains that substring
    will be returned.
    """
    results = []
    query = query.lower()
    for record in records:
        found_in_name = False
        # Look in any field whose header includes "name"
        for key, value in record.items():
            if value and "name" in key.lower():
                if query in value.lower():
                    found_in_name = True
                    break
        if found_in_name:
            if category:
                # Check the 'Type' or 'Entity Type' field for the category substring.
                rec_type = record.get("Type") or record.get("Entity Type") or ""
                if category.lower() in rec_type.lower():
                    results.append(record)
            else:
                results.append(record)
    return results

def print_record(record):
    """Print a single record in a formatted style."""
    print("-" * 40)
    for key, value in record.items():
        if value:
            print(f"{key}: {value}")

def main():
    csv_text = download_sdn_list()
    records = parse_sdn_list(csv_text)
    
    # Prompt for the search query.
    query = input("Enter search query (name): ").strip()
    if not query:
        print("No search query provided; exiting.")
        sys.exit(0)
    
    # Prompt for an optional category filter.
    category = input("Enter category (optional - e.g., individual, entity, vessel): ").strip()
    if not category:
        category = None

    print("\nSearching for records matching your query...")
    results = search_sdn_list(records, query, category)
    
    if not results:
        print("No matching records found.")
    else:
        print(f"Found {len(results)} matching record(s):\n")
        for rec in results:
            print_record(rec)

if __name__ == '__main__':
    main()
