import re
import requests
import xml.etree.ElementTree as ET
import string

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

def normalize_name(text):
    """
    Normalize a name string by:
      - Converting to lower case.
      - Removing punctuation (commas, periods, hyphens).
      - Collapsing multiple spaces.
    """
    if not text:
        return ""
    # Replace punctuation with space.
    translator = str.maketrans(string.punctuation, " " * len(string.punctuation))
    text = text.translate(translator)
    # Convert to lower case and collapse whitespace.
    return re.sub(r'\s+', ' ', text.strip().lower())

def get_official_name(entry, ns):
    """
    Construct the official name from <firstName> and <lastName>.
    If <firstName> is missing, use <lastName> only.
    """
    last_elem = entry.find("sdn:lastName", ns)
    first_elem = entry.find("sdn:firstName", ns)
    last_name = last_elem.text.strip() if last_elem is not None and last_elem.text else ""
    first_name = first_elem.text.strip() if first_elem is not None and first_elem.text else ""
    return (first_name + " " + last_name).strip() if first_name else last_name

def collect_name_variants(entry, ns):
    """
    Return a list of name variants for an entry.
    The first element is the official name.
    Then include each alternate name from the akaList.
    """
    variants = []
    official = get_official_name(entry, ns)
    if official:
        variants.append(official)
    aka_list = entry.find("sdn:akaList", ns)
    if aka_list is not None:
        for aka in aka_list.findall("sdn:aka", ns):
            # Build aka name from firstName and lastName.
            aka_first = aka.find("sdn:firstName", ns)
            aka_last = aka.find("sdn:lastName", ns)
            aka_name = ""
            if aka_first is not None and aka_first.text:
                aka_name += aka_first.text.strip() + " "
            if aka_last is not None and aka_last.text:
                aka_name += aka_last.text.strip()
            aka_name = aka_name.strip()
            if aka_name:
                variants.append(aka_name)
    return variants

def search_sdn(xml_data, search_term):
    """
    Parse the XML and return a list of distinct official names (in original form)
    where the search_term appears as a whole word in any of the name variants.
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

    results = []
    # Compile regex with word boundaries based on normalized search term.
    term_lower = search_term.lower().strip()
    # The pattern will search for the term as a whole word.
    pattern = re.compile(r'\b' + re.escape(term_lower) + r'\b')

    for entry in root.findall(entry_path, ns):
        # Get all name variants.
        variants = collect_name_variants(entry, ns)
        # Normalize each variant.
        found = False
        for name in variants:
            norm = normalize_name(name)
            if pattern.search(norm):
                found = True
                break
        if found:
            official = get_official_name(entry, ns)
            # Add only if not already in the results.
            if official and official not in results:
                results.append(official)
    return results

def main():
    # URL for the current OFAC SDN XML file (update if necessary)
    url = "https://www.treasury.gov/ofac/downloads/sdn.xml"
    print("Downloading OFAC database from", url)
    xml_data = fetch_ofac_data(url)
    if xml_data is None:
        return

    # Loop until user exits.
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
            print()

if __name__ == "__main__":
    main()
