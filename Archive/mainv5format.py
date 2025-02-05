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
    Normalize a name string:
      - Replace punctuation with spaces.
      - Convert to lower case.
      - Collapse multiple spaces.
    """
    if not text:
        return ""
    translator = str.maketrans(string.punctuation, " " * len(string.punctuation))
    text = text.translate(translator)
    return re.sub(r'\s+', ' ', text.strip().lower())

def get_official_name(entry, ns):
    """
    Construct the official name from <firstName> and <lastName>.
    If <firstName> is missing, return <lastName> only.
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

def extract_address(entry, ns):
    """
    Extract and return a concatenated address string from the <addressList>.
    For each <address> element, join the values of address1, address2, city,
    stateOrProvince, postalCode, and country (if available). Multiple addresses are separated by " | ".
    """
    address_list = entry.find("sdn:addressList", ns)
    if address_list is None:
        return ""
    addresses = []
    for addr in address_list.findall("sdn:address", ns):
        parts = []
        # Try common address parts.
        for tag in ["address1", "address2", "city", "stateOrProvince", "postalCode", "country"]:
            elem = addr.find("sdn:" + tag, ns)
            if elem is not None and elem.text:
                parts.append(elem.text.strip())
        if parts:
            addresses.append("; ".join(parts))
    return " | ".join(addresses)

def extract_programs(entry, ns):
    """
    Extract a semicolon-separated list of programs from the <programList>.
    """
    prog_list = entry.find("sdn:programList", ns)
    if prog_list is None:
        return ""
    programs = []
    for prog in prog_list.findall("sdn:program", ns):
        if prog.text:
            programs.append(prog.text.strip())
    return "; ".join(programs)

def extract_type(entry, ns):
    """
    Extract the value of <sdnType> (e.g., "Individual", "Entity", "Vessel").
    """
    type_elem = entry.find("sdn:sdnType", ns)
    return type_elem.text.strip() if type_elem is not None and type_elem.text else ""

def search_sdn(xml_data, search_term):
    """
    Parse the XML and return a list of dictionaries with fields:
      "Name", "Address", "Type", "Program(s)", "List", "Score"
    The entry is included if the search term (as a whole word, after normalization)
    appears in any name variant (official or aka).
    """
    try:
        root = ET.fromstring(xml_data)
    except Exception as e:
        print("Error parsing XML:", e)
        return []
    
    # Handle namespace if present.
    ns = {}
    if root.tag.startswith("{"):
        ns_uri = root.tag.split("}")[0][1:]
        ns = {"sdn": ns_uri}
        entry_path = "sdn:sdnEntry"
    else:
        entry_path = "sdnEntry"

    results = []
    term_norm = normalize_name(search_term)
    pattern = re.compile(r'\b' + re.escape(term_norm) + r'\b')
    
    for entry in root.findall(entry_path, ns):
        # Build list of name variants.
        variants = collect_name_variants(entry, ns)
        match = False
        for name in variants:
            if pattern.search(normalize_name(name)):
                match = True
                break
        if match:
            official = get_official_name(entry, ns)
            # Build the dictionary with additional details.
            row = {
                "Name": official,
                "Address": extract_address(entry, ns),
                "Type": extract_type(entry, ns),
                "Program(s)": extract_programs(entry, ns),
                "List": "SDN",   # Hardcoded as in the web tool.
                "Score": "100"   # Hardcoded as in the web tool.
            }
            if official and row not in results:
                results.append(row)
    return results

def print_results(results):
    """
    Print the results in a table format.
    """
    # Define column widths (adjust as needed)
    col_widths = {
        "Name": 40,
        "Address": 60,
        "Type": 12,
        "Program(s)": 40,
        "List": 6,
        "Score": 6
    }
    header = "{:<{Name}}  {:<{Address}}  {:<{Type}}  {:<{Program(s)}}  {:<{List}}  {:<{Score}}".format(
        "Name", "Address", "Type", "Program(s)", "List", "Score", **col_widths)
    print(header)
    print("-" * len(header))
    for row in results:
        print("{:<{Name}}  {:<{Address}}  {:<{Type}}  {:<{Program(s)}}  {:<{List}}  {:<{Score}}".format(
            row["Name"],
            row["Address"],
            row["Type"],
            row["Program(s)"],
            row["List"],
            row["Score"],
            **col_widths
        ))

def main():
    # URL for the current OFAC SDN XML file (update if necessary)
    url = "https://www.treasury.gov/ofac/downloads/sdn.xml"
    print("Downloading OFAC database from", url)
    xml_data = fetch_ofac_data(url)
    if xml_data is None:
        return

    # Loop to prompt for search terms.
    while True:
        search_term = input("Enter search term (or 'exit' to quit): ").strip()
        if not search_term or search_term.lower() in ("exit", "quit"):
            print("Exiting.")
            break

        results = search_sdn(xml_data, search_term)
        if not results:
            print(f"No results found for: {search_term}\n")
        else:
            print(f"\n# Results (Total: {len(results)}):")
            print_results(results)
            print()

if __name__ == "__main__":
    main()
