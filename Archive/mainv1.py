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
    """Parse the XML and return a list of names where the search_term appears as a separate word
    in either the main name or any AKA names."""
    try:
        root = ET.fromstring(xml_data)
    except Exception as e:
        print("Error parsing XML:", e)
        return []
    
    # If the XML uses a namespace, extract it.
    ns = {}
    if root.tag.startswith("{"):
        ns_uri = root.tag.split("}")[0][1:]
        ns = {"sdn": ns_uri}
        entry_path = "sdn:sdnEntry"
    else:
        entry_path = "sdnEntry"

    # Compile a regex pattern to match the search term as a whole word.
    pattern = re.compile(r'\b' + re.escape(search_term) + r'\b', flags=re.IGNORECASE)
    
    results = []
    for entry in root.findall(entry_path, ns):
        # Get the main name (lastName and optionally firstName)
        last_name_elem = entry.find("sdn:lastName", ns)
        first_name_elem = entry.find("sdn:firstName", ns)
        main_name = last_name_elem.text.strip() if last_name_elem is not None and last_name_elem.text else ""
        first_name = first_name_elem.text.strip() if first_name_elem is not None and first_name_elem.text else ""
        full_name = (first_name + " " + main_name).strip() if first_name else main_name

        match = bool(pattern.search(full_name))
        
        # If not matched in the main name, search in any AKA names.
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
                    if pattern.search(aka_name):
                        match = True
                        break

        if match:
            results.append(full_name)
    return results

def main():
    # URL for the current OFAC SDN XML file (update if necessary)
    url = "https://www.treasury.gov/ofac/downloads/sdn.xml"
    print("Downloading OFAC database from", url)
    xml_data = fetch_ofac_data(url)
    if xml_data is None:
        return

    search_term = input("Enter search term: ").strip()
    if not search_term:
        print("No search term entered.")
        return

    matching_names = search_sdn(xml_data, search_term)
    if not matching_names:
        print("No results found for:", search_term)
    else:
        # Print the results in a concise table format.
        print("\n# Names:")
        for name in matching_names:
            print(name)

if __name__ == "__main__":
    main()
