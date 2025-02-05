import re
import requests
import xml.etree.ElementTree as ET

def fetch_ofac_data(url):
    """Download the OFAC XML data from the provided URL."""
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.content
        else:
            print("Error fetching data. Status code:", response.status_code)
            return None
    except Exception as e:
        print("Error fetching data:", e)
        return None

def search_sdn(xml_data, search_term):
    """
    Parse the XML and return a list of distinct official names (constructed from <firstName> and <lastName>)
    where the search_term appears as a whole word (case–insensitively) in either the official name or any AKA names.
    
    Only entries with <sdnType> of "Entity" or "Vessel" are considered.
    """
    try:
        root = ET.fromstring(xml_data)
    except Exception as e:
        print("Error parsing XML:", e)
        return []
    
    # Determine namespace if present.
    ns = {}
    if root.tag.startswith("{"):
        ns_uri = root.tag.split("}")[0][1:]
        ns = {"sdn": ns_uri}
        entry_path = "sdn:sdnEntry"
    else:
        entry_path = "sdnEntry"
    
    # Compile regex pattern for whole-word search.
    pattern = re.compile(r'\b' + re.escape(search_term) + r'\b', flags=re.IGNORECASE)
    
    results = []
    for entry in root.findall(entry_path, ns):
        # Only process if sdnType is "Entity" or "Vessel"
        sdn_type_elem = entry.find("sdn:sdnType", ns)
        if sdn_type_elem is None or not sdn_type_elem.text:
            continue
        sdn_type = sdn_type_elem.text.strip()
        if sdn_type not in ("Entity", "Vessel"):
            continue

        # Build the official name.
        last_elem = entry.find("sdn:lastName", ns)
        first_elem = entry.find("sdn:firstName", ns)
        last_name = last_elem.text.strip() if last_elem is not None and last_elem.text else ""
        first_name = first_elem.text.strip() if first_elem is not None and first_elem.text else ""
        # For entities, often only lastName is provided.
        full_name = (first_name + " " + last_name).strip() if first_name else last_name

        # Check for whole-word match in the official name.
        match = full_name and pattern.search(full_name)

        # Also check in any AKA names if not already matched.
        if not match:
            aka_list = entry.find("sdn:akaList", ns)
            if aka_list is not None:
                for aka in aka_list.findall("sdn:aka", ns):
                    aka_last = aka.find("sdn:lastName", ns)
                    aka_first = aka.find("sdn:firstName", ns)
                    aka_name = ""
                    if aka_first is not None and aka_first.text:
                        aka_name += aka_first.text.strip() + " "
                    if aka_last is not None and aka_last.text:
                        aka_name += aka_last.text.strip()
                    aka_name = aka_name.strip()
                    if aka_name and pattern.search(aka_name):
                        match = True
                        break

        if match and full_name and full_name not in results:
            results.append(full_name)
    return results

def main():
    # URL for the current OFAC SDN XML file (update if necessary)
    url = "https://www.treasury.gov/ofac/downloads/sdn.xml"
    print("Downloading OFAC database from", url)
    xml_data = fetch_ofac_data(url)
    if xml_data is None:
        return

    # Loop indefinitely until the user chooses to quit.
    while True:
        search_term = input("Enter search term (or 'exit' to quit): ").strip()
        if not search_term or search_term.lower() in ("exit", "quit"):
            print("Exiting.")
            break

        matching_names = search_sdn(xml_data, search_term)
        if not matching_names:
            print(f"No results found for: {search_term}\n")
        else:
            print(f"\n# Names (Total: {len(matching_names)}):")
            for name in matching_names:
                print(name)
            print()  # Blank line for readability

if __name__ == "__main__":
    main()
