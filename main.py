import re
import string
import requests
import xml.etree.ElementTree as ET
from flask import Flask, request, jsonify

app = Flask(__name__)

OFAC_URL = "https://www.treasury.gov/ofac/downloads/sdn.xml"
ofac_xml_data = None

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
    Normalize a string by replacing punctuation with spaces, converting to lower case,
    and collapsing whitespace.
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
    The list includes the official name and any alternate names from the <akaList>.
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
    Joins address parts and separates multiple addresses with " | ".
    """
    address_list = entry.find("sdn:addressList", ns)
    if address_list is None:
        return ""
    addresses = []
    for addr in address_list.findall("sdn:address", ns):
        parts = []
        for tag in ["address1", "address2", "city", "stateOrProvince", "postalCode", "country"]:
            elem = addr.find("sdn:" + tag, ns)
            if elem is not None and elem.text:
                parts.append(elem.text.strip())
        if parts:
            addresses.append("; ".join(parts))
    return " | ".join(addresses)

def extract_programs(entry, ns):
    """
    Extract programs from the <programList> element as a semicolon-separated string.
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
    Extract the sanction type from the <sdnType> element.
    """
    type_elem = entry.find("sdn:sdnType", ns)
    return type_elem.text.strip() if type_elem is not None and type_elem.text else ""

def search_sdn(xml_data, name_search):
    """
    Parse the XML and return a list of dictionaries for matching entries.
    An entry is included if any normalized name variant (official or AKA) contains the search term
    as a whole word.
    
    Each dictionary includes:
      "Name", "Address", "Type", "Program(s)", "List", "Score".
    """
    try:
        root = ET.fromstring(xml_data)
    except Exception as e:
        print("Error parsing XML:", e)
        return []
    
    ns = {}
    if root.tag.startswith("{"):
        ns_uri = root.tag.split("}")[0][1:]
        ns = {"sdn": ns_uri}
        entry_path = "sdn:sdnEntry"
    else:
        entry_path = "sdnEntry"

    results = []
    term_norm = normalize_name(name_search)
    pattern = re.compile(r'\b' + re.escape(term_norm) + r'\b')
    
    for entry in root.findall(entry_path, ns):
        variants = collect_name_variants(entry, ns)
        match = any(pattern.search(normalize_name(v)) for v in variants)
        if match:
            official = get_official_name(entry, ns)
            row = {
                "Name": official,
                "Address": extract_address(entry, ns),
                "Type": extract_type(entry, ns),
                "Program(s)": extract_programs(entry, ns),
                "List": "SDN",
                "Score": "100"
            }
            if official and row not in results:
                results.append(row)
    return results

@app.route("/search_concise", methods=["GET"])
def search_concise():
    name_query = request.args.get("name", "").strip()
    if not name_query:
        return jsonify({"error": "Missing required query parameter 'name'."}), 400
    results = search_sdn(ofac_xml_data, name_query)
    names = [entry["Name"] for entry in results]
    return jsonify({"count": len(names), "names": names})

@app.route("/search_full", methods=["GET"])
def search_full():
    name_query = request.args.get("name", "").strip()
    if not name_query:
        return jsonify({"error": "Missing required query parameter 'name'."}), 400
    results = search_sdn(ofac_xml_data, name_query)
    return jsonify({"count": len(results), "results": results})

@app.route("/reload", methods=["POST"])
def reload_database():
    global ofac_xml_data
    new_data = fetch_ofac_data(OFAC_URL)
    if new_data is None:
        return jsonify({"error": "Failed to reload OFAC database."}), 500
    ofac_xml_data = new_data
    return jsonify({"message": "OFAC database reloaded successfully."})

if __name__ == "__main__":
    print("Downloading OFAC database from", OFAC_URL)
    ofac_xml_data = fetch_ofac_data(OFAC_URL)
    if ofac_xml_data is None:
        print("Failed to load OFAC data; exiting.")
    else:
        app.run(host="0.0.0.0", port=5000)
